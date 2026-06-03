# Vision Line Follower

**Versiyon:** 2.0.0 | **Lisans:** MIT

Dönem bitirme projesi. Arduino ile çizgi takip (PID kontrol), Raspberry Pi ile görsel işleme ve web yönetim arayüzü.

## v2.0 Yeni Özellikler

- **Web Yönetim Arayüzü**: Tarayıcıdan robot kontrolü
- **PID Kontrol**: Yumuşak dönüşler için ayarlanabilir Kp, Ki, Kd
- **Arduino Yükleme**: Web'den sketch yükleme (arduino-cli)
- **Heartbeat**: Otomatik bağlantı kontrolü ve yeniden bağlanma
- **Canlı Sensör İzleme**: 5 IR sensör durumu gerçek zamanlı

## Proje Yapısı

```
vision-line-follower/
├── arduino/
│   ├── serit_takip_robotu/          # v1.0 (eski)
│   │   └── serit_takip_robotu.ino
│   └── serit_takip_robotu_v2/       # v2.0 (PID + yeni protokol)
│       └── serit_takip_robotu_v2.ino
├── raspberrypi/
│   ├── gorsel_isleme.py             # v1.0 (eski)
│   ├── requirements.txt
│   ├── web/                         # v2.0 Web Arayüzü
│   │   ├── app.py                   # Flask API
│   │   ├── config.py                # Konfigürasyon
│   │   ├── serial_manager.py        # Seri port + heartbeat
│   │   ├── arduino_manager.py       # arduino-cli wrapper
│   │   ├── camera_manager.py        # Kamera yönetimi
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
│   │   └── test_extended_protocol/  # v2.0 protokol testi
│   └── raspberrypi/
│       ├── test_usb.py
│       ├── test_serial_manager.py
│       └── test_arduino_manager.py
└── docs/
    ├── pin_baglantilari.md
    ├── sorun_giderme.md
    └── web_arayuzu.md               # Web arayüzü dokümantasyonu
```

## Hızlı Başlangıç

### 1. Arduino'ya v2.0 Yükle
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

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/` | Ana sayfa |
| GET | `/video_feed` | MJPEG video akışı |
| GET | `/api/status` | Sistem durumu |
| POST | `/api/control/start` | Robot başlat |
| POST | `/api/control/stop` | Robot durdur |
| POST | `/api/config/speed` | Hız ayarla |
| POST | `/api/config/pid` | PID ayarla |
| GET | `/api/sensors` | Sensör değerleri |
| GET | `/api/arduino/sketches` | Sketch listesi |
| POST | `/api/arduino/upload` | Sketch yükle |
| GET | `/api/events` | SSE (gerçek zamanlı) |

## PID Ayarları

| Parametre | Varsayılan | Aralık | Açıklama |
|-----------|------------|--------|----------|
| **Kp** | 1.0 | 0-10 | Proportional (anlık hata) |
| **Ki** | 0.0 | 0-5 | Integral (birikmiş hata) |
| **Kd** | 0.5 | 0-10 | Derivative (hata değişimi) |
| **baseSpeed** | 100 | 0-255 | Temel motor hızı |

### PID Ayar İpuçları
1. Önce sadece Kp ile başla (Ki=0, Kd=0)
2. Robot sallanıyorsa Kp'yi düşür
3. Tepki yavaşsa Kp'yi artır
4. Sonra Kd ekle (titreşimi azaltır)
5. Ki genelde 0 bırakılabilir

## Motor Pin Bağlantıları

| Motor | PWM | Yön A | Yön B |
|-------|-----|-------|-------|
| Sol | D6 | D10 | D11 |
| Sağ | D5 | D8 | D9 |

## IR Sensör Pinleri

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

## Test Sırası

1. `test/arduino/test_extended_protocol` - Protokol testi
2. `test/arduino/test_sensor_kalibrasyon` - Sensör kontrolü
3. `test/raspberrypi/test_serial_manager.py` - Serial manager
4. `test/raspberrypi/test_arduino_manager.py` - Arduino manager

## Geliştirme

```bash
# Web sunucusu (geliştirme)
cd raspberrypi
python3 -m web.app

# Testler
cd test/raspberrypi
python3 -m pytest
```

## Dokümantasyon Referansları

- Donanım şemaları: `docs/pin_baglantilari.md`
- Hata çözümleri: `docs/sorun_giderme.md`
- Web arayüzü: `docs/web_arayuzu.md`
- Arduino detay: `arduino/README.md`
- Pi detay: `raspberrypi/README.md`
