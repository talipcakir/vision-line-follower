#!/usr/bin/env python3
# ============================================================
#  SERIT TAKIP ROBOTU - Baslatici Script
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

import os
import sys
import time
import signal
import subprocess
import serial
import serial.tools.list_ports

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
GORSEL_ISLEME_PATH = os.path.join(SCRIPT_DIR, 'gorsel_isleme.py')

# Calistirilan alt islem
gorsel_isleme_process = None

# Calisma durumu
running = True


# ============================================================
#  LOG FONKSIYONU
# ============================================================

def log(message):
    """Zaman damgali log mesaji yazdir"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}", flush=True)


# ============================================================
#  SINYAL ISLEYICILER
# ============================================================

def signal_handler(signum, frame):
    """SIGTERM/SIGINT sinyallerini yakala ve temiz kapat"""
    global running
    log(f"Sinyal alindi: {signum}")
    log("Kapatiliyor...")
    running = False
    stop_gorsel_isleme()
    sys.exit(0)


# SIGTERM ve SIGINT sinyallerini yakala
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


# ============================================================
#  ARDUINO BAGLANTI FONKSIYONLARI
# ============================================================

def find_arduino():
    """
    Arduino'nun bagli oldugu portu bul.
    PING komutu gonderip PONG cevabi bekler.
    """
    for port in ARDUINO_PORTS:
        try:
            # Port mevcut mu kontrol et
            if not os.path.exists(port):
                continue

            log(f"Port deneniyor: {port}")

            # Seri baglanti ac
            ser = serial.Serial(port, BAUD_RATE, timeout=2)
            time.sleep(2)  # Arduino reset icin bekle

            # Buffer'i temizle
            ser.reset_input_buffer()
            ser.reset_output_buffer()

            # PING gonder
            ser.write(b"PING\n")
            time.sleep(0.5)

            # Cevap oku
            response = ""
            while ser.in_waiting > 0:
                response += ser.readline().decode()

            ser.close()

            # PONG cevabi geldi mi?
            if "PONG" in response:
                log(f"Arduino bulundu: {port}")
                return port

            log(f"Port {port} - Cevap: {response.strip()}")

        except Exception as e:
            log(f"Port {port} - Hata: {e}")

    return None


def wait_for_arduino():
    """Arduino baglanana kadar bekle"""
    log("Arduino bekleniyor...")

    while running:
        port = find_arduino()
        if port:
            return port

        log(f"Arduino bulunamadi, {CHECK_INTERVAL} saniye sonra tekrar denenecek...")
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
        log("Gorsel isleme zaten calisiyor")
        return True

    if not os.path.exists(GORSEL_ISLEME_PATH):
        log(f"HATA: Gorsel isleme scripti bulunamadi: {GORSEL_ISLEME_PATH}")
        return False

    try:
        log(f"Gorsel isleme baslatiliyor: {GORSEL_ISLEME_PATH}")
        gorsel_isleme_process = subprocess.Popen(
            [sys.executable, GORSEL_ISLEME_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        log(f"Gorsel isleme baslatildi (PID: {gorsel_isleme_process.pid})")
        return True

    except Exception as e:
        log(f"HATA: Gorsel isleme baslatilamadi: {e}")
        return False


def stop_gorsel_isleme():
    """Gorsel isleme programini durdur"""
    global gorsel_isleme_process

    if gorsel_isleme_process:
        log("Gorsel isleme durduruluyor...")
        try:
            gorsel_isleme_process.terminate()
            gorsel_isleme_process.wait(timeout=5)
            log("Gorsel isleme durduruldu")
        except subprocess.TimeoutExpired:
            log("Zorla kapatiliyor...")
            gorsel_isleme_process.kill()
        except Exception as e:
            log(f"Durdurma hatasi: {e}")

        gorsel_isleme_process = None


def is_gorsel_isleme_running():
    """Gorsel isleme calisiyor mu kontrol et"""
    if gorsel_isleme_process:
        return gorsel_isleme_process.poll() is None
    return False


# ============================================================
#  ANA DONGU
# ============================================================

def main():
    """Ana program dongusu"""
    log("=" * 50)
    log("  SERIT TAKIP ROBOTU - Baslatici")
    log("=" * 50)
    log(f"Gorsel isleme scripti: {GORSEL_ISLEME_PATH}")
    log(f"Kontrol araligi: {CHECK_INTERVAL} saniye")
    log("=" * 50)

    arduino_port = None

    while running:
        try:
            # ----- ARDUINO BAGLANTISINI KONTROL ET -----
            if arduino_port is None:
                # Arduino'yu bul
                arduino_port = wait_for_arduino()
                if arduino_port is None:
                    continue

            # Arduino hala bagli mi?
            if not check_arduino_connected(arduino_port):
                log("Arduino baglantisi koptu!")
                stop_gorsel_isleme()
                arduino_port = None
                continue

            # ----- GORSEL ISLEME KONTROLU -----
            if not is_gorsel_isleme_running():
                # Gorsel isleme calismiyor, baslat
                if not start_gorsel_isleme():
                    log("Gorsel isleme baslatilamadi, 5 saniye bekleniyor...")
                    time.sleep(5)
                    continue

            # ----- GORSEL ISLEME CIKTISINI OKU -----
            if gorsel_isleme_process:
                try:
                    # Non-blocking okuma
                    import select
                    if select.select([gorsel_isleme_process.stdout], [], [], 0)[0]:
                        line = gorsel_isleme_process.stdout.readline()
                        if line:
                            print(f"[GORSEL] {line.strip()}", flush=True)
                except Exception:
                    pass

            # Kisa bekleme
            time.sleep(1)

        except KeyboardInterrupt:
            log("Klavye kesintisi alindi")
            break

        except Exception as e:
            log(f"HATA: {e}")
            time.sleep(5)

    # Temizlik
    stop_gorsel_isleme()
    log("Program sonlandi")


# ============================================================
#  PROGRAM GIRISI
# ============================================================

if __name__ == "__main__":
    main()
