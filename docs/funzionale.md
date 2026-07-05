# Descrizione funzionale — cosa fa il sistema

Questo documento spiega il comportamento del sistema dal punto di vista di chi
lo usa, senza dettagli implementativi (per quelli: [README](../README.md)).

## In una frase

In casa c'è un Arduino che ogni 10 minuti misura temperatura, umidità,
luminosità e gas; il Raspberry raccoglie tutto, ci aggiunge meteo e pollini di
Milano, e mostra la situazione su una pagina sempre aggiornata sul Kindle e su
una dashboard consultabile da qualunque browser di casa.

## Cosa misura e ogni quanto

| Cosa | Fonte | Frequenza |
|---|---|---|
| Temperatura, umidità, luminosità interne | Arduino (shield ENV) | ogni 10 minuti al server |
| Gas (fumo/GPL, valore grezzo MQ2) | Arduino | controllo ogni 10 s, invio ogni 10 min |
| Meteo esterno (temperatura, umidità, cielo) | Open-Meteo, coordinate zona Bocconi | ogni 10 minuti |
| Pollini (graminacee, betulla, ontano, artemisia, olivo, ambrosia) | Open-Meteo Air Quality | ogni ora |

In parallelo, l'Arduino continua a fare quello che faceva già prima di questo
progetto: invio a ThingSpeak ogni 20 secondi e log su microSD (ora ogni 10
minuti, allineato all'invio al server).

## La pagina Kindle (`/kindle`)

Pensata per restare sempre aperta sul Paperwhite come "quadro di controllo":

- **si aggiorna da sola ogni 10 minuti** (nessuna interazione necessaria);
- in alto due tabelle affiancate con i valori attuali: temperatura, umidità,
  luminosità | gas, stato allarme, meteo fuori, graminacee;
- sotto, 5 grafici in bianco e nero con l'andamento **delle ultime 24 ore**:
  temperatura (interna continua + esterna tratteggiata), umidità (idem),
  gas con linea allarme ALTO/BASSO, luminosità, e pollini;
- il grafico **pollini** è diverso dagli altri: mostra la **media giornaliera
  degli ultimi 15 giorni** (un punto al giorno) per graminacee, betulla e
  ambrosia — serve a capire come sta andando la stagione, non l'ora per ora;
- tutto è dimensionato per stare **in una sola schermata** del Paperwhite.

## La dashboard (`/dashboard`)

Per Mac e telefono, interattiva:

- stessi 5 grafici, a colori, uno sotto l'altro, con tooltip al passaggio;
- selettore periodo **Oggi / Settimana / Mese** (vale per tutti i grafici
  tranne i pollini, che restano sui 15 giorni);
- il grafico pollini mostra tutte e 6 le specie;
- si aggiorna da sola ogni 5 minuti.

## L'allarme gas: come funziona davvero

Tre livelli di reazione, dal più immediato al più "storico":

1. **Subito (entro 10-40 secondi)**: l'Arduino controlla il gas ogni 10
   secondi; se rileva un aumento sospetto e persistente (3 letture consecutive
   oltre il +20% rispetto alla base), suona il buzzer con la melodia e manda
   l'alert ad Alexa tramite VoiceMonkey. Questo non dipende dal Raspberry:
   funziona anche se il server è spento.
2. **Sul Kindle e in dashboard**: il campo "Allarme gas" nella tabella e la
   linea ALTO/BASSO nel grafico gas indicano se c'è stato **almeno un allarme
   negli ultimi 10 minuti**. Anche un allarme durato 30 secondi tra un invio e
   l'altro viene registrato: l'Arduino se lo "ricorda" fino all'invio
   successivo. ALTO su un intervallo = in quei 10 minuti qualcosa è successo.
3. **Storico**: gli allarmi restano nel database per sempre, quindi nei
   periodi Settimana/Mese della dashboard si vede quando sono avvenuti.

Nota: nei primi 2-3 minuti dopo l'accensione dell'Arduino il sensore MQ2 si
sta scaldando e legge valori in salita — può scattare un falso allarme al boot.

## I pollini: come leggerli

Il valore è la **media giornaliera in grani/m³**, lo stesso formato dei
bollettini pollinici. Per le **graminacee** le fasce indicative sono:

| Fascia | grani/m³ |
|---|---|
| Bassa | sotto 30 |
| Media | 30–49 |
| Alta | 50–149 |
| Molto alta | 150 e oltre |

La riga "Graminacee" nella tabella del Kindle mostra invece l'**ultimo valore
corrente** (l'ultima lettura oraria), utile per decidere se uscire adesso.

## Cosa succede se qualcosa non va

- **Il Raspberry è spento / la rete cade**: l'Arduino continua a funzionare in
  autonomia (allarme, buzzer, Alexa, ThingSpeak, log su SD). I dati di quel
  periodo non arrivano al server e restano un buco nei grafici; nessun recupero
  retroattivo.
- **Open-Meteo non risponde**: il server salta quel giro e riprova dopo 10
  minuti; sensori e pagine continuano a funzionare.
- **Fuori stagione pollini** (o dato non disponibile): il grafico pollini
  mostra "Nessun dato" senza errori.
- **Riavvio del Raspberry**: il container riparte da solo, i dati storici sono
  al sicuro (il database vive fuori dal container).
