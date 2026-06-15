# Sorun Giderme

Bu dosya sık karşılaşılan sorunları ve çözümlerini içerir.

## Motor Sorunları

### Robot hiç hareket etmiyor

**Kontrol listesi:**
- [ ] Pil bağlı ve şarjlı mı?
- [ ] L298N güç LED'i yanıyor mu?
- [ ] Motor kabloları doğru bağlı mı?
- [ ] Arduino'ya kod yüklendi mi?
- [ ] Web arayüzünden "BAŞLAT" basıldı mı?

**Çözüm adımları:**
1. Pil voltajını multimetre ile ölçün (7-12V olmalı)
2. L298N üzerindeki güç LED'ini kontrol edin
3. Motor kablolarını çıkarıp tekrar takın
4. Arduino'ya firmware yükleyin:
   ```bash
   arduino-cli compile --upload --fqbn arduino:avr:uno arduino/serit_takip_robotu_v2
   ```

### Motorlar ters dönüyor

**Çözüm:**
Motor kablolarını L298N üzerinde ters çevirin veya Arduino kodunda pin değerlerini değiştirin.

### Motorlardan biri çalışmıyor

**Kontrol:**
1. L298N üzerinde ilgili motor çıkışını test edin
2. Motor kablolarını değiştirerek motorun kendisini test edin
3. Arduino pin bağlantılarını kontrol edin
4. Web arayüzünden sensör değerlerini izleyin

## Çizgi Takip Sorunları

### Çizgiyi takip etmiyor

**Kontrol listesi:**
- [ ] IR sensör yüksekliği doğru mu? (yerden 1-2 cm)
- [ ] Sensörler siyah çizgiyi görüyor mu?
- [ ] Sensör VCC ve GND bağlı mı?

**Test adımları:**
1. Web arayüzünden sensör değerlerini izleyin
2. Siyah çizgi üzerinde sensör aktif (1), beyaz zeminde pasif (0) olmalı
3. PID parametrelerini ayarlayın (Kp: 1.0-2.0, Kd: 0.3-0.8)

### Çizgiyi kaybedince duruyor

**v2.2'de bu sorun çözüldü!**

Robot artık çizgiyi kaybettiğinde:
1. Son bilinen yöne dönmeye devam eder
2. Bulamazsa geri gider
3. Zigzag arama yapar

### Sensör değerleri ters

Bazı IR sensörler ters çalışır (siyahta 0, beyazda 1).

**Çözüm:**
Arduino kodunda sensör okuma mantığını ters çevirin.

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
1. Entegrasyon testini çalıştırın:
   ```bash
   cd ~/vision-line-follower/test/raspberrypi
   python3 test_integration.py
   ```

2. Web arayüzünden Arduino sekmesine gidin
3. "PING" butonuna basın - "PONG" yanıtı gelmeli

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

### USB kamera kullanmak istiyorum

USB kamera otomatik olarak desteklenir. Pi Camera yoksa USB kamera kullanılır.

## Kırmızı Algılama Sorunları

### Kırmızıyı algılamıyor

**Kontrol:**
1. Web arayüzünde HSV Kalibrasyon sekmesine gidin
2. "Renk Algılama" açık olmalı
3. Minimum alan değerini düşürün (500-1000 arası deneyin)

### Yanlış renkleri algılıyor

**HSV değerlerini ayarlayın:**
- Kırmızı Aralık 1: H: 0-10, S: 100-255, V: 50-255
- Kırmızı Aralık 2: H: 170-180, S: 100-255, V: 50-255

### Kırmızı görünce durmuyor

**Kontrol:**
1. HSV Kalibrasyon sekmesinde "Otomatik Durdurma" açık mı?
2. Algılama alanı yeterli mi? (min_area değeri)
3. Arduino bağlı mı?

## Servis Sorunları

### Servis başlamıyor

```bash
# Detaylı log görüntüle
journalctl -u serit_takip -n 100 --no-pager

# Manuel çalıştırma ile test
cd ~/vision-line-follower/raspberrypi
python3 -m web.app
```

### Port kullanımda hatası

```bash
# Portu kullanan işlemi bul
sudo lsof /dev/ttyACM0

# İşlemi sonlandır
sudo kill <PID>

# Servisi yeniden başlat
sudo systemctl restart serit_takip
```

### Web arayüzüne erişilemiyor

1. Servisin çalıştığını kontrol edin:
   ```bash
   sudo systemctl status serit_takip
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

### Log izleme

```bash
# Servis loglarını canlı izle
journalctl -u serit_takip -f

# Son 100 satır
journalctl -u serit_takip -n 100
```

### Hız ayarlama

Robot çok hızlı veya yavaşsa web arayüzünden hız ayarlayın:
- Yavaşlatmak için: 60-80 arası
- Normal: 100
- Hızlandırmak için: 120-150 arası

### PID ayarlama

| Parametre | Varsayılan | İpucu |
|-----------|------------|-------|
| Kp | 1.0 | Artırın = daha keskin dönüş |
| Ki | 0.0 | Nadiren gerekli, 0 bırakın |
| Kd | 0.5 | Artırın = daha stabil |

### Yeniden kurulum

Sorunlar devam ediyorsa:
```bash
cd ~/vision-line-follower/raspberrypi/service
./kurulum.sh
```

## İlgili Dosyalar

- [Pin Bağlantıları](pin_baglantilari.md)
- [Web Arayüzü](web_arayuzu.md)
- [Ana README](../README.md)
