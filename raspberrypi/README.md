# Raspberry Pi Kodları

Bu klasör Raspberry Pi 4 için yazılmış kodları içerir.

## Klasör Yapısı

```
raspberrypi/
├── README.md              # Bu dosya
├── gorsel_isleme.py       # Ana görsel işleme kodu
└── service/               # Otomatik başlatma servisi
    ├── README.md          # Servis kurulum talimatları
    ├── serit_takip.service
    ├── baslatici.py
    └── kurulum.sh
```

## Hızlı Kurulum

```bash
# 1. Proje dosyalarını Pi'ye kopyalayın
scp -r p/ pi@<raspberry-pi-ip>:~/

# 2. Pi'ye SSH ile bağlanın
ssh pi@<raspberry-pi-ip>

# 3. Kurulum scriptini çalıştırın
cd ~/vision-line-follower/raspberrypi/service
chmod +x kurulum.sh
./kurulum.sh
```

## Manuel Kurulum

### 1. Gerekli Paketler

```bash
sudo apt update
sudo apt install -y python3-pip python3-opencv python3-flask python3-picamera2
pip3 install pyserial numpy
```

### 2. Kamera Etkinleştirme

```bash
sudo raspi-config
# Interface Options > Camera > Enable
sudo reboot
```

### 3. Seri Port Yetkisi

```bash
sudo usermod -a -G dialout $USER
sudo reboot
```

## Ana Kod: gorsel_isleme.py

Bu kod şu işlevleri yapar:

1. **Kamera Görüntüsü**: Pi Camera'dan canlı görüntü alır
2. **Kırmızı Algılama**: HSV renk uzayında kırmızı renk arar
3. **Arduino Haberleşme**: USB üzerinden STOP/GO komutları gönderir
4. **Web Arayüzü**: Flask ile canlı görüntü yayını yapar

### Manuel Çalıştırma

```bash
cd ~/vision-line-follower/raspberrypi
python3 gorsel_isleme.py
```

### Web Arayüzü

Tarayıcıdan erişim:
```
http://<raspberry-pi-ip>:5000
```

Pi IP adresini bulmak için:
```bash
hostname -I
```

## Servis Kurulumu

Detaylı bilgi: [service/README.md](service/README.md)

### Servis Özellikleri

- Pi açılınca otomatik başlar
- Arduino USB bağlantısını bekler
- Bağlantı koparsa yeniden bağlanır
- Hata durumunda otomatik yeniden başlar

### Temel Komutlar

```bash
# Durum kontrol
sudo systemctl status serit_takip.service

# Başlat / Durdur
sudo systemctl start serit_takip.service
sudo systemctl stop serit_takip.service

# Log izle
sudo journalctl -u serit_takip.service -f
```

## Kırmızı Renk Ayarları

`gorsel_isleme.py` dosyasında HSV değerlerini ayarlayabilirsiniz:

```python
# Açık kırmızı aralığı
LOWER_RED1 = np.array([0, 120, 70])
UPPER_RED1 = np.array([10, 255, 255])

# Koyu kırmızı aralığı
LOWER_RED2 = np.array([170, 120, 70])
UPPER_RED2 = np.array([180, 255, 255])

# Minimum alan (piksel kare)
MIN_AREA = 1500
```

## Test

USB bağlantı testi: [test/README.md](../test/README.md)

## İlgili Dosyalar

- [Ana README](../README.md) - Proje genel bakış
- [Servis Kurulumu](service/README.md) - Otomatik başlatma
- [Pin Bağlantıları](../docs/pin_baglantilari.md) - Donanım şemaları
- [Sorun Giderme](../docs/sorun_giderme.md) - Hata çözümleri
- [Arduino Kodları](../arduino/README.md) - Arduino tarafı
- [Test Dosyaları](../test/README.md) - Test ve kalibrasyon
