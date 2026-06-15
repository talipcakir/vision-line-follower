# Vision Line Follower

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-2.2.0-blue.svg)]()

Dönem bitirme projesi. Arduino ile çizgi takip (PID kontrol), Raspberry Pi ile görsel işleme ve tam özellikli web yönetim arayüzü.

## v2.2 Yenilikler

- **Akıllı Çizgi Arama**: Çizgi kaybolunca geri dönüp zigzag arama yapar
- **Otomatik Kırmızı Durdurma**: Kamera kırmızı görünce robot otomatik durur
- **Tek Tuşla Kurulum**: Tek script ile tüm kurulum ve başlatma

## Özellikler

- 5 kanallı IR sensör ile siyah çizgi takibi (PID kontrol)
- Raspberry Pi kamera ile kırmızı renk algılama
- Kırmızı görünce otomatik durma
- USB seri haberleşme (Pi ↔ Arduino)
- **Web arayüzünden tam kontrol**
- HSV renk kalibrasyonu
- Arduino sketch yükleme
- Gerçek zamanlı log izleme
- Otomatik başlatma servisi

## Hızlı Başlangıç

### 1. Arduino'ya Firmware Yükle

```bash
# Arduino CLI ile
arduino-cli compile --upload --fqbn arduino:avr:uno arduino/serit_takip_robotu_v2

# veya Arduino IDE ile
# Dosya: arduino/serit_takip_robotu_v2/serit_takip_robotu_v2.ino
```

### 2. Raspberry Pi Kurulum (Tek Komut)

```bash
# Projeyi Pi'ye kopyalayın
scp -r . pi@<raspberry-pi-ip>:~/vision-line-follower

# Pi'de kurulum
ssh pi@<raspberry-pi-ip>
cd ~/vision-line-follower/raspberrypi/service
chmod +x kurulum.sh
./kurulum.sh
```

Kurulum scripti otomatik olarak:
- Tüm bağımlılıkları yükler
- Arduino CLI kurar
- Seri port yetkilerini ayarlar
- Systemd servisini kurar
- Projeyi başlatır

### 3. Web Arayüzüne Eriş

```
http://<raspberry-pi-ip>:5000
```

## Web Arayüzü Önizleme

```
┌─────────────────────────────────────────────────────────────┐
│  Vision Line Follower                    [● Bağlı (USB)]    │
├─────────────────────────────────────────────────────────────┤
│  [Kontrol] [HSV Kalibrasyon] [Arduino] [Log & Debug]        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────────────────────┐  │
│  │                 │  │  Robot Kontrolü                 │  │
│  │   Canlı        │  │  [▶ BAŞLAT]  [⏹ DURDUR]        │  │
│  │    Video       │  │  Durum: Çalışıyor               │  │
│  │                 │  ├─────────────────────────────────┤  │
│  └─────────────────┘  │  Hız: [======●====] 150         │  │
│                       ├─────────────────────────────────┤  │
│  Sensörler:           │  PID:  Kp[1.0] Ki[0.0] Kd[0.5]  │  │
│  [■][■][□][■][■]      │  [Uygula] [Kaydet] [Sıfırla]    │  │
└─────────────────────────────────────────────────────────────┘
```

## Proje Yapısı

```
vision-line-follower/
├── arduino/
│   └── serit_takip_robotu_v2/       # PID + akıllı çizgi arama
├── raspberrypi/
│   ├── web/                         # Web arayüzü
│   │   ├── app.py                   # Flask API
│   │   ├── config.py                # Konfigürasyon
│   │   ├── serial_manager.py        # Arduino iletişimi
│   │   ├── camera_manager.py        # Kamera ve algılama
│   │   ├── arduino_manager.py       # Sketch yönetimi
│   │   └── static/                  # Frontend
│   ├── service/                     # Systemd servisi
│   │   ├── kurulum.sh               # Tek tuşla kurulum
│   │   └── serit_takip.service
│   └── requirements.txt
├── test/                            # Test dosyaları
└── docs/                            # Dokümantasyon
```

## Donanım Listesi

| Bileşen | Adet | Açıklama |
|---------|------|----------|
| Arduino Uno | 1 | Motor kontrolü |
| Raspberry Pi 4 | 1 | Görsel işleme + Web sunucu |
| Pi Camera | 1 | Kamera modülü |
| L298N Motor Sürücü | 1 | DC motor kontrolü |
| DC Motor | 2 | Sol ve sağ tekerlekler |
| 5'li IR Sensör | 1 | Çizgi takip |
| USB Kablo | 1 | Pi-Arduino haberleşme |
| Pil (7-12V) | 1 | Arduino + motorlar |
| Power Bank (5V) | 1 | Raspberry Pi |

## Pin Bağlantıları

### Motor Pinleri (L298N)
| Motor | PWM | Yön A | Yön B |
|-------|-----|-------|-------|
| Sol | D6 | D10 | D11 |
| Sağ | D5 | D8 | D9 |

### IR Sensör Pinleri
| Sensör | Pin | Konum |
|--------|-----|-------|
| S1 | D2 | En sol |
| S2 | D3 | Sol |
| S3 | D4 | Orta |
| S4 | D7 | Sağ |
| S5 | D12 | En sağ |

## Servis Komutları

```bash
sudo systemctl start serit_takip    # Başlat
sudo systemctl stop serit_takip     # Durdur
sudo systemctl restart serit_takip  # Yeniden başlat
sudo systemctl status serit_takip   # Durum
journalctl -u serit_takip -f        # Log izle
```

## Geliştirme

```bash
# Geliştirme sunucusu
cd raspberrypi
python3 -m web.app

# Log dosyası
/var/log/vision-line-follower/app.log
```

## Dokümantasyon

| Dosya | İçerik |
|-------|--------|
| [CLAUDE.md](CLAUDE.md) | Proje özeti ve API referansı |
| [docs/pin_baglantilari.md](docs/pin_baglantilari.md) | Donanım şemaları |
| [docs/sorun_giderme.md](docs/sorun_giderme.md) | Sorun çözümleri |
| [docs/web_arayuzu.md](docs/web_arayuzu.md) | Web arayüzü kullanımı |

## Sorun Giderme

### Arduino algılanmıyor
```bash
# Port kontrolü
ls -la /dev/ttyACM* /dev/ttyUSB*

# Yetki ekleme (gerekirse)
sudo usermod -a -G dialout $USER
sudo reboot
```

### Kamera çalışmıyor
```bash
# Kamera kontrolü
libcamera-hello --list-cameras

# Kamerayı etkinleştir
sudo raspi-config
# Interface Options > Camera > Enable
```

### Web arayüzüne erişilemiyor
```bash
# Servis durumu
sudo systemctl status serit_takip

# Port kontrolü
sudo netstat -tlnp | grep 5000
```

## Lisans

Bu proje [MIT Lisansı](LICENSE) altında lisanslanmıştır.

## Yazar

**Talip Çakır** - Dönem Bitirme Projesi
