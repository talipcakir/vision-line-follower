#!/usr/bin/env python3
# ============================================================
#  VISION LINE FOLLOWER - Raspberry Pi Gorsel Isleme
#  Kirmizi renk algilandiginda Arduino'ya USB uzerinden
#  STOP komutu gonderir.
# ============================================================

__version__ = "1.0.0"
__author__ = "Talip Çakır"

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

from flask import Flask, Response
from picamera2 import Picamera2
import cv2
import numpy as np
import serial
import time

# ============================================================
#  ORTAM DEGISKENLERI (.env dosyasindan veya sistemden)
# ============================================================

def get_env(key, default, type_func=str):
    """Ortam degiskenini oku, yoksa varsayilan deger kullan"""
    value = os.environ.get(key, default)
    try:
        return type_func(value)
    except (ValueError, TypeError):
        return type_func(default)

# .env dosyasini oku (varsa)
env_file = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())

# ============================================================
#  AYARLAR
# ============================================================

# Seri port
SERIAL_PORT = get_env('SERIAL_PORT', '/dev/ttyACM0')
BAUD_RATE = get_env('BAUD_RATE', '9600', int)

# Kamera
CAMERA_WIDTH = get_env('CAMERA_WIDTH', '640', int)
CAMERA_HEIGHT = get_env('CAMERA_HEIGHT', '480', int)

# Web sunucu
WEB_HOST = get_env('WEB_HOST', '0.0.0.0')
WEB_PORT = get_env('WEB_PORT', '5000', int)

# Kirmizi renk algilama (HSV)
RED1_H_MIN = get_env('RED1_H_MIN', '0', int)
RED1_H_MAX = get_env('RED1_H_MAX', '10', int)
RED1_S_MIN = get_env('RED1_S_MIN', '120', int)
RED1_V_MIN = get_env('RED1_V_MIN', '70', int)

RED2_H_MIN = get_env('RED2_H_MIN', '170', int)
RED2_H_MAX = get_env('RED2_H_MAX', '180', int)
RED2_S_MIN = get_env('RED2_S_MIN', '120', int)
RED2_V_MIN = get_env('RED2_V_MIN', '70', int)

MIN_AREA = get_env('MIN_DETECTION_AREA', '1500', int)

# Loglama
LOG_LEVEL = get_env('LOG_LEVEL', 'INFO')
LOG_FILE = get_env('LOG_FILE', '')

# HSV araliklari
LOWER_RED1 = np.array([RED1_H_MIN, RED1_S_MIN, RED1_V_MIN])
UPPER_RED1 = np.array([RED1_H_MAX, 255, 255])
LOWER_RED2 = np.array([RED2_H_MIN, RED2_S_MIN, RED2_V_MIN])
UPPER_RED2 = np.array([RED2_H_MAX, 255, 255])

# ============================================================
#  LOGLAMA AYARLARI
# ============================================================

def setup_logging():
    """Loglama sistemini kur"""
    log_format = '%(asctime)s [%(levelname)s] %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # Log seviyesi
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

    # Root logger
    logger = logging.getLogger()
    logger.setLevel(level)

    # Konsol handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(console_handler)

    # Dosya handler (eger belirtilmisse)
    if LOG_FILE:
        log_dir = os.path.dirname(LOG_FILE)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=5*1024*1024,  # 5 MB
            backupCount=3
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        logger.addHandler(file_handler)

    return logger

logger = setup_logging()

# ============================================================
#  SERI PORT BAGLANTISI
# ============================================================

arduino = None

def connect_arduino():
    """Arduino'ya baglan"""
    global arduino
    try:
        arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  # Arduino resetlenmesi icin bekle
        logger.info(f"Arduino baglantisi basarili: {SERIAL_PORT}")
        return True
    except Exception as e:
        logger.error(f"Arduino baglanamadi: {e}")
        logger.info("Port kontrol: ls /dev/tty*")
        arduino = None
        return False

def send_command(command):
    """Arduino'ya komut gonder"""
    if arduino and arduino.is_open:
        try:
            arduino.write(f"{command}\n".encode())
            logger.debug(f"Komut gonderildi: {command}")
            return True
        except Exception as e:
            logger.error(f"Komut gonderilemedi: {e}")
            return False
    return False

# ============================================================
#  KAMERA AYARLARI
# ============================================================

app = Flask(__name__)
picam2 = None

def setup_camera():
    """Kamerayi baslat"""
    global picam2
    try:
        picam2 = Picamera2()
        config = picam2.create_preview_configuration(
            main={"size": (CAMERA_WIDTH, CAMERA_HEIGHT)}
        )
        picam2.configure(config)
        picam2.start()
        time.sleep(2)  # Stabilizasyon
        logger.info(f"Kamera baslatildi: {CAMERA_WIDTH}x{CAMERA_HEIGHT}")
        return True
    except Exception as e:
        logger.error(f"Kamera baslatilamadi: {e}")
        return False

# ============================================================
#  VIDEO AKISI VE GORSEL ISLEME
# ============================================================

last_command = None

def generate():
    """Video akisi olustur ve kirmizi algilama yap"""
    global last_command

    frame_count = 0
    start_time = time.time()

    while True:
        # Kameradan goruntu al
        frame = picam2.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # HSV renk uzayina donustur
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Kirmizi renk maskesi
        mask_red1 = cv2.inRange(hsv, LOWER_RED1, UPPER_RED1)
        mask_red2 = cv2.inRange(hsv, LOWER_RED2, UPPER_RED2)
        mask_red = mask_red1 + mask_red2

        # Gurultu azaltma
        mask_red = cv2.erode(mask_red, None, iterations=2)
        mask_red = cv2.dilate(mask_red, None, iterations=2)

        # Konturleri bul
        contours, _ = cv2.findContours(
            mask_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        red_detected = False

        # Kirmizi nesne ara
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > MIN_AREA:
                red_detected = True
                x, y, w, h = cv2.boundingRect(cnt)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 3)
                cv2.putText(
                    frame, "KIRMIZI - DURDU",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2
                )
                break

        # Arduino'ya komut gonder (sadece durum degistiginde)
        if red_detected:
            if last_command != "STOP":
                send_command("STOP")
                last_command = "STOP"
                logger.info("KIRMIZI ALGILANDI - STOP komutu gonderildi")
        else:
            if last_command != "GO":
                send_command("GO")
                last_command = "GO"
                logger.info("Kirmizi yok - GO komutu gonderildi")

        # Durum gostergesi
        status = "DURDU" if red_detected else "CALISIYOR"
        color = (0, 0, 255) if red_detected else (0, 255, 0)
        cv2.putText(
            frame, f"Durum: {status}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2
        )

        # Versiyon bilgisi
        cv2.putText(
            frame, f"v{__version__}",
            (CAMERA_WIDTH - 70, CAMERA_HEIGHT - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (128, 128, 128), 1
        )

        # FPS hesapla (her 30 frame'de bir logla)
        frame_count += 1
        if frame_count % 30 == 0:
            elapsed = time.time() - start_time
            fps = frame_count / elapsed
            logger.debug(f"FPS: {fps:.1f}")

        # JPEG olarak kodla
        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
        )

# ============================================================
#  WEB ROTALARI
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
    """Durum API"""
    return {
        "status": "running",
        "version": __version__,
        "arduino_connected": arduino is not None and arduino.is_open,
        "last_command": last_command
    }

@app.route('/health')
def health():
    """Saglik kontrolu"""
    return {"healthy": True, "version": __version__}

# ============================================================
#  ANA PROGRAM
# ============================================================

def main():
    """Ana fonksiyon"""
    logger.info("=" * 50)
    logger.info(f"  VISION LINE FOLLOWER v{__version__}")
    logger.info("=" * 50)
    logger.info(f"Seri Port: {SERIAL_PORT}")
    logger.info(f"Baud Rate: {BAUD_RATE}")
    logger.info(f"Kamera: {CAMERA_WIDTH}x{CAMERA_HEIGHT}")
    logger.info(f"Web: http://0.0.0.0:{WEB_PORT}")
    logger.info(f"Log Seviyesi: {LOG_LEVEL}")
    if LOG_FILE:
        logger.info(f"Log Dosyasi: {LOG_FILE}")
    logger.info("=" * 50)

    # Arduino baglantisi
    connect_arduino()

    # Kamera baslat
    if not setup_camera():
        logger.error("Kamera baslatilamadi, cikiliyor...")
        sys.exit(1)

    try:
        # Flask sunucusu
        app.run(host=WEB_HOST, port=WEB_PORT, threaded=True)

    except KeyboardInterrupt:
        logger.info("Klavye ile durduruldu")

    finally:
        # Temizlik
        logger.info("Kapatiliyor...")

        if arduino and arduino.is_open:
            send_command("GO")
            arduino.close()
            logger.info("Seri port kapatildi")

        if picam2:
            picam2.stop()
            logger.info("Kamera durduruldu")

        logger.info("Program sonlandi")


if __name__ == '__main__':
    main()
