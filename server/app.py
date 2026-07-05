import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask, Response, abort, jsonify, render_template, request

import charts
import db
import weather

TZ = ZoneInfo("Europe/Rome")

app = Flask(__name__)
db.init_db()

SENSOR_FIELDS = ("temperature", "humidity", "gas", "lux", "alarm_state")


@app.post("/api/sensors")
def receive_sensor_data():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Body JSON mancante o non valido"}), 400

    missing = [f for f in SENSOR_FIELDS if f not in data]
    if missing:
        return jsonify({"error": f"Campi mancanti: {', '.join(missing)}"}), 400

    try:
        db.insert_sensor_reading(
            temperature=float(data["temperature"]),
            humidity=float(data["humidity"]),
            gas=int(data["gas"]),
            lux=float(data["lux"]),
            alarm_state=int(data["alarm_state"]),
        )
    except (TypeError, ValueError):
        return jsonify({"error": "Valori non numerici nei campi"}), 400

    return jsonify({"status": "ok"}), 201


def _format_local(iso_timestamp):
    return datetime.fromisoformat(iso_timestamp).astimezone(TZ).strftime("%H:%M")


@app.get("/kindle")
def kindle():
    sensors = db.get_readings("sensor_readings", "today")
    weather_rows = db.get_readings("weather_readings", "today")
    last = sensors[-1] if sensors else None
    last_weather = weather_rows[-1] if weather_rows else None
    return render_template(
        "kindle.html",
        last=last,
        last_time=_format_local(last["timestamp"]) if last else None,
        weather=last_weather,
        weather_time=_format_local(last_weather["timestamp"]) if last_weather else None,
        generated_at=datetime.now(TZ).strftime("%d/%m/%Y %H:%M"),
        metrics=list(charts.METRICS),
        cache_ts=int(time.time()),
    )


@app.get("/chart/<metric>.png")
def chart_png(metric):
    if metric not in charts.METRICS:
        abort(404)
    png = charts.render_chart(metric)
    return Response(
        png,
        mimetype="image/png",
        # il browser del Kindle tende a cachare le immagini: forziamo il refresh
        headers={"Cache-Control": "no-store"},
    )


if __name__ == "__main__":
    # In debug il reloader di Flask esegue app.py due volte (processo padre + figlio):
    # lo scheduler va avviato solo nel figlio, dove WERKZEUG_RUN_MAIN è settato
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        weather.start_scheduler()
    # Sul Mac la porta 5000 è occupata da AirPlay Receiver: usare PORT=5001
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
