/*
  MKR ENV Shield - Read Sensors


  The circuit:
  - Arduino MKR board
  - Arduino MKR ENV Shield attached
  - Mq2 sensor
  - Buzzer attivo
  - Transistor


  ----
  - integrazione con Alexa

  I segreti (WiFi, ThingSpeak, VoiceMonkey) sono in arduino_secrets.h,
  che NON va committato: vedi arduino_secrets.h.example.
*/

#include <Arduino_MKRENV.h>
#include <SPI.h>
#include <SD.h>
#include <WiFiNINA.h>
#include <ThingSpeak.h>

#include "arduino_secrets.h"


#define NOTE_B0  31
#define NOTE_C1  33
#define NOTE_CS1 35
#define NOTE_D1  37
#define NOTE_DS1 39
#define NOTE_E1  41
#define NOTE_F1  44
#define NOTE_FS1 46
#define NOTE_G1  49
#define NOTE_GS1 52
#define NOTE_A1  55
#define NOTE_AS1 58
#define NOTE_B1  62
#define NOTE_C2  65
#define NOTE_CS2 69
#define NOTE_D2  73
#define NOTE_DS2 78
#define NOTE_E2  82
#define NOTE_F2  87
#define NOTE_FS2 93
#define NOTE_G2  98
#define NOTE_GS2 104
#define NOTE_A2  110
#define NOTE_AS2 117
#define NOTE_B2  123
#define NOTE_C3  131
#define NOTE_CS3 139
#define NOTE_D3  147
#define NOTE_DS3 156
#define NOTE_E3  165
#define NOTE_F3  175
#define NOTE_FS3 185
#define NOTE_G3  196
#define NOTE_GS3 208
#define NOTE_A3  220
#define NOTE_AS3 233
#define NOTE_B3  247
#define NOTE_C4  262
#define NOTE_CS4 277
#define NOTE_D4  294
#define NOTE_DS4 311
#define NOTE_E4  330
#define NOTE_F4  349
#define NOTE_FS4 370
#define NOTE_G4  392
#define NOTE_GS4 415
#define NOTE_A4  440
#define NOTE_AS4 466
#define NOTE_B4  494
#define NOTE_C5  523
#define NOTE_CS5 554
#define NOTE_D5  587
#define NOTE_DS5 622
#define NOTE_E5  659
#define NOTE_F5  698
#define NOTE_FS5 740
#define NOTE_G5  784
#define NOTE_GS5 831
#define NOTE_A5  880
#define NOTE_AS5 932
#define NOTE_B5  988
#define NOTE_C6  1047
#define NOTE_CS6 1109
#define NOTE_D6  1175
#define NOTE_DS6 1245
#define NOTE_E6  1319
#define NOTE_F6  1397
#define NOTE_FS6 1480
#define NOTE_G6  1568
#define NOTE_GS6 1661
#define NOTE_A6  1760
#define NOTE_AS6 1865
#define NOTE_B6  1976
#define NOTE_C7  2093
#define NOTE_CS7 2217
#define NOTE_D7  2349
#define NOTE_DS7 2489
#define NOTE_E7  2637
#define NOTE_F7  2794
#define NOTE_FS7 2960
#define NOTE_G7  3136
#define NOTE_GS7 3322
#define NOTE_A7  3520
#define NOTE_AS7 3729
#define NOTE_B7  3951
#define NOTE_C8  4186
#define NOTE_CS8 4435
#define NOTE_D8  4699
#define NOTE_DS8 4978


#define melodyPin 5

const int MQ2_PIN = A1;   // use the analog pin you wired
const int BUZZER_PIN = 5;
// const int BUTTON_PIN = 2;
// ---------- SD ----------
const int SD_CS = 4;
File dataFile;

// ---------- WiFi ----------
char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;

WiFiClient client;

// ---------- ThingSpeak ----------
unsigned long channelID = SECRET_TS_CHANNEL_ID;
const char* writeAPIKey = SECRET_TS_WRITE_APIKEY;

// ---------- Timing ----------
unsigned long lastUpdate = 0;
const unsigned long interval = 20000; // 20 seconds (ThingSpeak)

unsigned long lastSdLog = 0;
const unsigned long sdLogInterval = 600000UL; // 10 minuti (log su SD)

// ----------- allarm logic --------

const unsigned long gasSampleInterval = 10000;   // 10 secondi
unsigned long lastGasSampleTime = 0;

int gasSamples[4] = {0, 0, 0, 0};
int gasSampleCount = 0;

int latestMq2Value = 0;

bool alarmLatched = false;

int alarmState = 0; // logica per Alexa

// ---------- Mario main theme melody
int melody[] = {
  NOTE_E7, NOTE_E7, 0, NOTE_E7,
  0, NOTE_C7, NOTE_E7, 0,
  NOTE_G7, 0, 0,  0,
  NOTE_G6, 0, 0, 0,

  NOTE_C7, 0, 0, NOTE_G6,
  0, 0, NOTE_E6, 0,
  0, NOTE_A6, 0, NOTE_B6,
  0, NOTE_AS6, NOTE_A6, 0,

  NOTE_G6, NOTE_E7, NOTE_G7,
  NOTE_A7, 0, NOTE_F7, NOTE_G7,
  0, NOTE_E7, 0, NOTE_C7,
  NOTE_D7, NOTE_B6, 0, 0,

  NOTE_C7, 0, 0, NOTE_G6,
  0, 0, NOTE_E6, 0,
  0, NOTE_A6, 0, NOTE_B6,
  0, NOTE_AS6, NOTE_A6, 0,

  NOTE_G6, NOTE_E7, NOTE_G7,
  NOTE_A7, 0, NOTE_F7, NOTE_G7,
  0, NOTE_E7, 0, NOTE_C7,
  NOTE_D7, NOTE_B6, 0, 0
};
//Mario main them tempo
int tempo[] = {
  12, 12, 12, 12,
  12, 12, 12, 12,
  12, 12, 12, 12,
  12, 12, 12, 12,

  12, 12, 12, 12,
  12, 12, 12, 12,
  12, 12, 12, 12,
  12, 12, 12, 12,

  9, 9, 9,
  12, 12, 12, 12,
  12, 12, 12, 12,
  12, 12, 12, 12,

  12, 12, 12, 12,
  12, 12, 12, 12,
  12, 12, 12, 12,
  12, 12, 12, 12,

  9, 9, 9,
  12, 12, 12, 12,
  12, 12, 12, 12,
  12, 12, 12, 12,
};
//Underworld melody
int underworld_melody[] = {
  NOTE_C4, NOTE_C5, NOTE_A3, NOTE_A4,
  NOTE_AS3, NOTE_AS4, 0,
  0,
  NOTE_C4, NOTE_C5, NOTE_A3, NOTE_A4,
  NOTE_AS3, NOTE_AS4, 0,
  0,
  NOTE_F3, NOTE_F4, NOTE_D3, NOTE_D4,
  NOTE_DS3, NOTE_DS4, 0,
  0,
  NOTE_F3, NOTE_F4, NOTE_D3, NOTE_D4,
  NOTE_DS3, NOTE_DS4, 0,
  0, NOTE_DS4, NOTE_CS4, NOTE_D4,
  NOTE_CS4, NOTE_DS4,
  NOTE_DS4, NOTE_GS3,
  NOTE_G3, NOTE_CS4,
  NOTE_C4, NOTE_FS4, NOTE_F4, NOTE_E3, NOTE_AS4, NOTE_A4,
  NOTE_GS4, NOTE_DS4, NOTE_B3,
  NOTE_AS3, NOTE_A3, NOTE_GS3,
  0, 0, 0
};
//Underwolrd tempo
int underworld_tempo[] = {
  12, 12, 12, 12,
  12, 12, 6,
  3,
  12, 12, 12, 12,
  12, 12, 6,
  3,
  12, 12, 12, 12,
  12, 12, 6,
  3,
  12, 12, 12, 12,
  12, 12, 6,
  6, 18, 18, 18,
  6, 6,
  6, 6,
  6, 6,
  18, 18, 18, 18, 18, 18,
  10, 10, 10,
  10, 10, 10,
  3, 3, 3
};


void setup() {

  Serial.begin(9600);
  delay(2000);
  // while (!Serial);

  if (!ENV.begin()) {
    Serial.println("Failed to initialize MKR ENV Shield!");
    while (1);
  }

  pinMode(MQ2_PIN, INPUT);

  // SD init
  if (!SD.begin(SD_CS)) {
    Serial.println("SD initialization failed!");
    while (1);
  }
  Serial.println("SD OK");

  // WiFi init
  WiFi.begin(ssid, pass);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("WiFi connected");

  ThingSpeak.begin(client);

  // Create header if file is new
  if (!SD.exists("data.csv")) {
    dataFile = SD.open("data.csv", FILE_WRITE);
    dataFile.println("time,temperature,humidity,pressure,lux,uva,uvb,uvIndex,mq2,alarm_state");
    dataFile.close();
  }

  pinMode(5, OUTPUT);
  pinMode(13, OUTPUT);
}


void loop() {

  // buzzerSound();

    // -------- Campionamento gas ogni 10 secondi --------
  if (millis() - lastGasSampleTime >= gasSampleInterval) {
    lastGasSampleTime = millis();

    latestMq2Value = analogRead(MQ2_PIN);
    addGasSample(latestMq2Value);

    Serial.print("MQ2 sample: ");
    Serial.println(latestMq2Value);

    if (gasSampleCount == 4) {
      Serial.print("Window: ");
      Serial.print(gasSamples[0]); Serial.print(" | ");
      Serial.print(gasSamples[1]); Serial.print(" | ");
      Serial.print(gasSamples[2]); Serial.print(" | ");
      Serial.println(gasSamples[3]);
    }

    bool danger = gasDangerDetected();

    if (danger) {
        alarmState = 1;
      } else {
        alarmState = 0;
      }

    if (danger && !alarmLatched) {
      Serial.println("⚠ Gas danger detected -> start melody");
      alarmLatched = true;

      triggerAlexaGasAlert();

      while (client.connected()) {
        String line = client.readStringUntil('\n');
        Serial.println(line);
      }


      sing(1);   // Mario theme
      sing(1);
      sing(2);
    }

    // resetta il latch quando il pericolo non c'è più
    if (!danger) {
      alarmLatched = false;
    }
  }


  if (millis() - lastUpdate >= interval) {
    lastUpdate = millis();

    float temperature = ENV.readTemperature() - 4.0F;
    float humidity    = ENV.readHumidity();
    float pressure    = ENV.readPressure();
    float illuminance = ENV.readIlluminance();
    int mq2Value      = analogRead(MQ2_PIN);

    // ---------- Send to ThingSpeak ----------
    ThingSpeak.setField(1, temperature);
    ThingSpeak.setField(2, humidity);
    ThingSpeak.setField(3, pressure);
    ThingSpeak.setField(4, illuminance);
    ThingSpeak.setField(5, mq2Value);
    ThingSpeak.setField(6, alarmState);

    // ThingSpeak.writeFields(channelID, writeAPIKey);
    // Serial.println("Data logged & sent.");

    int status = ThingSpeak.writeFields(channelID, writeAPIKey);

    if (status == 200) {
      Serial.println("ThingSpeak update OK");
    } else {
      Serial.print("ThingSpeak error: ");
      Serial.println(status);
    }


    // // ---------- Verify SD content ----------
    // File verifyFile = SD.open("data.csv");
    // if (verifyFile) {
    //   Serial.println("---- SD Content ----");
    //   while (verifyFile.available()) {
    //     Serial.write(verifyFile.read());
    //   }
    //   Serial.println("\n--------------------");
    //   verifyFile.close();
    // } else {
    //   Serial.println("Failed to open file for verification");
    // }
  }


  // -------- Log su SD ogni 10 minuti --------
  if (millis() - lastSdLog >= sdLogInterval) {
    lastSdLog = millis();

    float temperature = ENV.readTemperature() - 4.0F;
    float humidity    = ENV.readHumidity();
    float pressure    = ENV.readPressure();
    float illuminance = ENV.readIlluminance();
    float uva         = ENV.readUVA();
    float uvb         = ENV.readUVB();
    float uvIndex     = ENV.readUVIndex();
    int mq2Value      = analogRead(MQ2_PIN);

    unsigned long timestamp = millis() / 1000;

    dataFile = SD.open("data.csv", FILE_WRITE);
    if (dataFile) {
      dataFile.print(timestamp); dataFile.print(",");
      dataFile.print(temperature); dataFile.print(",");
      dataFile.print(humidity); dataFile.print(",");
      dataFile.print(pressure); dataFile.print(",");
      dataFile.print(illuminance); dataFile.print(",");
      dataFile.print(uva); dataFile.print(",");
      dataFile.print(uvb); dataFile.print(",");
      dataFile.print(uvIndex); dataFile.print(",");
      dataFile.print(mq2Value); dataFile.print(",");
      dataFile.println(alarmState);
      dataFile.close();
      Serial.println("SD log scritto");
    } else {
      Serial.println("SD: apertura data.csv fallita");
    }
  }
}

int song = 0;

void buzzerSound() {
  digitalWrite(BUZZER_PIN, HIGH);  // buzzer ON
  delay(1000);

  digitalWrite(BUZZER_PIN, LOW);   // buzzer OFF
  delay(1000);

  digitalWrite(BUZZER_PIN, HIGH);  // buzzer ON
  delay(1000);

  digitalWrite(BUZZER_PIN, LOW);   // buzzer OFF
  delay(1000);

  digitalWrite(BUZZER_PIN, HIGH);  // buzzer ON
  delay(1000);

  digitalWrite(BUZZER_PIN, LOW);   // buzzer OFF
  delay(1000);

  //sing the tunes
  sing(1);
  sing(1);
  // sing(2);
}

void sing(int s) {
  // iterate over the notes of the melody:
  song = s;
  if (song == 2) {
    Serial.println(" 'Underworld Theme'");
    int size = sizeof(underworld_melody) / sizeof(int);
    for (int thisNote = 0; thisNote < size; thisNote++) {

      // to calculate the note duration, take one second
      // divided by the note type.
      //e.g. quarter note = 1000 / 4, eighth note = 1000/8, etc.
      int noteDuration = 1000 / underworld_tempo[thisNote];

      buzz(melodyPin, underworld_melody[thisNote], noteDuration);

      // to distinguish the notes, set a minimum time between them.
      // the note's duration + 30% seems to work well:
      int pauseBetweenNotes = noteDuration * 1.30;
      delay(pauseBetweenNotes);

      // stop the tone playing:
      buzz(melodyPin, 0, noteDuration);

    }

  } else {

    Serial.println(" 'Mario Theme'");
    int size = sizeof(melody) / sizeof(int);
    for (int thisNote = 0; thisNote < size; thisNote++) {

      // to calculate the note duration, take one second
      // divided by the note type.
      //e.g. quarter note = 1000 / 4, eighth note = 1000/8, etc.
      int noteDuration = 1000 / tempo[thisNote];

      buzz(melodyPin, melody[thisNote], noteDuration);

      // to distinguish the notes, set a minimum time between them.
      // the note's duration + 30% seems to work well:
      int pauseBetweenNotes = noteDuration * 1.30;
      delay(pauseBetweenNotes);

      // stop the tone playing:
      buzz(melodyPin, 0, noteDuration);

    }
  }
}

void buzz(int targetPin, long frequency, long length) {
  digitalWrite(13, HIGH);
  long delayValue = 1000000 / frequency / 2; // calculate the delay value between transitions
  //// 1 second's worth of microseconds, divided by the frequency, then split in half since
  //// there are two phases to each cycle
  long numCycles = frequency * length / 1000; // calculate the number of cycles for proper timing
  //// multiply frequency, which is really cycles per second, by the number of seconds to
  //// get the total number of cycles to produce
  for (long i = 0; i < numCycles; i++) { // for the calculated length of time...
    digitalWrite(targetPin, HIGH); // write the buzzer pin high to push out the diaphram
    delayMicroseconds(delayValue); // wait for the calculated delay value
    digitalWrite(targetPin, LOW); // write the buzzer pin low to pull back the diaphram
    delayMicroseconds(delayValue); // wait again or the calculated delay value
  }
  digitalWrite(13, LOW);

}


void addGasSample(int sample) {
  gasSamples[0] = gasSamples[1];
  gasSamples[1] = gasSamples[2];
  gasSamples[2] = gasSamples[3];
  gasSamples[3] = sample;

  if (gasSampleCount < 4) {
    gasSampleCount++;
  }
}

bool gasDangerDetected() {
  if (gasSampleCount < 4) {
    return false;
  }

  int baseline = gasSamples[0];
  if (baseline <= 0) {
    return false;
  }

  float threshold = baseline * 1.20;

  return (
    gasSamples[1] > threshold &&
    gasSamples[2] > threshold &&
    gasSamples[3] > threshold
  );
}


void triggerAlexaGasAlert() {

  WiFiSSLClient client;

  Serial.println("Calling VoiceMonkey...");

  if (client.connect("api-v2.voicemonkey.io", 443)) {

    client.print("GET /trigger?token=");
    client.print(SECRET_VOICEMONKEY_TOKEN);
    client.print("&device=");
    client.print(VOICEMONKEY_DEVICE);
    client.println(" HTTP/1.1");
    client.println("Host: api-v2.voicemonkey.io");
    client.println("Connection: close");
    client.println();

    while (client.connected()) {
      String line = client.readStringUntil('\n');
      Serial.println(line);
    }

  } else {

    Serial.println("VoiceMonkey connection failed");

  }

}
