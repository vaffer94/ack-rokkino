# ack-rokkino — Dashboard sensori casa

Sistema di monitoraggio ambientale domestico: un **Arduino MKR** con shield ENV
e sensore gas MQ2 misura temperatura, umidità, luminosità e gas; un **Raspberry Pi**
raccoglie i dati, li arricchisce con meteo e pollini da Open-Meteo, e li serve su
due pagine web — una ottimizzata per il **Kindle Paperwhite** (e-ink, senza
JavaScript) e una **dashboard interattiva** per browser moderni.

Documentazione:
- [Descrizione funzionale](docs/funzionale.md) — cosa fa il sistema, dal punto di vista di chi lo usa
- [Guida al deploy](docs/deploy.md) — come portare le modifiche sul Raspberry
- [noteVF.md](noteVF.md) — note operative personali (cambio router, ecc.)

## Architettura

```mermaid
flowchart LR
    subgraph Casa
        A[Arduino MKR<br/>ENV shield + MQ2 + buzzer]
        R[Raspberry Pi<br/>Docker: Flask + SQLite]
        K[Kindle Paperwhite]
        B[Browser Mac / telefono]
    end
    subgraph Cloud
        TS[ThingSpeak]
        VM[VoiceMonkey → Alexa]
        OM[Open-Meteo API<br/>meteo + pollini]
    end

    A -- "HTTP POST ogni 10 min<br/>/api/sensors" --> R
    A -- "ogni 20 s" --> TS
    A -- "su allarme gas" --> VM
    A -- "log CSV ogni 10 min" --> SD[(microSD)]
    R -- "fetch ogni 10 min<br/>(pollini: 1/ora)" --> OM
    K -- "GET /kindle" --> R
    B -- "GET /dashboard" --> R
```

## Flusso dei dati

```mermaid
sequenceDiagram
    participant A as Arduino
    participant F as Flask (Raspberry)
    participant DB as SQLite
    participant OM as Open-Meteo
    participant K as Kindle/Browser

    loop ogni 10 minuti
        A->>F: POST /api/sensors {temperature, humidity, gas, lux, alarm_state}
        F->>DB: INSERT sensor_readings (timestamp UTC)
    end
    loop ogni 10 minuti (scheduler APScheduler)
        F->>OM: GET meteo corrente
        F->>DB: INSERT weather_readings
        alt ultima lettura pollini > 55 min fa
            F->>OM: GET pollini (air quality API)
            F->>DB: INSERT pollen_readings
        end
    end
    K->>F: GET /kindle (o /dashboard)
    F->>DB: SELECT (oggi / periodo)
    F-->>K: HTML + grafici PNG (Kindle) oppure JSON + Chart.js (dashboard)
```

## Logica allarme gas (lato Arduino)

Il controllo del gas avviene **ogni 10 secondi** con una finestra mobile di 4
campioni: se gli ultimi 3 superano del 20% il campione base, scatta l'allarme
(buzzer con melodia + trigger Alexa via VoiceMonkey). Poiché al server i dati
vanno solo ogni 10 minuti, un **latch** (`alarmInWindow`) ricorda se c'è stato
almeno un allarme dall'ultimo invio: è questo valore che finisce nel campo
`alarm_state` del DB e nella linea ALTO/BASSO dei grafici.

```mermaid
flowchart TD
    S[Campione MQ2 ogni 10 s] --> W{Finestra 4 campioni:<br/>ultimi 3 > base +20%?}
    W -- sì --> AL[alarmState = 1<br/>alarmInWindow = 1 latch]
    W -- no --> N[alarmState = 0]
    AL --> M{Già suonato?}
    M -- no --> Z[Buzzer melodia + alert Alexa]
    T[Timer 10 minuti] --> P[POST al server con alarmInWindow<br/>+ scrittura su SD]
    P --> RST[alarmInWindow = 0]
```

## Componenti

| Percorso | Ruolo |
|---|---|
| `arduino/sketch/sketch.ino` | Sketch MKR: sensori, allarme, ThingSpeak, SD, POST al server |
| `arduino/arduino_secrets.h.example` | Template dei segreti (WiFi, chiavi, IP server) — la copia reale è gitignorata |
| `server/app.py` | App Flask: route web + API, avvio scheduler |
| `server/db.py` | SQLite: schema, insert, query per periodo, media giornaliera pollini |
| `server/weather.py` | Client Open-Meteo (meteo + pollini) + job APScheduler |
| `server/charts.py` | Grafici PNG con matplotlib per la pagina Kindle (b/n, e-ink) |
| `server/templates/kindle.html` | Pagina statica per Kindle: no JS, `<meta refresh>` 10 min |
| `server/templates/dashboard.html` | Dashboard Chart.js con selettore periodo |
| `server/static/chart.min.js` | Chart.js 4.4.1 in locale (funziona senza internet) |
| `server/Dockerfile` + `docker-compose.yml` | Container (python:3.12-slim, multi-arch ARM) |

## Schema database (SQLite, `server/data/sensors.db`)

Tutti i timestamp sono ISO8601 in UTC; la conversione in ora italiana avviene
in fase di visualizzazione.

- **sensor_readings**: `id, timestamp, temperature, humidity, gas (MQ2 grezzo), lux, alarm_state (0/1, "almeno un allarme negli ultimi 10 min")`
- **weather_readings**: `id, timestamp, temperature, humidity, description (it)`
- **pollen_readings**: `id, timestamp, grass, birch, alder, mugwort, olive, ragweed` (grani/m³, specie CAMS)

Il DB vive fuori dal container (volume `./data:/app/data`): sopravvive a
rebuild e riavvii. Nessuna retention: i dati si accumulano indefinitamente.

## API

| Endpoint | Descrizione |
|---|---|
| `POST /api/sensors` | Riceve il JSON dall'Arduino, valida i 5 campi, salva con timestamp corrente |
| `GET /kindle` | Pagina e-ink: tabelle valori attuali + 5 grafici PNG |
| `GET /dashboard` | Dashboard interattiva Chart.js |
| `GET /api/data?period=today\|week\|month` | JSON per la dashboard (sensori + meteo, downsampling a ~500 punti; pollini sempre media giornaliera 15 gg) |
| `GET /chart/<metric>.png` | PNG per il Kindle; `metric` = `temperature`, `humidity`, `gas`, `lux`, `pollen` |

## Scelte tecniche principali

- **Porta 5001 ovunque** (Mac in sviluppo e Raspberry in produzione): sul Mac la
  5000 è occupata da AirPlay Receiver; tenere la stessa porta evita di dover
  mai cambiare `SERVER_PORT` nello sketch.
- **Pollini = media giornaliera** degli ultimi 15 giorni: è lo standard dei
  bollettini pollinici, confrontabile con le soglie di rischio (graminacee:
  bassa <30, media 30–49, alta 50–149 grani/m³).
- **Grafici Kindle come PNG matplotlib**: il browser del Paperwhite non regge
  librerie JS moderne; PNG in bianco e nero con linee differenziate
  (continua/tratteggiata/puntinata) al posto dei colori.
- **Chart.js con asse X numerico** (epoch ms): sensori (10 min) e meteo (1 h)
  hanno densità diverse; l'asse a categorie li disallineerebbe.
- **Segreti fuori da git**: tutto ciò che è sensibile sta in
  `arduino_secrets.h` (gitignorato ovunque); nel repo c'è solo il template.
