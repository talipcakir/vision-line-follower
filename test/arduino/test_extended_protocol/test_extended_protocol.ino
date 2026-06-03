// ============================================================
//  GENİŞLETİLMİŞ PROTOKOL TESTİ - Arduino
// ============================================================
//
//  AMAC:
//  v2.0 protokolündeki tüm komutları test etmek için
//  kullanılır. PID ve sensör komutları dahil.
//
//  KULLANIM:
//  1. Bu kodu Arduino'ya yükleyin
//  2. Serial Monitor açın (9600 baud)
//  3. Komutları test edin
//
//  TEST KOMUTLARI:
//  PING           -> PONG
//  VERSION        -> VERSION:2.0.0
//  SPEED:100      -> OK_SPEED:100
//  PID:1.5,0.1,0.5 -> OK_PID:1.5,0.1,0.5
//  CONFIG         -> CONFIG:100,1.50,0.10,0.50
//  SENSORS        -> SENSORS:0,1,1,0,0
//  SAVE           -> OK_SAVED
//  LOAD           -> OK_LOADED
//  RESET          -> OK_RESET
//  STOP           -> OK_STOPPED
//  GO             -> OK_RUNNING
//  STATUS         -> STATUS_STOPPED | STATUS_RUNNING
//
// ============================================================

#include <EEPROM.h>

const char* VERSION = "2.0.0";

// Simüle edilmiş sensör değerleri
int sensorValues[5] = {0, 1, 1, 0, 0};

// Ayarlar
int baseSpeed = 100;
float Kp = 1.0, Ki = 0.0, Kd = 0.5;
bool robotStopped = false;

// EEPROM
const int EEPROM_MAGIC = 0;
const int EEPROM_SPEED = 1;
const int EEPROM_KP = 2;
const int EEPROM_KI = 6;
const int EEPROM_KD = 10;
const byte EEPROM_MAGIC_VALUE = 0xAB;

String serialBuffer = "";

void setup() {
  Serial.begin(9600);
  loadSettings();

  Serial.println("========================================");
  Serial.println("  GENISLETILMIS PROTOKOL TESTI v2.0");
  Serial.println("========================================");
  Serial.println("");
  Serial.println("Kullanilabilir komutlar:");
  Serial.println("  PING, VERSION, STATUS");
  Serial.println("  STOP, GO");
  Serial.println("  SPEED:<0-255>");
  Serial.println("  PID:<Kp>,<Ki>,<Kd>");
  Serial.println("  CONFIG, SENSORS");
  Serial.println("  SAVE, LOAD, RESET");
  Serial.println("");
  Serial.println("ROBOT_READY");
}

void loop() {
  // Sensör değerlerini rastgele değiştir (test için)
  static unsigned long lastChange = 0;
  if (millis() - lastChange > 500) {
    lastChange = millis();
    // Orta sensörü genelde aktif tut
    sensorValues[2] = 1;
    // Diğerlerini rastgele
    for (int i = 0; i < 5; i++) {
      if (i != 2 && random(10) < 3) {
        sensorValues[i] = 1 - sensorValues[i];
      }
    }
  }

  // Seri komutları işle
  while (Serial.available() > 0) {
    char c = Serial.read();

    if (c == '\n') {
      serialBuffer.trim();
      handleCommand(serialBuffer);
      serialBuffer = "";
    } else {
      serialBuffer += c;
    }
  }
}

void handleCommand(String cmd) {
  if (cmd == "PING") {
    Serial.println("PONG");
  }
  else if (cmd == "VERSION") {
    Serial.print("VERSION:");
    Serial.println(VERSION);
  }
  else if (cmd == "STOP") {
    robotStopped = true;
    Serial.println("OK_STOPPED");
  }
  else if (cmd == "GO") {
    robotStopped = false;
    Serial.println("OK_RUNNING");
  }
  else if (cmd == "STATUS") {
    Serial.println(robotStopped ? "STATUS_STOPPED" : "STATUS_RUNNING");
  }
  else if (cmd == "SENSORS") {
    Serial.print("SENSORS:");
    for (int i = 0; i < 5; i++) {
      Serial.print(sensorValues[i]);
      if (i < 4) Serial.print(",");
    }
    Serial.println();
  }
  else if (cmd == "CONFIG") {
    Serial.print("CONFIG:");
    Serial.print(baseSpeed);
    Serial.print(",");
    Serial.print(Kp, 2);
    Serial.print(",");
    Serial.print(Ki, 2);
    Serial.print(",");
    Serial.println(Kd, 2);
  }
  else if (cmd.startsWith("SPEED:")) {
    int newSpeed = cmd.substring(6).toInt();
    baseSpeed = constrain(newSpeed, 0, 255);
    Serial.print("OK_SPEED:");
    Serial.println(baseSpeed);
  }
  else if (cmd.startsWith("PID:")) {
    String params = cmd.substring(4);
    int comma1 = params.indexOf(',');
    int comma2 = params.lastIndexOf(',');

    if (comma1 > 0 && comma2 > comma1) {
      Kp = constrain(params.substring(0, comma1).toFloat(), 0.0, 10.0);
      Ki = constrain(params.substring(comma1 + 1, comma2).toFloat(), 0.0, 5.0);
      Kd = constrain(params.substring(comma2 + 1).toFloat(), 0.0, 10.0);

      Serial.print("OK_PID:");
      Serial.print(Kp, 2);
      Serial.print(",");
      Serial.print(Ki, 2);
      Serial.print(",");
      Serial.println(Kd, 2);
    } else {
      Serial.println("ERROR:INVALID_PID_FORMAT");
    }
  }
  else if (cmd == "SAVE") {
    saveSettings();
    Serial.println("OK_SAVED");
  }
  else if (cmd == "LOAD") {
    loadSettings();
    Serial.println("OK_LOADED");
  }
  else if (cmd == "RESET") {
    baseSpeed = 100;
    Kp = 1.0;
    Ki = 0.0;
    Kd = 0.5;
    Serial.println("OK_RESET");
  }
  else if (cmd == "HELP") {
    Serial.println("Komutlar: PING, VERSION, STOP, GO, STATUS,");
    Serial.println("SPEED:<n>, PID:<Kp>,<Ki>,<Kd>, CONFIG,");
    Serial.println("SENSORS, SAVE, LOAD, RESET, HELP");
  }
  else if (cmd.length() > 0) {
    Serial.print("ERROR:UNKNOWN_CMD:");
    Serial.println(cmd);
  }
}

void saveSettings() {
  EEPROM.write(EEPROM_MAGIC, EEPROM_MAGIC_VALUE);
  EEPROM.write(EEPROM_SPEED, baseSpeed);
  EEPROM.put(EEPROM_KP, Kp);
  EEPROM.put(EEPROM_KI, Ki);
  EEPROM.put(EEPROM_KD, Kd);
}

void loadSettings() {
  if (EEPROM.read(EEPROM_MAGIC) == EEPROM_MAGIC_VALUE) {
    baseSpeed = constrain(EEPROM.read(EEPROM_SPEED), 0, 255);
    EEPROM.get(EEPROM_KP, Kp);
    EEPROM.get(EEPROM_KI, Ki);
    EEPROM.get(EEPROM_KD, Kd);
    Kp = constrain(Kp, 0.0, 10.0);
    Ki = constrain(Ki, 0.0, 5.0);
    Kd = constrain(Kd, 0.0, 10.0);
  }
}
