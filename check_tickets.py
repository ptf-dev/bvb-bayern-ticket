#!/usr/bin/env python3
import subprocess, threading, resend, tkinter as tk, os, sys, json, time
from datetime import datetime

URL = "https://www.ticket-onlineshop.com/ols/bvb/de/profis/channel/shop/index/"
MATCH = "Bayern"
NO_TICKETS = "Derzeit keine Tickets"
INTERVAL = 3600
CHECKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_check.py")

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BVB vs Bayern Ticket Tracker")
        self.root.configure(bg="#1a1a1a")
        self.running = False

        tk.Label(self.root, text="BVB vs FC Bayern München", font=("Helvetica", 18, "bold"),
                 fg="#FDE100", bg="#1a1a1a").pack(pady=(15,0))
        tk.Label(self.root, text="Sa 28.02.2026 · 18:30 · SIGNAL IDUNA PARK",
                 fg="#999", bg="#1a1a1a").pack()

        f = tk.Frame(self.root, bg="#1a1a1a")
        f.pack(pady=10)
        tk.Label(f, text="Email:", fg="#999", bg="#1a1a1a").grid(row=0, column=0, sticky="e")
        self.email_entry = tk.Entry(f, width=30, bg="#2a2a2a", fg="#ccc", insertbackground="#ccc")
        self.email_entry.grid(row=0, column=1, padx=5)
        self.email_entry.insert(0, os.environ.get("BVB_EMAIL", ""))
        tk.Label(f, text="Resend API Key:", fg="#999", bg="#1a1a1a").grid(row=1, column=0, sticky="e")
        self.key_entry = tk.Entry(f, width=30, show="*", bg="#2a2a2a", fg="#ccc", insertbackground="#ccc")
        self.key_entry.grid(row=1, column=1, padx=5, pady=3)
        self.key_entry.insert(0, os.environ.get("BVB_RESEND_KEY", ""))

        tk.Label(f, text="", bg="#1a1a1a").grid(row=2, column=0, pady=5)
        tk.Label(f, text="BVB IMA/Email:", fg="#999", bg="#1a1a1a").grid(row=3, column=0, sticky="e")
        self.bvb_email = tk.Entry(f, width=30, bg="#2a2a2a", fg="#ccc", insertbackground="#ccc")
        self.bvb_email.grid(row=3, column=1, padx=5)
        self.bvb_email.insert(0, os.environ.get("BVB_ACCOUNT_EMAIL", ""))
        tk.Label(f, text="BVB Password:", fg="#999", bg="#1a1a1a").grid(row=4, column=0, sticky="e")
        self.bvb_pw = tk.Entry(f, width=30, show="*", bg="#2a2a2a", fg="#ccc", insertbackground="#ccc")
        self.bvb_pw.grid(row=4, column=1, padx=5, pady=3)
        self.bvb_pw.insert(0, os.environ.get("BVB_ACCOUNT_PW", ""))

        self.status = tk.Label(self.root, text="Stopped", font=("Helvetica", 14),
                               fg="#ff4444", bg="#1a1a1a")
        self.status.pack(pady=10)

        self.log = tk.Text(self.root, height=10, width=50, bg="#2a2a2a", fg="#ccc",
                           font=("Menlo", 11), state="disabled", borderwidth=0)
        self.log.pack(padx=15)

        self.btn = tk.Button(self.root, text="Start", font=("Helvetica", 13, "bold"),
                             bg="#FDE100", fg="#000", width=20, command=self.toggle)
        self.btn.pack(pady=15)

        self.root.mainloop()

    def log_msg(self, msg):
        self.log.config(state="normal")
        self.log.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def send(self, subject, html):
        email = self.email_entry.get().strip()
        key = self.key_entry.get().strip()
        if email and key:
            try:
                resend.api_key = key
                resend.Emails.send({"from": "onboarding@resend.dev", "to": email,
                    "subject": subject, "html": html})
                self.log_msg(f"Email sent to {email}")
            except Exception as e:
                self.log_msg(f"Email failed: {e}")

    def toggle(self):
        self.running = not self.running
        if self.running:
            self.btn.config(text="Stop")
            self.status.config(text="Checking...", fg="#FDE100")
            self.log_msg("Started tracking")
            self.send("BVB Tracker Started", "<p>Tracking BVB vs Bayern tickets. You'll be notified when available.</p>")
            threading.Thread(target=self.loop, daemon=True).start()
        else:
            self.btn.config(text="Start")
            self.status.config(text="Stopped", fg="#ff4444")
            self.log_msg("Stopped")

    def check_page(self):
        bvb_email = self.bvb_email.get().strip()
        bvb_pw = self.bvb_pw.get().strip()
        result = subprocess.run(
            [sys.executable, CHECKER, bvb_email, bvb_pw],
            capture_output=True, text=True, timeout=180
        )
        data = json.loads(result.stdout)
        text = data["text"]

        if not text or "not a robot" in text.lower():
            return "captcha"
        # Check for Bayern match specifically
        if MATCH in text:
            if NO_TICKETS in text:
                return "no_tickets"
            if "Tickets ab" in text:
                return "available"
        # Fallback: check general "no tickets" message
        if "Aktuell sind keine Tickets" in text:
            return "no_tickets"
        if "Tickets ab" in text or "Ticket kaufen" in text:
            return "available"
        if "Hinweise" in text:
            return "no_tickets"  # page loaded but no ticket sales
        return "unknown"

    def loop(self):
        while self.running:
            try:
                self.root.after(0, self.log_msg, "Checking...")
                result = self.check_page()
                if result == "captcha":
                    self.root.after(0, self.log_msg, "CAPTCHA/empty - solve it in browser next time")
                elif result == "no_match":
                    self.root.after(0, self.log_msg, "Match not found on page")
                elif result == "no_tickets":
                    self.root.after(0, self.log_msg, "No tickets yet")
                elif result == "available":
                    self.root.after(0, self.found)
                    return
                else:
                    self.root.after(0, self.log_msg, "Page changed - check manually")
            except Exception as e:
                self.root.after(0, self.log_msg, f"Error: {e}")
            for _ in range(INTERVAL):
                if not self.running:
                    return
                time.sleep(1)

    def found(self):
        self.status.config(text="TICKETS AVAILABLE!", fg="#00ff00")
        self.btn.config(text="Start")
        self.running = False
        self.log_msg("TICKETS FOUND!")
        subprocess.run(["osascript", "-e",
            'display notification "BVB vs Bayern tickets available!" with title "BVB Tickets!" sound name "Glass"'])
        self.send("BVB Tickets Available!", f"<h2>BVB vs Bayern tickets are available!</h2><p><a href='{URL}'>Buy now</a></p>")

App()
