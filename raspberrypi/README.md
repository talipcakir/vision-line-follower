# Raspberry Pi Kodları

Bu klasör Raspberry Pi 4 için yazılmış kodları içerir.

**Versiyon:** 1.0.0

## Klasör Yapısı

```
raspberrypi/
├── README.md              # Bu dosya
├── requirements.txt       # Python bağımlılıkları
├── .env.example           # Örnek ortam değişkenleri
├── gorsel_isleme.py       # Ana görsel işleme kodu
├── logs/                  # Log dosyaları (otomatik oluşur)
└── service/               # Otomatik başlatma servisi
    ├── README.md
    ├── serit_takip.service
    ├── baslatici.py
    └── kurulum.sh
```

## Hızlı Kurulum

```bash
# 1. Proje dosyalarını Pi'ye kopyalayın
scp -r vision-line-follower/ pi@<raspberry-pi-ip>:~/

# 2. Pi'ye SSH ile bağlanın
ssh pi@<raspberry-pi-ip>

# 3. Kurulum scriptini çalıştırın
cd ~/vision-line-follower/raspberrypi/service
chmod +x kurulum.sh
./kurulum.sh
```

## Manuel Kurulum

### 1. Sistem Paketleri

```bash
sudo apt update
sudo apt install -y python3-pip python3-opencv python3-flask python3-picamera2
```

### 2. Python Bağımlılıkları

```bash
cd ~/vision-line-follower/raspberrypi
pip3 install -r requirements.txt
```

### 3. Kamera Etkinleştirme

```bash
sudo raspi-config
# Interface Options > Camera > Enable
sudo reboot
```

### 4. Seri Port Yetkisi

```bash
sudo usermod -a -G dialout $USER
sudo reboot
```

### 5. Ortam Değişkenleri (Opsiyonel)

```bash
# Örnek dosyayı kopyalayın
cp .env.example .env

# İhtiyaca göre düzenleyin
nano .env
```

## Konfigürasyon

Ayarlar `.env` dosyasından veya ortam değişkenlerinden okunur.

| Değişken | Varsayılan | Açıklama |
|----------|------------|----------|
| `SERIAL_PORT` | `/dev/ttyACM0` | Arduino portu |
| `BAUD_RATE` | `9600` | Seri hız |
| `CAMERA_WIDTH` | `640` | Kamera genişlik |
| `CAMERA_HEIGHT` | `480` | Kamera yükseklik |
| `WEB_PORT` | `5000` | Web sunucu portu |
| `LOG_LEVEL` | `INFO` | Log seviyesi |
| `LOG_FILE` | (boş) | Log dosya yolu |
| `MIN_DETECTION_AREA` | `1500` | Min. kırmızı alan |

Tüm ayarlar için: [.env.example](.env.example)

## Çalıştırma

### Manuel

```bash
cd ~/vision-line-follower/raspberrypi
python3 gorsel_isleme.py
```

### Servis ile (Önerilen)

```bash
# Başlat
sudo systemctl start serit_takip.service

# Durum
sudo systemctl status serit_takip.service

# Log izle
sudo journalctl -u serit_takip.service -f
```

Detaylı bilgi: [service/README.md](service/README.md)

## Web Arayüzü

Tarayıcıdan erişim:
```
http://<raspberry-pi-ip>:5000
```

### API Endpointleri

| Endpoint | Açıklama |
|----------|----------|
| `/` | Canlı video akışı |
| `/status` | JSON durum bilgisi |
| `/health` | Sağlık kontrolü |

## Loglama

Log dosyaları `logs/` klasöründe saklanır:
- `logs/vision.log` - Görsel işleme logları
- `logs/baslatici.log` - Servis başlatıcı logları

Log seviyesi `.env` dosyasından ayarlanabilir:
```
LOG_LEVEL=DEBUG
LOG_FILE=logs/vision.log
```

## Kırmızı Renk Ayarları

HSV değerleri `.env` dosyasından ayarlanabilir:

```bash
# Açık kırmızı (0-10 derece)
RED1_H_MIN=0
RED1_H_MAX=10
RED1_S_MIN=120
RED1_V_MIN=70

# Koyu kırmızı (170-180 derece)
RED2_H_MIN=170
RED2_H_MAX=180

# Minimum algılama alanı
MIN_DETECTION_AREA=1500
```

## Test

USB bağlantı testi: [../test/README.md](../test/README.md)

## İlgili Dosyalar

- [Ana README](../README.md) - Proje genel bakış
- [Servis Kurulumu](service/README.md) - Otomatik başlatma
- [Pin Bağlantıları](../docs/pin_baglantilari.md) - Donanım şemaları
- [Sorun Giderme](../docs/sorun_giderme.md) - Hata çözümleri
- [Arduino Kodları](../arduino/README.md) - Arduino tarafı
- [Test Dosyaları](../test/README.md) - Test ve kalibrasyon
