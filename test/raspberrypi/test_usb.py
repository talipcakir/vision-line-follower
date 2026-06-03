#!/usr/bin/env python3
# ============================================================
#  USB SERI HABERLESME TESTI - Raspberry Pi
# ============================================================
#
#  AMAC:
#  Raspberry Pi ile Arduino arasindaki USB seri haberlesmeyi
#  test etmek icin kullanilir.
#
#  KULLANIM:
#  1. test_usb_arduino.ino kodunu Arduino'ya yukleyin
#  2. Arduino'yu Raspberry Pi'ye USB ile baglayin
#  3. Bu scripti calistirin: python3 test_usb_pi.py
#
#  GEREKSINIMLER:
#  pip3 install pyserial
#
# ============================================================

import serial
import time
import sys

# ============================================================
#  AYARLAR
# ============================================================

# Arduino'nun bagli oldugu seri port
# Farkli portlari denemek icin liste kullaniyoruz
POSSIBLE_PORTS = [
    '/dev/ttyACM0',   # Arduino Uno, Mega (Linux)
    '/dev/ttyUSB0',   # Arduino Nano, klon kartlar (Linux)
    '/dev/ttyACM1',   # Alternatif port
    '/dev/ttyUSB1',   # Alternatif port
    'COM3',           # Windows
    'COM4',           # Windows
]

BAUD_RATE = 9600


# ============================================================
#  ARDUINO BAGLANTISI
# ============================================================

def find_arduino():
    """Arduino'nun bagli oldugu portu bul"""
    print("Arduino araniyor...")
    print("-" * 40)

    for port in POSSIBLE_PORTS:
        try:
            print(f"  Deneniyor: {port}...", end=" ")
            ser = serial.Serial(port, BAUD_RATE, timeout=2)
            time.sleep(2)  # Arduino reset icin bekle

            # PING testi yap
            ser.write(b"PING\n")
            time.sleep(0.5)
            response = ser.readline().decode().strip()

            if response == "PONG":
                print("BULUNDU!")
                return ser
            else:
                print(f"Cevap: {response}")
                ser.close()

        except Exception as e:
            print(f"Hata: {e}")

    return None


# ============================================================
#  TEST FONKSIYONLARI
# ============================================================

def send_command(ser, command, expected_response=None):
    """Komut gonder ve cevabi kontrol et"""
    ser.write(f"{command}\n".encode())
    time.sleep(0.3)

    response = ""
    while ser.in_waiting > 0:
        response += ser.readline().decode()

    response = response.strip()

    if expected_response:
        if expected_response in response:
            return True, response
        else:
            return False, response
    else:
        return True, response


def run_tests(ser):
    """Tum testleri calistir"""
    print("\n" + "=" * 50)
    print("  USB SERI HABERLESME TESTLERI")
    print("=" * 50)

    tests = [
        ("PING Testi", "PING", "PONG"),
        ("STOP Testi", "STOP", "OK_STOPPED"),
        ("STATUS Testi (STOP sonrasi)", "STATUS", "STATUS_STOPPED"),
        ("GO Testi", "GO", "OK_RUNNING"),
        ("STATUS Testi (GO sonrasi)", "STATUS", "STATUS_RUNNING"),
    ]

    passed = 0
    failed = 0

    for test_name, command, expected in tests:
        print(f"\n[TEST] {test_name}")
        print(f"  Komut: {command}")
        print(f"  Beklenen: {expected}")

        success, response = send_command(ser, command, expected)

        print(f"  Gelen: {response}")

        if success:
            print("  Sonuc: BASARILI ✓")
            passed += 1
        else:
            print("  Sonuc: BASARISIZ ✗")
            failed += 1

    # Ozet
    print("\n" + "=" * 50)
    print("  TEST SONUCLARI")
    print("=" * 50)
    print(f"  Basarili: {passed}")
    print(f"  Basarisiz: {failed}")
    print(f"  Toplam: {passed + failed}")
    print("=" * 50)

    return failed == 0


def interactive_mode(ser):
    """Interaktif komut moduna gec"""
    print("\n" + "=" * 50)
    print("  INTERAKTIF MOD")
    print("=" * 50)
    print("Komut girin (cikis icin 'exit' yazin):")
    print("Kullanilabilir: PING, STOP, GO, STATUS, HELP")
    print("-" * 50)

    while True:
        try:
            command = input("\n> ").strip()

            if command.lower() == 'exit':
                print("Cikis yapiliyor...")
                break

            if command:
                success, response = send_command(ser, command)
                print(f"Cevap: {response}")

        except KeyboardInterrupt:
            print("\nCikis yapiliyor...")
            break


# ============================================================
#  ANA PROGRAM
# ============================================================

def main():
    print("=" * 50)
    print("  USB SERI HABERLESME TESTI")
    print("  Raspberry Pi <-> Arduino")
    print("=" * 50)

    # Arduino'yu bul
    arduino = find_arduino()

    if not arduino:
        print("\n" + "!" * 50)
        print("  HATA: Arduino bulunamadi!")
        print("!" * 50)
        print("\nKontrol edin:")
        print("  1. Arduino USB ile bagli mi?")
        print("  2. test_usb_arduino.ino yuklendi mi?")
        print("  3. Dogru port: ls /dev/tty*")
        print("  4. Yetki var mi: sudo chmod 666 /dev/ttyACM0")
        sys.exit(1)

    print(f"\nArduino bulundu: {arduino.port}")

    # Testleri calistir
    all_passed = run_tests(arduino)

    # Interaktif mod
    if all_passed:
        print("\nTum testler basarili!")
        answer = input("\nInteraktif moda gecmek ister misiniz? (e/h): ")
        if answer.lower() == 'e':
            interactive_mode(arduino)
    else:
        print("\nBazi testler basarisiz oldu.")
        print("Arduino kodunu ve baglantilari kontrol edin.")

    # Temizlik
    arduino.close()
    print("\nBaglanti kapatildi.")


if __name__ == "__main__":
    main()
