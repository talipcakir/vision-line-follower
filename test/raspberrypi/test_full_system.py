#!/usr/bin/env python3
"""
TAM SİSTEM TESTİ
================
Bu script Arduino + Kamera entegrasyonunu test eder.
Kırmızı görünce STOP gönderir.

Kullanım:
  python3 test_full_system.py

Çıkmak için: Ctrl+C
"""

import sys
import time
import threading

try:
    import serial
    import cv2
    import numpy as np
    from picamera2 import Picamera2
except ImportError as e:
    print(f"HATA: Eksik modül - {e}")
    print("Kurulum: sudo apt install python3-opencv python3-picamera2 python3-serial")
    sys.exit(1)

# ============================================================
#  AYARLAR
# ============================================================

SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 9600

# HSV kırmızı aralıkları
LOWER_RED1 = np.array([0, 120, 70])
UPPER_RED1 = np.array([10, 255, 255])
LOWER_RED2 = np.array([170, 120, 70])
UPPER_RED2 = np.array([180, 255, 255])

MIN_AREA = 1500

# ============================================================
#  GLOBAL DEĞİŞKENLER
# ============================================================

arduino = None
camera = None
running = True
robot_active = False
red_detected = False

# ============================================================
#  ARDUINO BAĞLANTISI
# ============================================================

def connect_arduino():
    global arduino
    print(f"Arduino bağlanıyor: {SERIAL_PORT}")

    try:
        arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        time.sleep(2.5)  # Arduino reset
        arduino.reset_input_buffer()

        # PING testi
        arduino.write(b"PING\n")
        time.sleep(0.5)
        response = arduino.readline().decode().strip()

        if "PONG" in response:
            print(f"[OK] Arduino bağlandı")

            # Versiyon al
            arduino.write(b"VERSION\n")
            time.sleep(0.3)
            ver = arduino.readline().decode().strip()
            print(f"[OK] Firmware: {ver}")
            return True
        else:
            print(f"[HATA] Arduino yanıt vermedi: {response}")
            return False

    except Exception as e:
        print(f"[HATA] Arduino bağlantı hatası: {e}")
        return False

def send_command(cmd):
    global arduino
    if arduino and arduino.is_open:
        try:
            arduino.write(f"{cmd}\n".encode())
            time.sleep(0.2)
            response = arduino.readline().decode().strip()
            return response
        except:
            pass
    return ""

# ============================================================
#  KAMERA
# ============================================================

def start_camera():
    global camera
    print("Kamera başlatılıyor...")

    try:
        camera = Picamera2()
        config = camera.create_preview_configuration(
            main={"size": (640, 480), "format": "RGB888"}
        )
        camera.configure(config)
        camera.start()
        time.sleep(1)
        print("[OK] Kamera başlatıldı")
        return True
    except Exception as e:
        print(f"[HATA] Kamera hatası: {e}")
        return False

def detect_red(frame):
    """Kırmızı renk algılama"""
    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)

    mask1 = cv2.inRange(hsv, LOWER_RED1, UPPER_RED1)
    mask2 = cv2.inRange(hsv, LOWER_RED2, UPPER_RED2)
    mask = mask1 + mask2

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > MIN_AREA:
            return True, area

    return False, 0

# ============================================================
#  ANA DÖNGÜ
# ============================================================

def camera_loop():
    global running, red_detected, robot_active

    last_detection = False

    while running:
        if camera is None:
            time.sleep(0.1)
            continue

        try:
            frame = camera.capture_array()
            detected, area = detect_red(frame)

            if detected and not last_detection:
                print(f"\n[!] KIRMIZI ALGILANDI! Alan: {area}px")
                red_detected = True

                if robot_active:
                    response = send_command("STOP")
                    print(f"[!] STOP gönderildi -> {response}")
                    robot_active = False

            elif not detected and last_detection:
                print("[i] Kırmızı kayboldu")
                red_detected = False

            last_detection = detected

        except Exception as e:
            print(f"[HATA] Kamera döngüsü: {e}")

        time.sleep(0.1)

def main():
    global running, robot_active

    print("=" * 50)
    print("  TAM SİSTEM TESTİ")
    print("  Arduino + Kamera Entegrasyonu")
    print("=" * 50)
    print()

    # Arduino bağlan
    if not connect_arduino():
        print("\nArduino bağlanamadı!")
        print("Kontrol edin:")
        print(f"  1. Arduino {SERIAL_PORT} portuna bağlı mı?")
        print("  2. Firmware yüklü mü?")
        print("  3. Port yetkisi var mı? (sudo usermod -a -G dialout $USER)")
        return

    # Kamera başlat
    if not start_camera():
        print("\nKamera başlatılamadı!")
        return

    # Kamera thread'i başlat
    cam_thread = threading.Thread(target=camera_loop, daemon=True)
    cam_thread.start()

    print()
    print("=" * 50)
    print("KOMUTLAR:")
    print("  g = GO (robotu başlat)")
    print("  s = STOP (robotu durdur)")
    print("  p = PING (bağlantı testi)")
    print("  r = SENSORS (sensör değerleri)")
    print("  c = CONFIG (mevcut ayarlar)")
    print("  q = Çıkış")
    print("=" * 50)
    print()
    print("Kırmızı nesne gösterildiğinde robot otomatik durur.")
    print()

    try:
        while running:
            cmd = input("> ").strip().lower()

            if cmd == 'q':
                running = False
                break
            elif cmd == 'g':
                response = send_command("GO")
                print(f"GO -> {response}")
                if "OK_RUNNING" in response:
                    robot_active = True
            elif cmd == 's':
                response = send_command("STOP")
                print(f"STOP -> {response}")
                robot_active = False
            elif cmd == 'p':
                response = send_command("PING")
                print(f"PING -> {response}")
            elif cmd == 'r':
                response = send_command("SENSORS")
                print(f"SENSORS -> {response}")
                if response.startswith("SENSORS:"):
                    vals = response[8:].split(",")
                    print(f"  S1={vals[0]} S2={vals[1]} S3={vals[2]} S4={vals[3]} S5={vals[4]}")
                    print(f"  (0=çizgi, 1=beyaz)")
            elif cmd == 'c':
                response = send_command("CONFIG")
                print(f"CONFIG -> {response}")
            elif cmd:
                # Diğer komutları doğrudan gönder
                response = send_command(cmd.upper())
                print(f"{cmd.upper()} -> {response}")

    except KeyboardInterrupt:
        print("\nÇıkış...")

    running = False

    # Temizlik
    if robot_active:
        send_command("STOP")

    if arduino:
        arduino.close()

    if camera:
        camera.stop()

    print("Program sonlandı.")

if __name__ == "__main__":
    main()
