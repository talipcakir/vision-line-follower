#!/usr/bin/env python3
# ============================================================
#  VISION LINE FOLLOWER - Baslatici Script
# ============================================================
#
#  AMAC:
#  Bu script systemd servisi tarafindan calistirilir.
#  Arduino USB baglantisini bekler ve gorsel isleme
#  programini baslatir.
#
#  OZELLIKLER:
#  - Arduino baglanana kadar bekler
#  - Baglanti koparsa yeniden baglanir
#  - Hatalari loglar
#  - Temiz kapatma destegi (SIGTERM)
#
# ============================================================

__version__ = "1.0.0"

import os
import sys
import time
import signal
import subprocess
import logging
from logging.handlers import RotatingFileHandler

import serial

# ============================================================
#  AYARLAR
# ============================================================

# Arduino'nun bagli olabilecegi portlar
ARDUINO_PORTS = [
    '/dev/ttyACM0',
    '/dev/ttyACM1',
    '/dev/ttyUSB0',
    '/dev/ttyUSB1',
]

# Seri port ayarlari
BAUD_RATE = 9600

# Kontrol araligi (saniye)
CHECK_INTERVAL = 2

# Gorsel isleme script yolu
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(SCRIPT_DIR)  # raspberrypi/
GORSEL_ISLEME_PATH = os.path.join(PARENT_DIR, 'gorsel_isleme.py')

# Log ayarlari
LOG_DIR = os.path.join(PARENT_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'baslatici.log')

# ============================================================
#  LOGLAMA
# ============================================================

def setup_logging():
    """Loglama sistemini kur"""
    os.makedirs(LOG_DIR, exist_ok=True)

    log_format = '%(asctime)s [%(levelname)s] %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    logger = logging.getLogger('baslatici')
    logger.setLevel(logging.INFO)

    # Konsol
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(console)

    # Dosya
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=2*1024*1024,  # 2 MB
        backupCount=3
    )
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(file_handler)

    return logger

logger = setup_logging()

# ============================================================
#  GLOBAL DEGISKENLER
# ============================================================

gorsel_isleme_process = None
running = True

# ============================================================
#  SINYAL ISLEYICILER
# ============================================================

def signal_handler(signum, frame):
    """SIGTERM/SIGINT sinyallerini yakala"""
    global running
    logger.info(f"Sinyal alindi: {signum}")
    running = False
    stop_gorsel_isleme()
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# ============================================================
#  ARDUINO BAGLANTI FONKSIYONLARI
# ============================================================

def find_arduino():
    """Arduino'nun bagli oldugu portu bul"""
    for port in ARDUINO_PORTS:
        try:
            if not os.path.exists(port):
                continue

            logger.debug(f"Port deneniyor: {port}")

            ser = serial.Serial(port, BAUD_RATE, timeout=2)
            time.sleep(2)

            ser.reset_input_buffer()
            ser.reset_output_buffer()
            ser.write(b"PING\n")
            time.sleep(0.5)

            response = ""
            while ser.in_waiting > 0:
                response += ser.readline().decode()

            ser.close()

            if "PONG" in response:
                logger.info(f"Arduino bulundu: {port}")
                return port

        except Exception as e:
            logger.debug(f"Port {port} - Hata: {e}")

    return None


def wait_for_arduino():
    """Arduino baglanana kadar bekle"""
    logger.info("Arduino bekleniyor...")

    while running:
        port = find_arduino()
        if port:
            return port

        logger.debug(f"Arduino bulunamadi, {CHECK_INTERVAL}s sonra tekrar...")
        time.sleep(CHECK_INTERVAL)

    return None


def check_arduino_connected(port):
    """Arduino hala bagli mi kontrol et"""
    try:
        if not os.path.exists(port):
            return False

        ser = serial.Serial(port, BAUD_RATE, timeout=1)
        ser.write(b"PING\n")
        time.sleep(0.3)

        response = ""
        while ser.in_waiting > 0:
            response += ser.readline().decode()

        ser.close()
        return "PONG" in response

    except Exception:
        return False

# ============================================================
#  GORSEL ISLEME YONETIMI
# ============================================================

def start_gorsel_isleme():
    """Gorsel isleme programini baslat"""
    global gorsel_isleme_process

    if gorsel_isleme_process and gorsel_isleme_process.poll() is None:
        logger.debug("Gorsel isleme zaten calisiyor")
        return True

    if not os.path.exists(GORSEL_ISLEME_PATH):
        logger.error(f"Script bulunamadi: {GORSEL_ISLEME_PATH}")
        return False

    try:
        logger.info(f"Gorsel isleme baslatiliyor...")
        gorsel_isleme_process = subprocess.Popen(
            [sys.executable, GORSEL_ISLEME_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        logger.info(f"Gorsel isleme baslatildi (PID: {gorsel_isleme_process.pid})")
        return True

    except Exception as e:
        logger.error(f"Baslatilamadi: {e}")
        return False


def stop_gorsel_isleme():
    """Gorsel isleme programini durdur"""
    global gorsel_isleme_process

    if gorsel_isleme_process:
        logger.info("Gorsel isleme durduruluyor...")
        try:
            gorsel_isleme_process.terminate()
            gorsel_isleme_process.wait(timeout=5)
            logger.info("Durduruldu")
        except subprocess.TimeoutExpired:
            logger.warning("Zorla kapatiliyor...")
            gorsel_isleme_process.kill()
        except Exception as e:
            logger.error(f"Durdurma hatasi: {e}")

        gorsel_isleme_process = None


def is_gorsel_isleme_running():
    """Gorsel isleme calisiyor mu"""
    if gorsel_isleme_process:
        return gorsel_isleme_process.poll() is None
    return False

# ============================================================
#  ANA DONGU
# ============================================================

def main():
    """Ana program"""
    logger.info("=" * 50)
    logger.info(f"  VISION LINE FOLLOWER - Baslatici v{__version__}")
    logger.info("=" * 50)
    logger.info(f"Gorsel isleme: {GORSEL_ISLEME_PATH}")
    logger.info(f"Log dosyasi: {LOG_FILE}")
    logger.info("=" * 50)

    arduino_port = None

    while running:
        try:
            # Arduino baglantisi kontrol
            if arduino_port is None:
                arduino_port = wait_for_arduino()
                if arduino_port is None:
                    continue

            if not check_arduino_connected(arduino_port):
                logger.warning("Arduino baglantisi koptu!")
                stop_gorsel_isleme()
                arduino_port = None
                continue

            # Gorsel isleme kontrol
            if not is_gorsel_isleme_running():
                if not start_gorsel_isleme():
                    logger.error("Baslatilamadi, 5s bekleniyor...")
                    time.sleep(5)
                    continue

            # Alt islem ciktisini oku
            if gorsel_isleme_process:
                try:
                    import select
                    if select.select([gorsel_isleme_process.stdout], [], [], 0)[0]:
                        line = gorsel_isleme_process.stdout.readline()
                        if line:
                            # Alt islem loglarini yonlendir
                            print(f"[GORSEL] {line.strip()}", flush=True)
                except Exception:
                    pass

            time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Klavye ile durduruldu")
            break

        except Exception as e:
            logger.error(f"Hata: {e}")
            time.sleep(5)

    stop_gorsel_isleme()
    logger.info("Program sonlandi")


if __name__ == "__main__":
    main()
