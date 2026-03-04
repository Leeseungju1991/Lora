from __future__ import annotations

import threading
import time
from flask import Flask, render_template_string, redirect, url_for

from lora_sim.spi_bus import SPIBus
from lora_sim.sx1272 import AirChannel, SX1272, Mode
from gateway import Gateway, GatewayDB

app = Flask(__name__)

# 공유 객체(데모)
air = AirChannel()
db = GatewayDB("gateway.sqlite3")
db.init()
gateway = Gateway(air, db)

# (옵션) 웹앱만 켜도 DB가 갱신되도록 background poller 실행
def poller() -> None:
    while True:
        gateway.process_once()
        time.sleep(0.2)

t = threading.Thread(target=poller, daemon=True)
t.start()

TEMPLATE = """
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8"/>
  <title>LoRa Gateway Demo</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; }
    nav a { margin-right: 12px; }
    table { border-collapse: collapse; width: 100%; margin-top: 12px; }
    th, td { border: 1px solid #ddd; padding: 8px; font-size: 14px; }
    th { background: #f6f6f6; text-align: left; }
    code { background: #f3f3f3; padding: 2px 4px; border-radius: 6px; }
  </style>
</head>
<body>
  <h1>LoRa Gateway Demo</h1>
  <nav>
    <a href="{{ url_for('devices') }}">Devices</a>
    <a href="{{ url_for('packets') }}">Packets</a>
  </nav>
  <hr/>
  {{ body|safe }}
</body>
</html>
"""

@app.get("/")
def root():
    return redirect(url_for("devices"))

@app.get("/devices")
def devices():
    rows = db.list_devices()
    body = """<h2>Devices</h2>
    <table>
      <thead><tr><th>device_id</th><th>first_seen</th><th>last_seen</th></tr></thead>
      <tbody>
    """
    for r in rows:
        body += f"<tr><td><code>{r['device_id']}</code></td><td>{r['first_seen']}</td><td>{r['last_seen']}</td></tr>"
    body += "</tbody></table>"
    return render_template_string(TEMPLATE, body=body)

@app.get("/packets")
def packets():
    rows = db.list_packets(200)
    body = """<h2>Packets (최근 200개)</h2>
    <table>
      <thead><tr><th>id</th><th>ts</th><th>device_id</th><th>payload_hex</th></tr></thead>
      <tbody>
    """
    for r in rows:
        body += f"<tr><td>{r['id']}</td><td>{r['ts']}</td><td><code>{r['device_id']}</code></td><td><code>{r['payload_hex']}</code></td></tr>"
    body += "</tbody></table>"
    return render_template_string(TEMPLATE, body=body)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
