from flask import Flask, jsonify, render_template_string, request, Response
import json
import os
import time
import cv2
import numpy as np
import RPi.GPIO as GPIO
import requests

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
# HUMAN DETECTION (HOG + SVM, built into OpenCV)
# -------------------------------------
hog = cv2.HOGDescriptor()
hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())


def detect_humans(frame):
    """Detect humans using HOG + SVM (no external models required)."""
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
# FIRE & SMOKE DETECTION
# -------------------------------------
prev_gray = None
last_fire_alert = 0
last_smoke_alert = 0
last_human_alert = 0
ALERT_COOLDOWN = 5  # seconds between repeated camera alerts


def detect_fire(frame):
    """Detect fire using HSV color thresholding."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Tuned fire color range (orange/yellow/red)
    lower = np.array([0, 120, 150])
    upper = np.array([35, 255, 255])

    mask = cv2.inRange(hsv, lower, upper)
    mask = cv2.GaussianBlur(mask, (15, 15), 0)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 500:  # filter tiny noise
            x, y, w, h = cv2.boundingRect(cnt)
            boxes.append((x, y, x + w, y + h))

    return boxes


def detect_smoke(frame):
    """Detect smoke from motion + low saturation and high brightness."""
    global prev_gray

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (21, 21), 0)

    if prev_gray is None:
        prev_gray = blurred
        return []

    # Motion detection
    diff = cv2.absdiff(prev_gray, blurred)
    prev_gray = blurred

    _, thresh = cv2.threshold(diff, 15, 255, cv2.THRESH_BINARY)

    # Smoke color mask: low saturation, mid-high value
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower = np.array([0, 0, 120])
    upper = np.array([180, 80, 255])
    smoke_mask = cv2.inRange(hsv, lower, upper)

    combined = cv2.bitwise_and(thresh, smoke_mask)

    contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 800:  # avoid small noise
            x, y, w, h = cv2.boundingRect(cnt)
            boxes.append((x, y, x + w, y + h))

    return boxes


# -------------------------------------
# SERVO CONTROL (Dummy safe pin)
# -------------------------------------
GPIO.setmode(GPIO.BCM)
SERVO_PIN = 17  # CHANGE TO REAL PIN WHEN KNOWN

try:
    GPIO.setup(SERVO_PIN, GPIO.OUT)
    pwm = GPIO.PWM(SERVO_PIN, 50)
    pwm.start(7.5)
    servo_enabled = True
except Exception as e:
    print("Servo disabled (dummy mode):", e)
    servo_enabled = False

servo_position = 7.5


def move_servo(delta):
    global servo_position
    if not servo_enabled:
        print("Dummy servo mode - ignoring move")
        return

    servo_position = max(5.0, min(10.0, servo_position + delta))
    pwm.ChangeDutyCycle(servo_position)


def servo_left():
    move_servo(-0.5)


def servo_right():
    move_servo(+0.5)


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
# ALERT LOG
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
# CAMERA + AI STREAM
# -------------------------------------
def generate_frames():
    global last_fire_alert, last_smoke_alert, last_human_alert

    while True:
        ret, frame = camera.read()
        if not ret:
            continue

        # HUMAN / FIRE / SMOKE detection
        humans = detect_humans(frame)
        fire_boxes = detect_fire(frame)
        smoke_boxes = detect_smoke(frame)

        human_detected = len(humans) > 0
        fire_detected = len(fire_boxes) > 0
        smoke_detected = len(smoke_boxes) > 0

        # Draw humans (green)
        for (x1, y1, x2, y2) in humans:
            cv2.rectangle(frame, (x1, y1), (x2, y2),
                          (0, 255, 0), 2)
            cv2.putText(frame, "HUMAN",
                        (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 255, 0), 2)

        # Draw fire (orange)
        for (x1, y1, x2, y2) in fire_boxes:
            cv2.rectangle(frame, (x1, y1), (x2, y2),
                          (0, 140, 255), 2)
            cv2.putText(frame, "FIRE",
                        (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 140, 255), 2)

        # Draw smoke (light gray)
        for (x1, y1, x2, y2) in smoke_boxes:
            cv2.rectangle(frame, (x1, y1), (x2, y2),
                          (200, 200, 200), 2)
            cv2.putText(frame, "SMOKE",
                        (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (200, 200, 200), 2)

        now = time.time()

        # Throttled alert logging
        if human_detected and now - last_human_alert > ALERT_COOLDOWN:
            last_human_alert = now
            try:
                requests.get("http://127.0.0.1:8080/log_alert?msg=HUMAN_DETECTED_CAMERA")
            except:
                pass

        if fire_detected and now - last_fire_alert > ALERT_COOLDOWN:
            last_fire_alert = now
            try:
                requests.get("http://127.0.0.1:8080/log_alert?msg=FIRE_DETECTED_CAMERA")
            except:
                pass

        if smoke_detected and now - last_smoke_alert > ALERT_COOLDOWN:
            last_smoke_alert = now
            try:
                requests.get("http://127.0.0.1:8080/log_alert?msg=SMOKE_DETECTED_CAMERA")
            except:
                pass

        # Encode frame for MJPEG stream
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
# HTML TEMPLATES
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
<a class="button" href="/camera">AI Camera (Human / Fire / Smoke)</a>

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
    document.getElementById("dist_mq3").innerHTML = "Gas Distance: " + (d.DIST_MQ3 || 0);
    document.getElementById("dist_temp").innerHTML = "Temp Distance: " + (d.DIST_TEMP || 0);

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

<h1>🎥 AI Camera (Human / Fire / Smoke)</h1>
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