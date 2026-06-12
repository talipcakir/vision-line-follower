# Raspberry Pi Kurulum Rehberi

## ADIM 1: Pi'ye Bağlan (Windows'tan)

PowerShell aç ve çalıştır:

```
ssh pi@<PI_IP_ADRESI>
```

Şifreni gir.


## ADIM 2: Projeyi İndir

```
cd ~
git clone https://github.com/talipcakir/vision-line-follower.git
```


## ADIM 3: Satır Sonu Düzelt (Windows CRLF sorunu)

```
cd ~/vision-line-follower
sed -i 's/\r$//' raspberrypi/service/kurulum.sh
sed -i 's/\r$//' raspberrypi/service/serit_takip.service
```


## ADIM 4: Gerekli Paketleri Kur

```
sudo apt update
sudo apt install -y python3-pip python3-opencv python3-flask python3-numpy python3-serial
```

PiCamera varsa:
```
sudo apt install -y python3-picamera2
```


## ADIM 5: Seri Port Yetkisi

```
sudo usermod -a -G dialout $USER
sudo usermod -a -G video $USER
```


## ADIM 6: Log Dizini Oluştur

```
sudo mkdir -p /var/log/vision-line-follower
sudo chown $USER:$USER /var/log/vision-line-follower
```


## ADIM 7: Servisi Kur

```
sudo cp ~/vision-line-follower/raspberrypi/service/serit_takip.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable serit_takip.service
```


## ADIM 8: Yeniden Başlat (Yetki için)

```
sudo reboot
```


## ADIM 9: Yeniden Bağlan ve Başlat

Windows'tan tekrar bağlan:
```
ssh pi@<PI_IP_ADRESI>
```

Servisi başlat:
```
sudo systemctl start serit_takip.service
```

Durumu kontrol et:
```
sudo systemctl status serit_takip.service
```


## ADIM 10: Web Arayüzü

Tarayıcıdan aç:
```
http://<PI_IP_ADRESI>:5000
```


---

## FAYDALI KOMUTLAR

Servisi durdur:
```
sudo systemctl stop serit_takip.service
```

Logları izle:
```
sudo journalctl -u serit_takip.service -f
```

Manuel başlat (test için):
```
cd ~/vision-line-follower/raspberrypi
python3 -m web.app
```

Pi IP adresini bul:
```
hostname -I
```


---

## SORUN GİDERME

Eğer hata alırsan:

1. Satır sonu düzelt:
```
cd ~/vision-line-follower
find . -type f -name "*.sh" -exec sed -i 's/\r$//' {} \;
find . -type f -name "*.py" -exec sed -i 's/\r$//' {} \;
find . -type f -name "*.service" -exec sed -i 's/\r$//' {} \;
```

2. Bağımlılıkları kontrol et:
```
python3 -c "import flask; import serial; import cv2; import numpy; print('OK')"
```

3. Arduino bağlı mı kontrol et:
```
ls /dev/ttyACM* /dev/ttyUSB*
```
