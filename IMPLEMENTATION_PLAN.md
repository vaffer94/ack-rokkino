# Piano di implementazione — Dashboard sensori (Arduino → Raspberry → Kindle/Browser)

## Obiettivo del progetto

Estendere il sistema Arduino MKR ENV (che già invia dati a ThingSpeak) per inviare
anche i dati a un server Flask su Raspberry Pi. Il server salva i dati in SQLite,
recupera dati meteo da un'API gratuita, e serve due pagine web:

- **`/kindle`** — pagina statica leggerissima (no JS), ottimizzata per il browser
  del Kindle Paperwhite (mod. EY21), con grafici come immagini PNG e i dati di oggi.
- **`/dashboard`** — pagina interattiva (Chart.js) per browser moderni, con
  selettore di periodo (oggi / settimana / mese).

## Architettura

```
Arduino MKR ENV --(HTTP POST ogni 10 min)--> Raspberry Pi (Flask + SQLite)
      |                                             |
      +--(ThingSpeak, invariato, ogni 20s)          +--(fetch periodico)--> Open-Meteo API
                                                     |
                                                     +--> /kindle   (HTML statico + PNG)
                                                     +--> /dashboard (HTML + Chart.js)
```

**Meteo**: Open-Meteo (gratuita, senza API key), punto vicino a Milano zona Bocconi
(lat 45.404, lon 9.188).

**Retention dati**: nessuna cancellazione, dati conservati indefinitamente.

## Struttura del progetto

```
ack-rokkino/
├── arduino/
│   └── sketch.ino              # sketch aggiornato
├── server/
│   ├── app.py                  # Flask app + route
│   ├── db.py                   # gestione SQLite (schema, insert, query)
│   ├── weather.py              # client Open-Meteo + job periodico
│   ├── charts.py                # generazione grafici PNG (matplotlib) per Kindle
│   ├── templates/
│   │   ├── kindle.html
│   │   └── dashboard.html
│   ├── static/
│   │   ├── chart.min.js
│   │   └── style.css
│   ├── data/
│   │   └── sensors.db          # DB SQLite (creato a runtime, gitignored)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
├── IMPLEMENTATION_PLAN.md
└── .gitignore
```

## Schema database (SQLite)

Tabella `sensor_readings`:
| campo         | tipo     | note                        |
|---------------|----------|-----------------------------|
| id            | INTEGER  | PK autoincrement            |
| timestamp     | TEXT     | ISO8601, UTC                |
| temperature   | REAL     |                             |
| humidity      | REAL     |                             |
| gas           | INTEGER  | valore MQ2 grezzo           |
| lux           | REAL     |                             |
| alarm_state   | INTEGER  | 0/1                         |

Tabella `weather_readings`:
| campo         | tipo     | note                        |
|---------------|----------|-----------------------------|
| id            | INTEGER  | PK autoincrement            |
| timestamp     | TEXT     | ISO8601, UTC                |
| temperature   | REAL     |                             |
| humidity      | REAL     |                             |
| description   | TEXT     | es. "cielo sereno"          |

## API endpoint del server

- `POST /api/sensors` — riceve JSON da Arduino: `{temperature, humidity, gas, lux, alarm_state}`, salva con timestamp corrente
- `GET /kindle` — pagina HTML statica con dati di oggi + immagini grafici
- `GET /dashboard` — pagina HTML interattiva
- `GET /api/data?period=today|week|month` — JSON con i dati per Chart.js (usato dalla dashboard via JS)
- `GET /chart/<metric>.png` — immagine PNG del grafico (usato dalla pagina Kindle), `metric` = temperature|humidity|gas|lux|weather

## Fasi di implementazione

Ogni fase produce qualcosa di testabile *prima* di passare alla successiva.
Consiglio di fare un commit git al termine di ogni fase.

### Fase 0 — Setup progetto
- Creare struttura cartelle, virtualenv Python, `requirements.txt` (flask, requests, matplotlib, apscheduler)
- `.gitignore` (venv, `*.db`, `__pycache__`)
- **Test**: `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt` senza errori

### Fase 1 — Livello database
- `db.py`: funzioni `init_db()`, `insert_sensor_reading(...)`, `insert_weather_reading(...)`, `get_readings(table, period)`
- **Test**: script Python a riga di comando che inserisce 2-3 record finti e li rilegge; ispezionare con `sqlite3 server/data/sensors.db "SELECT * FROM sensor_readings;"`

### Fase 2 — Flask base + endpoint ricezione dati
- `app.py` con endpoint `POST /api/sensors`
- **Test**: da terminale, simulare l'Arduino:
  ```bash
  curl -X POST http://localhost:5000/api/sensors \
    -H "Content-Type: application/json" \
    -d '{"temperature":22.5,"humidity":45,"gas":120,"lux":300,"alarm_state":0}'
  ```
  poi controllare che sia comparso nel DB

### Fase 3 — Integrazione meteo
- `weather.py`: funzione che chiama Open-Meteo per lat/lon Bocconi, job con APScheduler ogni 10-15 min che salva in `weather_readings`
- **Test**: lanciare la funzione manualmente da una shell Python, verificare la risposta e l'inserimento nel DB; poi lasciare il job attivo qualche minuto e controllare che si aggiorni da solo

### Fase 4 — Pagina Kindle
- `charts.py`: genera PNG con matplotlib per ogni metrica (dati di oggi)
- Route `/chart/<metric>.png` e template `kindle.html` (no JS, `<meta refresh>`, riquadro "ultimi valori")
- **Test**: aprire `http://localhost:5000/kindle` da browser normale sul Mac, poi da browser sul telefono, infine dal Kindle (stesso WiFi di casa, digitando l'IP del Raspberry)

### Fase 5 — Dashboard interattiva
- `dashboard.html` con Chart.js, selettore periodo, chiamate a `/api/data?period=...`
- **Test**: aprire `http://localhost:5000/dashboard`, cambiare periodo, verificare che i grafici si aggiornino

### Fase 6 — Aggiornamento sketch Arduino
- Aggiungere timer separato (10 minuti) e funzione che fa `HTTP POST` all'IP del Raspberry, lasciando invariata la logica ThingSpeak esistente
- **Test**: con Arduino collegato via USB, monitor seriale acceso, verificare nei log di Flask (`flask run --debug`) che le richieste arrivino ogni 10 minuti con dati plausibili

### Fase 7 — Dockerizzazione
- `Dockerfile` (Python slim, arch compatibile ARM per Raspberry Pi 4/5) + `docker-compose.yml` con volume per il DB
- **Test in locale sul Mac**: `docker compose up --build`, verificare che tutto funzioni come in Fase 4-5 ma dentro al container

### Fase 8 — Deploy sul Raspberry
- Copiare/pull del repo sul Raspberry, `docker compose up -d`
- Configurare IP statico (o hostname) del Raspberry sulla rete di casa
- Aggiornare nello sketch Arduino l'IP di destinazione
- **Test end-to-end**: Arduino reale che manda dati, Raspberry che li riceve e salva, Kindle che mostra la pagina aggiornata

### Fase 9 — Rifiniture (facoltativa)
- Avvio automatico del container al boot del Raspberry (`restart: unless-stopped` in docker-compose)
- Eventuale autenticazione basica se il Raspberry è raggiungibile da fuori casa
- Backup periodico del file `.db`

## Come procedere con Claude Code

1. Salva questo file nella cartella `/Users/vaniaferrari/REPO_github/ack-rokkino`
2. Apri il terminale, `cd` nella cartella, lancia Claude Code
3. Chiedi: *"Leggi IMPLEMENTATION_PLAN.md e iniziamo dalla Fase 0"*
4. Prosegui fase per fase, facendo commit git a ogni fase completata e testata
