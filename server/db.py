import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "sensors.db"

PERIOD_DELTAS = {
    "today": timedelta(days=1),
    "week": timedelta(weeks=1),
    "month": timedelta(days=30),
}


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            temperature REAL,
            humidity REAL,
            gas INTEGER,
            lux REAL,
            alarm_state INTEGER
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS weather_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            temperature REAL,
            humidity REAL,
            description TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def insert_sensor_reading(temperature, humidity, gas, lux, alarm_state, timestamp=None):
    timestamp = timestamp or datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO sensor_readings (timestamp, temperature, humidity, gas, lux, alarm_state)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (timestamp, temperature, humidity, gas, lux, alarm_state),
    )
    conn.commit()
    conn.close()


def insert_weather_reading(temperature, humidity, description, timestamp=None):
    timestamp = timestamp or datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO weather_readings (timestamp, temperature, humidity, description)
        VALUES (?, ?, ?, ?)
        """,
        (timestamp, temperature, humidity, description),
    )
    conn.commit()
    conn.close()


def get_readings(table, period="today"):
    if table not in ("sensor_readings", "weather_readings"):
        raise ValueError(f"Tabella sconosciuta: {table}")
    if period not in PERIOD_DELTAS:
        raise ValueError(f"Periodo sconosciuto: {period}")

    since = (datetime.now(timezone.utc) - PERIOD_DELTAS[period]).isoformat()
    conn = get_connection()
    rows = conn.execute(
        f"SELECT * FROM {table} WHERE timestamp >= ? ORDER BY timestamp ASC",
        (since,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
