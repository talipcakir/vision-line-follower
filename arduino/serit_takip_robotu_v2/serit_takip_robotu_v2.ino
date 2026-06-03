// ============================================================
//  SERIT TAKIP ROBOTU v2.0 - PID Kontrol + Web Yönetim
//  Dönem Bitirme Projesi
// ============================================================
//
//  YENİ ÖZELLİKLER:
//  - PID kontrol ile yumuşak dönüşler
//  - Web arayüzünden hız ve PID ayarı
//  - Sensör değerlerini okuma
//  - Heartbeat desteği
//  - EEPROM ile ayar saklama
//
//  KOMUTLAR:
//  PING              -> PONG
//  STOP              -> OK_STOPPED
//  GO                -> OK_RUNNING
//  STATUS            -> STATUS_STOPPED | STATUS_RUNNING
//  SPEED:<0-255>     -> OK_SPEED:<value>
//  PID:<Kp>,<Ki>,<Kd> -> OK_PID:<Kp>,<Ki>,<Kd>
//  SENSORS           -> SENSORS:<s1>,<s2>,<s3>,<s4>,<s5>
//  CONFIG            -> CONFIG:<speed>,<Kp>,<Ki>,<Kd>
//  SAVE              -> OK_SAVED
//  LOAD              -> OK_LOADED
//  VERSION           -> VERSION:2.0.0
//  RESET             -> OK_RESET
//
// ============================================================

#include <EEPROM.h>

// ============================================================
//  VERSİYON
// ============================================================
const char* FIRMWARE_VERSION = "2.0.0";

// ============================================================
//  PIN TANIMLARI
// ============================================================

// Sol Motor (L298N)
const int pinENA = 6;   // PWM hız
const int pinIN1 = 10;  // Yön A
const int pinIN2 = 11;  // Yön B

// Sağ Motor (L298N)
const int pinENB = 5;   // PWM hız
const int pinIN3 = 8;   // Yön A
const int pinIN4 = 9;   // Yön B

// IR Sensörler (soldan sağa)
const int pinS1 = 2;    // En sol
const int pinS2 = 3;    // Hafif sol
const int pinS3 = 4;    // Orta
const int pinS4 = 7;    // Hafif sağ
const int pinS5 = 12;   // En sağ

// ============================================================
//  AYARLAR VE DEĞİŞKENLER
// ============================================================

// Hız ayarı (0-255)
int baseSpeed = 100;

// PID parametreleri
float Kp = 1.0;
float Ki = 0.0;
float Kd = 0.5;

// PID değişkenleri
float lastError = 0;
float integral = 0;

// Durum
bool robotStopped = false;
String serialBuffer = "";

// Son bilinen hata yönü (çizgi kaybında kullanılır)
int lastDirection = 0;  // -1: sol, 0: düz, 1: sağ

// EEPROM adresleri
const int EEPROM_MAGIC = 0;      // Geçerlilik bayrağı
const int EEPROM_SPEED = 1;      // baseSpeed
const int EEPROM_KP = 2;         // Kp (4 byte float)
const int EEPROM_KI = 6;         // Ki (4 byte float)
const int EEPROM_KD = 10;        // Kd (4 byte float)
const byte EEPROM_MAGIC_VALUE = 0xAB;

// ============================================================
//  SETUP
// ============================================================
void setup() {
  Serial.begin(9600);

  // Motor pinleri
  pinMode(pinENA, OUTPUT);
  pinMode(pinIN1, OUTPUT);
  pinMode(pinIN2, OUTPUT);
  pinMode(pinENB, OUTPUT);
  pinMode(pinIN3, OUTPUT);
  pinMode(pinIN4, OUTPUT);

  // Sensör pinleri
  pinMode(pinS1, INPUT);
  pinMode(pinS2, INPUT);
  pinMode(pinS3, INPUT);
  pinMode(pinS4, INPUT);
  pinMode(pinS5, INPUT);

  // Motor yönü: ileri
  digitalWrite(pinIN1, HIGH);
  digitalWrite(pinIN2, LOW);
  digitalWrite(pinIN3, HIGH);
  digitalWrite(pinIN4, LOW);

  // EEPROM'dan ayarları yükle
  loadSettings();

  Serial.println("ROBOT_READY");
}

// ============================================================
//  ANA DÖNGÜ
// ============================================================
void loop() {
  // Seri komutları işle
  processSerial();

  // Robot durdurulmuşsa motorları kapat
  if (robotStopped) {
    analogWrite(pinENA, 0);
    analogWrite(pinENB, 0);
    return;
  }

  // Sensörleri oku ve PID ile motor kontrolü yap
  int error = calculateError();
  int pidOutput = calculatePID(error);
  applyMotorSpeeds(pidOutput);
}

// ============================================================
//  SERİ KOMUT İŞLEME
// ============================================================
void processSerial() {
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
  // PING: Bağlantı testi
  if (cmd == "PING") {
    Serial.println("PONG");
  }
  // STOP: Robotu durdur
  else if (cmd == "STOP") {
    robotStopped = true;
    Serial.println("OK_STOPPED");
  }
  // GO: Robota devam et
  else if (cmd == "GO") {
    robotStopped = false;
    integral = 0;  // PID integralini sıfırla
    lastError = 0;
    Serial.println("OK_RUNNING");
  }
  // STATUS: Durum sorgula
  else if (cmd == "STATUS") {
    Serial.println(robotStopped ? "STATUS_STOPPED" : "STATUS_RUNNING");
  }
  // VERSION: Firmware versiyonu
  else if (cmd == "VERSION") {
    Serial.print("VERSION:");
    Serial.println(FIRMWARE_VERSION);
  }
  // SENSORS: Sensör değerlerini oku
  else if (cmd == "SENSORS") {
    Serial.print("SENSORS:");
    Serial.print(digitalRead(pinS1));
    Serial.print(",");
    Serial.print(digitalRead(pinS2));
    Serial.print(",");
    Serial.print(digitalRead(pinS3));
    Serial.print(",");
    Serial.print(digitalRead(pinS4));
    Serial.print(",");
    Serial.println(digitalRead(pinS5));
  }
  // CONFIG: Mevcut ayarları göster
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
  // SPEED:<value>: Hız ayarla
  else if (cmd.startsWith("SPEED:")) {
    int newSpeed = cmd.substring(6).toInt();
    newSpeed = constrain(newSpeed, 0, 255);
    baseSpeed = newSpeed;
    Serial.print("OK_SPEED:");
    Serial.println(baseSpeed);
  }
  // PID:<Kp>,<Ki>,<Kd>: PID parametrelerini ayarla
  else if (cmd.startsWith("PID:")) {
    String params = cmd.substring(4);
    int comma1 = params.indexOf(',');
    int comma2 = params.lastIndexOf(',');

    if (comma1 > 0 && comma2 > comma1) {
      Kp = params.substring(0, comma1).toFloat();
      Ki = params.substring(comma1 + 1, comma2).toFloat();
      Kd = params.substring(comma2 + 1).toFloat();

      // Sınırla
      Kp = constrain(Kp, 0.0, 10.0);
      Ki = constrain(Ki, 0.0, 5.0);
      Kd = constrain(Kd, 0.0, 10.0);

      // İntegrali sıfırla
      integral = 0;

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
  // SAVE: Ayarları EEPROM'a kaydet
  else if (cmd == "SAVE") {
    saveSettings();
    Serial.println("OK_SAVED");
  }
  // LOAD: Ayarları EEPROM'dan yükle
  else if (cmd == "LOAD") {
    loadSettings();
    Serial.println("OK_LOADED");
  }
  // RESET: Varsayılan ayarlara dön
  else if (cmd == "RESET") {
    baseSpeed = 100;
    Kp = 1.0;
    Ki = 0.0;
    Kd = 0.5;
    integral = 0;
    lastError = 0;
    Serial.println("OK_RESET");
  }
  // Bilinmeyen komut
  else if (cmd.length() > 0) {
    Serial.print("ERROR:UNKNOWN_CMD:");
    Serial.println(cmd);
  }
}

// ============================================================
//  EEPROM FONKSİYONLARI
// ============================================================
void saveSettings() {
  EEPROM.write(EEPROM_MAGIC, EEPROM_MAGIC_VALUE);
  EEPROM.write(EEPROM_SPEED, baseSpeed);
  EEPROM.put(EEPROM_KP, Kp);
  EEPROM.put(EEPROM_KI, Ki);
  EEPROM.put(EEPROM_KD, Kd);
}

void loadSettings() {
  if (EEPROM.read(EEPROM_MAGIC) == EEPROM_MAGIC_VALUE) {
    baseSpeed = EEPROM.read(EEPROM_SPEED);
    EEPROM.get(EEPROM_KP, Kp);
    EEPROM.get(EEPROM_KI, Ki);
    EEPROM.get(EEPROM_KD, Kd);

    // Geçerlilik kontrolü
    baseSpeed = constrain(baseSpeed, 0, 255);
    Kp = constrain(Kp, 0.0, 10.0);
    Ki = constrain(Ki, 0.0, 5.0);
    Kd = constrain(Kd, 0.0, 10.0);
  }
}

// ============================================================
//  PID KONTROL
// ============================================================

// Sensörlerden hata hesapla
// Hata: -2 (en sol) ile +2 (en sağ) arası
int calculateError() {
  int s1 = digitalRead(pinS1);  // En sol
  int s2 = digitalRead(pinS2);  // Hafif sol
  int s3 = digitalRead(pinS3);  // Orta
  int s4 = digitalRead(pinS4);  // Hafif sağ
  int s5 = digitalRead(pinS5);  // En sağ

  // Ağırlıklı ortalama ile hata hesapla
  // HIGH = çizgi var (siyah), LOW = çizgi yok (beyaz)
  // Sensör ağırlıkları: -2, -1, 0, +1, +2

  int sum = s1 + s2 + s3 + s4 + s5;

  if (sum == 0) {
    // Hiç sensör çizgi görmüyor - son yöne devam et
    return lastDirection * 3;
  }

  float weightedSum = (s1 * -2) + (s2 * -1) + (s3 * 0) + (s4 * 1) + (s5 * 2);
  float error = weightedSum / sum;

  // Son yönü güncelle
  if (error < -0.5) lastDirection = -1;
  else if (error > 0.5) lastDirection = 1;
  else lastDirection = 0;

  return (int)(error * 10);  // -20 ile +20 arası
}

// PID çıktısı hesapla
int calculatePID(int error) {
  // Proportional
  float P = Kp * error;

  // Integral (windup önleme ile)
  integral += error;
  integral = constrain(integral, -100, 100);
  float I = Ki * integral;

  // Derivative
  float D = Kd * (error - lastError);
  lastError = error;

  // Toplam PID çıktısı
  int output = (int)(P + I + D);
  return constrain(output, -baseSpeed, baseSpeed);
}

// Motor hızlarını uygula
void applyMotorSpeeds(int pidOutput) {
  int leftSpeed = baseSpeed + pidOutput;
  int rightSpeed = baseSpeed - pidOutput;

  // Hız sınırları
  leftSpeed = constrain(leftSpeed, 0, 255);
  rightSpeed = constrain(rightSpeed, 0, 255);

  // Motorlara uygula
  analogWrite(pinENA, leftSpeed);
  analogWrite(pinENB, rightSpeed);
}

// ============================================================
//  KODUN SONU
// ============================================================
