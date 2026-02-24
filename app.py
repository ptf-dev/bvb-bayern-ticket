#!/usr/bin/env python3
"""BVB Ticket Tracker - Flask Web App using Eventim API."""
import os, time, threading, requests, resend
from datetime import datetime
from flask import Flask, jsonify

app = Flask(__name__)

API_URL = "https://public-api.eventim.com/seatmap/api/public/availability/tixx-1001-619883"
SHOP_URL = "https://www.ticket-onlineshop.com/ols/bvb/de/profis/channel/shop/index/"
INTERVAL = 300  # 5 minutes
EMAIL = os.environ.get("BVB_EMAIL", "")
RESEND_KEY = os.environ.get("BVB_RESEND_KEY", "")

state = {"running": False, "status": "stopped", "logs": []}

def log(msg):
    entry = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    state["logs"] = state["logs"][-50:] + [entry]
    print(entry, flush=True)

def send(subject, html):
    if EMAIL and RESEND_KEY:
        try:
            resend.api_key = RESEND_KEY
            resend.Emails.send({"from": "onboarding@resend.dev", "to": EMAIL,
                "subject": subject, "html": html})
            log(f"Email sent to {EMAIL}")
        except Exception as e:
            log(f"Email failed: {e}")

def check_api():
    r = requests.get(API_URL, params={"a_affiliateId": "412"}, headers={
        "accept": "application/json",
        "origin": "https://www.ticket-onlineshop.com",
        "referer": "https://www.ticket-onlineshop.com/",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "x-version": "6.20.0",
    }, timeout=30)
    r.raise_for_status()
    data = r.json()
    seats = data.get("seats", [])
    ga = data.get("generalAdmissions", [])
    return seats, ga, data

def loop():
    while state["running"]:
        try:
            log("Checking API...")
            state["status"] = "checking"
            seats, ga, data = check_api()
            if seats or ga:
                count = len(seats) + len(ga)
                log(f"TICKETS FOUND! {count} available")
                state["status"] = "found"
                send("BVB Tickets Available!",
                     f"<h2>BVB vs Bayern tickets are available!</h2>"
                     f"<p>{len(seats)} seats, {len(ga)} GA sections</p>"
                     f"<p><a href='{SHOP_URL}'>Buy now</a></p>")
                for _ in range(60):
                    if not state["running"]: return
                    time.sleep(1)
                continue
            else:
                log("No tickets yet")
                state["status"] = "running"
        except Exception as e:
            log(f"Error: {e}")
            state["status"] = "running"
        for _ in range(INTERVAL):
            if not state["running"]: return
            time.sleep(1)

@app.route("/")
def index():
    return PAGE_HTML

@app.route("/api/status")
def api_status():
    return jsonify(state)

@app.route("/api/start", methods=["POST"])
def start():
    if not state["running"]:
        state["running"] = True
        state["status"] = "running"
        log("Started tracking")
        send("BVB Tracker Started", "<p>Tracking BVB vs Bayern tickets via API. Checking every 5 min.</p>")
        threading.Thread(target=loop, daemon=True).start()
    return jsonify(state)

@app.route("/api/stop", methods=["POST"])
def stop():
    state["running"] = False
    state["status"] = "stopped"
    log("Stopped")
    return jsonify(state)

PAGE_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BVB Ticket Tracker</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#1a1a1a;color:#ccc;font-family:Helvetica,Arial,sans-serif;display:flex;justify-content:center;padding:30px}
.c{max-width:500px;width:100%;text-align:center}
h1{color:#FDE100;font-size:24px;margin-bottom:4px}
.sub{color:#999;margin-bottom:20px}
#status{font-size:20px;font-weight:bold;margin:15px 0}
.stopped{color:#ff4444}.running{color:#FDE100}.found{color:#00ff00}.checking{color:#FDE100}
#log{background:#2a2a2a;border-radius:8px;padding:12px;font-family:Menlo,monospace;font-size:13px;
  text-align:left;height:300px;overflow-y:auto;margin:15px 0;white-space:pre-wrap}
button{background:#FDE100;color:#000;border:none;padding:12px 40px;font-size:16px;font-weight:bold;
  border-radius:6px;cursor:pointer}
button:hover{background:#e6cc00}
</style></head>
<body><div class="c">
<h1>BVB vs FC Bayern M&uuml;nchen</h1>
<p class="sub">Sa 28.02.2026 &middot; 18:30 &middot; SIGNAL IDUNA PARK</p>
<div id="status" class="stopped">Stopped</div>
<div id="log"></div>
<button id="btn" onclick="toggle()">Start</button>
</div>
<script>
const labels={stopped:"Stopped",running:"Running",checking:"Checking...",found:"TICKETS AVAILABLE!"};
function update(){
  fetch("/api/status").then(r=>r.json()).then(d=>{
    document.getElementById("status").textContent=labels[d.status]||d.status;
    document.getElementById("status").className=d.status;
    document.getElementById("log").textContent=d.logs.join("\\n");
    document.getElementById("btn").textContent=d.running?"Stop":"Start";
    var el=document.getElementById("log");el.scrollTop=el.scrollHeight;
  }).catch(()=>{});
}
function toggle(){
  var running=document.getElementById("btn").textContent==="Stop";
  fetch(running?"/api/stop":"/api/start",{method:"POST"}).then(()=>update());
}
setInterval(update,3000);update();
</script></body></html>"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
