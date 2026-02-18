#!/usr/bin/env python3
"""Headless BVB ticket checker for VPS deployment (no GUI)."""
import subprocess, json, sys, os, time, resend

URL = "https://www.ticket-onlineshop.com/ols/bvb/de/profis/channel/shop/index/"
MATCH = "Bayern"
NO_TICKETS = "Derzeit keine Tickets"
INTERVAL = 3600
CHECKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_check.py")

EMAIL = os.environ.get("BVB_EMAIL", "")
RESEND_KEY = os.environ.get("BVB_RESEND_KEY", "")
BVB_ACCOUNT = os.environ.get("BVB_ACCOUNT_EMAIL", "")
BVB_PW = os.environ.get("BVB_ACCOUNT_PW", "")

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

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
        if NO_TICKETS in text:
            return "no_tickets"
        if "Tickets ab" in text:
            return "available"
    if "Aktuell sind keine Tickets" in text:
        return "no_tickets"
    if "Tickets ab" in text or "Ticket kaufen" in text:
        return "available"
    if "Hinweise" in text:
        return "no_tickets"
    return "unknown"

if __name__ == "__main__":
    log("Started tracking (headless)")
    send("BVB Tracker Started", "<p>Tracking BVB vs Bayern tickets (VPS). You'll be notified when available.</p>")

    while True:
        try:
            log("Checking...")
            result = check_page()
            if result == "captcha":
                log("CAPTCHA/empty - retrying next cycle")
            elif result == "no_tickets":
                log("No tickets yet")
            elif result == "available":
                log("TICKETS FOUND!")
                send("BVB Tickets Available!", f"<h2>BVB vs Bayern tickets are available!</h2><p><a href='{URL}'>Buy now</a></p>")
                break
            else:
                log("Page changed - check manually")
                send("BVB Tracker - Check Manually", f"<p>Page content changed unexpectedly. <a href='{URL}'>Check now</a></p>")
        except Exception as e:
            log(f"Error: {e}")
        time.sleep(INTERVAL)
