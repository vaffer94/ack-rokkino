# Guida al deploy — portare le modifiche sul Raspberry

Come lavorare quando serve modificare qualcosa e rimettere in produzione.
Il principio: **si sviluppa e si prova sul Mac, si committa su GitHub, e il
Raspberry si aggiorna con `git pull` + rebuild del container**.

## Prerequisiti (già a posto, per riferimento)

- Il repo è clonato sul Raspberry in `~/ack-rokkino`;
- Docker + Docker Compose installati sul Raspberry;
- il container gira con `restart: unless-stopped` (riparte da solo al boot);
- al Raspberry si accede con **Raspberry Pi Connect** (da browser:
  [connect.raspberrypi.com](https://connect.raspberrypi.com) → login → shell
  sul dispositivo `vafferRaspPi`). Non serve SSH né conoscere l'IP per
  amministrarlo — Connect funziona anche da fuori casa;
- `server/.env` presente (non committato, come `arduino_secrets.h`) con le
  credenziali del bot Telegram — vedi sezione dedicata più sotto. Senza
  questo file `docker compose up` si rifiuta di partire (l'`env_file` in
  `docker-compose.yml` punta lì).

## Notifiche Telegram: creare il bot e configurare `server/.env`

Da fare una volta sola (o quando si vuole cambiare bot/destinatario):

1. Su Telegram, cerca **@BotFather**, apri la chat, `/newbot` e segui le
   istruzioni (nome + username che finisce per `bot`) → ottieni un **token**
   tipo `123456789:AAHdq7...`.
2. Manda un messaggio qualsiasi al bot appena creato, poi apri nel browser
   `https://api.telegram.org/bot<TOKEN>/getUpdates`: nel JSON cerca
   `"chat":{"id": ...}` → quel numero è il **chat_id**.
3. Sul Raspberry:
   ```bash
   cd ~/ack-rokkino/server
   cp .env.example .env
   nano .env   # incollare TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID
   ```
4. `docker compose up --build -d` (o semplice `docker compose up -d` se il
   codice non è cambiato, basta far ripartire il container per rileggere `.env`).

Per testare che arrivi davvero una notifica, senza dover aspettare un evento
vero, si può simulare un allarme gas:
```bash
curl -X POST http://127.0.0.1:5001/api/sensors \
  -H "Content-Type: application/json" \
  -d '{"temperature": 25.0, "humidity": 45, "gas": 900, "lux": 100, "alarm_state": 1}'
```

## Flusso normale: modifica al server (Python, template, CSS)

### 1. Sul Mac — modifica e prova in locale

```bash
cd ~/REPO_github/ack-rokkino/server
PORT=5001 ./venv/bin/python app.py
```

Aprire `http://localhost:5001/kindle` e `/dashboard` e verificare la modifica.
(In alternativa si può provare direttamente in Docker anche sul Mac:
`docker compose up --build -d` nella stessa cartella.)

### 2. Sul Mac — commit e push

```bash
git add -A
git commit -m "descrizione della modifica"
git push
```

⚠️ Mai committare `arduino_secrets.h` (è gitignorato, ma se git dovesse
proporlo in `git status`, fermarsi: qualcosa non va).

### 3. Sul Raspberry (via Connect) — pull e rebuild

Aprire la shell da Raspberry Pi Connect e incollare:

```bash
cd ~/ack-rokkino/server
git pull
docker compose up --build -d
docker compose logs -f    # Ctrl+C per uscire, il container resta su
```

Il rebuild ci mette 1-3 minuti (di più se è cambiato `requirements.txt`).
`docker compose up --build -d` fa tutto: ricostruisce l'immagine col nuovo
codice e sostituisce il container al volo. **I dati non si perdono mai**: il
database sta in `~/ack-rokkino/server/data/`, fuori dal container.

### 4. Verifica

- nei log: `Running on http://0.0.0.0:5000` e, entro un minuto,
  `[weather] salvato: ...`;
- dal browser: `http://192.168.1.17:5001/kindle` (IP attuale del Pi — se è
  cambiato: `hostname -I` sul Raspberry);
- il POST dell'Arduino arriva ogni 10 minuti: nei log si vede
  `POST /api/sensors` → se dopo 10-15 minuti non compare, vedi Troubleshooting.

## Flusso modifiche Arduino (sketch)

Lo sketch non passa dal Raspberry: si carica dal Mac con l'IDE.

1. modificare `arduino/sketch/sketch.ino` (e/o `arduino_secrets.h` per
   credenziali e IP — questo file esiste solo in locale, non su GitHub);
2. Arduino IDE → Verifica (✓) → Carica (→) con la MKR collegata via USB;
3. aprire il monitor seriale (9600 baud) e attendere il ciclo da 10 minuti:
   deve comparire `Server: HTTP/1.1 201 CREATED`;
4. committare e pushare anche lo sketch, così il repo resta allineato:
   `git add arduino/ && git commit -m "..." && git push`.

Trucco per non aspettare 10 minuti a ogni test: ridurre temporaneamente
`sdLogInterval` a `60000UL` (1 minuto), testare, poi rimettere `600000UL`
e ricaricare.

## Comandi utili sul Raspberry

```bash
docker ps                          # il container c'è ed è Up?
docker compose logs -f             # log in diretta (Ctrl+C per uscire)
docker compose logs --tail 50     # ultime 50 righe
docker compose restart             # riavvio senza rebuild
docker compose down                # ferma tutto
docker compose up -d               # riparte (senza rebuild)
docker compose up --build -d      # riparte ricostruendo (dopo un git pull)
sqlite3 ~/ack-rokkino/server/data/sensors.db "SELECT COUNT(*) FROM sensor_readings;"
                                   # quante letture ci sono (serve: sudo apt install sqlite3)
```

## Troubleshooting

| Sintomo | Cosa controllare |
|---|---|
| Pagine non raggiungibili | `docker ps` sul Pi; l'IP è ancora quello? (`hostname -I`) |
| L'Arduino non consegna (`connessione fallita` sul seriale) | IP del Pi cambiato → aggiornare `SERVER_HOST` in `arduino_secrets.h` e ricaricare; Arduino e Pi sulla stessa rete? |
| `git pull` rifiutato sul Pi per modifiche locali | sul Pi non si edita mai a mano: `git checkout -- .` e ripetere il pull |
| Grafici vuoti dopo il deploy | normale se il DB è nuovo: si riempiono al primo POST (10 min) e al primo giro meteo (subito) |
| Il rebuild fallisce per rete/pacchetti | riprovare; se persiste: `docker system prune` e di nuovo `docker compose up --build -d` |
| `docker compose up` si rifiuta di partire lamentando `.env` | manca `server/.env` (vedi sezione Notifiche Telegram sopra): copiarlo da `.env.example` |
| Notifiche Telegram non arrivano | controllare `docker compose logs` per righe `[window_alert] ...`: se dicono "non configurati" mancano le credenziali in `.env`; se c'è un errore HTTP, controllare che token/chat_id siano corretti (rigenerare con `/newbot` e `getUpdates` se in dubbio) |

## Backup del database (consigliato ogni tanto)

Dal Mac, con il Pi acceso — copia il DB via Connect non è comodo, quindi il
modo più semplice è dal Raspberry stesso su una USB, oppure:

```bash
# sul Raspberry: crea una copia datata accanto all'originale
cp ~/ack-rokkino/server/data/sensors.db ~/sensors-backup-$(date +%Y%m%d).db
```

(il file si può poi scaricare col file manager di Raspberry Pi Connect,
funzione "Remote Shell" → oppure condividere via rete quando serve).
