#!/usr/bin/env python3
"""Check BVB ticket page using Chrome remote debugging with auto-login."""
import subprocess, json, time, requests, websocket, sys

URL = "https://www.ticket-onlineshop.com/ols/bvb/de/profis/channel/shop/index/"
OAUTH_URL = "https://www.ticket-onlineshop.com/ols/bvb/de/profis/channel/shop/oauth/start?target_uri=https://www.ticket-onlineshop.com/ols/bvb/de/profis/channel/shop/index"
PORT = 9222
import platform, shutil

def find_chrome():
    if platform.system() == "Darwin":
        return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    for p in ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"]:
        found = shutil.which(p)
        if found:
            return found
    return "google-chrome"

CHROME = find_chrome()
USER_DIR = "/tmp/bvb-chrome-debug"

def js(ws, expr):
    ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate",
        "params": {"expression": expr, "awaitPromise": True}}))
    r = json.loads(ws.recv())
    return r.get("result", {}).get("result", {}).get("value", "")

def wait_for_tab(keyword, exclude=None, timeout=120):
    for _ in range(timeout // 2):
        try:
            tabs = requests.get(f"http://localhost:{PORT}/json", timeout=3).json()
            for t in tabs:
                u = t.get("url", "")
                if keyword in u and (not exclude or exclude not in u):
                    return t
        except:
            pass
        time.sleep(2)
    return None

def get_page_text(bvb_email="", bvb_pw=""):
    subprocess.run(["pkill", "-f", f"remote-debugging-port={PORT}"], capture_output=True)
    time.sleep(1)

    # If we have credentials, go to OAuth login first
    start_url = OAUTH_URL if (bvb_email and bvb_pw) else URL

    proc = subprocess.Popen([
        CHROME, "--incognito",
        f"--remote-debugging-port={PORT}",
        "--remote-allow-origins=*",
        f"--user-data-dir={USER_DIR}", start_url
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    text = ""
    try:
        if bvb_email and bvb_pw:
            # Wait for OAuth/login page to load (past queue)
            time.sleep(20)
            tab = wait_for_tab("ticket-onlineshop", exclude="queue", timeout=60)
            if tab:
                ws = websocket.create_connection(tab["webSocketDebuggerUrl"])
                # Fill IMA (member number) and Kennwort (password) fields
                js(ws, f"""
                    function fillForm(doc) {{
                        var inputs = doc.querySelectorAll('input');
                        var filled = false;
                        for (var i of inputs) {{
                            var n = (i.name || '').toLowerCase();
                            var id = (i.id || '').toLowerCase();
                            var ph = (i.placeholder || '').toLowerCase();
                            var label = '';
                            if (i.id) {{ var lb = doc.querySelector('label[for=\"'+i.id+'\"]'); if (lb) label = lb.textContent.toLowerCase(); }}
                            if (n.includes('ima') || id.includes('ima') || ph.includes('ima') || label.includes('ima') || i.type === 'email' || n === 'email' || n === 'username' || id === 'email' || id === 'username' || ph.includes('mail')) {{
                                i.value = '{bvb_email}';
                                i.dispatchEvent(new Event('input', {{bubbles:true}}));
                                i.dispatchEvent(new Event('change', {{bubbles:true}}));
                                filled = true;
                            }}
                            if (n.includes('kennwort') || id.includes('kennwort') || ph.includes('kennwort') || label.includes('kennwort') || i.type === 'password' || n === 'password' || id === 'password') {{
                                i.value = '{bvb_pw}';
                                i.dispatchEvent(new Event('input', {{bubbles:true}}));
                                i.dispatchEvent(new Event('change', {{bubbles:true}}));
                                filled = true;
                            }}
                        }}
                        return filled;
                    }}
                    var done = fillForm(document);
                    if (!done) {{
                        var frames = document.querySelectorAll('iframe');
                        for (var f of frames) {{
                            try {{ fillForm(f.contentDocument); }} catch(e) {{}}
                        }}
                    }}
                """)
                time.sleep(1)
                js(ws, """
                    function clickSubmit(doc) {{
                        var btn = doc.querySelector('button[type=submit], input[type=submit]');
                        if (!btn) btn = doc.querySelector('form button');
                        if (btn) {{ btn.click(); return true; }}
                        return false;
                    }}
                    if (!clickSubmit(document)) {{
                        var frames = document.querySelectorAll('iframe');
                        for (var f of frames) {{
                            try {{ if (clickSubmit(f.contentDocument)) break; }} catch(e) {{}}
                        }}
                    }}
                """)
                ws.close()
                # Wait for redirect back to ticket page after login
                time.sleep(20)

        # Now read the main ticket page
        tab = wait_for_tab("ticket-onlineshop", exclude="queue", timeout=60)
        if tab:
            ws = websocket.create_connection(tab["webSocketDebuggerUrl"])
            text = js(ws, "document.body.innerText")
            ws.close()
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except: proc.kill()
    return text

if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else ""
    pw = sys.argv[2] if len(sys.argv) > 2 else ""
    t = get_page_text(email, pw)
    # Print just the result
    print(json.dumps({"text": t}))
