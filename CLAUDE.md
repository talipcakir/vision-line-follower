# Vision Line Follower

**Versiyon:** 2.2.0 | **Lisans:** MIT

Dönem bitirme projesi. Arduino ile çizgi takip (PID kontrol), Raspberry Pi ile görsel işleme ve web yönetim arayüzü.

## v2.2 Yenilikler

- **Akıllı Çizgi Arama**: Çizgi kaybolunca geri dönüş + zigzag arama
- **Otomatik Kırmızı Durdurma**: Kamera kırmızı görünce robot otomatik durur
- **Callback Mekanizması**: SSE'ye bağımlı olmayan sürekli algılama

## Tüm Özellikler

- **Web Yönetim Arayüzü**: Tarayıcıdan tam robot kontrolü
- **PID Kontrol**: Ayarlanabilir Kp, Ki, Kd parametreleri
- **HSV Kalibrasyon**: Web'den kırmızı renk algılama ayarları
- **Arduino Yükleme**: Web'den sketch derleme ve yükleme
- **Heartbeat**: Otomatik bağlantı kontrolü ve yeniden bağlanma
- **Canlı Sensör İzleme**: 5 IR sensör durumu gerçek zamanlı
- **Detaylı Loglama**: Tüm işlemler loglanır ve web'den izlenebilir
- **SSE**: Server-Sent Events ile gerçek zamanlı güncellemeler

## Proje Yapısı

```
vision-line-follower/
├── arduino/
│   └── serit_takip_robotu_v2/       # Ana firmware (PID + protokol)
│       └── serit_takip_robotu_v2.ino
├── raspberrypi/
│   ├── requirements.txt
│   ├── web/                         # Web Arayüzü
│   │   ├── __init__.py
│   │   ├── app.py                   # Flask API
│   │   ├── config.py                # Konfigürasyon (HSV dahil)
│   │   ├── serial_manager.py        # Seri port + heartbeat
│   │   ├── arduino_manager.py       # arduino-cli wrapper
│   │   ├── camera_manager.py        # Kamera + renk algılama
│   │   └── static/                  # Frontend
│   │       ├── index.html
│   │       ├── css/style.css
│   │       └── js/app.js
│   └── service/
│       ├── serit_takip.service
│       └── kurulum.sh
├── test/
│   ├── arduino/
│   │   ├── test_cizgi_takip/
│   │   ├── test_sensor_kalibrasyon/
│   │   ├── test_usb/
│   │   └── test_extended_protocol/
│   └── raspberrypi/
│       ├── test_usb.py
│       ├── test_serial_manager.py
│       └── test_arduino_manager.py
└── docs/
    ├── pin_baglantilari.md
    ├── sorun_giderme.md
    └── web_arayuzu.md
```

## Hızlı Başlangıç

### 1. Arduino'ya Firmware Yükle
```bash
arduino-cli compile --upload --fqbn arduino:avr:uno arduino/serit_takip_robotu_v2
```

### 2. Raspberry Pi Kurulum
```bash
cd raspberrypi/service
chmod +x kurulum.sh
./kurulum.sh
```

### 3. Web Arayüzüne Eriş
```
http://<raspberry-pi-ip>:5000
```

## Web Arayüzü Sekmeleri

### Kontrol Sekmesi
- Robot başlat/durdur
- Hız ayarı (0-255)
- PID parametreleri (Kp, Ki, Kd)
- IR sensör görselleştirme
- Canlı kamera görüntüsü

### HSV Kalibrasyon Sekmesi
- Renk algılama aç/kapat
- Otomatik durdurma aç/kapat
- Kırmızı aralık 1 (H: 0-10)
- Kırmızı aralık 2 (H: 170-180)
- Minimum algılama alanı
- Blur ve morfolojik işlemler

### Arduino Sekmesi
- Bağlantı durumu ve yönetimi
- Mevcut portları listeleme
- Sketch derleme ve yükleme
- Komut terminali
- Hızlı komut butonları

### Log & Debug Sekmesi
- Gerçek zamanlı sistem logları
- Komut geçmişi
- Algılama geçmişi
- Sistem bilgileri

## Seri Protokol v2.0

| Komut | Yanıt | Açıklama |
|-------|-------|----------|
| `PING` | `PONG` | Bağlantı testi |
| `STOP` | `OK_STOPPED` | Robotu durdur |
| `GO` | `OK_RUNNING` | Robota devam et |
| `STATUS` | `STATUS_*` | Durum sorgula |
| `VERSION` | `VERSION:2.0.0` | Firmware versiyonu |
| `SPEED:<0-255>` | `OK_SPEED:<n>` | Hız ayarla |
| `PID:<Kp>,<Ki>,<Kd>` | `OK_PID:...` | PID parametreleri |
| `SENSORS` | `SENSORS:s1,s2,s3,s4,s5` | Sensör değerleri |
| `CONFIG` | `CONFIG:speed,Kp,Ki,Kd` | Mevcut ayarlar |
| `SAVE` | `OK_SAVED` | EEPROM'a kaydet |
| `LOAD` | `OK_LOADED` | EEPROM'dan yükle |
| `RESET` | `OK_RESET` | Varsayılana dön |

## Web API Endpoints

### Genel
| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/` | Ana sayfa |
| GET | `/video_feed` | MJPEG video akışı |
| GET | `/api/status` | Tam sistem durumu |
| GET | `/api/health` | Sağlık kontrolü |

### Robot Kontrolü
| Method | Endpoint | Açıklama |
|--------|----------|----------|
| POST | `/api/control/start` | Robot başlat |
| POST | `/api/control/stop` | Robot durdur |
| POST | `/api/command` | Manuel komut |

### Konfigürasyon
| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/config` | Mevcut ayarlar |
| POST | `/api/config/speed` | Hız ayarla |
| POST | `/api/config/pid` | PID ayarla |
| POST | `/api/config/save` | EEPROM kaydet |
| POST | `/api/config/reset` | Sıfırla |

### HSV Kalibrasyon
| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/hsv` | HSV ayarları |
| POST | `/api/hsv` | HSV güncelle |
| POST | `/api/hsv/save` | Dosyaya kaydet |
| POST | `/api/hsv/reset` | Varsayılana dön |
| POST | `/api/hsv/toggle` | Algılama aç/kapat |

### Arduino
| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/arduino/status` | CLI durumu |
| GET | `/api/arduino/ports` | Port listesi |
| GET | `/api/arduino/sketches` | Sketch listesi |
| POST | `/api/arduino/compile` | Sketch derle |
| POST | `/api/arduino/upload` | Sketch yükle |

### Log
| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/logs` | Sistem logları |
| GET | `/api/logs/command-history` | Komut geçmişi |
| GET | `/api/logs/detection-history` | Algılama geçmişi |
| GET | `/api/events` | SSE stream |

## PID Ayarları

| Parametre | Varsayılan | Aralık | Açıklama |
|-----------|------------|--------|----------|
| **Kp** | 1.0 | 0-10 | Anlık hata tepkisi |
| **Ki** | 0.0 | 0-5 | Birikmiş hata düzeltme |
| **Kd** | 0.5 | 0-10 | Hata değişim hızı |
| **baseSpeed** | 100 | 0-255 | Temel motor hızı |

## HSV Varsayılan Değerler

| Parametre | Kırmızı 1 | Kırmızı 2 |
|-----------|-----------|-----------|
| H Min | 0 | 170 |
| H Max | 10 | 180 |
| S Min | 120 | 120 |
| V Min | 70 | 70 |

- **Min Alan**: 1500 piksel
- **Blur Kernel**: 5

## Donanım Pin Bağlantıları

### Motor Pinleri
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

## Heartbeat

- **Interval**: 2 saniye
- **Max Failures**: 3 ardışık
- **Otomatik Reconnect**: Evet
- **Timeout**: 5 saniye

## Servis Komutları

```bash
# Durum
sudo systemctl status serit_takip.service

# Başlat
sudo systemctl start serit_takip.service

# Durdur
sudo systemctl stop serit_takip.service

# Yeniden başlat
sudo systemctl restart serit_takip.service

# Log izle
sudo journalctl -u serit_takip.service -f
```

## Geliştirme

```bash
# Web sunucusu (geliştirme)
cd raspberrypi
python3 -m web.app

# Log dosyası (varsayılan)
/var/log/vision-line-follower/app.log
```

## Dokümantasyon

- Donanım şemaları: `docs/pin_baglantilari.md`
- Hata çözümleri: `docs/sorun_giderme.md`
- Web arayüzü: `docs/web_arayuzu.md`
