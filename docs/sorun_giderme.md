# Sorun Giderme

Bu dosya sık karşılaşılan sorunları ve çözümlerini içerir.

## Motor Sorunları

### Robot hiç hareket etmiyor

**Kontrol listesi:**
- [ ] Pil bağlı ve şarjlı mı?
- [ ] L298N güç LED'i yanıyor mu?
- [ ] Motor kabloları doğru bağlı mı?
- [ ] Arduino'ya kod yüklendi mi?

**Çözüm adımları:**
1. Pil voltajını multimetre ile ölçün (7-12V olmalı)
2. L298N üzerindeki güç LED'ini kontrol edin
3. Motor kablolarını çıkarıp tekrar takın
4. Arduino IDE'den kodu tekrar yükleyin

### Motorlar ters dönüyor

**Çözüm:**
Motor kablolarını L298N üzerinde ters çevirin veya kodda IN1/IN2 (veya IN3/IN4) değerlerini değiştirin.

### Motorlardan biri çalışmıyor

**Kontrol:**
1. L298N üzerinde ilgili motor çıkışını test edin
2. Motor kablolarını değiştirerek motorun kendisini test edin
3. Arduino pin bağlantılarını kontrol edin

## Sensör Sorunları

### Çizgiyi takip etmiyor

**Kontrol listesi:**
- [ ] IR sensör yüksekliği doğru mu? (yerden 1-2 cm)
- [ ] Sensörler siyah çizgiyi görüyor mu?
- [ ] Sensör VCC ve GND bağlı mı?

**Test adımları:**
1. `test/arduino/test_sensor_kalibrasyon` kodunu yükleyin
2. Serial Monitor'den sensör değerlerini izleyin
3. Siyah çizgi üzerinde 0, beyaz zeminde 1 okumalı

### Sensör değerleri ters

Bazı IR sensörler ters çalışır (siyahta 1, beyazda 0). 

**Çözüm:**
Kodda `== HIGH` kontrollerini `== LOW` olarak değiştirin.

### Sensör hiç tepki vermiyor

1. Sensör VCC'nin Arduino 5V'a bağlı olduğunu kontrol edin
2. GND bağlantısını kontrol edin
3. Sensör üzerindeki LED'lerin yandığını kontrol edin

## USB Haberleşme Sorunları

### Arduino algılanmıyor

**Pi üzerinde kontrol:**
```bash
# Bağlı USB cihazları listele
ls -la /dev/ttyACM* /dev/ttyUSB*

# Eğer cihaz görünmüyorsa
dmesg | tail -20
```

**Çözümler:**
1. USB kablosunu değiştirin (bazı kablolar sadece şarj için)
2. Farklı USB port deneyin
3. Arduino'yu yeniden takın

### "Permission denied" hatası

```bash
# Seri port yetkisi ekle
sudo usermod -a -G dialout $USER

# Yeniden başlat
sudo reboot
```

### Seri iletişim çalışmıyor

**Test adımları:**
1. Arduino'ya `test/arduino/test_usb` kodunu yükleyin
2. Pi'de test scripti çalıştırın:
```bash
cd ~/vision-line-follower/test/raspberrypi
python3 test_usb.py
```

**Baud rate kontrolü:**
Arduino ve Pi kodlarında baud rate aynı olmalı (9600).

## Kamera Sorunları

### Kamera görüntüsü gelmiyor

**Kontrol:**
```bash
# Kamera durumunu kontrol et
libcamera-hello --list-cameras

# Kamera test
libcamera-hello -t 5000
```

**Çözüm:**
```bash
# Kamerayı etkinleştir
sudo raspi-config
# Interface Options > Camera > Enable

sudo reboot
```

### Kamera kablosu sorunlu

1. Pi'yi kapatın
2. Kamera kablosunu çıkarıp tekrar takın
3. Kablo yönünün doğru olduğundan emin olun (mavi taraf yukarı)

## Servis Sorunları

### Servis başlamıyor

```bash
# Detaylı log görüntüle
sudo journalctl -u serit_takip.service -n 100 --no-pager

# Manuel çalıştırma ile test
cd ~/vision-line-follower
python3 baslatici.py
```

### Port kullanımda hatası

```bash
# Portu kullanan işlemi bul
sudo lsof /dev/ttyACM0

# İşlemi sonlandır
sudo kill <PID>

# Servisi yeniden başlat
sudo systemctl restart serit_takip.service
```

### Web arayüzüne erişilemiyor

1. Servisin çalıştığını kontrol edin:
```bash
sudo systemctl status serit_takip.service
```

2. Pi'nin IP adresini öğrenin:
```bash
hostname -I
```

3. 5000 portunun açık olduğunu kontrol edin:
```bash
sudo netstat -tlnp | grep 5000
```

## Genel İpuçları

### Debug için Serial Monitor

Arduino IDE'de `Tools > Serial Monitor` açarak robot durumunu izleyebilirsiniz.

### Log izleme

```bash
# Servis loglarını canlı izle
sudo journalctl -u serit_takip.service -f
```

### Hız ayarlama

Robot çok hızlı veya yavaşsa `baseSpeed` değerini ayarlayın:
- Yavaşlatmak için: değeri azaltın (örn: 60)
- Hızlandırmak için: değeri artırın (örn: 120)

## İlgili Dosyalar

- [Pin Bağlantıları](pin_baglantilari.md)
- [Arduino README](../arduino/README.md)
- [Raspberry Pi README](../raspberrypi/README.md)
- [Test README](../test/README.md)
