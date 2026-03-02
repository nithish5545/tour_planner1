import os
import sqlite3
from flask import Flask, render_template, request, redirect, session, url_for

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


# Auto initialize DB on startup
init_db()

# ================= ROUTES =================

@app.route("/")
def home():
    return redirect("/login")


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


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    return render_template("dashboard.html",
                           name=session["user_name"])


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


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# IMPORTANT: DO NOT add app.run(debug=True)
