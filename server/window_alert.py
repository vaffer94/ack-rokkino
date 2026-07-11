"""Promemoria "chiudi la finestra": rileva quando la finestra è stata aperta
per raffrescare la stanza e avvisa su Telegram quando l'esterno torna a
scaldare, prima che la stanza si riscaldi troppo.

Attivo solo d'estate (temperatura esterna > SUMMER_MIN_OUTDOOR_TEMP): sotto
quella soglia una variazione percentuale diventa instabile (vicino allo
zero/negativo) ed è un discorso diverso da affrontare a parte.
"""
import os
from datetime import datetime, timedelta, timezone

import requests

import db

SUMMER_MIN_OUTDOOR_TEMP = 25.0
OPEN_DROP_THRESHOLD = 0.5       # °C, calo minimo sostenuto (finestra aperta)
CLOSE_RISE_PCT = 0.04           # 4%, salita minima per singolo confronto
CLOSE_OUTDOOR_SAMPLES = 5       # ultimi 40 min (10 min/campione)
CLOSE_OUTDOOR_MIN_RISES = 2     # su 4 confronti nella finestra di cui sopra
OPEN_STATE_TIMEOUT_HOURS = 6

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def check_and_notify():
    """Entry point chiamato dopo ogni nuova lettura sensore. Non deve mai
    far fallire la richiesta che l'ha invocato: logga ed esce in caso di
    problemi (dati insufficienti, Telegram irraggiungibile, ecc.)."""
    try:
        _check_and_notify()
    except Exception as exc:
        print(f"[window_alert] errore: {exc}")


def _chronological(table, limit):
    """Ultime `limit` letture in ordine cronologico (più vecchia prima)."""
    return list(reversed(db.get_latest_readings(table, limit)))


def _check_and_notify():
    indoor = _chronological("sensor_readings", 3)
    outdoor = _chronological("weather_readings", CLOSE_OUTDOOR_SAMPLES)
    if len(indoor) < 3 or len(outdoor) < 3:
        return  # dati insufficienti (es. subito dopo un deploy pulito)

    if outdoor[-1]["temperature"] <= SUMMER_MIN_OUTDOOR_TEMP:
        return  # fuori "modalità estate"

    last_event = db.get_last_window_event()
    state = "open_detected" if last_event and last_event["event"] == "opened" else "idle"

    if state == "idle":
        _check_open(indoor, outdoor)
    else:
        _check_close(indoor, outdoor, last_event)


def _check_open(indoor, outdoor):
    t2, t1, t0 = indoor[-3]["temperature"], indoor[-2]["temperature"], indoor[-1]["temperature"]
    outdoor_now = outdoor[-1]["temperature"]

    sustained_drop = t2 > t1 > t0 and (t2 - t0) >= OPEN_DROP_THRESHOLD
    if outdoor_now < t0 and sustained_drop:
        db.insert_window_event("opened")
        print("[window_alert] finestra aperta rilevata")


def _check_close(indoor, outdoor, last_event):
    opened_at = datetime.fromisoformat(last_event["timestamp"])
    if datetime.now(timezone.utc) - opened_at > timedelta(hours=OPEN_STATE_TIMEOUT_HOURS):
        # troppo tempo senza un vero segnale di richiusura: si riparte da idle
        db.insert_window_event("expired")
        return

    t2, t1, t0 = indoor[-3]["temperature"], indoor[-2]["temperature"], indoor[-1]["temperature"]
    indoor_rising = t2 < t1 < t0

    rises = 0
    for prev_row, cur_row in zip(outdoor, outdoor[1:]):
        prev, cur = prev_row["temperature"], cur_row["temperature"]
        if prev and (cur - prev) / prev >= CLOSE_RISE_PCT:
            rises += 1
    outdoor_rising = rises >= CLOSE_OUTDOOR_MIN_RISES

    if outdoor_rising and indoor_rising:
        send_telegram_message("🌡️ Chiudi la finestra: fuori sta tornando a scaldare.")
        db.insert_window_event("closed_notified")


def send_telegram_message(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[window_alert] TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID non configurati, salto invio")
        return
    try:
        resp = requests.post(
            TELEGRAM_API_URL.format(token=token),
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        resp.raise_for_status()
        print(f"[window_alert] notifica Telegram inviata: {text}")
    except requests.RequestException as exc:
        print(f"[window_alert] invio Telegram fallito: {exc}")
