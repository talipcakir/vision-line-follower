#!/usr/bin/env python3
# ============================================================
#  SERIT TAKIP ROBOTU - Raspberry Pi Gorsel Isleme
#  Kirmizi renk algilandiginda Arduino'ya USB uzerinden
#  STOP komutu gonderir.
# ============================================================
#
#  CALISMA MANTIGI:
#  1. Kameradan goruntu al
#  2. HSV renk uzayinda kirmizi rengi ara
#  3. Kirmizi bulunursa Arduino'ya "STOP" gonder
#  4. Kirmizi yoksa Arduino'ya "GO" gonder
#  5. Web arayuzunde canli goruntu goster
#
#  HABERLESME:
#  Raspberry Pi <--USB--> Arduino
#  - Port: /dev/ttyACM0 (veya /dev/ttyUSB0)
#  - Baud rate: 9600
#  - Komutlar: "STOP\n", "GO\n"
#
# ============================================================

from flask import Flask, Response
from picamera2 import Picamera2
import cv2
import numpy as np
import serial
import time

# ============================================================
#  SERI PORT AYARLARI (USB)
# ============================================================
#  Arduino USB ile baglandiginda genellikle su portlardan
#  birinde gorunur:
#    - /dev/ttyACM0 (Arduino Uno, Mega)
#    - /dev/ttyUSB0 (Arduino Nano, klon kartlar)
#
#  Portu bulmak icin terminalde: ls /dev/tty*
#  Baud rate Arduino ile ayni olmali: 9600

SERIAL_PORT = '/dev/ttyACM0'  # Arduino'nun bagli oldugu port
BAUD_RATE = 9600              # Haberlesme hizi

# Seri port baglantisi olustur
try:
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # Arduino resetlenmesi icin bekle
    print(f"Arduino baglantisi basarili: {SERIAL_PORT}")
except Exception as e:
    print(f"HATA: Arduino baglanamadi: {e}")
    print("Port adini kontrol edin: ls /dev/tty*")
    arduino = None

# ============================================================
#  KAMERA AYARLARI
# ============================================================
#  Picamera2 ile Raspberry Pi kamera modulu kullanilir.
#  640x480 cozunurluk yeterli ve hizli islem saglar.

app = Flask(__name__)

picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 480)})
picam2.configure(config)
picam2.start()
time.sleep(2)  # Kameranin stabilize olmasi icin

# ============================================================
#  KIRMIZI RENK ALGILAMA AYARLARI (HSV)
# ============================================================
#  HSV renk uzayi kullanilir (Hue, Saturation, Value).
#  Kirmizi renk HSV'de iki aralikta bulunur:
#    - 0-10 derece (acik kirmizi)
#    - 170-180 derece (koyu kirmizi)
#
#  Bu iki aralik birlestirilir.

# Acik kirmizi araligi (0-10 derece)
LOWER_RED1 = np.array([0, 120, 70])
UPPER_RED1 = np.array([10, 255, 255])

# Koyu kirmizi araligi (170-180 derece)
LOWER_RED2 = np.array([170, 120, 70])
UPPER_RED2 = np.array([180, 255, 255])

# Minimum alan (piksel kare)
# Kucuk kirmizi noktalar (gurultu) filtrelenir
MIN_AREA = 1500

# ============================================================
#  ARDUINO'YA KOMUT GONDER
# ============================================================
#  Arduino'ya USB seri port uzerinden komut gonderir.
#  Komutlar satir sonu (\n) ile biter.

def send_command(command):
    """Arduino'ya komut gonder"""
    if arduino and arduino.is_open:
        try:
            arduino.write(f"{command}\n".encode())
            return True
        except Exception as e:
            print(f"Komut gonderilemedi: {e}")
            return False
    return False

# Son gonderilen komut (gereksiz tekrari onlemek icin)
last_command = None

# ============================================================
#  VIDEO AKISI VE GORSEL ISLEME
# ============================================================
#  Her frame icin:
#  1. Kameradan goruntu al
#  2. BGR'dan HSV'ye donustur
#  3. Kirmizi renk maskesi olustur
#  4. Konturleri bul
#  5. Yeterli buyuklukte kirmizi varsa STOP gonder
#  6. Yoksa GO gonder

def generate():
    """Video akisi olustur ve kirmizi algilama yap"""
    global last_command

    while True:
        # ----- ADIM 1: KAMERADAN GORUNTU AL -----
        frame = picam2.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # ----- ADIM 2: HSV RENK UZAYINA DONUSTUR -----
        # BGR (Blue-Green-Red) formatindan
        # HSV (Hue-Saturation-Value) formatina gecis
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # ----- ADIM 3: KIRMIZI RENK MASKESI OLUSTUR -----
        # Iki kirmizi araligini birlestir
        mask_red1 = cv2.inRange(hsv, LOWER_RED1, UPPER_RED1)
        mask_red2 = cv2.inRange(hsv, LOWER_RED2, UPPER_RED2)
        mask_red = mask_red1 + mask_red2

        # ----- ADIM 4: GURULTU AZALTMA -----
        # Erode: Kucuk beyaz noktalari sil
        # Dilate: Kalan alanlari genislet
        mask_red = cv2.erode(mask_red, None, iterations=2)
        mask_red = cv2.dilate(mask_red, None, iterations=2)

        # ----- ADIM 5: KONTURLERI BUL -----
        # Maskedeki beyaz alanlarin dis hatlarini bul
        contours, _ = cv2.findContours(
            mask_red,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        red_detected = False

        # ----- ADIM 6: EN BUYUK KIRMIZI NESNEYI BUL -----
        for cnt in contours:
            area = cv2.contourArea(cnt)

            # Minimum alandan buyukse kirmizi kabul et
            if area > MIN_AREA:
                red_detected = True

                # Dikdortgen ciz (gorsellik icin)
                x, y, w, h = cv2.boundingRect(cnt)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 3)
                cv2.putText(
                    frame, "KIRMIZI - DURDU",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2
                )
                break

        # ----- ADIM 7: ARDUINO'YA KOMUT GONDER -----
        # Sadece durum degistiginde komut gonder
        # Gereksiz tekrari onler, seri portu yormaZ
        if red_detected:
            if last_command != "STOP":
                send_command("STOP")
                last_command = "STOP"
                print(">>> STOP komutu gonderildi")
        else:
            if last_command != "GO":
                send_command("GO")
                last_command = "GO"
                print(">>> GO komutu gonderildi")

        # ----- ADIM 8: DURUM GOSTERGESI CIZ -----
        status = "DURDU" if red_detected else "CALISIYOR"
        color = (0, 0, 255) if red_detected else (0, 255, 0)
        cv2.putText(
            frame, f"Durum: {status}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2
        )

        # ----- ADIM 9: JPEG OLARAK KODLA -----
        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        # HTTP multipart stream formatinda gonder
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
        )


# ============================================================
#  WEB ARAYUZU ROTALARI
# ============================================================

@app.route('/')
def video():
    """Ana sayfa - canli video akisi"""
    return Response(
        generate(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/status')
def status():
    """Durum sayfasi"""
    return "Serit Takip Robotu - Gorsel Isleme Aktif (USB Seri)"


# ============================================================
#  ANA PROGRAM
# ============================================================

if __name__ == '__main__':
    try:
        print("=" * 50)
        print("  SERIT TAKIP ROBOTU - Gorsel Isleme")
        print("=" * 50)
        print(f"Seri Port: {SERIAL_PORT}")
        print(f"Baud Rate: {BAUD_RATE}")
        print("Web arayuzu: http://<raspberry-pi-ip>:5000")
        print("=" * 50)

        app.run(host='0.0.0.0', port=5000, threaded=True)

    except KeyboardInterrupt:
        print("\nProgram sonlandiriliyor...")

    finally:
        # Temizlik islemleri
        if arduino and arduino.is_open:
            send_command("GO")  # Robotu serbest birak
            arduino.close()
            print("Seri port kapatildi")

        picam2.stop()
        print("Kamera durduruldu")
