from flask import Flask, jsonify, render_template_string, request, Response
import json
import os
import time
import cv2
import numpy as np
import requests
from gpiozero import Servo
from time import sleep

# -------------------------------------
# PATHS
# -------------------------------------
JSON_FILE = "/tmp/mq3_latest.json"
ALERT_LOG = "/home/rpi/disaster_alert_log.json"

# Ensure alert log exists
if not os.path.exists(ALERT_LOG):
    with open(ALERT_LOG, "w") as f:
        json.dump([], f)

app = Flask(__name__)

# -------------------------------------
# CAMERA SETUP
# -------------------------------------
camera = cv2.VideoCapture(0)

# -------------------------------------
# HUMAN DETECTION (HOG)
# -------------------------------------
hog = cv2.HOGDescriptor()
hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

def detect_humans(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    rects, weights = hog.detectMultiScale(
        gray,
        winStride=(8, 8),
        padding=(8, 8),
        scale=1.05
    )

    humans = []
    for (x, y, w, h) in rects:
        humans.append((x, y, x + w, y + h))

    return humans


# -------------------------------------
# SMOKE & FIRE DETECTION REMOVED
# -------------------------------------
# (Everything commented or disabled by request)

# -------------------------------------
# SERVO CONTROL — Microstep + Zero Jitter
# -------------------------------------
try:
    # Safe pulse window for SG90 & MG90S clones (prevents jitter)
    servo = Servo(13, min_pulse_width=0.0006, max_pulse_width=0.0023)
    servo_position = 0.0  # range: -1 to +1
    servo_enabled = True
except Exception as e:
    print("Servo disabled:", e)
    servo_enabled = False
    servo = None


def move_servo(delta):
    """
    Move servo in small microsteps, then disable PWM entirely.
    This eliminates jitter on all small hobby servos.
    """
    global servo_position

    if not servo_enabled:
        return

    target = max(-1, min(1, servo_position + delta))

    steps = 5
    step_size = (target - servo_position) / steps

    for _ in range(steps):
        servo_position += step_size
        servo.value = servo_position
        sleep(0.05)  # smooth movement

    servo.value = None  # disable PWM → zero jitter


def servo_left():
    move_servo(-0.1)


def servo_right():
    move_servo(+0.1)


# -------------------------------------
# SENSOR DATA
# -------------------------------------
def read_data():
    try:
        with open(JSON_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


# -------------------------------------
# ALERT LOG SYSTEM
# -------------------------------------
def read_alerts():
    try:
        with open(ALERT_LOG, "r") as f:
            return json.load(f)
    except:
        return []


def write_alert(message):
    alerts = read_alerts()
    alerts.append({
        "message": message,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })
    with open(ALERT_LOG, "w") as f:
        json.dump(alerts, f, indent=2)


@app.route("/log_alert")
def log_alert():
    msg = request.args.get("msg", "Unknown alert")
    write_alert(msg)
    return "OK"


@app.route("/alerts")
def alerts():
    return jsonify(read_alerts())


# -------------------------------------
# CAMERA STREAM — HUMAN ONLY
# -------------------------------------
ALERT_COOLDOWN = 5
last_human_alert = 0

def generate_frames():
    global last_human_alert

    while True:
        ret, frame = camera.read()
        if not ret:
            continue

        humans = detect_humans(frame)
        human_detected = len(humans) > 0

        for (x1, y1, x2, y2) in humans:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, "HUMAN", (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 255, 0), 2)

        now = time.time()

        if human_detected and now - last_human_alert > ALERT_COOLDOWN:
            last_human_alert = now
            requests.get("http://127.0.0.1:8080/log_alert?msg=HUMAN_DETECTED_CAMERA")

        _, buffer = cv2.imencode(".jpg", frame)
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" +
               buffer.tobytes() + b"\r\n")


@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


# -------------------------------------
# SERVO ROUTES
# -------------------------------------
@app.route("/servo/left")
def cam_left():
    servo_left()
    return "OK"


@app.route("/servo/right")
def cam_right():
    servo_right()
    return "OK"


# -------------------------------------
# DASHBOARD ROUTES
# -------------------------------------
@app.route("/")
def dashboard():
    return render_template_string(PAGE_HTML)


@app.route("/data")
def data():
    return jsonify(read_data())


@app.route("/camera")
def camera_page():
    return render_template_string(CAMERA_HTML)


# -------------------------------------
# HTML Templates
# -------------------------------------
PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Disaster Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body { background:#111; color:#eee; font-family:Arial; padding:20px; }
.card { background:#222; padding:15px; border-radius:8px; margin-bottom:20px; }
.button { background:#444; padding:10px 20px; color:white; text-decoration:none; border-radius:8px; }
.button:hover { background:#666; }
</style>
</head>
<body>

<h1>🔥 Disaster Monitor Dashboard</h1>
<a class="button" href="/camera">AI Camera (Human Detection)</a>

<div class="card">
  <h2>Live Readings</h2>
  <p id="gas">Gas: --</p>
  <p id="temp">Temp: --</p>
  <p id="dist_mq3">Gas Distance: --</p>
  <p id="dist_temp">Temp Distance: --</p>
  <p id="status" style="font-weight:bold;color:orange;">Status: Unknown</p>
</div>

<div class="card">
  <h2>Alerts</h2>
  <div id="alertLog" style="height:200px;overflow-y:auto;"></div>
</div>

<div class="card"><h2>Gas</h2><canvas id="gasChart"></canvas></div>
<div class="card"><h2>Temperature</h2><canvas id="tempChart"></canvas></div>

<script>
let gasChart, tempChart;
let prevDanger = false;

function setup(){
    gasChart = new Chart(document.getElementById("gasChart"), {
        type:"line",
        data:{ labels:[], datasets:[{ label:"MQ3", data:[] }] },
        options:{ animation:false }
    });
    tempChart = new Chart(document.getElementById("tempChart"), {
        type:"line",
        data:{ labels:[], datasets:[{ label:"Temp", data:[] }] },
        options:{ animation:false }
    });
}
setup();

async function loop(){
    let d = await (await fetch("/data")).json();

    let gas = d.MQ3 || 0;
    let temp = d.TEMP || 0;

    document.getElementById("gas").innerHTML = "Gas: " + gas;
    document.getElementById("temp").innerHTML = "Temp: " + temp;

    let danger = gas >= 350 || temp >= 60;

    if(danger && !prevDanger)
        fetch("/log_alert?msg=THRESHOLD_DANGER_SENSOR");

    prevDanger = danger;

    document.getElementById("status").innerHTML = danger ? "DANGER" : "Normal";
    document.getElementById("status").style.color = danger ? "red" : "lightgreen";

    let t = new Date().toLocaleTimeString();
    gasChart.data.labels.push(t);
    gasChart.data.datasets[0].data.push(gas);
    tempChart.data.labels.push(t);
    tempChart.data.datasets[0].data.push(temp);

    if(gasChart.data.labels.length > 30){
        gasChart.data.labels.shift();
        gasChart.data.datasets[0].data.shift();
        tempChart.data.labels.shift();
        tempChart.data.datasets[0].data.shift();
    }

    gasChart.update();
    tempChart.update();

    let alerts = await (await fetch("/alerts")).json();
    let html = "";
    for (let a of alerts.slice().reverse()){
        html += `<p>🔥 <b>${a.timestamp}</b> — ${a.message}</p>`;
    }
    document.getElementById("alertLog").innerHTML = html;
}
setInterval(loop, 1000);
</script>

</body>
</html>
"""

CAMERA_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Camera</title>
<style>
body { background:#111; color:#eee; font-family:Arial; text-align:center; padding:20px; }
.button { padding:15px 30px; background:#444; color:white; border-radius:8px; font-size:20px; }
.button:hover { background:#666; }
</style>
</head>
<body>

<h1>🎥 AI Camera (Human Detection)</h1>
<img src="/video_feed" style="width:80%;border:3px solid #444;border-radius:10px;"/>

<br><br>
<button class="button" onclick="left()">⬅ LEFT</button>
<button class="button" onclick="right()">RIGHT ➡</button>

<script>
function left(){ fetch("/servo/left"); }
function right(){ fetch("/servo/right"); }
</script>

</body>
</html>
"""

# -------------------------------------
# RUN SERVER
# -------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)
