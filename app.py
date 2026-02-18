#!/usr/bin/env python3
"""BVB Ticket Tracker - Flask Web App."""
import subprocess, json, sys, os, time, threading, resend
from datetime import datetime
from flask import Flask, jsonify, Response

app = Flask(__name__)

URL = "https://www.ticket-onlineshop.com/ols/bvb/de/profis/channel/shop/index/"
MATCH = "Bayern"
NO_TICKETS = "Derzeit keine Tickets"
INTERVAL = 3600
CHECKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_check.py")

EMAIL = os.environ.get("BVB_EMAIL", "")
RESEND_KEY = os.environ.get("BVB_RESEND_KEY", "")
BVB_ACCOUNT = os.environ.get("BVB_ACCOUNT_EMAIL", "")
BVB_PW = os.environ.get("BVB_ACCOUNT_PW", "")

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

def check_page():
    result = subprocess.run(
        [sys.executable, CHECKER, BVB_ACCOUNT, BVB_PW],
        capture_output=True, text=True, timeout=180
    )
    data = json.loads(result.stdout)
    text = data["text"]
    if not text or "not a robot" in text.lower():
        return "captcha"
    if MATCH in text:
        if NO_TICKETS in text: return "no_tickets"
        if "Tickets ab" in text: return "available"
    if "Aktuell sind keine Tickets" in text: return "no_tickets"
    if "Tickets ab" in text or "Ticket kaufen" in text: return "available"
    if "Hinweise" in text: return "no_tickets"
    return "unknown"

def loop():
    while state["running"]:
        try:
            log("Checking...")
            state["status"] = "checking"
            result = check_page()
            if result == "captcha":
                log("CAPTCHA/empty - retrying next cycle")
                state["status"] = "running"
            elif result == "no_tickets":
                log("No tickets yet")
                state["status"] = "running"
            elif result == "available":
                log("TICKETS FOUND!")
                state["status"] = "found"
                send("BVB Tickets Available!",
                     f"<h2>BVB vs Bayern tickets are available!</h2><p><a href='{URL}'>Buy now</a></p>")
                state["running"] = False
                return
            else:
                log("Page changed - check manually")
                state["status"] = "running"
                send("BVB Tracker - Check Manually",
                     f"<p>Page content changed. <a href='{URL}'>Check now</a></p>")
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
        send("BVB Tracker Started", "<p>Tracking BVB vs Bayern tickets. You'll be notified when available.</p>")
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
