"""Generazione grafici PNG con matplotlib per la pagina Kindle.

Grafici in bianco e nero, linee spesse e font grandi: sul Paperwhite
lo schermo è e-ink in scala di grigi.
"""
import io
from datetime import datetime
from zoneinfo import ZoneInfo

import matplotlib

matplotlib.use("Agg")  # backend senza display, obbligatorio in un server
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

import db

TZ = ZoneInfo("Europe/Rome")

# metric -> (titolo, colonna, tabella)
METRICS = {
    "temperature": ("Temperatura interna (°C)", "temperature", "sensor_readings"),
    "humidity": ("Umidità interna (%)", "humidity", "sensor_readings"),
    "gas": ("Gas MQ2 (valore grezzo)", "gas", "sensor_readings"),
    "lux": ("Luminosità (lux)", "lux", "sensor_readings"),
    "weather": ("Temperatura esterna (°C)", "temperature", "weather_readings"),
}

plt.rcParams.update({"font.size": 14})


def render_chart(metric):
    """Ritorna i byte PNG del grafico con i dati di oggi per la metrica data."""
    title, column, table = METRICS[metric]
    rows = db.get_readings(table, "today")
    times = [datetime.fromisoformat(r["timestamp"]).astimezone(TZ) for r in rows]
    values = [r[column] for r in rows]

    fig, ax = plt.subplots(figsize=(7, 3.5), dpi=100)
    if values:
        ax.plot(times, values, color="black", linewidth=2)
        ax.xaxis.set_major_formatter(DateFormatter("%H:%M", tz=TZ))
        ax.grid(True, color="0.8")
    else:
        ax.text(0.5, 0.5, "Nessun dato oggi", ha="center", va="center", fontsize=18)
        ax.set_xticks([])
        ax.set_yticks([])
    ax.set_title(title)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()
