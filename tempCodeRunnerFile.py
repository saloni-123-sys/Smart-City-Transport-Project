from flask import Flask, render_template, request, redirect, session
import sqlite3
import joblib
import pandas as pd
from datetime import datetime

app = Flask(__name__)
app.secret_key = "smartcity123"


model = joblib.load(r"D:\DataAnalysis Code & datasets\Smart_City_transport_project\traffic_model.pkl")
scaler = joblib.load(r"D:\DataAnalysis Code & datasets\Smart_City_transport_project\scaler.pkl")
le_dict = joblib.load(r"D:\DataAnalysis Code & datasets\Smart_City_transport_project\encoders.pkl")

# ---------------- DB ----------------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS history(
            id INTEGER PRIMARY KEY,
            user TEXT,
            traffic TEXT,
            route TEXT,
            time TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------------- LOGIN ----------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # simple auth (you can upgrade later)
        if username == "admin" and password == "1234":
            session['user'] = username
            return redirect('/home')
        else:
            return "❌ Invalid Login"

    return render_template("login.html")

# ---------------- HOME ----------------
@app.route('/home')
def home():
    if 'user' not in session:
        return redirect('/')
    return render_template("home.html", user=session['user'])

# ---------------- CONGESTION LOGIC ----------------
def congestion_level(speed):
    if speed < 20:
        return "🔴 High Congestion"
    elif speed < 40:
        return "🟡 Medium Congestion"
    else:
        return "🟢 Low Congestion"

# ---------------- ROUTE SUGGESTION ----------------
def best_route(traffic):
    if traffic == "🔴 High Congestion":
        return "Use Bypass Route 🚧"
    elif traffic == "🟡 Medium Congestion":
        return "Use Alternate Road 🛣️"
    else:
        return "Main Route is Best 🚗"

# ---------------- PREDICT ----------------
@app.route('/predict', methods=['GET','POST'])
def predict():

    result = None
    route = None
    congestion = None

    if request.method == 'POST':

        distance = float(request.form['distance'])
        time = float(request.form['time'])

        speed = distance / (time + 1)

        pred = model.predict([[distance, time, speed]])[0]

        if pred == 2:
            result = "🔴 High Traffic"
        elif pred == 1:
            result = "🟡 Medium Traffic"
        else:
            result = "🟢 Low Traffic"

        congestion = congestion_level(speed)
        route = best_route(congestion)

        # SAVE HISTORY
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO history(user,traffic,route,time) VALUES (?,?,?,?)",
                  (session['user'], result, route, str(datetime.now())))
        conn.commit()
        conn.close()

    return render_template("predict.html",
                           result=result,
                           route=route,
                           congestion=congestion)

# ---------------- MAP ----------------
@app.route('/map')
def map():
    return render_template("map.html")

# ---------------- HISTORY ----------------
@app.route('/history')
def history():
    conn = sqlite3.connect("database.db")
    df = pd.read_sql_query("SELECT * FROM history", conn)
    conn.close()
    return render_template("history.html", data=df.values)

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True)