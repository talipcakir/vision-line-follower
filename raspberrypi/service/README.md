# Raspberry Pi Servis Kurulumu

Bu klasör, şerit takip robotunun Raspberry Pi tarafında otomatik olarak başlaması için gerekli dosyaları içerir.

## Servis Ne Yapar?

1. Raspberry Pi açıldığında otomatik olarak başlar
2. Arduino'nun USB'ye bağlanmasını bekler
3. Arduino algılandığında görsel işleme programını başlatır
4. Kamera ile kırmızı renk algılar ve Arduino'ya komut gönderir
5. Hata durumunda otomatik yeniden başlar

## Dosyalar

```
service/
├── README.md                    # Bu dosya (kurulum talimatları)
├── serit_takip.service          # Systemd servis dosyası
├── baslatici.py                 # Ana başlatıcı script
└── kurulum.sh                   # Otomatik kurulum scripti
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

### Adım 1: Gerekli Paketleri Yükleyin

```bash
sudo apt update
sudo apt install -y python3-pip python3-opencv python3-flask python3-picamera2
pip3 install pyserial numpy
```

### Adım 2: Seri Port Yetkisi

```bash
# Kullanıcıyı dialout grubuna ekle
sudo usermod -a -G dialout $USER

# Yeniden başlat (gerekli)
sudo reboot
```

### Adım 3: Proje Dosyalarını Kopyalayın

```bash
# Proje klasörünü oluştur
mkdir -p ~/vision-line-follower

# Dosyaları kopyala
cp ~/vision-line-follower/gorsel_isleme.py ~/vision-line-follower/
cp ~/vision-line-follower/service/baslatici.py ~/vision-line-follower/
```

### Adım 4: Servis Dosyasını Kopyalayın

```bash
# Servis dosyasını systemd klasörüne kopyala
sudo cp ~/vision-line-follower/service/serit_takip.service /etc/systemd/system/

# Systemd'yi yeniden yükle
sudo systemctl daemon-reload
```

### Adım 5: Servisi Etkinleştirin

```bash
# Servisi etkinleştir (açılışta otomatik başlar)
sudo systemctl enable serit_takip.service

# Servisi şimdi başlat
sudo systemctl start serit_takip.service
```

## Servis Komutları

```bash
# Servis durumunu kontrol et
sudo systemctl status serit_takip.service

# Servisi başlat
sudo systemctl start serit_takip.service

# Servisi durdur
sudo systemctl stop serit_takip.service

# Servisi yeniden başlat
sudo systemctl restart serit_takip.service

# Logları görüntüle
sudo journalctl -u serit_takip.service -f

# Son 50 log satırı
sudo journalctl -u serit_takip.service -n 50
```

## Sorun Giderme

### Servis başlamıyor

```bash
# Detaylı log görüntüle
sudo journalctl -u serit_takip.service -n 100 --no-pager

# Python dosyasını manuel çalıştır
cd ~/vision-line-follower
python3 baslatici.py
```

### Arduino algılanmıyor

```bash
# Bağlı USB cihazları listele
ls -la /dev/ttyACM* /dev/ttyUSB*

# Seri port yetkisini kontrol et
groups $USER  # 'dialout' grubu olmalı

# Yetki yoksa ekle ve yeniden başlat
sudo usermod -a -G dialout $USER
sudo reboot
```

### Kamera çalışmıyor

```bash
# Kamera durumunu kontrol et
libcamera-hello --list-cameras

# Kamerayı etkinleştir
sudo raspi-config
# Interface Options > Camera > Enable
sudo reboot
```

### Port kullanımda hatası

```bash
# Portu kullanan işlemi bul
sudo lsof /dev/ttyACM0

# İşlemi sonlandır
sudo kill <PID>

# Veya servisi yeniden başlat
sudo systemctl restart serit_takip.service
```

## Web Arayüzü

Servis çalışırken tarayıcıdan canlı görüntüyü izleyebilirsiniz:

```
http://<raspberry-pi-ip>:5000
```

Raspberry Pi'nin IP adresini bulmak için:
```bash
hostname -I
```

## Servis Yapılandırması

`/etc/systemd/system/serit_takip.service` dosyasını düzenleyerek ayarları değiştirebilirsiniz:

```ini
[Service]
# Çalışma dizini
WorkingDirectory=/home/pi/vision-line-follower

# Çalıştırılacak komut
ExecStart=/usr/bin/python3 /home/pi/vision-line-follower/baslatici.py

# Hata durumunda yeniden başlatma gecikmesi (saniye)
RestartSec=5

# Kullanıcı adı (pi değilse değiştirin)
User=pi
```

Değişiklik sonrası:
```bash
sudo systemctl daemon-reload
sudo systemctl restart serit_takip.service
```

## İlgili Dosyalar

- [Raspberry Pi README](../README.md) - Pi genel kurulum
- [Ana README](../../README.md) - Proje genel bakış
- [Sorun Giderme](../../docs/sorun_giderme.md) - Detaylı hata çözümleri
- [Test Dosyaları](../../test/README.md) - USB bağlantı testi
