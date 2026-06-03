// 5 Kanal IR Sensör Pinleri (Digital)
const int sensor1 = 2;   // En sol
const int sensor2 = 3;
const int sensor3 = 4;   // Orta
const int sensor4 = 7;
const int sensor5 = 12;  // En sag

// Motor Pinleri (L298N)
const int pinENA = 6;   // Sol motor hız (PWM)
const int pinIN1 = 10;  // Sol motor yön
const int pinIN2 = 11;
const int pinENB = 5;   // Sağ motor hız (PWM)
const int pinIN3 = 8;   // Sağ motor yön
const int pinIN4 = 9;

// Motor hızı (0-255)
const int HIZ_MAX = 120;
const int HIZ_MIN = 40;

// Sensör ağırlıkları (pozisyon)
const int agirlik[] = {-2, -1, 0, 1, 2};

// Siyah = 0, Beyaz = 1
const int SIYAH = 0;

void setup() {
  Serial.begin(9600);

  pinMode(sensor1, INPUT);
  pinMode(sensor2, INPUT);
  pinMode(sensor3, INPUT);
  pinMode(sensor4, INPUT);
  pinMode(sensor5, INPUT);

  pinMode(pinENA, OUTPUT);
  pinMode(pinIN1, OUTPUT);
  pinMode(pinIN2, OUTPUT);
  pinMode(pinENB, OUTPUT);
  pinMode(pinIN3, OUTPUT);
  pinMode(pinIN4, OUTPUT);

  dur();
  Serial.println("Cizgi takip hazir!");
}

void loop() {
  int s[] = {
    digitalRead(sensor1),
    digitalRead(sensor2),
    digitalRead(sensor3),
    digitalRead(sensor4),
    digitalRead(sensor5)
  };

  // Ağırlıklı ortalama hesapla
  int toplam = 0;
  int aktifSensor = 0;

  for (int i = 0; i < 5; i++) {
    if (s[i] == SIYAH) {
      toplam += agirlik[i];
      aktifSensor++;
    }
  }

  // Debug
  Serial.print(s[0]);
  Serial.print(s[1]);
  Serial.print(s[2]);
  Serial.print(s[3]);
  Serial.print(s[4]);

  // Hiç sensör siyah görmüyorsa dur
  if (aktifSensor == 0) {
    dur();
    Serial.println(" -> DUR");
    delay(10);
    return;
  }

  // Pozisyon: -2 (sol) ile +2 (sağ) arası
  float pozisyon = (float)toplam / aktifSensor;

  Serial.print(" Poz:");
  Serial.print(pozisyon);

  // Hız hesapla (pozisyona göre)
  int solHiz, sagHiz;

  if (pozisyon < -0.5) {
    // Sola dön: sağ motor hızlı, sol motor yavaş/geri
    sagHiz = HIZ_MAX;
    solHiz = map(pozisyon * 100, -200, -50, -HIZ_MIN, HIZ_MIN);
    solHiz = constrain(solHiz, -HIZ_MAX, HIZ_MAX);
    Serial.println(" -> SOL");
  }
  else if (pozisyon > 0.5) {
    // Sağa dön: sol motor hızlı, sağ motor yavaş/geri
    solHiz = HIZ_MAX;
    sagHiz = map(pozisyon * 100, 50, 200, HIZ_MIN, -HIZ_MIN);
    sagHiz = constrain(sagHiz, -HIZ_MAX, HIZ_MAX);
    Serial.println(" -> SAG");
  }
  else {
    // Düz git
    solHiz = HIZ_MAX;
    sagHiz = HIZ_MAX;
    Serial.println(" -> ILERI");
  }

  motorKontrol(solHiz, sagHiz);
  delay(10);
}

void motorKontrol(int solHiz, int sagHiz) {
  // Sol motor
  if (solHiz >= 0) {
    digitalWrite(pinIN1, HIGH);
    digitalWrite(pinIN2, LOW);
    analogWrite(pinENA, solHiz);
  } else {
    digitalWrite(pinIN1, LOW);
    digitalWrite(pinIN2, HIGH);
    analogWrite(pinENA, -solHiz);
  }

  // Sağ motor
  if (sagHiz >= 0) {
    digitalWrite(pinIN3, HIGH);
    digitalWrite(pinIN4, LOW);
    analogWrite(pinENB, sagHiz);
  } else {
    digitalWrite(pinIN3, LOW);
    digitalWrite(pinIN4, HIGH);
    analogWrite(pinENB, -sagHiz);
  }
}

void dur() {
  analogWrite(pinENA, 0);
  analogWrite(pinENB, 0);
  digitalWrite(pinIN1, LOW);
  digitalWrite(pinIN2, LOW);
  digitalWrite(pinIN3, LOW);
  digitalWrite(pinIN4, LOW);
}
