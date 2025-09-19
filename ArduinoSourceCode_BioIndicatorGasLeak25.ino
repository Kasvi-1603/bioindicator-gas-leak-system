#define BLYNK_TEMPLATE_ID "TMPL3kioqArG5"
#define BLYNK_TEMPLATE_NAME "Moss Gas Leak Detection System"
#define BLYNK_AUTH_TOKEN "I5w3dPSYuRvOBRK_DSS8XQF1HhRsAeoS"

#include <WiFi.h>
#include <BlynkSimpleEsp32.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BMP085_U.h>
#include <DHT.h>

// ==== WiFi Credentials ====
char ssid[] = "abc";       
char pass[] = "xyz";               

// ==== DHT22 Settings ====
#define DHTPIN 4
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

// ==== LM35 ====
#define LM35PIN 34

// ==== KY-038 Sound Sensor ====
#define SOUND_PIN 35

// ==== BMP180 Sensor ====
Adafruit_BMP085_Unified bmp = Adafruit_BMP085_Unified(10085);

// ==== Serial Message Buffer ====
String incomingData = "";

void setup() {
  Serial.begin(115200);
  delay(2000);

  Blynk.begin(BLYNK_AUTH_TOKEN, ssid, pass);

  Serial.println("Initializing DHT22...");
  dht.begin();

  Serial.println("Initializing BMP180...");
  if (!bmp.begin()) {
    Serial.println("BMP180 not found. Check wiring!");
    while (1);
  }

  Serial.println("Setup complete.\n");
}

void loop() {
  Blynk.run();

  // === Handle Serial Command from Python ===
  if (Serial.available()) {
    incomingData = Serial.readStringUntil('\n');
    incomingData.trim();

    Serial.println("Received from Serial: " + incomingData);

    if (incomingData == "ALERT") {
      Serial.println("Triggering Blynk logEvent...");
      Blynk.logEvent("cv_alert", "⚠ Moss gas leak detected by Python script");
    }
  }

  // === Sensor Readings ===
  Serial.println("==== Sensor Readings ====");

  // --- DHT22 ---
  float dhtTemp = dht.readTemperature();
  float dhtHum = dht.readHumidity();

  if (!isnan(dhtTemp) && !isnan(dhtHum)) {
    Serial.print("DHT22 Temp: "); Serial.print(dhtTemp); Serial.println(" °C");
    Serial.print("DHT22 Humidity: "); Serial.print(dhtHum); Serial.println(" %");

    Blynk.virtualWrite(V0, dhtTemp);
    Blynk.virtualWrite(V1, dhtHum);
  } else {
    Serial.println("DHT22 read failed.");
  }

  // --- LM35 ---
  int lmRaw = analogRead(LM35PIN);
  float lmVoltage = lmRaw * (3.3 / 4095.0);  
  float lmTemp = lmVoltage * 100.0;
  Serial.print("LM35 Temp: "); Serial.print(lmTemp); Serial.println(" °C");
  Blynk.virtualWrite(V2, lmTemp);

  // --- KY-038 ---
  int soundLevel = analogRead(SOUND_PIN);
  Serial.print("KY-038 Sound Level: "); Serial.println(soundLevel);
  Blynk.virtualWrite(V3, soundLevel);

  // --- BMP180 ---
  sensors_event_t event;
  bmp.getEvent(&event);

  if (event.pressure) {
    float pressure_hPa = event.pressure;
    float pressure_kPa = pressure_hPa / 10.0;

    Serial.print("BMP180 Pressure: "); Serial.print(pressure_kPa); Serial.println(" kPa");

    float bmpTemp;
    bmp.getTemperature(&bmpTemp);
    Serial.print("BMP180 Temp: "); Serial.print(bmpTemp); Serial.println(" °C");

    Blynk.virtualWrite(V4, pressure_kPa);
    Blynk.virtualWrite(V5, bmpTemp);

    if (pressure_kPa > 91.0) {
      Blynk.virtualWrite(V7, "⚠ High Pressure!");
      Blynk.logEvent("pressure_alert", "⚠ Pressure exceeds 105 kPa!");
    } else {
      Blynk.virtualWrite(V7, "Normal");
    }
  } else {
    Serial.println("BMP180 read failed.");
  }

  // --- Sound Alert ---
  if (soundLevel > 2500) {
    Blynk.virtualWrite(V8, "🔊 Loud Sound Detected!");
    Blynk.logEvent("sound_alert", "🔊 Sound level too high!");
  } else {
    Blynk.virtualWrite(V8, "Normal");
  }

  Serial.println("==========================\n");
  delay(3000);  // 3-second delay
}