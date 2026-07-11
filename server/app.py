import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask, Response, abort, jsonify, render_template, request

import charts
import db
import weather
import window_alert

TZ = ZoneInfo("Europe/Rome")

app = Flask(__name__)
db.init_db()

SENSOR_FIELDS = ("temperature", "humidity", "gas", "lux", "alarm_state")


def _gas_alarm_just_triggered(alarm_state):
    """True se questo è il primo 1 dopo uno 0 (o il primissimo dato): evita
    di rimandare la notifica ad ogni lettura finché l'allarme resta attivo."""
    if alarm_state != 1:
        return False
    previous = db.get_latest_readings("sensor_readings", 2)
    return len(previous) < 2 or previous[1]["alarm_state"] != 1


@app.post("/api/sensors")
def receive_sensor_data():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Body JSON mancante o non valido"}), 400

    missing = [f for f in SENSOR_FIELDS if f not in data]
    if missing:
        return jsonify({"error": f"Campi mancanti: {', '.join(missing)}"}), 400

    try:
        alarm_state = int(data["alarm_state"])
        db.insert_sensor_reading(
            temperature=float(data["temperature"]),
            humidity=float(data["humidity"]),
            gas=int(data["gas"]),
            lux=float(data["lux"]),
            alarm_state=alarm_state,
        )
    except (TypeError, ValueError):
        return jsonify({"error": "Valori non numerici nei campi"}), 400

    if _gas_alarm_just_triggered(alarm_state):
        window_alert.send_telegram_message("🚨 Allarme gas rilevato!")

    window_alert.check_and_notify()

    return jsonify({"status": "ok"}), 201


def _downsample(rows, max_points=500):
    """Riduce i punti per non appesantire Chart.js sui periodi lunghi."""
    step = max(1, len(rows) // max_points)
    return rows[::step]


@app.get("/api/data")
def api_data():
    period = request.args.get("period", "today")
    if period not in db.PERIOD_DELTAS:
        return jsonify({"error": f"Periodo non valido: {period}"}), 400
    return jsonify(
        {
            "sensors": _downsample(db.get_readings("sensor_readings", period)),
            "weather": _downsample(db.get_readings("weather_readings", period)),
            # pollini: sempre max giornaliero degli ultimi 15 giorni,
            # indipendente dal periodo selezionato
            "pollen": db.get_daily_pollen(),
        }
    )


@app.get("/api/latest")
def api_latest():
    limit = request.args.get("limit", 15, type=int)
    return jsonify(
        {
            "sensors": db.get_latest_readings("sensor_readings", limit),
            "weather": db.get_latest_readings("weather_readings", limit),
        }
    )


@app.get("/dashboard")
def dashboard():
    return render_template("dashboard.html")


def _format_local(iso_timestamp):
    return datetime.fromisoformat(iso_timestamp).astimezone(TZ).strftime("%H:%M")


@app.get("/kindle")
def kindle():
    sensors = db.get_readings("sensor_readings", "today")
    weather_rows = db.get_readings("weather_readings", "today")
    pollen_rows = db.get_readings("pollen_readings", "today")
    last = sensors[-1] if sensors else None
    last_weather = weather_rows[-1] if weather_rows else None
    last_pollen = pollen_rows[-1] if pollen_rows else None
    return render_template(
        "kindle.html",
        last=last,
        last_time=_format_local(last["timestamp"]) if last else None,
        weather=last_weather,
        weather_time=_format_local(last_weather["timestamp"]) if last_weather else None,
        pollen=last_pollen,
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
    # FLASK_DEBUG=0 nel container Docker; in sviluppo il default è debug attivo
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    # In debug il reloader di Flask esegue app.py due volte (processo padre + figlio):
    # lo scheduler va avviato solo nel figlio, dove WERKZEUG_RUN_MAIN è settato
    if not debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        weather.start_scheduler()
    # Sul Mac la porta 5000 è occupata da AirPlay Receiver: usare PORT=5001
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=debug)
