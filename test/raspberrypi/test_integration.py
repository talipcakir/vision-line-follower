#!/usr/bin/env python3
"""
Arduino-Pi Entegrasyon Testi
Bu script Arduino ile Pi arasındaki iletişimi test eder.
"""

import sys
import time
import serial
import serial.tools.list_ports


def find_arduino():
    """Arduino'yu otomatik bul"""
    for port in serial.tools.list_ports.comports():
        desc = (port.description or "").lower()
        mfr = (port.manufacturer or "").lower()
        if any(x in desc or x in mfr for x in ['arduino', 'ch340', 'cp210', 'ftdi', 'usb serial']):
            return port.device

    # Linux'ta yaygın portlar
    for port in ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyACM1']:
        try:
            test = serial.Serial(port, 9600, timeout=1)
            test.close()
            return port
        except:
            pass

    return None


def test_connection(ser):
    """Bağlantı testi"""
    print("\n[TEST 1] Bağlantı testi (PING)")
    ser.write(b"PING\n")
    time.sleep(0.5)
    response = ser.readline().decode().strip()
    print(f"  Gönderilen: PING")
    print(f"  Alınan: {response}")
    return response == "PONG"


def test_version(ser):
    """Versiyon kontrolü"""
    print("\n[TEST 2] Versiyon kontrolü")
    ser.write(b"VERSION\n")
    time.sleep(0.3)
    response = ser.readline().decode().strip()
    print(f"  Gönderilen: VERSION")
    print(f"  Alınan: {response}")
    return response.startswith("VERSION:")


def test_sensors(ser):
    """Sensör okuma"""
    print("\n[TEST 3] Sensör okuma")
    ser.write(b"SENSORS\n")
    time.sleep(0.3)
    response = ser.readline().decode().strip()
    print(f"  Gönderilen: SENSORS")
    print(f"  Alınan: {response}")
    if response.startswith("SENSORS:"):
        sensors = response[8:].split(",")
        print(f"  Sensörler: S1={sensors[0]}, S2={sensors[1]}, S3={sensors[2]}, S4={sensors[3]}, S5={sensors[4]}")
        return True
    return False


def test_config(ser):
    """Konfigürasyon okuma"""
    print("\n[TEST 4] Konfigürasyon okuma")
    ser.write(b"CONFIG\n")
    time.sleep(0.3)
    response = ser.readline().decode().strip()
    print(f"  Gönderilen: CONFIG")
    print(f"  Alınan: {response}")
    if response.startswith("CONFIG:"):
        parts = response[7:].split(",")
        print(f"  Hız: {parts[0]}, Kp: {parts[1]}, Ki: {parts[2]}, Kd: {parts[3]}")
        return True
    return False


def test_start_stop(ser):
    """Başlat/Durdur testi"""
    print("\n[TEST 5] Başlat/Durdur testi")

    # GO
    ser.write(b"GO\n")
    time.sleep(0.3)
    response1 = ser.readline().decode().strip()
    print(f"  Gönderilen: GO -> {response1}")

    # STATUS
    ser.write(b"STATUS\n")
    time.sleep(0.3)
    response2 = ser.readline().decode().strip()
    print(f"  Gönderilen: STATUS -> {response2}")

    time.sleep(1)

    # STOP
    ser.write(b"STOP\n")
    time.sleep(0.3)
    response3 = ser.readline().decode().strip()
    print(f"  Gönderilen: STOP -> {response3}")

    return response1 == "OK_RUNNING" and response3 == "OK_STOPPED"


def test_speed(ser):
    """Hız ayarı testi"""
    print("\n[TEST 6] Hız ayarı testi")
    ser.write(b"SPEED:120\n")
    time.sleep(0.3)
    response = ser.readline().decode().strip()
    print(f"  Gönderilen: SPEED:120 -> {response}")
    return response == "OK_SPEED:120"


def test_pid(ser):
    """PID ayarı testi"""
    print("\n[TEST 7] PID ayarı testi")
    ser.write(b"PID:1.50,0.10,0.75\n")
    time.sleep(0.3)
    response = ser.readline().decode().strip()
    print(f"  Gönderilen: PID:1.50,0.10,0.75 -> {response}")
    return response.startswith("OK_PID:")


def main():
    print("=" * 50)
    print("  Arduino-Pi Entegrasyon Testi")
    print("=" * 50)

    # Port bul
    port = find_arduino()
    if not port:
        print("\n[HATA] Arduino bulunamadı!")
        print("Kontrol edin:")
        print("  - Arduino USB ile bağlı mı?")
        print("  - Doğru sürücüler yüklü mü?")
        sys.exit(1)

    print(f"\nArduino bulundu: {port}")

    # Bağlan
    try:
        ser = serial.Serial(port, 9600, timeout=2)
        time.sleep(2.5)  # Arduino reset bekle
        ser.reset_input_buffer()
        print("Bağlantı kuruldu")
    except Exception as e:
        print(f"\n[HATA] Bağlantı kurulamadı: {e}")
        sys.exit(1)

    # Testleri çalıştır
    results = []

    results.append(("Bağlantı (PING)", test_connection(ser)))
    results.append(("Versiyon", test_version(ser)))
    results.append(("Sensörler", test_sensors(ser)))
    results.append(("Konfigürasyon", test_config(ser)))
    results.append(("Başlat/Durdur", test_start_stop(ser)))
    results.append(("Hız Ayarı", test_speed(ser)))
    results.append(("PID Ayarı", test_pid(ser)))

    # Reset
    ser.write(b"RESET\n")
    time.sleep(0.3)

    # Sonuçlar
    print("\n" + "=" * 50)
    print("  TEST SONUÇLARI")
    print("=" * 50)

    passed = 0
    for name, result in results:
        status = "BAŞARILI" if result else "BAŞARISIZ"
        symbol = "✓" if result else "✗"
        print(f"  {symbol} {name}: {status}")
        if result:
            passed += 1

    print(f"\nToplam: {passed}/{len(results)} test başarılı")

    ser.close()

    if passed == len(results):
        print("\n[OK] Tüm testler başarılı!")
        sys.exit(0)
    else:
        print("\n[UYARI] Bazı testler başarısız!")
        sys.exit(1)


if __name__ == "__main__":
    main()
