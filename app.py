from flask import Flask, render_template, request, redirect, session
import sqlite3
import joblib
import pandas as pd
from datetime import datetime

app = Flask(__name__)
app.secret_key = "smartcity123"

# ---------------- LOAD MODEL ----------------
model = joblib.load(r"D:\DataAnalysis Code & datasets\Smart_City_transport_project\traffic_model.pkl")
scaler = joblib.load(r"D:\DataAnalysis Code & datasets\Smart_City_transport_project\scaler.pkl")
le_dict = joblib.load(r"D:\DataAnalysis Code & datasets\Smart_City_transport_project\encoders.pkl")

# ---------------- FEATURES (IMPORTANT) ----------------
features = [
 'distance_km',
 'travel_time_min',
 'avg_speed',
 'road_type',
 'vehicle_type',
 'hour',
 'is_weekend',
 'peak_hour',
 'rainfall',
 'weather_severity',
 'visibility',
 'congestion_index',
 'efficiency'
]

# ---------------- DATABASE INIT ----------------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

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

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        try:
            c.execute("INSERT INTO users(username,password) VALUES (?,?)",
                      (username, password))
            conn.commit()
            conn.close()
            return redirect('/')
        except:
            return "❌ Username already exists"

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route('/', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE username=? AND password=?",
                  (username, password))

        user = c.fetchone()
        conn.close()

        if user:
            session['user'] = username
            return redirect('/home')
        else:
            return "❌ Invalid Credentials"

    return render_template("login.html")

# ---------------- HOME ----------------
@app.route('/home')
def home():
    if 'user' not in session:
        return redirect('/')
    return render_template("home.html", user=session['user'])

# ---------------- MODEL FUNCTION ----------------
def smart_transport_system(input_data):

    input_df = pd.DataFrame([input_data])

    # feature engineering
    input_df['peak_hour'] = input_df['hour'].apply(lambda x: 1 if (8<=x<=11 or 17<=x<=21) else 0)
    input_df['congestion_index'] = input_df['travel_time_min'] / (input_df['distance_km'] + 1)
    input_df['efficiency'] = input_df['distance_km'] / (input_df['travel_time_min'] + 1)

    # encoding
    for col in le_dict:
        input_df[col] = le_dict[col].transform(input_df[col])

    # reorder columns
    input_df = input_df[features]

    # scaling
    input_scaled = scaler.transform(input_df)

    # prediction
    pred = model.predict(input_scaled)[0]

    return pred

# ---------------- CONGESTION ----------------
def congestion_level(speed):
    if speed < 20:
        return "High Congestion"
    elif speed < 40:
        return "Medium Congestion"
    else:
        return "Low Congestion"

# ---------------- ROUTE ENGINE ----------------
def best_route(level):
    if "High" in level:
        return "Use Bypass Route"
    elif "Medium" in level:
        return "Use Alternate Route"
    else:
        return "Main Route is Best"

# ---------------- PREDICT ----------------
@app.route('/predict', methods=['GET','POST'])
def predict():

    result = None
    route = None
    congestion = None

    if request.method == 'POST':

        input_data = {
            'distance_km': float(request.form['distance_km']),
            'travel_time_min': float(request.form['travel_time_min']),
            'avg_speed': float(request.form['avg_speed']),
            'road_type': request.form['road_type'],
            'vehicle_type': request.form['vehicle_type'],
            'hour': int(request.form['hour']),
            'is_weekend': int(request.form['is_weekend']),
            'rainfall': float(request.form['rainfall']),
            'weather_severity': int(request.form['weather_severity']),
            'visibility': float(request.form['visibility']),
            'source': request.form['source'],
            'destination': request.form['destination']
        }

        pred = smart_transport_system(input_data)

        label_map = {
            0: "Low Traffic",
            1: "Medium Traffic",
            2: "High Traffic"
        }

        result = label_map[pred]

        speed = input_data['avg_speed']
        congestion = congestion_level(speed)
        route = best_route(result)

        # save history
        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        c.execute("""
            INSERT INTO history(user,traffic,route,time)
            VALUES (?,?,?,?)
        """, (session['user'], result, route, str(datetime.now())))

        conn.commit()
        conn.close()

    return render_template("predict.html",
                           result=result,
                           route=route,
                           congestion=congestion)

# ---------------- MAP ----------------
@app.route('/map')
def map():
    if 'user' not in session:
        return redirect('/')
    return render_template("map.html")

# ---------------- HISTORY ----------------
@app.route('/history')
def history():
    if 'user' not in session:
        return redirect('/')

    conn = sqlite3.connect("database.db")
    df = pd.read_sql_query("SELECT * FROM history WHERE user=?",
                           conn, params=(session['user'],))
    conn.close()

    return render_template("history.html", data=df.values)

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)