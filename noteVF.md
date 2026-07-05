FASE 2:

Tre note:

Quando aprirai sketch.ino nell'IDE Arduino, ti chiederà di spostarlo in una cartella chiamata sketch — accetta pure, ma tieni arduino_secrets.h nella stessa cartella dello sketch.
Il file sul Desktop (temp/:: codice attuale IDE) contiene ancora i segreti in chiaro: ti consiglio di cancellarlo quando non ti serve più.
Ho notato (senza toccarlo) che nella scrittura su SD c'è un piccolo bug pre-esistente: l'header CSV non include alarm_state e la sequenza println(mq2Value); print(","); println(alarmState); print(";") produce righe malformate. Se vuoi lo sistemiamo alla Fase 6.
