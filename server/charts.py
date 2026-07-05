"""Generazione grafici PNG con matplotlib per la pagina Kindle.

Grafici in bianco e nero, pensati per l'e-ink del Paperwhite.
Dimensioni compatte: 4 grafici in griglia 2x2 devono stare in una schermata
insieme alle tabelle dei valori attuali.
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

# metric -> (titolo, colonna)
# "temperature" è speciale: combina interna (sensori) ed esterna (meteo)
METRICS = {
    "temperature": ("Temperatura (°C)", "temperature"),
    "humidity": ("Umidità interna (%)", "humidity"),
    "gas": ("Gas MQ2", "gas"),
    "lux": ("Luminosità (lux)", "lux"),
}

plt.rcParams.update({"font.size": 9})

FIGSIZE = (3.5, 2.2)
DPI = 100


def _series(table, column):
    rows = db.get_readings(table, "today")
    times = [datetime.fromisoformat(r["timestamp"]).astimezone(TZ) for r in rows]
    values = [r[column] for r in rows]
    return times, values


def render_chart(metric):
    """Ritorna i byte PNG del grafico con i dati di oggi per la metrica data."""
    title, column = METRICS[metric]
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)

    times, values = _series("sensor_readings", column)
    if values:
        if metric == "temperature":
            ax.plot(times, values, color="black", linewidth=1.5, label="interna")
            w_times, w_values = _series("weather_readings", "temperature")
            if w_values:
                ax.plot(w_times, w_values, color="black", linewidth=1.5,
                        linestyle="--", label="esterna")
            ax.legend(fontsize=8, frameon=False)
        else:
            ax.plot(times, values, color="black", linewidth=1.5)
        ax.xaxis.set_major_formatter(DateFormatter("%H:%M", tz=TZ))
        ax.grid(True, color="0.85")
    else:
        ax.text(0.5, 0.5, "Nessun dato oggi", ha="center", va="center", fontsize=12)
        ax.set_xticks([])
        ax.set_yticks([])
    ax.set_title(title, fontsize=10)
    fig.tight_layout(pad=0.6)

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()
