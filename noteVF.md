FASE 2:

Tre note:

Quando aprirai sketch.ino nell'IDE Arduino, ti chiederà di spostarlo in una cartella chiamata sketch — accetta pure, ma tieni arduino_secrets.h nella stessa cartella dello sketch.
Il file sul Desktop (temp/:: codice attuale IDE) contiene ancora i segreti in chiaro: ti consiglio di cancellarlo quando non ti serve più.
Ho notato (senza toccarlo) che nella scrittura su SD c'è un piccolo bug pre-esistente: l'header CSV non include alarm_state e la sequenza println(mq2Value); print(","); println(alarmState); print(";") produce righe malformate. Se vuoi lo sistemiamo alla Fase 6.

FASE 8:
Bene, tutto committato. La Fase 8 è quasi interamente lavoro manuale sul Raspberry — io non ho accesso a quella macchina, quindi ti guido passo passo. Ecco la sequenza completa:

## 1. Prerequisiti sul Raspberry

Collegati in SSH al Raspberry (`ssh pi@<ip-raspberry>` o simile) e verifica Docker:

```bash
docker --version
docker compose version
```

Se non ci sono, installali con lo script ufficiale:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# poi esci e rientra in SSH perché il gruppo abbia effetto
```

## 2. Copia il repo sul Raspberry

Il modo più comodo è un `git clone` diretto sul Raspberry (così in futuro basta `git pull` per aggiornare):

```bash
git clone https://github.com/vaffer94/ack-rokkino.git
cd ack-rokkino/server
```

## 3. IP statico del Raspberry

Prima di avviare il container, fissa l'IP del Raspberry sulla rete di casa — altrimenti l'Arduino perde il riferimento a ogni riavvio del router. Il modo più semplice è dalla pagina di amministrazione del router (assegna un IP fisso via DHCP reservation alla MAC address del Raspberry, che trovi con `ip addr show` o `ifconfig`). In alternativa lo imposti direttamente sul Raspberry via `nmtui` o modificando `/etc/dhcpcd.conf`, ma la riserva DHCP dal router è più robusta e non rischia di andare in conflitto con altri device.

## 4. Avvia il container

```bash
cd ack-rokkino/server
docker compose up --build -d
docker compose logs -f
```

Controlla che nei log compaia `Running on http://0.0.0.0:5000` e, dopo poco, `[weather] salvato: ...` (lo scheduler meteo/pollini che parte). Poi da un browser qualsiasi in rete locale: `http://<ip-fisso-raspberry>:5001/kindle` e `/dashboard`.

## 5. Aggiorna l'IP nello sketch Arduino

Nel file `arduino/sketch/arduino_secrets.h` (quello locale sul tuo Mac, non è nel repo):

```cpp
#define SERVER_HOST "192.168.1.XXX"  // IP fisso del Raspberry
#define SERVER_PORT 5001
```

Poi ricarica lo sketch sulla MKR da Arduino IDE.

## 6. Test end-to-end

Con l'Arduino acceso, monitor seriale aperto, aspetta il ciclo da 10 minuti e verifica:

- seriale: `Server: HTTP/1.1 201 CREATED`
- `docker compose logs -f` sul Raspberry: riga `POST /api/sensors` in arrivo dall'IP dell'Arduino
- `/kindle` sul Raspberry mostra i valori aggiornati

---

# 🔄 COSA FARE QUANDO CAMBIA IL ROUTER (nuova WiFi)

Tempo stimato: ~10 minuti. Servono: Mac con Arduino IDE, accesso al Raspberry.
(Nota: dall'01/08/2026 il router è di proprietà e l'IP del Pi è riservato —
vedi punto 6, ormai fatto. Questa checklist resta valida per un eventuale
trasloco o cambio di router futuro: ha già funzionato una volta.)

## 1. Ricollegare il Raspberry alla nuova WiFi

⚠️ Appena cambia la rete, il Raspberry è offline e Raspberry Pi Connect NON
funziona (ha bisogno di internet). Non ho tastiera/monitor da attaccare,
quindi le strade sono queste, in ordine di preferenza:

### Opzione A — PRECARICARE la rete nuova PRIMA del cambio (la migliore)
Appena conosco nome e password del nuovo WiFi, **mentre il Pi è ancora online
sulla rete vecchia**, da Connect:
```bash
sudo nmcli connection add type wifi ifname wlan0 con-name casa-nuova \
  ssid "NOME_NUOVA_RETE" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "PASSWORD_NUOVA"
```
NetworkManager si collega da solo a qualunque rete conosciuta: quando la
nuova si accende, il Pi ci si aggancia automaticamente. Non devo fare altro.
→ **Da fare appena ho le credenziali del nuovo WiFi, senza aspettare!**

### Opzione B — Cavo ethernet
Collegare il Pi a una porta LAN del router nuovo con un cavo ethernet:
la rete via cavo funziona subito senza configurazione, Connect torna su,
e da lì configuro il WiFi con calma (`sudo nmtui`). Il cavo si può anche
lasciare per sempre: è più stabile del WiFi.

### Opzione C — Tastiera + schermo (se riesco a procurarmeli)
Attaccare tastiera e monitor (micro-HDMI) al Pi, fare login, poi:
- `sudo nmtui` → "Activate a connection" → scegliere la nuova rete → password;
- verificare con `ping -c 3 google.com`.
Da qui in poi Connect torna a funzionare.

### Opzione D — Raspberry Pi Imager (ULTIMA SPIAGGIA)
Riscrive la SD da zero: si perde tutto (Docker, repo, **database**).
Solo se A, B e C sono impossibili. Prima di farlo, se il Pi è acceso ma
irraggiungibile, provare a recuperare il DB togliendo la SD e leggendola
dal Mac. Poi: Imager con WiFi/hostname/SSH preconfigurati, e rifare il
setup seguendo docs/deploy.md (sezione Prerequisiti) — circa 30 minuti.

Verifica finale (qualunque opzione): `ping -c 3 google.com` dal Pi.

## 2. Trovare il nuovo IP del Raspberry

```bash
hostname -I
```

Il primo indirizzo (es. `192.168.1.xx`) è quello che serve. Segnarlo.

## 3. Aggiornare lo sketch Arduino (sul Mac)

Aprire `arduino/sketch/arduino_secrets.h` e aggiornare **tre valori**:

```cpp
#define SECRET_SSID "nome-nuova-rete"
#define SECRET_PASS "password-nuova-rete"
#define SERVER_HOST "192.168.1.xx"   // nuovo IP del Raspberry (punto 2)
```

Compilare e caricare con l'IDE. Sul monitor seriale, al primo ciclo da 10 min,
deve comparire `Server: HTTP/1.1 201 CREATED`.

## 4. Il server sul Raspberry riparte da solo

Il container Docker ha `restart: unless-stopped`: al boot del Pi riparte
senza fare nulla. Per controllare:

```bash
docker ps    # deve esserci "server-sensors-1" con stato Up
```

Se non c'è: `cd ~/ack-rokkino/server && docker compose up -d`

## 5. Aggiornare i segnalibri su Kindle e telefono

- `http://<nuovo-ip>:5001/kindle`
- `http://<nuovo-ip>:5001/dashboard`

## 6. ✅ IP fisso definitivo — FATTO l'01/08/2026

Pannello del router: `http://192.168.0.1` → **Dispositivi connessi** →
**Dispositivi** → `MODIFICA` sulla riga del Pi → **IP riservato**.
Il Pi è già nell'elenco perché connesso, quindi non va riaggiunto: il MAC
è già compilato. Per verificarlo dal Pi: `ip addr show wlan0` (riga
`link/ether`).

Da qui in poi l'IP non cambia più, nemmeno dopo un blackout o un riavvio
del router: per un prossimo cambio rete bastano i punti 1 e 3 (credenziali
WiFi).

---

## 📌 Indirizzi attuali (rete propria, IP riservato dal router)

- Raspberry: `192.168.0.182` — riservato, non cambia
- Pagina Kindle: `http://192.168.0.182:5001/kindle`
- Dashboard: `http://192.168.0.182:5001/dashboard`
- Router: `http://192.168.0.1`

Nome rete, utente SSH e comandi pronti: vedi `ACCESSI.local.md` (file solo
locale, escluso da Git).

## ✅ Fatto l'01/08/2026 — passaggio alla rete di casa

Migrazione dalla WiFi della vicina (in trasloco) alla rete propria, fatta
tutta da remoto, senza tastiera né monitor attaccati al Pi:

1. dalla shell di Raspberry Pi Connect, **mentre il Pi era ancora online
   sulla rete vecchia**, verifica che la rete nuova fosse visibile e con
   buon segnale:
   `sudo nmcli dev wifi rescan; sleep 10; sudo nmcli dev wifi list`;
2. connessione con un comando solo (salva la rete e ci si collega):
   `sudo nmcli device wifi connect "<nome-rete>" password "<password>"`;
3. la shell di Connect si è scollegata — previsto, il Pi stava cambiando
   rete — ma il client Connect **non è ripartito da solo**;
4. il Pi è stato ritrovato dal Mac con
   `dscacheutil -q host -a name vafferRaspPi.local`: nuovo indirizzo su una
   **sottorete diversa** (`192.168.0.x` invece di `192.168.1.x`);
5. riserva DHCP dal pannello del router (punto 6);
6. aggiornamento di `arduino_secrets.h` e ricarica dello sketch (punto 3).

⚠️ **Lezione utile.** La rete vecchia è rimasta salvata come riserva: in
caso di password sbagliata sarebbe bastato togliere e ridare corrente al Pi
per tornare indietro. Non cancellare mai la rete vecchia prima di aver
verificato che la nuova funziona.

Due trappole incontrate:
- `nmtui` nel terminale del browser mostrava **una sola rete**, facendo
  sembrare che il Pi non vedesse la rete nuova. Era un problema di
  visualizzazione: `nmcli dev wifi list` le elencava tutte, con segnale.
- subito dopo il cambio, il Pi rispondeva in 5-7 **secondi**. Si è
  sistemato da solo entro pochi minuti (10 ms): è la connessione che si
  assesta, non serve intervenire.

## ✅ Fatto l'11/07/2026 — notifiche Telegram + dashboard

Lavoro sul branch `feature-closeWindow` (non ancora mergiato su `main`):

- **Promemoria "chiudi la finestra"** (`server/window_alert.py`): rileva da
  solo quando la finestra è aperta (calo sostenuto di temperatura interna,
  non un singolo scatto isolato) e avvisa su Telegram quando l'esterno torna
  a scaldare — solo d'estate (esterna > 25°). Dettagli in
  `docs/funzionale.md` e nel README (sezione "Notifiche Telegram").
- **Notifica gas su Telegram**: era in lista come idea da fare con ntfy.sh,
  realizzata invece riusando la stessa infrastruttura Telegram del punto
  precedente (poche righe in `app.py`). Notifica solo al primo 1 dopo uno 0,
  non ripete finché l'allarme resta attivo.
- **Tabelle "Ultimi dati registrati"** in dashboard: ultime 15 letture
  sensori + meteo, sempre le più recenti indipendentemente dal periodo
  scelto (nuovo endpoint `/api/latest`).
- **Etichette valore sui grafici**: pallini + numero sui massimi/minimi
  locali e sull'ultima misura, sempre visibili (non solo al passaggio del
  mouse). Densità adattata alla larghezza reale del grafico e al tipo di
  dispositivo (touch vs mouse, non solo la larghezza della finestra).
  ⚠️ **Non ancora soddisfacente su mobile** secondo Vania (settimana/mese
  restano troppo fitti) — da rivedere, vedi "Prossime idee" sotto.

Per portare questo branch sul Raspberry: `git fetch && git checkout
feature-closeWindow`, creare `server/.env` da `.env.example` con le
credenziali Telegram (vedi `docs/deploy.md`), poi il solito
`docker compose up --build -d`.

## 💡 Prossime idee (non urgenti)

### CI/CD — deploy automatico sul Raspberry
Oggi il deploy è manuale (2 comandi da Connect, vedi docs/deploy.md). Se un
giorno voglio automatizzarlo, il vincolo è che il Pi non è raggiungibile da
internet: deve essere lui a controllare GitHub ("pull-based"), non GitHub a
chiamarlo. Due strade, dalla più semplice:

1. **Cron sul Pi** (consigliata come primo passo): script che ogni 5-10 min fa
   `git fetch` su un branch dedicato `deploy`; se ci sono commit nuovi →
   `git pull && docker compose up --build -d`. Con il branch dedicato posso
   pushare su `main` liberamente: va in produzione solo ciò che mergio su
   `deploy`. Zero infrastruttura esterna.
2. **GitHub Actions + runner self-hosted sul Pi**: il runner si collega a
   GitHub in uscita (funziona dietro NAT), al push parte il deploy e vedo i
   log nella UI di GitHub. Più completo (ci si può agganciare anche un test
   automatico pre-deploy), ma più setup e un servizio in più sul Pi.

Da fare eventualmente DOPO il trasloco, a sistema stabile.

### Prossime candidate (miglior rapporto utilità/sforzo)
1. **Densità delle etichette sui grafici da mobile — ancora da sistemare**:
   dopo diversi tentativi (raggio in pixel, poi raggruppamento per giorno di
   calendario, poi rilevazione touch invece che larghezza), su settimana e
   mese resta "troppo fitto" secondo Vania. Prossimo tentativo da discutere
   con lei: forse ridurre ulteriormente, o cambiare approccio (es. mostrare
   le etichette solo al tap su un punto invece che tutte insieme).
2. **Avviso "Arduino muto"**: se l'Arduino si blocca o perde la rete, i
   grafici si fermano in silenzio. Banner sul Kindle "⚠ nessun dato da X ore"
   quando l'ultimo POST è più vecchio di 30 min (+ eventuale notifica ntfy).
3. **Autenticazione su dashboard/kindle/API + chiave per l'Arduino** — da
   dati come luminosità/gas/allarme si capisce quando sei in casa, quindi
   diventa importante appena la pagina è raggiungibile anche da fuori (es.
   con Tailscale, o se un giorno esponi la porta dal tuo router). Due parti:
   - **Login (utente/password) su `/dashboard`, `/kindle`, `/chart/<metric>.png`,
     `/api/data`, `/api/latest`**: HTTP Basic Auth di Flask, credenziali in un
     file `server/.env` (non committato, come `arduino_secrets.h`).
   - **Chiave segreta per `POST /api/sensors`**: l'Arduino manda un header
     `X-API-Key` con un token generato a caso; il server rifiuta chi non lo
     manda o lo sbaglia. Aggiornamento da fare anche in `arduino/sketch/sketch.ino`
     e `arduino_secrets.h`.
   - Attenzione: Basic Auth da solo non cifra le credenziali — va bene su
     WiFi di casa o dentro un tunnel già cifrato (es. Tailscale), ma non va
     esposto in chiaro su internet senza HTTPS.

### Altre idee parcheggiate
- **Pressione e UV nel server**: lo shield ENV li misura già (vanno su SD e
  ThingSpeak) ma non sono nel POST al server → aggiungere campo al JSON,
  colonna nel DB e grafico. La pressione anticipa i cambi di tempo.
- **Fascia pollini in chiaro sul Kindle**: quando la media graminacee supera
  30 (media) o 50 (alta), scrivere la fascia ("Graminacee: 54 — ALTA")
  invece del numero da interpretare.
- **Import dello storico dalla microSD**: script una-tantum che importa il
  data.csv (mesi di dati pre-server) nel DB per riempire lo storico.
- **Min/max di oggi sul Kindle**: riga "oggi: min 19,5° / max 28,3°".
- **Gunicorn al posto del dev server Flask**: toglie il WARNING nei log,
  sistemazione "da produzione" (~30 min).
- Ignorare i primi 2-3 minuti di letture MQ2 dopo il boot dell'Arduino
  (il sensore in riscaldamento può causare un falso allarme).
- Backup periodico automatico del DB (cron sul Pi che copia sensors.db,
  magari su USB o verso il Mac).

## 🧹 Pulizie rimandate

- Il DB sul **Mac** (`server/data/sensors.db`) contiene dati finti di test.
  Quello sul **Raspberry** è partito pulito: è lui il DB "vero".
- In `arduino/` c'è una copia vecchia e non più usata di `arduino_secrets.h`
  (fuori da `sketch/`): si può cancellare, quella attiva è
  `arduino/sketch/arduino_secrets.h`.
