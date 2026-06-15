# Test Dosyaları v2.2

Bu klasör test ve kalibrasyon için kullanılan kodları içerir.

## Klasör Yapısı

```
test/
├── arduino/                            # Arduino test kodları
│   ├── test_cizgi_takip/              # Bağımsız çizgi takip testi
│   ├── test_sensor_kalibrasyon/       # IR sensör kalibrasyon
│   ├── test_usb/                      # USB haberleşme testi
│   └── test_extended_protocol/        # Genişletilmiş protokol testi
└── raspberrypi/                        # Raspberry Pi test kodları
    ├── test_integration.py            # Tam entegrasyon testi
    ├── test_usb.py                    # USB haberleşme testi
    ├── test_serial_manager.py         # SerialManager testi
    └── test_arduino_manager.py        # ArduinoManager testi
```

## Önerilen Test Sırası

### 1. Sensör Kalibrasyonu

IR sensörlerin doğru çalıştığını kontrol edin.

```bash
# Arduino IDE veya CLI ile yükleyin
arduino-cli compile --upload --fqbn arduino:avr:uno test/arduino/test_sensor_kalibrasyon
```

Serial Monitor'de (9600 baud):
- Siyah çizgi üzerinde: `1` görmeli
- Beyaz zemin üzerinde: `0` görmeli

### 2. USB Haberleşme Testi

Arduino ve Pi arasındaki bağlantıyı test edin.

**Arduino tarafı:**
```bash
arduino-cli compile --upload --fqbn arduino:avr:uno test/arduino/test_usb
```

**Pi tarafı:**
```bash
cd ~/vision-line-follower/test/raspberrypi
python3 test_usb.py
```

### 3. Entegrasyon Testi

Tüm komutları test eden kapsamlı test:

```bash
cd ~/vision-line-follower/test/raspberrypi
python3 test_integration.py
```

Bu test:
- PING/PONG bağlantı kontrolü
- VERSION firmware kontrolü
- SENSORS sensör okuma
- CONFIG ayar okuma
- GO/STOP motor kontrolü
- SPEED/PID parametre ayarı

### 4. Çizgi Takip Testi

Pi olmadan bağımsız çizgi takip testi:

```bash
arduino-cli compile --upload --fqbn arduino:avr:uno test/arduino/test_cizgi_takip
```

## Test Detayları

### test_sensor_kalibrasyon

**Amaç:** IR sensörlerin doğru çalıştığını doğrulamak

**Çıktı formatı:**
```
S1:1  S2:0  S3:0  S4:0  S5:1
```

### test_usb (Arduino)

**Amaç:** Seri haberleşme protokolünü test etmek

**Desteklenen komutlar:**
| Komut | Yanıt |
|-------|-------|
| PING | PONG |
| STOP | OK_STOPPED |
| GO | OK_RUNNING |
| STATUS | STATUS_* |

### test_integration.py

**Amaç:** Tam sistem entegrasyonunu doğrulamak

**Çıktı:**
```
[TEST] Bağlantı (PING)
  Gönderilen: PING
  Alınan: PONG
  BAŞARILI

Toplam: 7/7 test başarılı
```

## Sorun Giderme

### Arduino bulunamıyor

```bash
# Portları listele
ls -la /dev/ttyACM* /dev/ttyUSB*

# Yetki ekle
sudo usermod -a -G dialout $USER
sudo reboot
```

### Sensör değerleri ters

Bazı IR sensörler ters çalışır. Test kodunda:
```cpp
const int SIYAH = 0;  // veya 1
```

### Serial Monitor açılmıyor

- Doğru port seçili mi kontrol edin
- Test scriptlerinin portu kullanmadığından emin olun
