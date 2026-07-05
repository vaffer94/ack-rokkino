import os

from flask import Flask, jsonify, request

import db

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


if __name__ == "__main__":
    # Sul Mac la porta 5000 è occupata da AirPlay Receiver: usare PORT=5001
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
