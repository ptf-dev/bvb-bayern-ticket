FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends wget xvfb xauth \
    && wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && (apt-get install -y --no-install-recommends /tmp/chrome.deb || apt-get install -fy --no-install-recommends) \
    && rm -f /tmp/chrome.deb && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY browser_check.py app.py ./

EXPOSE 5000

CMD Xvfb :99 -screen 0 1280x720x24 -nolisten tcp & export DISPLAY=:99 && python3 app.py
