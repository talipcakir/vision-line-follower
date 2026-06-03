# Test Dosyaları

Bu klasör test ve kalibrasyon için kullanılan kodları içerir.

## Klasör Yapısı

```
test/
├── README.md                           # Bu dosya
├── arduino/                            # Arduino test kodları
│   ├── test_cizgi_takip/              # Sadece çizgi takip testi
│   │   └── test_cizgi_takip.ino
│   ├── test_sensor_kalibrasyon/       # IR sensör kalibrasyon
│   │   └── test_sensor_kalibrasyon.ino
│   └── test_usb/                      # USB haberleşme testi
│       └── test_usb.ino
└── raspberrypi/                        # Raspberry Pi test kodları
    └── test_usb.py                    # USB haberleşme testi
```

## Test Sırası (Önerilen)

Robotu ilk kez kurarken şu sırayla test edin:

### 1. Sensör Kalibrasyonu

IR sensörlerin doğru çalıştığını kontrol edin.

```bash
# Arduino IDE'den yükleyin:
test/arduino/test_sensor_kalibrasyon/test_sensor_kalibrasyon.ino
```

Serial Monitor'de (9600 baud):
- Siyah çizgi üzerinde: `0` görmeli
- Beyaz zemin üzerinde: `1` görmeli

### 2. Çizgi Takip Testi

Motorların ve sensörlerin birlikte çalışmasını test edin.

```bash
# Arduino IDE'den yükleyin:
test/arduino/test_cizgi_takip/test_cizgi_takip.ino
```

**Not:** Bu test Raspberry Pi olmadan çalışır. Sadece çizgi takip yapar.

### 3. USB Haberleşme Testi

Arduino ve Raspberry Pi arasındaki USB bağlantısını test edin.

**Adım 1: Arduino'ya test kodunu yükleyin**
```bash
# Arduino IDE'den:
test/arduino/test_usb/test_usb.ino
```

**Adım 2: Pi'de test scriptini çalıştırın**
```bash
cd ~/vision-line-follower/test/raspberrypi
python3 test_usb.py
```

**Beklenen çıktı:**
```
[TEST] PING Testi
  Komut: PING
  Beklenen: PONG
  Gelen: PONG
  Sonuc: BASARILI ✓
```

## Test Kodları Detayları

### test_sensor_kalibrasyon

**Amaç:** IR sensörlerin doğru çalışıp çalışmadığını kontrol etmek.

**Kullanım:**
1. Kodu Arduino'ya yükleyin
2. Serial Monitor açın (9600 baud)
3. Sensörleri siyah/beyaz yüzey üzerinde gezdirin
4. Değerleri gözlemleyin

**Çıktı formatı:**
```
S1:0  S2:1  S3:1  S4:1  S5:0
```

### test_cizgi_takip

**Amaç:** Raspberry Pi olmadan sadece çizgi takip fonksiyonunu test etmek.

**Özellikler:**
- 5 sensörlü çizgi takip
- Ağırlıklı ortalama hesaplama
- PWM motor kontrolü

**Motor hız ayarları:**
```cpp
const int HIZ_MAX = 120;
const int HIZ_MIN = 40;
```

### test_usb (Arduino)

**Amaç:** Arduino'nun seri komutları doğru alıp yanıtladığını test etmek.

**Desteklenen komutlar:**
| Komut | Cevap | LED |
|-------|-------|-----|
| PING | PONG | - |
| STOP | OK_STOPPED | Yanar |
| GO | OK_RUNNING | Söner |
| STATUS | STATUS_STOPPED veya STATUS_RUNNING | - |
| HELP | Komut listesi | - |

### test_usb.py (Raspberry Pi)

**Amaç:** Pi'den Arduino'ya USB bağlantısını test etmek.

**Özellikler:**
- Otomatik port bulma (/dev/ttyACM0, /dev/ttyUSB0)
- PING/PONG testi
- STOP/GO komut testi
- İnteraktif mod

**Çalıştırma:**
```bash
python3 test_usb.py
```

## Sorun Giderme

### Sensör değerleri ters

Bazı IR sensörler ters çalışır. Kodda şu değişikliği yapın:
```cpp
const int SIYAH = 1;  // 0 yerine 1
```

### USB port bulunamıyor

```bash
# Bağlı portları listele
ls -la /dev/ttyACM* /dev/ttyUSB*

# Yetki ekle
sudo usermod -a -G dialout $USER
sudo reboot
```

### Serial Monitor açılmıyor

Arduino IDE'de doğru port seçili olmalı:
- **Tools > Port > COMx** (Windows)
- **Tools > Port > /dev/ttyACM0** (Linux/Pi)

## İlgili Dosyalar

- [Ana README](../README.md) - Proje genel bakış
- [Arduino Kodları](../arduino/README.md) - Ana Arduino kodu
- [Raspberry Pi Kodları](../raspberrypi/README.md) - Ana Pi kodu
- [Pin Bağlantıları](../docs/pin_baglantilari.md) - Donanım şemaları
- [Sorun Giderme](../docs/sorun_giderme.md) - Detaylı hata çözümleri
