# Raspberry Pi - Vision Line Follower v2.2

Bu dizin Raspberry Pi üzerinde çalışan web yönetim arayüzü ve görsel işleme kodlarını içerir.

## Hızlı Kurulum

```bash
cd service
chmod +x kurulum.sh
./kurulum.sh
```

Bu komut tek seferde:
- Tüm bağımlılıkları yükler
- Arduino CLI kurar
- Seri port yetkilerini ayarlar
- Systemd servisini kurar ve başlatır

## Dizin Yapısı

```
raspberrypi/
├── web/                    # Web uygulaması
│   ├── app.py              # Flask API ve web sunucu
│   ├── config.py           # Konfigürasyon yönetimi
│   ├── serial_manager.py   # Arduino seri iletişimi
│   ├── camera_manager.py   # Kamera ve renk algılama
│   ├── arduino_manager.py  # Arduino CLI wrapper
│   └── static/             # Frontend dosyaları
│       ├── index.html
│       ├── css/style.css
│       └── js/app.js
├── service/                # Systemd servisi
│   ├── kurulum.sh          # Tek tuşla kurulum
│   └── serit_takip.service # Servis tanımı
└── requirements.txt        # Python bağımlılıkları
```

## Geliştirme Modu

```bash
cd raspberrypi
python3 -m web.app
```

Web arayüzü: http://localhost:5000

## Servis Komutları

```bash
sudo systemctl start serit_takip    # Başlat
sudo systemctl stop serit_takip     # Durdur
sudo systemctl restart serit_takip  # Yeniden başlat
sudo systemctl status serit_takip   # Durum
journalctl -u serit_takip -f        # Log izle
```

## API Endpoints

### Genel
- `GET /` - Web arayüzü
- `GET /video_feed` - MJPEG video akışı
- `GET /api/status` - Sistem durumu
- `GET /api/health` - Sağlık kontrolü

### Robot Kontrolü
- `POST /api/control/start` - Robot başlat
- `POST /api/control/stop` - Robot durdur
- `POST /api/command` - Manuel komut gönder

### Konfigürasyon
- `GET /api/config` - Mevcut ayarlar
- `POST /api/config/speed` - Hız ayarla
- `POST /api/config/pid` - PID parametreleri
- `POST /api/config/save` - EEPROM kaydet

### HSV Kalibrasyon
- `GET /api/hsv` - HSV ayarları
- `POST /api/hsv` - HSV güncelle
- `POST /api/hsv/toggle` - Algılama aç/kapat

### Arduino
- `GET /api/arduino/status` - CLI durumu
- `GET /api/arduino/ports` - Port listesi
- `POST /api/arduino/upload` - Sketch yükle

## Ortam Değişkenleri

| Değişken | Varsayılan | Açıklama |
|----------|------------|----------|
| `SERIAL_PORT` | /dev/ttyACM0 | Arduino portu |
| `BAUD_RATE` | 9600 | Seri port hızı |
| `WEB_PORT` | 5000 | Web sunucu portu |
| `LOG_LEVEL` | INFO | Log seviyesi |
| `LOG_FILE` | /var/log/vision-line-follower/app.log | Log dosyası |

## Sorun Giderme

Detaylı sorun giderme için: [../docs/sorun_giderme.md](../docs/sorun_giderme.md)
