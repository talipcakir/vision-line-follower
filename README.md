# Vision Line Follower

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)]()

Dönem bitirme projesi. Arduino ile çizgi takip (PID kontrol), Raspberry Pi ile görsel işleme ve tam özellikli web yönetim arayüzü.

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

## Web Arayüzü Önizleme

```
┌─────────────────────────────────────────────────────────────┐
│  Vision Line Follower                    [● Bağlı (USB)]    │
├─────────────────────────────────────────────────────────────┤
│  [Kontrol] [HSV Kalibrasyon] [Arduino] [Log & Debug]        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────────────────────┐  │
│  │                 │  │  Robot Kontrolü                 │  │
│  │   📷 Canlı      │  │  [▶ BAŞLAT]  [⏹ DURDUR]        │  │
│  │    Video        │  │  Durum: Çalışıyor               │  │
│  │                 │  ├─────────────────────────────────┤  │
│  └─────────────────┘  │  Hız: [======●====] 150         │  │
│                       ├─────────────────────────────────┤  │
│  Sensörler:           │  PID:  Kp[1.0] Ki[0.0] Kd[0.5]  │  │
│  [■][■][□][■][■]      │  [Uygula] [Kaydet] [Sıfırla]    │  │
└─────────────────────────────────────────────────────────────┘
```

## Hızlı Başlangıç

### 1. Arduino'ya Firmware Yükle

```bash
# Arduino CLI ile
arduino-cli compile --upload --fqbn arduino:avr:uno arduino/serit_takip_robotu_v2

# veya Arduino IDE ile: arduino/serit_takip_robotu_v2/serit_takip_robotu_v2.ino
```

### 2. Raspberry Pi Kurulum

```bash
# Dosyaları Pi'ye kopyalayın
scp -r . pi@<raspberry-pi-ip>:~/vision-line-follower

# Pi'de kurulum scriptini çalıştırın
ssh pi@<raspberry-pi-ip>
cd ~/vision-line-follower/raspberrypi/service
chmod +x kurulum.sh
./kurulum.sh
```

### 3. Web Arayüzüne Eriş

```
http://<raspberry-pi-ip>:5000
```

## Proje Yapısı

```
vision-line-follower/
├── arduino/
│   └── serit_takip_robotu_v2/       # PID kontrollü firmware
├── raspberrypi/
│   ├── web/                         # Web arayüzü
│   │   ├── app.py                   # Flask API
│   │   ├── config.py                # Konfigürasyon
│   │   ├── serial_manager.py        # Arduino iletişimi
│   │   ├── camera_manager.py        # Kamera ve algılama
│   │   ├── arduino_manager.py       # Sketch yönetimi
│   │   └── static/                  # Frontend
│   └── service/                     # Systemd servisi
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

## Web Arayüzü Özellikleri

### Kontrol Sekmesi
- Robot başlat/durdur
- Hız ayarı (0-255)
- PID parametreleri
- Canlı sensör izleme
- Kamera görüntüsü

### HSV Kalibrasyon
- Renk algılama aç/kapat
- Kırmızı renk aralıkları ayarı
- Minimum algılama alanı
- Anlık önizleme

### Arduino Yönetimi
- Port listesi ve bağlantı
- Sketch derleme ve yükleme
- Komut terminali
- Firmware bilgisi

### Log & Debug
- Gerçek zamanlı sistem logları
- Komut geçmişi
- Algılama geçmişi
- Sistem istatistikleri

## Servis Komutları

```bash
sudo systemctl start serit_takip.service    # Başlat
sudo systemctl stop serit_takip.service     # Durdur
sudo systemctl restart serit_takip.service  # Yeniden başlat
sudo systemctl status serit_takip.service   # Durum
sudo journalctl -u serit_takip.service -f   # Log izle
```

## Geliştirme

```bash
# Geliştirme sunucusu
cd raspberrypi
python3 -m web.app

# Log dosyası
/var/log/vision-line-follower/app.log
```

## API Referansı

Detaylı API dokümantasyonu için: [CLAUDE.md](CLAUDE.md)

## Dokümantasyon

| Dosya | İçerik |
|-------|--------|
| [CLAUDE.md](CLAUDE.md) | Proje özeti ve API referansı |
| [docs/pin_baglantilari.md](docs/pin_baglantilari.md) | Donanım şemaları |
| [docs/sorun_giderme.md](docs/sorun_giderme.md) | Sorun çözümleri |
| [docs/web_arayuzu.md](docs/web_arayuzu.md) | Web arayüzü kullanımı |

## Lisans

Bu proje [MIT Lisansı](LICENSE) altında lisanslanmıştır.

## Yazar

**Talip Çakır**

---

Bu proje eğitim amaçlı dönem bitirme projesi olarak geliştirilmiştir.
