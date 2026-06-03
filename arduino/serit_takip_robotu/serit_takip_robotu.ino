// ============================================================
//  SERIT TAKIP ROBOTU - Arduino Kodu
//  Donem Bitirme Projesi
// ============================================================
//
//  PROJE ACIKLAMASI:
//  Bu robot, zemindeki siyah cizgiyi 5 kanalli IR sensor dizisi
//  ile takip eder. Ayrica Raspberry Pi'dan USB seri port uzerinden
//  gelen komutlarla kirmizi renk algilandiginda durur.
//
//  CALISMA MANTIGI:
//  1. Raspberry Pi kamera ile ortami izler
//  2. Kirmizi renk gorurse USB uzerinden "STOP" komutu gonderir
//  3. Kirmizi yoksa "GO" komutu gonderir
//  4. Arduino seri porttan komutu okur
//  5. "STOP" ise motorlari durdurur
//  6. "GO" ise IR sensorlerle cizgi takip eder
//
//  HABERLESME:
//  Raspberry Pi <--USB--> Arduino
//  - Baud rate: 9600
//  - Komutlar: "STOP" (dur), "GO" (devam)
//
//  DONANIM:
//  - Arduino Uno
//  - L298N Motor Surucu
//  - 2x DC Motor (sol ve sag tekerlek)
//  - 5 Kanalli IR Sensor Dizisi
//  - Raspberry Pi 4 + Pi Camera
//  - USB Kablo (Pi ile Arduino arasinda)
//
// ============================================================

// ============================================================
//  PIN TANIMLARI
// ============================================================

// ------------------------------------------------------------
//  SOL MOTOR PINLERI (L298N)
// ------------------------------------------------------------
//  ENA: PWM sinyali ile hiz kontrolu (0-255 arasi deger)
//  IN1, IN2: Motor don yonu kontrolu
//    - IN1=HIGH, IN2=LOW  -> Ileri
//    - IN1=LOW,  IN2=HIGH -> Geri
//    - IN1=LOW,  IN2=LOW  -> Dur
int pinENA = 6;   // Sol motor hiz (PWM) - D6 pini
int pinIN1 = 10;  // Sol motor yon A - D10 pini
int pinIN2 = 11;  // Sol motor yon B - D11 pini

// ------------------------------------------------------------
//  SAG MOTOR PINLERI (L298N)
// ------------------------------------------------------------
//  ENB: PWM sinyali ile hiz kontrolu (0-255 arasi deger)
//  IN3, IN4: Motor don yonu kontrolu
//    - IN3=HIGH, IN4=LOW  -> Ileri
//    - IN3=LOW,  IN4=HIGH -> Geri
//    - IN3=LOW,  IN4=LOW  -> Dur
int pinENB = 5;   // Sag motor hiz (PWM) - D5 pini
int pinIN3 = 8;   // Sag motor yon A - D8 pini
int pinIN4 = 9;   // Sag motor yon B - D9 pini

// ------------------------------------------------------------
//  IR SENSOR PINLERI (5 Kanalli Dizi)
// ------------------------------------------------------------
//  Sensorler soldan saga dogru siralanmistir.
//  Her sensor dijital cikis verir:
//    - HIGH (1): Beyaz zemin (cizgi yok)
//    - LOW  (0): Siyah cizgi (cizgi var)
//
//  Sensor Yerlesimi (robota ustten bakis):
//
//       S1    S2    S3    S4    S5
//       |     |     |     |     |
//    [EN SOL]      [ORTA]      [EN SAG]
//
int pinS1 = 2;    // En sol sensor - D2 pini
int pinS2 = 3;    // Hafif sol sensor - D3 pini
int pinS3 = 4;    // Orta sensor - D4 pini
int pinS4 = 7;    // Hafif sag sensor - D7 pini
int pinS5 = 12;   // En sag sensor - D12 pini

// ------------------------------------------------------------
//  HIZ AYARLARI
// ------------------------------------------------------------
//  baseSpeed: Temel motor hizi (0-255 arasi)
//    - 0: Motor durur
//    - 255: Maksimum hiz
//    - 90: Orta yavas hiz (onerilen baslangic degeri)
//
//  Donuslerde bu deger arttirilip azaltilarak
//  farkli tekerlek hizlari olusturulur.
int baseSpeed = 90;

// ------------------------------------------------------------
//  SERI HABERLESME DEGISKENLERI
// ------------------------------------------------------------
//  Raspberry Pi'dan gelen komutlari saklamak icin
//  STOP komutu alindiysa robotStopped = true olur
bool robotStopped = false;    // Robot durdu mu?
String serialBuffer = "";     // Gelen veriyi biriktirmek icin

// ============================================================
//  SETUP FONKSIYONU
// ============================================================
//  Arduino acildiginda bir kere calisir.
//  Tum pinlerin giris/cikis modlarini ayarlar.
//
void setup() {

  // ----------------------------------------------------------
  //  SERI PORT BASLAT (RASPBERRY PI HABERLESME)
  // ----------------------------------------------------------
  //  9600 baud hizinda seri iletisim baslatilir.
  //  Raspberry Pi ile ayni baud rate kullanilmali.
  //  USB kablosu uzerinden haberlesme yapilir.

  Serial.begin(9600);

  // ----------------------------------------------------------
  //  MOTOR PINLERINI CIKIS OLARAK AYARLA
  // ----------------------------------------------------------
  //  OUTPUT: Bu pinlerden sinyal GONDERECEGIZ
  //  Motorlari surmek icin gerekli

  // Sol motor pinleri
  pinMode(pinENA, OUTPUT);  // PWM hiz kontrolu
  pinMode(pinIN1, OUTPUT);  // Yon kontrolu
  pinMode(pinIN2, OUTPUT);  // Yon kontrolu

  // Sag motor pinleri
  pinMode(pinENB, OUTPUT);  // PWM hiz kontrolu
  pinMode(pinIN3, OUTPUT);  // Yon kontrolu
  pinMode(pinIN4, OUTPUT);  // Yon kontrolu

  // ----------------------------------------------------------
  //  SENSOR PINLERINI GIRIS OLARAK AYARLA
  // ----------------------------------------------------------
  //  INPUT: Bu pinlerden sinyal OKUYACAGIZ
  //  Sensorlerin cizgi gorup gormedigini anlamak icin

  pinMode(pinS1, INPUT);  // En sol sensor
  pinMode(pinS2, INPUT);  // Hafif sol sensor
  pinMode(pinS3, INPUT);  // Orta sensor
  pinMode(pinS4, INPUT);  // Hafif sag sensor
  pinMode(pinS5, INPUT);  // En sag sensor

  // ----------------------------------------------------------
  //  MOTOR DONUS YONUNU ILERI OLARAK AYARLA
  // ----------------------------------------------------------
  //  Baslangicta her iki motor ileri yone ayarlanir.
  //  IN1=HIGH, IN2=LOW: Sol motor ileri
  //  IN3=HIGH, IN4=LOW: Sag motor ileri

  digitalWrite(pinIN1, HIGH);
  digitalWrite(pinIN2, LOW);
  digitalWrite(pinIN3, HIGH);
  digitalWrite(pinIN4, LOW);

  // Baslangic mesaji
  Serial.println("ROBOT_READY");
}

// ============================================================
//  LOOP FONKSIYONU
// ============================================================
//  Arduino calistigi surece surekli tekrar eder.
//  Her dongude:
//  1. Seri porttan komut okunur
//  2. STOP/GO durumuna gore islem yapilir
//  3. IR sensorler okunur
//  4. Cizgi konumuna gore motor hizlari ayarlanir
//
void loop() {

  // ----------------------------------------------------------
  //  ADIM 1: SERI PORTTAN KOMUT OKU
  // ----------------------------------------------------------
  //  Raspberry Pi USB uzerinden komut gonderir:
  //    - "STOP": Kirmizi algilandi, dur
  //    - "GO": Kirmizi yok, devam et
  //
  //  Serial.available(): Okunacak veri var mi?
  //  Serial.read(): Bir karakter oku

  while (Serial.available() > 0) {
    char c = Serial.read();

    // Satir sonu karakteri geldiginde komutu islet
    if (c == '\n') {
      // Boslukları temizle
      serialBuffer.trim();

      // STOP komutu: Robotu durdur
      if (serialBuffer == "STOP") {
        robotStopped = true;
        Serial.println("OK_STOPPED");
      }
      // GO komutu: Robota devam et
      else if (serialBuffer == "GO") {
        robotStopped = false;
        Serial.println("OK_RUNNING");
      }
      // PING komutu: Baglanti testi
      else if (serialBuffer == "PING") {
        Serial.println("PONG");
      }
      // STATUS komutu: Durum sorgula
      else if (serialBuffer == "STATUS") {
        if (robotStopped) {
          Serial.println("STATUS_STOPPED");
        } else {
          Serial.println("STATUS_RUNNING");
        }
      }

      // Buffer'i temizle, yeni komut icin hazirla
      serialBuffer = "";
    }
    else {
      // Karakteri buffer'a ekle
      serialBuffer += c;
    }
  }

  // ----------------------------------------------------------
  //  ADIM 2: STOP DURUMUNU KONTROL ET
  // ----------------------------------------------------------
  //  Eger Raspberry Pi "STOP" komutu gonderdiyse
  //  motorlari durdur ve fonksiyondan cik.

  if (robotStopped) {
    // KIRMIZI ALGILANDI - ACIL DURUM, MOTORLARI DURDUR
    analogWrite(pinENA, 0);  // Sol motor hizi = 0
    analogWrite(pinENB, 0);  // Sag motor hizi = 0

    // return ile fonksiyondan cik, asagidaki kodlar calismasin
    // Boylece robot "GO" komutuna kadar durur
    return;
  }

  // ----------------------------------------------------------
  //  ADIM 3: IR SENSORLERI OKU
  // ----------------------------------------------------------
  //  Her sensorun durumu okunur:
  //    - HIGH (1): Beyaz zemin goruyor (cizgi yok)
  //    - LOW  (0): Siyah cizgi goruyor (cizgi var)
  //
  //  NOT: Bazi sensorler tersi calisabilir.
  //  Kalibrasyon ile kontrol edin.

  int s1 = digitalRead(pinS1);  // En sol
  int s2 = digitalRead(pinS2);  // Hafif sol
  int s3 = digitalRead(pinS3);  // Orta
  int s4 = digitalRead(pinS4);  // Hafif sag
  int s5 = digitalRead(pinS5);  // En sag

  // ----------------------------------------------------------
  //  ADIM 4: MOTOR HIZLARINI HESAPLA
  // ----------------------------------------------------------
  //  Hangi sensor cizgiyi goruyorsa ona gore
  //  sol ve sag motor hizlari ayarlanir.
  //
  //  TEMEL MANTIK:
  //  - Cizgi solda ise: Sag motor hizlanir, sol motor yavaslar
  //    -> Robot sola doner, cizgiye yaklasir
  //  - Cizgi sagda ise: Sol motor hizlanir, sag motor yavaslar
  //    -> Robot saga doner, cizgiye yaklasir
  //  - Cizgi ortada ise: Iki motor esit hizda
  //    -> Robot duz gider

  int sol = baseSpeed;  // Sol motor hizi
  int sag = baseSpeed;  // Sag motor hizi

  // ORTA SENSOR CIZGIYI GORUYOR - DUZ GIT
  // En ideal durum: robot tam cizgi ustunde
  if (s3 == HIGH) {
    sol = baseSpeed;
    sag = baseSpeed;
  }

  // HAFIF SOL SENSOR CIZGIYI GORUYOR - SOLA DON
  // Cizgi biraz solda, hafif donus yeterli
  else if (s2 == HIGH) {
    sol = baseSpeed - 30;   // Sol motor yavasla
    sag = baseSpeed + 50;   // Sag motor hizlan
  }

  // EN SOL SENSOR CIZGIYI GORUYOR - SERT SOLA DON
  // Cizgi cok solda, keskin donus gerekli
  else if (s1 == HIGH) {
    sol = baseSpeed - 50;   // Sol motor cok yavasla
    sag = baseSpeed + 70;   // Sag motor cok hizlan
  }

  // HAFIF SAG SENSOR CIZGIYI GORUYOR - SAGA DON
  // Cizgi biraz sagda, hafif donus yeterli
  else if (s4 == HIGH) {
    sol = baseSpeed + 50;   // Sol motor hizlan
    sag = baseSpeed - 30;   // Sag motor yavasla
  }

  // EN SAG SENSOR CIZGIYI GORUYOR - SERT SAGA DON
  // Cizgi cok sagda, keskin donus gerekli
  else if (s5 == HIGH) {
    sol = baseSpeed + 70;   // Sol motor cok hizlan
    sag = baseSpeed - 50;   // Sag motor cok yavasla
  }

  // HIC SENSOR CIZGI GORMUYOR - DUR
  // Cizgi kayboldu veya robot cizgiden cikti
  else {
    sol = 0;
    sag = 0;
  }

  // ----------------------------------------------------------
  //  ADIM 5: HIZ DEGERLERINI SINIRLA
  // ----------------------------------------------------------
  //  constrain() fonksiyonu degeri min-max araliginda tutar.
  //  PWM degeri 0-255 araliginda olmali.
  //  Negatif veya 255'ten buyuk degerler sorun yaratir.

  sol = constrain(sol, 0, 255);  // Sol hiz: 0-255 arasi
  sag = constrain(sag, 0, 255);  // Sag hiz: 0-255 arasi

  // ----------------------------------------------------------
  //  ADIM 6: MOTORLARA HIZ UYGULA
  // ----------------------------------------------------------
  //  analogWrite() ile PWM sinyali gonderilir.
  //  0 = motor durur, 255 = maksimum hiz
  //  Aradaki degerler orantili hiz saglar.

  analogWrite(pinENA, sol);  // Sol motora hiz uygula
  analogWrite(pinENB, sag);  // Sag motora hiz uygula
}

// ============================================================
//  KODUN SONU
// ============================================================
