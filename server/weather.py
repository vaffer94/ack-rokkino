"""Client Open-Meteo + job periodico che salva in weather_readings.

Open-Meteo è gratuita e senza API key. Punto vicino a Milano zona Bocconi.
"""
from datetime import datetime, timezone

import requests
from apscheduler.schedulers.background import BackgroundScheduler

import db

LAT = 45.404
LON = 9.188
FETCH_INTERVAL_MINUTES = 10

API_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

# specie di polline fornite da Open-Meteo (dati CAMS, copertura europea)
# chiave API -> colonna DB
POLLEN_FIELDS = {
    "grass_pollen": "grass",
    "birch_pollen": "birch",
    "alder_pollen": "alder",
    "mugwort_pollen": "mugwort",
    "olive_pollen": "olive",
    "ragweed_pollen": "ragweed",
}

# Codici WMO usati da Open-Meteo → descrizione in italiano
WEATHER_CODES = {
    0: "cielo sereno",
    1: "prevalentemente sereno",
    2: "parzialmente nuvoloso",
    3: "coperto",
    45: "nebbia",
    48: "nebbia con brina",
    51: "pioviggine leggera",
    53: "pioviggine moderata",
    55: "pioviggine intensa",
    56: "pioviggine gelata leggera",
    57: "pioviggine gelata intensa",
    61: "pioggia leggera",
    63: "pioggia moderata",
    65: "pioggia intensa",
    66: "pioggia gelata leggera",
    67: "pioggia gelata intensa",
    71: "neve leggera",
    73: "neve moderata",
    75: "neve intensa",
    77: "granelli di neve",
    80: "rovesci leggeri",
    81: "rovesci moderati",
    82: "rovesci violenti",
    85: "rovesci di neve leggeri",
    86: "rovesci di neve intensi",
    95: "temporale",
    96: "temporale con grandine leggera",
    99: "temporale con grandine intensa",
}


def fetch_current_weather():
    """Chiama Open-Meteo e restituisce {temperature, humidity, description}."""
    resp = requests.get(
        API_URL,
        params={
            "latitude": LAT,
            "longitude": LON,
            "current": "temperature_2m,relative_humidity_2m,weather_code",
        },
        timeout=10,
    )
    resp.raise_for_status()
    current = resp.json()["current"]
    code = current["weather_code"]
    return {
        "temperature": current["temperature_2m"],
        "humidity": current["relative_humidity_2m"],
        "description": WEATHER_CODES.get(code, f"codice meteo {code}"),
    }


def fetch_current_pollen():
    """Chiama l'Air Quality API e ritorna i pollini (grani/m³) per specie."""
    resp = requests.get(
        AIR_QUALITY_URL,
        params={
            "latitude": LAT,
            "longitude": LON,
            "current": ",".join(POLLEN_FIELDS),
        },
        timeout=10,
    )
    resp.raise_for_status()
    current = resp.json()["current"]
    return {column: current.get(field) for field, column in POLLEN_FIELDS.items()}


def fetch_and_store():
    """Recupera meteo e pollini correnti e li salva nel DB. Ritorna il meteo salvato."""
    weather = None
    try:
        weather = fetch_current_weather()
        db.insert_weather_reading(
            temperature=weather["temperature"],
            humidity=weather["humidity"],
            description=weather["description"],
        )
        print(f"[weather] salvato: {weather}")
    except requests.RequestException as exc:
        # Non far crashare il job: al prossimo giro riprova
        print(f"[weather] fetch fallito: {exc}")

    # il dato che interessa è il massimo della giornata: campionare ogni ora basta
    if _pollen_needs_update():
        try:
            pollen = fetch_current_pollen()
            # fuori stagione/copertura l'API può dare tutti null: inutile salvare
            if any(v is not None for v in pollen.values()):
                db.insert_pollen_reading(**pollen)
                print(f"[pollen] salvato: {pollen}")
            else:
                print("[pollen] nessun dato disponibile, salto")
        except requests.RequestException as exc:
            print(f"[pollen] fetch fallito: {exc}")

    return weather


def _pollen_needs_update():
    """True se l'ultima lettura pollini ha più di ~55 minuti."""
    rows = db.get_readings("pollen_readings", "today")
    if not rows:
        return True
    last = datetime.fromisoformat(rows[-1]["timestamp"])
    return (datetime.now(timezone.utc) - last).total_seconds() > 55 * 60


def start_scheduler():
    """Avvia il job in background: primo fetch subito, poi ogni FETCH_INTERVAL_MINUTES."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        fetch_and_store,
        "interval",
        minutes=FETCH_INTERVAL_MINUTES,
        next_run_time=datetime.now(),
    )
    scheduler.start()
    return scheduler
