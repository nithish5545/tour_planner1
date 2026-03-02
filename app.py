from flask import Flask, render_template, request, redirect, session, jsonify, send_file
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from io import BytesIO
from reportlab.pdfgen import canvas
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")


# ================= DATABASE ============
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# ================= INIT DATABASE =================
@app.route("/init-db")
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        is_admin INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS destinations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        state TEXT,
        name TEXT,
        hotel_cost REAL,
        food_cost REAL,
        sightseeing_cost REAL,
        image_url TEXT,
        lat REAL,
        lon REAL
    );

    CREATE TABLE IF NOT EXISTS trips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        destination TEXT,
        days INTEGER,
        total_cost REAL
    );
    """)

    # Auto insert default destinations if empty
    cursor.execute("SELECT COUNT(*) FROM destinations")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
        INSERT INTO destinations
        (state,name,hotel_cost,food_cost,sightseeing_cost,image_url,lat,lon)
        VALUES (?,?,?,?,?,?,?,?)
        """, [
            ("Tamil Nadu","Ooty",2500,1000,1500,
             "https://images.unsplash.com/photo-1507525428034-b723cf961d3e",11.4064,76.6932),
            ("Tamil Nadu","Kodaikanal",2200,900,1300,
             "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee",10.2381,77.4892),
            ("Kerala","Munnar",2400,1100,1400,
             "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429",10.0889,77.0595),
            ("Kerala","Alleppey",2600,1200,1600,
             "https://images.unsplash.com/photo-1500534623283-312aade485b7",9.4981,76.3388)
        ])

    conn.commit()
    conn.close()
    return "Database initialized successfully!"


# ================= HOME =================
@app.route("/")
def home():
    if "user_id" in session:
        return redirect("/dashboard")
    return redirect("/login")


# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (name,email,password,is_admin) VALUES (?,?,?,?)",
                (
                    request.form["name"],
                    request.form["email"],
                    generate_password_hash(request.form["password"]),
                    0
                )
            )
            conn.commit()
        except sqlite3.IntegrityError:
            return "Email already exists"

        conn.close()
        return redirect("/login")

    return render_template("register.html")


# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email=?",
                       (request.form["email"],))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], request.form["password"]):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["is_admin"] = user["is_admin"]
            return redirect("/dashboard")

        return "Invalid Credentials"

    return render_template("login.html")


# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM trips WHERE user_id=?",
                   (session["user_id"],))
    total = cursor.fetchone()[0]
    conn.close()

    return render_template("dashboard.html",
                           name=session["user_name"],
                           total_trips=total)


# ================= BUDGET PAGE =================
@app.route("/budget")
def budget():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM destinations")
    destinations = cursor.fetchall()
    conn.close()

    return render_template("budget.html", destinations=destinations)


# ================= DESTINATION =================
@app.route("/destination/<int:id>")
def destination(id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM destinations WHERE id=?", (id,))
    data = cursor.fetchone()
    conn.close()

    if not data:
        return "Destination not found"

    return render_template("destination.html", destination=data)


# ================= SAVE TRIP =================
@app.route("/save-trip", methods=["POST"])
def save_trip():
    if "user_id" not in session:
        return jsonify({"error": "Login required"})

    data = request.get_json()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO trips (user_id,destination,days,total_cost)
        VALUES (?,?,?,?)
    """, (
        session["user_id"],
        data["destination"],
        data["days"],
        data["total"]
    ))
    conn.commit()
    trip_id = cursor.lastrowid
    conn.close()

    return jsonify({"trip_id": trip_id})


# ================= CAR RENTAL =================
@app.route("/car-rental", methods=["GET", "POST"])
def car_rental():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        car_type = request.form["car_type"]
        days = int(request.form["days"])

        prices = {"Hatchback": 2000, "Sedan": 3000, "SUV": 5000}
        total = prices.get(car_type, 2000) * days

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO trips (user_id,destination,days,total_cost)
            VALUES (?,?,?,?)
        """, (
            session["user_id"],
            f"Car Rental - {car_type}",
            days,
            total
        ))
        conn.commit()
        conn.close()

        return render_template("car_rental.html",
                               result=True,
                               total=total)

    return render_template("car_rental.html")


# ================= SAVED TRIPS =================
@app.route("/saved-trips")
def saved_trips():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trips WHERE user_id=?",
                   (session["user_id"],))
    trips = cursor.fetchall()
    conn.close()

    return render_template("saved_trips.html", trips=trips)


# ================= DOWNLOAD RECEIPT =================
@app.route("/download-receipt/<int:trip_id>")
def download_receipt(trip_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trips WHERE id=?", (trip_id,))
    trip = cursor.fetchone()
    conn.close()

    if not trip:
        return "Trip not found"

    buffer = BytesIO()
    p = canvas.Canvas(buffer)

    p.drawString(100, 800, "Tour Planner Receipt")
    p.drawString(100, 780, f"Destination: {trip['destination']}")
    p.drawString(100, 760, f"Days: {trip['days']}")
    p.drawString(100, 740, f"Total Cost: ₹{trip['total_cost']}")

    p.save()
    buffer.seek(0)

    return send_file(buffer,
                     as_attachment=True,
                     download_name="receipt.pdf",
                     mimetype="application/pdf")


# ================= ADMIN =================
@app.route("/admin")
def admin():
    if session.get("is_admin") != 1:
        return "Access Denied"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM destinations")
    destinations = cursor.fetchall()
    conn.close()

    return render_template("admin_dashboard.html",
                           destinations=destinations)


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run()
