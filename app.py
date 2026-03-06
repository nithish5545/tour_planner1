import sqlite3
from flask import Flask, render_template, request, redirect, session, url_for
from flask import Flask
import os

app = Flask(__name__, static_folder="static", template_folder="templates")

app = Flask(__name__)
app.secret_key = "supersecretkey"


# ================= DATABASE =================
def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


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
        image_url TEXT
    );

    CREATE TABLE IF NOT EXISTS trips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        destination TEXT,
        days INTEGER,
        total_cost REAL
    );
    """)

    conn.commit()
    conn.close()


init_db()


# ================= HOME =================
@app.route("/")
def home():
    return redirect("/login")


# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO users (name,email,password)
            VALUES (?,?,?)
        """, (
            request.form["name"],
            request.form["email"],
            request.form["password"]
        ))

        conn.commit()
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

        if user and user["password"] == request.form["password"]:
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

    return render_template("dashboard.html",
                           name=session["user_name"])


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

    return render_template("budget.html",
                           destinations=destinations)


# ================= DESTINATION =================
@app.route("/destination/<int:id>", methods=["GET", "POST"])
def destination(id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM destinations WHERE id=?",
                   (id,))
    place = cursor.fetchone()

    if not place:
        conn.close()
        return "Destination not found"

    if request.method == "POST":
        days = int(request.form["days"])
        total = (place["hotel_cost"] +
                 place["food_cost"] +
                 place["sightseeing_cost"]) * days

        cursor.execute("""
            INSERT INTO trips (user_id,destination,days,total_cost)
            VALUES (?,?,?,?)
        """, (
            session["user_id"],
            place["name"],
            days,
            total
        ))

        conn.commit()
        trip_id = cursor.lastrowid
        conn.close()

        return redirect(url_for("booking_success",
                                trip_id=trip_id))

    conn.close()
    return render_template("destination.html",
                           place=place)


# ================= BOOKING SUCCESS =================
@app.route("/booking-success/<int:trip_id>")
def booking_success(trip_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trips WHERE id=?",
                   (trip_id,))
    trip = cursor.fetchone()
    conn.close()

    if not trip:
        return "Booking not found"

    return render_template("booking_success.html",
                           trip=trip)


# ================= CAR RENTAL =================
@app.route("/car-rental", methods=["GET", "POST"])
def car_rental():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        days = int(request.form["days"])
        total = days * 2000

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO trips (user_id,destination,days,total_cost)
            VALUES (?,?,?,?)
        """, (
            session["user_id"],
            "Car Rental",
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

    return render_template("saved_trips.html",
                           trips=trips)


# ================= ADMIN =================
@app.route("/admin")
def admin_dashboard():
    if "user_id" not in session or not session.get("is_admin"):
        return "Access Denied"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM destinations")
    destinations = cursor.fetchall()
    conn.close()

    return render_template("admin_dashboard.html",
                           destinations=destinations)


@app.route("/admin/add", methods=["GET", "POST"])
def admin_add():
    if "user_id" not in session or not session.get("is_admin"):
        return "Access Denied"

    if request.method == "POST":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO destinations
            (state,name,hotel_cost,food_cost,sightseeing_cost,image_url)
            VALUES (?,?,?,?,?,?)
        """, (
            request.form["state"],
            request.form["name"],
            request.form["hotel"],
            request.form["food"],
            request.form["sight"],
            request.form["image"]
        ))
        conn.commit()
        conn.close()
        return redirect("/admin")

    return render_template("add_destination.html")


@app.route("/admin/delete/<int:id>")
def admin_delete(id):
    if "user_id" not in session or not session.get("is_admin"):
        return "Access Denied"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM destinations WHERE id=?",
                   (id,))
    conn.commit()
    conn.close()

    return redirect("/admin")


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

