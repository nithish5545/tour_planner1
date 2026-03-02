from flask import Flask, render_template, request, redirect, session, jsonify, send_file
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

load_dotenv()

app = Flask(__name__)

# ---------------- SECURITY ----------------
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

# ---------------- DATABASE ----------------
import os

def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("mysql.railway.internal"),
        user=os.environ.get("root"),
        password=os.environ.get("qlKFHEAjmmlMtBFWiYpNgEFHzqmJpMoj"),
        database=os.environ.get("railway"),
        port=int(os.environ.get("3306"))
    )

# ---------------- HOME ----------------
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect('/dashboard')
    return redirect('/login')

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO users (name,email,password) VALUES (%s,%s,%s)",
            (
                request.form['name'],
                request.form['email'],
                generate_password_hash(request.form['password'])
            )
        )

        conn.commit()
        conn.close()
        return redirect('/login')

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE email=%s",
                       (request.form['email'],))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], request.form['password']):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['is_admin'] = user['is_admin']
            return redirect('/dashboard')

        return "Invalid Credentials"

    return render_template("login.html")

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM destinations LIMIT 6")
    destinations = cursor.fetchall()

    conn.close()

    return render_template("dashboard.html",
                           name=session['user_name'],
                           destinations=destinations)

# ---------------- DOWNLOAD RECEIPT ----------------
@app.route('/download-receipt/<int:trip_id>')
def download_receipt(trip_id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM trips WHERE id=%s AND user_id=%s",
                   (trip_id, session['user_id']))
    trip = cursor.fetchone()
    conn.close()

    if not trip:
        return "Trip not found"

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    elements = []

    styles = getSampleStyleSheet()

    elements.append(Paragraph("Tour Planner Receipt", styles['Heading1']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Destination: {trip['destination']}", styles['Normal']))
    elements.append(Paragraph(f"Days: {trip['days']}", styles['Normal']))
    elements.append(Paragraph(f"Total: ₹{trip['total_cost']}", styles['Normal']))

    doc.build(elements)
    buffer.seek(0)

    return send_file(buffer,
                     as_attachment=True,
                     download_name="receipt.pdf",
                     mimetype='application/pdf')

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')
@app.route("/init-db")
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # USERS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100),
        email VARCHAR(100) UNIQUE,
        password VARCHAR(255),
        is_admin TINYINT(1) DEFAULT 0,
        profile_image VARCHAR(255)
    )
    """)

    # DESTINATIONS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS destinations (
        id INT AUTO_INCREMENT PRIMARY KEY,
        state VARCHAR(100),
        name VARCHAR(100),
        hotel_cost INT,
        food_cost INT,
        sightseeing_cost INT,
        image_url TEXT,
        lat FLOAT,
        lon FLOAT
    )
    """)

    # TRIPS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trips (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        destination VARCHAR(100),
        days INT,
        total_cost FLOAT
    )
    """)

    conn.commit()
    conn.close()

    return "Database Initialized Successfully!"
if __name__ == "__main__":
    app.run()