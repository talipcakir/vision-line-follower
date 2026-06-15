# Servis Kurulumu v2.2

Bu klasör Raspberry Pi servis kurulumu için gerekli dosyaları içerir.

## Dosyalar

```
service/
├── kurulum.sh          # Tek tuşla kurulum scripti
└── serit_takip.service # Systemd servis şablonu
```

## Tek Tuşla Kurulum

```bash
chmod +x kurulum.sh
./kurulum.sh
```

Bu script otomatik olarak:
1. Sistem paketlerini yükler (Flask, OpenCV, pyserial)
2. Arduino CLI kurar
3. Seri port yetkilerini ayarlar (dialout grubu)
4. Kamera yetkilerini ayarlar (video grubu)
5. Log dizinini oluşturur
6. Systemd servisini kurar ve etkinleştirir
7. (Opsiyonel) Servisi başlatır

## Servis Komutları

```bash
sudo systemctl start serit_takip    # Başlat
sudo systemctl stop serit_takip     # Durdur
sudo systemctl restart serit_takip  # Yeniden başlat
sudo systemctl status serit_takip   # Durum
sudo systemctl enable serit_takip   # Açılışta başlat
sudo systemctl disable serit_takip  # Açılışta başlatma
```

## Log İzleme

```bash
# Canlı log
journalctl -u serit_takip -f

# Son 100 satır
journalctl -u serit_takip -n 100

# Bugünkü loglar
journalctl -u serit_takip --since today
```

## Manuel Kurulum

Eğer kurulum scripti çalışmazsa manuel adımlar:

```bash
# 1. Paketleri yükle
sudo apt update
sudo apt install -y python3-flask python3-numpy python3-serial python3-opencv

# 2. Seri port yetkisi
sudo usermod -a -G dialout $USER
sudo usermod -a -G video $USER

# 3. Log dizini
sudo mkdir -p /var/log/vision-line-follower
sudo chown $USER:$USER /var/log/vision-line-follower

# 4. Servis dosyası (kullanıcı adını değiştirin)
sudo cp serit_takip.service /etc/systemd/system/
sudo nano /etc/systemd/system/serit_takip.service

# 5. Servisi etkinleştir
sudo systemctl daemon-reload
sudo systemctl enable serit_takip
sudo systemctl start serit_takip
```

## Sorun Giderme

### Servis başlamıyor

```bash
# Detaylı log
journalctl -u serit_takip -n 50 --no-pager

# Manuel test
cd ~/vision-line-follower/raspberrypi
python3 -m web.app
```

### Port yetkisi hatası

```bash
groups $USER  # 'dialout' olmalı
sudo usermod -a -G dialout $USER
sudo reboot
```

### Web arayüzüne erişilemiyor

```bash
# Servis çalışıyor mu?
sudo systemctl status serit_takip

# Port açık mı?
sudo netstat -tlnp | grep 5000

# IP adresi
hostname -I
```
