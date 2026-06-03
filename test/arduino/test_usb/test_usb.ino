// ============================================================
//  USB SERI HABERLESME TESTI - Arduino
// ============================================================
//
//  AMAC:
//  Raspberry Pi ile Arduino arasindaki USB seri haberlesmeyi
//  test etmek icin kullanilir.
//
//  KULLANIM:
//  1. Bu kodu Arduino'ya yukleyin
//  2. Arduino IDE'de Serial Monitor acin (9600 baud)
//  3. Asagidaki komutlari gonderip cevaplari kontrol edin:
//     - PING -> PONG
//     - STOP -> OK_STOPPED (LED yanar)
//     - GO -> OK_RUNNING (LED soner)
//     - STATUS -> STATUS_STOPPED veya STATUS_RUNNING
//
//  LED:
//  Arduino uzerindeki dahili LED (pin 13) kullanilir.
//  STOP komutunda yanar, GO komutunda soner.
//
// ============================================================

// Dahili LED pini (Arduino Uno'da pin 13)
const int LED_PIN = 13;

// Robot durumu
bool robotStopped = false;

// Seri veri buffer'i
String serialBuffer = "";

void setup() {
  // ----- SERI PORT BASLAT -----
  // 9600 baud - Raspberry Pi ile ayni olmali
  Serial.begin(9600);

  // ----- LED PININI AYARLA -----
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);  // Baslangicta kapali

  // ----- BASLANGIC MESAJI -----
  Serial.println("========================================");
  Serial.println("  USB SERI HABERLESME TESTI - Arduino");
  Serial.println("========================================");
  Serial.println("");
  Serial.println("Kullanilabilir komutlar:");
  Serial.println("  PING   -> Baglanti testi (PONG doner)");
  Serial.println("  STOP   -> Robotu durdur (LED yanar)");
  Serial.println("  GO     -> Robota devam et (LED soner)");
  Serial.println("  STATUS -> Mevcut durumu sorgula");
  Serial.println("");
  Serial.println("ROBOT_READY");
}

void loop() {
  // ----- SERI PORTTAN VERI OKU -----
  while (Serial.available() > 0) {
    char c = Serial.read();

    // Satir sonu geldiginde komutu islet
    if (c == '\n') {
      // Boslukları temizle
      serialBuffer.trim();

      // Komutu buyuk harfe cevir (kucuk harf de kabul et)
      serialBuffer.toUpperCase();

      // ----- KOMUTLARI ISLET -----

      // PING: Baglanti testi
      if (serialBuffer == "PING") {
        Serial.println("PONG");
      }

      // STOP: Robotu durdur
      else if (serialBuffer == "STOP") {
        robotStopped = true;
        digitalWrite(LED_PIN, HIGH);  // LED yak
        Serial.println("OK_STOPPED");
      }

      // GO: Robota devam et
      else if (serialBuffer == "GO") {
        robotStopped = false;
        digitalWrite(LED_PIN, LOW);  // LED sondur
        Serial.println("OK_RUNNING");
      }

      // STATUS: Durum sorgula
      else if (serialBuffer == "STATUS") {
        if (robotStopped) {
          Serial.println("STATUS_STOPPED");
        } else {
          Serial.println("STATUS_RUNNING");
        }
      }

      // HELP: Yardim
      else if (serialBuffer == "HELP") {
        Serial.println("Komutlar: PING, STOP, GO, STATUS, HELP");
      }

      // Bilinmeyen komut
      else if (serialBuffer.length() > 0) {
        Serial.print("ERROR_UNKNOWN_COMMAND: ");
        Serial.println(serialBuffer);
      }

      // Buffer'i temizle
      serialBuffer = "";
    }
    else {
      // Karakteri buffer'a ekle
      serialBuffer += c;
    }
  }

  // ----- LED DURUMUNU GUNCELLE -----
  // (Ek gorsel geri bildirim)
  if (robotStopped) {
    // STOP modunda: LED surekli yanik
    digitalWrite(LED_PIN, HIGH);
  } else {
    // GO modunda: LED kapali
    digitalWrite(LED_PIN, LOW);
  }
}

// ============================================================
//  TEST ADIMLARI
// ============================================================
//
//  1. ARDUINO IDE ILE TEST:
//     - Kodu Arduino'ya yukleyin
//     - Tools > Serial Monitor acin
//     - Baud rate: 9600, Line ending: Newline
//     - "PING" yazin, "PONG" cevabi gelmeli
//     - "STOP" yazin, LED yanmali, "OK_STOPPED" gelmeli
//     - "GO" yazin, LED sonmeli, "OK_RUNNING" gelmeli
//
//  2. RASPBERRY PI ILE TEST:
//     - Arduino'yu Pi'ye USB ile baglayin
//     - test_usb_pi.py dosyasini calistirin
//     - Otomatik test yapilacak
//
// ============================================================
