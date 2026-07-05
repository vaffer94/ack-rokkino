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
from matplotlib.dates import AutoDateLocator, DateFormatter

import db

TZ = ZoneInfo("Europe/Rome")

# metric -> (titolo, colonna)
# "temperature" e "humidity" combinano interna (sensori) ed esterna (meteo);
# "pollen" mostra le specie principali da pollen_readings
METRICS = {
    "temperature": ("Temperatura (°C)", "temperature"),
    "humidity": ("Umidità (%)", "humidity"),
    "gas": ("Gas MQ2", "gas"),
    "lux": ("Luminosità (lux)", "lux"),
    "pollen": ("Pollini, media giorno (grani/m³)", None),
}

POLLEN_DAYS = 15

# specie mostrate nel grafico pollini del Kindle: le più rilevanti per chi
# è allergico a graminacee; stili diversi perché l'e-ink non ha colori
POLLEN_SERIES = [
    ("grass", "graminacee", "-"),
    ("birch", "betulla", "--"),
    ("ragweed", "ambrosia", ":"),
]

plt.rcParams.update({"font.size": 9})

FIGSIZE = (3.5, 2.2)
DPI = 100


def _series(table, column):
    rows = db.get_readings(table, "today")
    times = [datetime.fromisoformat(r["timestamp"]).astimezone(TZ) for r in rows]
    values = [r[column] for r in rows]
    return times, values


def _no_data(ax):
    ax.text(0.5, 0.5, "Nessun dato oggi", ha="center", va="center", fontsize=12)
    ax.set_xticks([])
    ax.set_yticks([])


def render_chart(metric):
    """Ritorna i byte PNG del grafico con i dati di oggi per la metrica data."""
    title, column = METRICS[metric]
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    has_data = False

    if metric == "pollen":
        rows = db.get_daily_pollen(POLLEN_DAYS)
        days = [datetime.fromisoformat(r["day"]) for r in rows]
        for db_column, label, style in POLLEN_SERIES:
            values = [r[db_column] for r in rows]
            if any(v is not None for v in values):
                ax.plot(days, values, color="black", linewidth=1.5,
                        linestyle=style, label=label, marker="o", markersize=3)
                has_data = True
        if has_data:
            ax.legend(fontsize=8, frameon=False)
            ax.xaxis.set_major_locator(AutoDateLocator(maxticks=6, tz=TZ))
            ax.xaxis.set_major_formatter(DateFormatter("%d/%m"))
            ax.grid(True, color="0.85")
        else:
            _no_data(ax)
        ax.set_title(title, fontsize=10)
        fig.tight_layout(pad=0.6)
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        plt.close(fig)
        return buf.getvalue()
    else:
        times, values = _series("sensor_readings", column)
        if values:
            has_data = True
            if metric in ("temperature", "humidity"):
                ax.plot(times, values, color="black", linewidth=1.5, label="interna")
                w_times, w_values = _series("weather_readings", column)
                if w_values:
                    ax.plot(w_times, w_values, color="black", linewidth=1.5,
                            linestyle="--", label="esterna")
                ax.legend(fontsize=8, frameon=False)
            else:
                ax.plot(times, values, color="black", linewidth=1.5)

    if has_data:
        ax.xaxis.set_major_locator(AutoDateLocator(maxticks=5, tz=TZ))
        ax.xaxis.set_major_formatter(DateFormatter("%H:%M", tz=TZ))
        ax.grid(True, color="0.85")
    else:
        _no_data(ax)
    ax.set_title(title, fontsize=10)
    fig.tight_layout(pad=0.6)

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()
