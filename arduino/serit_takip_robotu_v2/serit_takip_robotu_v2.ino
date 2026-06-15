// ============================================================
//  SERIT TAKIP ROBOTU v2.2 - Akıllı Çizgi Arama + Pi Entegrasyonu
//  Dönem Bitirme Projesi
// ============================================================
//
//  SENSÖR: Siyah çizgi = 0 (LOW), Beyaz zemin = 1 (HIGH)
//
//  KOMUTLAR:
//  PING              -> PONG
//  STOP              -> OK_STOPPED
//  GO                -> OK_RUNNING
//  STATUS            -> STATUS_STOPPED | STATUS_RUNNING | STATUS_SEARCHING
//  SPEED:<0-255>     -> OK_SPEED:<value>
//  PID:<Kp>,<Ki>,<Kd> -> OK_PID:<Kp>,<Ki>,<Kd>
//  SENSORS           -> SENSORS:<s1>,<s2>,<s3>,<s4>,<s5>
//  CONFIG            -> CONFIG:<speed>,<Kp>,<Ki>,<Kd>
//  SAVE              -> OK_SAVED
//  LOAD              -> OK_LOADED
//  VERSION           -> VERSION:2.2.0
//  RESET             -> OK_RESET
//
// ============================================================

#include <EEPROM.h>

const char* FIRMWARE_VERSION = "2.2.0";

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
//  SENSÖR POLARİTESİ
// ============================================================
// SIYAH çizgi üzerinde sensör 0 (LOW) veriyor
// BEYAZ zemin üzerinde sensör 1 (HIGH) veriyor
const int CIZGI = 0;  // Çizgi algılandığında okunan değer

// ============================================================
//  AYARLAR
// ============================================================

int baseSpeed = 150;
int searchSpeed = 100;
int reverseSpeed = 80;

// PID parametreleri
float Kp = 1.5;
float Ki = 0.0;
float Kd = 0.8;

// PID değişkenleri
float lastError = 0;
float integral = 0;

// Robot durumları
enum RobotState {
  STATE_STOPPED,
  STATE_RUNNING,
  STATE_SEARCHING,
  STATE_REVERSING
};

RobotState robotState = STATE_STOPPED;
String serialBuffer = "";

// Çizgi takip değişkenleri
int lastDirection = 0;           // -1: sol, 0: düz, 1: sağ
unsigned long lastLineTime = 0;  // Son çizgi görülme zamanı
unsigned long searchStartTime = 0;
int searchPhase = 0;

// Zaman sabitleri (ms)
const unsigned long SEARCH_TIMEOUT = 300;    // Çizgi kaybolunca aramaya başla
const unsigned long REVERSE_TIME = 250;      // Geri gitme süresi
const unsigned long SEARCH_PHASE_TIME = 350; // Her arama fazı süresi
const int MAX_SEARCH_PHASES = 8;             // Maksimum arama fazı

// EEPROM
const int EEPROM_MAGIC = 0;
const int EEPROM_SPEED = 1;
const int EEPROM_KP = 2;
const int EEPROM_KI = 6;
const int EEPROM_KD = 10;
const byte EEPROM_MAGIC_VALUE = 0xAD;

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

  stopMotors();
  loadSettings();

  delay(100);
  Serial.println("ROBOT_READY");
}

// ============================================================
//  ANA DÖNGÜ
// ============================================================
void loop() {
  processSerial();

  if (robotState == STATE_STOPPED) {
    stopMotors();
    return;
  }

  // Sensörleri oku (0 = çizgi, 1 = beyaz)
  int s1 = digitalRead(pinS1);
  int s2 = digitalRead(pinS2);
  int s3 = digitalRead(pinS3);
  int s4 = digitalRead(pinS4);
  int s5 = digitalRead(pinS5);

  // Kaç sensör çizgi görüyor?
  int lineCount = 0;
  if (s1 == CIZGI) lineCount++;
  if (s2 == CIZGI) lineCount++;
  if (s3 == CIZGI) lineCount++;
  if (s4 == CIZGI) lineCount++;
  if (s5 == CIZGI) lineCount++;

  unsigned long currentTime = millis();

  // Çizgi görülüyor mu?
  if (lineCount > 0) {
    lastLineTime = currentTime;

    if (robotState == STATE_SEARCHING || robotState == STATE_REVERSING) {
      robotState = STATE_RUNNING;
      integral = 0;
      lastError = 0;
      searchPhase = 0;
    }

    // PID takip
    int error = calculateError(s1, s2, s3, s4, s5, lineCount);
    int pidOutput = calculatePID(error);
    applyMotorSpeeds(pidOutput);
  }
  else {
    // Çizgi kayıp!
    handleLineLost(currentTime);
  }
}

// ============================================================
//  HATA HESAPLAMA
// ============================================================
int calculateError(int s1, int s2, int s3, int s4, int s5, int lineCount) {
  // Ağırlıklı ortalama: -2 (sol) ile +2 (sağ) arası
  // CIZGI (0) gören sensörler hesaba katılır
  int weightedSum = 0;

  if (s1 == CIZGI) weightedSum += -2;
  if (s2 == CIZGI) weightedSum += -1;
  if (s3 == CIZGI) weightedSum += 0;
  if (s4 == CIZGI) weightedSum += 1;
  if (s5 == CIZGI) weightedSum += 2;

  float position = (float)weightedSum / lineCount;

  // Son yönü güncelle
  if (position < -0.5) lastDirection = -1;
  else if (position > 0.5) lastDirection = 1;
  else lastDirection = 0;

  return (int)(position * 10);  // -20 ile +20 arası
}

// ============================================================
//  PID KONTROL
// ============================================================
int calculatePID(int error) {
  float P = Kp * error;

  integral += error;
  integral = constrain(integral, -100, 100);
  float I = Ki * integral;

  float D = Kd * (error - lastError);
  lastError = error;

  int output = (int)(P + I + D);
  return constrain(output, -baseSpeed, baseSpeed);
}

void applyMotorSpeeds(int pidOutput) {
  int leftSpeed = baseSpeed + pidOutput;
  int rightSpeed = baseSpeed - pidOutput;

  leftSpeed = constrain(leftSpeed, 0, 255);
  rightSpeed = constrain(rightSpeed, 0, 255);

  // İleri yön
  digitalWrite(pinIN1, HIGH);
  digitalWrite(pinIN2, LOW);
  digitalWrite(pinIN3, HIGH);
  digitalWrite(pinIN4, LOW);

  analogWrite(pinENA, leftSpeed);
  analogWrite(pinENB, rightSpeed);
}

// ============================================================
//  ÇİZGİ ARAMA
// ============================================================
void handleLineLost(unsigned long currentTime) {
  unsigned long lostDuration = currentTime - lastLineTime;

  // İlk kısa süre: son yöne doğru git
  if (lostDuration < SEARCH_TIMEOUT) {
    if (lastDirection < 0) {
      setMotors(-searchSpeed, searchSpeed);  // Sola dön
    } else if (lastDirection > 0) {
      setMotors(searchSpeed, -searchSpeed);  // Sağa dön
    } else {
      setMotors(searchSpeed, searchSpeed);   // Düz git
    }
    return;
  }

  // Arama moduna geç
  if (robotState != STATE_SEARCHING && robotState != STATE_REVERSING) {
    robotState = STATE_REVERSING;
    searchStartTime = currentTime;
    searchPhase = 0;
  }

  // Geri gitme fazı
  if (robotState == STATE_REVERSING) {
    if (currentTime - searchStartTime < REVERSE_TIME) {
      setMotorsReverse(reverseSpeed, reverseSpeed);
    } else {
      robotState = STATE_SEARCHING;
      searchStartTime = currentTime;
      searchPhase = 0;
    }
    return;
  }

  // Zigzag arama
  if (robotState == STATE_SEARCHING) {
    unsigned long searchElapsed = currentTime - searchStartTime;
    int currentPhase = searchElapsed / SEARCH_PHASE_TIME;

    if (currentPhase >= MAX_SEARCH_PHASES) {
      // Tekrar geri git ve ters yöne bak
      robotState = STATE_REVERSING;
      searchStartTime = currentTime;
      lastDirection = -lastDirection;
      if (lastDirection == 0) lastDirection = 1;
      return;
    }

    int turnIntensity = searchSpeed + (currentPhase * 15);
    turnIntensity = min(turnIntensity, 180);

    // Zigzag: önce son bilinen yöne, sonra ters yöne
    if (currentPhase % 2 == 0) {
      if (lastDirection <= 0) {
        setMotors(-turnIntensity, turnIntensity);
      } else {
        setMotors(turnIntensity, -turnIntensity);
      }
    } else {
      if (lastDirection <= 0) {
        setMotors(turnIntensity, -turnIntensity);
      } else {
        setMotors(-turnIntensity, turnIntensity);
      }
    }
  }
}

// ============================================================
//  MOTOR KONTROL
// ============================================================
void setMotors(int leftSpeed, int rightSpeed) {
  if (leftSpeed >= 0) {
    digitalWrite(pinIN1, HIGH);
    digitalWrite(pinIN2, LOW);
    analogWrite(pinENA, leftSpeed);
  } else {
    digitalWrite(pinIN1, LOW);
    digitalWrite(pinIN2, HIGH);
    analogWrite(pinENA, -leftSpeed);
  }

  if (rightSpeed >= 0) {
    digitalWrite(pinIN3, HIGH);
    digitalWrite(pinIN4, LOW);
    analogWrite(pinENB, rightSpeed);
  } else {
    digitalWrite(pinIN3, LOW);
    digitalWrite(pinIN4, HIGH);
    analogWrite(pinENB, -rightSpeed);
  }
}

void setMotorsReverse(int leftSpeed, int rightSpeed) {
  digitalWrite(pinIN1, LOW);
  digitalWrite(pinIN2, HIGH);
  analogWrite(pinENA, leftSpeed);

  digitalWrite(pinIN3, LOW);
  digitalWrite(pinIN4, HIGH);
  analogWrite(pinENB, rightSpeed);
}

void stopMotors() {
  analogWrite(pinENA, 0);
  analogWrite(pinENB, 0);
  digitalWrite(pinIN1, LOW);
  digitalWrite(pinIN2, LOW);
  digitalWrite(pinIN3, LOW);
  digitalWrite(pinIN4, LOW);
}

// ============================================================
//  SERİ KOMUTLAR
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
  if (cmd == "PING") {
    Serial.println("PONG");
  }
  else if (cmd == "STOP") {
    robotState = STATE_STOPPED;
    stopMotors();
    Serial.println("OK_STOPPED");
  }
  else if (cmd == "GO") {
    robotState = STATE_RUNNING;
    integral = 0;
    lastError = 0;
    lastLineTime = millis();
    searchPhase = 0;
    Serial.println("OK_RUNNING");
  }
  else if (cmd == "STATUS") {
    switch (robotState) {
      case STATE_STOPPED:
        Serial.println("STATUS_STOPPED");
        break;
      case STATE_RUNNING:
        Serial.println("STATUS_RUNNING");
        break;
      default:
        Serial.println("STATUS_SEARCHING");
        break;
    }
  }
  else if (cmd == "VERSION") {
    Serial.print("VERSION:");
    Serial.println(FIRMWARE_VERSION);
  }
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
    newSpeed = constrain(newSpeed, 0, 255);
    baseSpeed = newSpeed;
    searchSpeed = max(60, baseSpeed - 50);
    reverseSpeed = max(50, baseSpeed - 70);
    Serial.print("OK_SPEED:");
    Serial.println(baseSpeed);
  }
  else if (cmd.startsWith("PID:")) {
    String params = cmd.substring(4);
    int c1 = params.indexOf(',');
    int c2 = params.lastIndexOf(',');

    if (c1 > 0 && c2 > c1) {
      Kp = constrain(params.substring(0, c1).toFloat(), 0.0, 10.0);
      Ki = constrain(params.substring(c1 + 1, c2).toFloat(), 0.0, 5.0);
      Kd = constrain(params.substring(c2 + 1).toFloat(), 0.0, 10.0);
      integral = 0;

      Serial.print("OK_PID:");
      Serial.print(Kp, 2);
      Serial.print(",");
      Serial.print(Ki, 2);
      Serial.print(",");
      Serial.println(Kd, 2);
    } else {
      Serial.println("ERROR:INVALID_PID");
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
    baseSpeed = 150;
    searchSpeed = 100;
    reverseSpeed = 80;
    Kp = 1.5;
    Ki = 0.0;
    Kd = 0.8;
    integral = 0;
    lastError = 0;
    Serial.println("OK_RESET");
  }
  else if (cmd.length() > 0) {
    Serial.print("ERROR:UNKNOWN:");
    Serial.println(cmd);
  }
}

// ============================================================
//  EEPROM
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
    baseSpeed = constrain(EEPROM.read(EEPROM_SPEED), 0, 255);
    EEPROM.get(EEPROM_KP, Kp);
    EEPROM.get(EEPROM_KI, Ki);
    EEPROM.get(EEPROM_KD, Kd);

    Kp = constrain(Kp, 0.0, 10.0);
    Ki = constrain(Ki, 0.0, 5.0);
    Kd = constrain(Kd, 0.0, 10.0);

    searchSpeed = max(60, baseSpeed - 50);
    reverseSpeed = max(50, baseSpeed - 70);
  }
}
