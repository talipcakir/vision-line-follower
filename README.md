# Şerit Takip Robotu

Dönem bitirme projesi. Arduino ile çizgi takip, Raspberry Pi ile görsel işleme (kırmızı renk algılama) yapan otonom robot.

## Özellikler

- 5 kanallı IR sensör ile siyah çizgi takibi
- Raspberry Pi kamera ile kırmızı renk algılama
- Kırmızı görünce otomatik durma
- USB seri haberleşme (Pi ↔ Arduino)
- Web arayüzünden canlı görüntü izleme
- Otomatik başlatma servisi

## Proje Yapısı

```
vision-line-follower/
├── README.md                              # Bu dosya
├── CLAUDE.md                              # Proje özeti
│
├── arduino/                               # Arduino kodları
│   ├── README.md                          # Arduino kurulum talimatları
│   └── serit_takip_robotu/                # Arduino IDE gerekliliği
│       └── serit_takip_robotu.ino         # Ana Arduino kodu
│
├── raspberrypi/                           # Raspberry Pi kodları
│   ├── README.md                          # Pi kurulum talimatları
│   ├── gorsel_isleme.py                   # Görsel işleme kodu
│   └── service/                           # Otomatik başlatma
│       ├── README.md                      # Servis kurulum talimatları
│       ├── serit_takip.service
│       ├── baslatici.py
│       └── kurulum.sh
│
├── docs/                                  # Dokümantasyon
│   ├── README.md
│   ├── pin_baglantilari.md                # Donanım bağlantı şemaları
│   └── sorun_giderme.md                   # Sorun çözümleri
│
└── test/                                  # Test dosyaları
    ├── README.md                          # Test talimatları
    ├── arduino/
    │   ├── test_cizgi_takip/
    │   ├── test_sensor_kalibrasyon/
    │   └── test_usb/
    └── raspberrypi/
        └── test_usb.py
```

## Hızlı Başlangıç

### 1. Arduino Kurulumu

```bash
# Arduino IDE'den yükleyin:
arduino/serit_takip_robotu/serit_takip_robotu.ino
```

Detaylı bilgi: [arduino/README.md](arduino/README.md)

### 2. Raspberry Pi Kurulumu

```bash
# Dosyaları Pi'ye kopyalayın
scp -r . pi@<raspberry-pi-ip>:~/vision-line-follower

# Pi'de kurulum scriptini çalıştırın
ssh pi@<raspberry-pi-ip>
cd ~/vision-line-follower/raspberrypi/service
chmod +x kurulum.sh
./kurulum.sh
```

Detaylı bilgi: [raspberrypi/README.md](raspberrypi/README.md)

### 3. Test

Kurulum sonrası test sırası:
1. Sensör kalibrasyonu
2. Çizgi takip testi
3. USB haberleşme testi

Detaylı bilgi: [test/README.md](test/README.md)

## Donanım Listesi

| Bileşen | Adet | Açıklama |
|---------|------|----------|
| Arduino Uno | 1 | Motor kontrolü |
| Raspberry Pi 4 | 1 | Görsel işleme |
| Pi Camera | 1 | Kamera modülü |
| L298N Motor Sürücü | 1 | DC motor kontrolü |
| DC Motor | 2 | Sol ve sağ tekerlekler |
| 5'li IR Sensör Dizisi | 1 | Çizgi takip |
| USB Kablo | 1 | Pi-Arduino haberleşme |
| Pil (7-12V) | 1 | Arduino + motorlar |
| Power Bank (5V) | 1 | Raspberry Pi |

## Pin Bağlantıları

### Motor Pinleri

| Motor | PWM | Yön A | Yön B |
|-------|-----|-------|-------|
| Sol | D6 | D10 | D11 |
| Sağ | D5 | D8 | D9 |

### Sensör Pinleri

| Sensör | Pin | Konum |
|--------|-----|-------|
| S1 | D2 | En sol |
| S2 | D3 | Hafif sol |
| S3 | D4 | Orta |
| S4 | D7 | Hafif sağ |
| S5 | D12 | En sağ |

Detaylı şema: [docs/pin_baglantilari.md](docs/pin_baglantilari.md)

## Çalıştırma

### Otomatik (Servis ile)

Kurulum sonrası:
- Pi açılınca servis otomatik başlar
- Arduino USB'ye bağlanınca algılanır
- Web arayüzü: `http://<pi-ip>:5000`

### Manuel

```bash
# Arduino'ya güç verin (pil)
# USB ile Pi'ye bağlayın

# Pi'de çalıştırın:
cd ~/vision-line-follower/raspberrypi
python3 gorsel_isleme.py
```

### Servis Komutları

```bash
sudo systemctl status serit_takip.service   # Durum
sudo systemctl start serit_takip.service    # Başlat
sudo systemctl stop serit_takip.service     # Durdur
sudo journalctl -u serit_takip.service -f   # Log izle
```

## Dokümantasyon

| Dosya | İçerik |
|-------|--------|
| [docs/pin_baglantilari.md](docs/pin_baglantilari.md) | Tüm donanım bağlantı şemaları |
| [docs/sorun_giderme.md](docs/sorun_giderme.md) | Sık karşılaşılan sorunlar ve çözümleri |
| [arduino/README.md](arduino/README.md) | Arduino kurulum ve kullanım |
| [raspberrypi/README.md](raspberrypi/README.md) | Raspberry Pi kurulum ve kullanım |
| [raspberrypi/service/README.md](raspberrypi/service/README.md) | Otomatik başlatma servisi |
| [test/README.md](test/README.md) | Test ve kalibrasyon talimatları |

## Sorun Giderme

Sık karşılaşılan sorunlar için: [docs/sorun_giderme.md](docs/sorun_giderme.md)

### Hızlı Kontrol Listesi

- [ ] Pil şarjlı ve bağlı mı?
- [ ] USB kablo takılı mı?
- [ ] Arduino'ya kod yüklendi mi?
- [ ] Pi'de servis çalışıyor mu?
- [ ] Sensörler doğru yükseklikte mi? (1-2 cm)

## Lisans

Bu proje eğitim amaçlıdır.
