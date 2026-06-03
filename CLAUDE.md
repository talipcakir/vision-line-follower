# Vision Line Follower

**Versiyon:** 1.0.0 | **Lisans:** MIT

Dönem bitirme projesi. Arduino ile çizgi takip, Raspberry Pi ile görsel işleme (kırmızı renk algılama).

## Proje Yapısı

```
vision-line-follower/
├── README.md                    # Ana dokümantasyon
├── LICENSE                      # MIT Lisansı
├── CLAUDE.md                    # Bu dosya
├── .gitignore
├── arduino/
│   ├── README.md
│   └── serit_takip_robotu/
│       └── serit_takip_robotu.ino
├── raspberrypi/
│   ├── README.md
│   ├── requirements.txt         # Python bağımlılıkları
│   ├── .env.example             # Örnek konfigürasyon
│   ├── gorsel_isleme.py
│   └── service/
│       ├── README.md
│       ├── serit_takip.service
│       ├── baslatici.py
│       └── kurulum.sh
├── docs/
│   ├── README.md
│   ├── pin_baglantilari.md
│   └── sorun_giderme.md
└── test/
    ├── README.md
    ├── arduino/
    │   ├── test_cizgi_takip/
    │   ├── test_sensor_kalibrasyon/
    │   └── test_usb/
    └── raspberrypi/
        └── test_usb.py
```

## Sistem Bileşenleri

| Bileşen | Güç | Açıklama |
|---------|-----|----------|
| Arduino Uno | Pil (7-12V) | Motor kontrolü + sensör okuma |
| Raspberry Pi 4 | Power Bank (5V) | Kamera + görsel işleme |
| L298N | Pil üzerinden | Motor sürücü |
| 5 Kanal IR Sensör | Arduino 5V | Çizgi takip |
| Pi Camera | Pi üzerinden | Kırmızı algılama |
| USB Kablo | - | Sadece haberleşme |

## Haberleşme (USB Seri)

```
Raspberry Pi <--USB--> Arduino
Port: /dev/ttyACM0 | Baud: 9600

Komutlar:
  STOP   -> OK_STOPPED    (Kırmızı algılandı)
  GO     -> OK_RUNNING    (Devam et)
  PING   -> PONG          (Bağlantı testi)
  STATUS -> STATUS_*      (Durum sorgula)
```

## Motor Pin Bağlantıları

| Motor | PWM | Yön A | Yön B |
|-------|-----|-------|-------|
| Sol | D6 | D10 | D11 |
| Sağ | D5 | D8 | D9 |

## Hız Ayarı

`arduino/serit_takip_robotu/serit_takip_robotu.ino`:
```cpp
int baseSpeed = 90;  // 0-255 (varsayılan: 90)
```

## Pi Servis Kurulumu

```bash
scp -r . pi@<ip>:~/vision-line-follower
ssh pi@<ip>
cd ~/vision-line-follower/raspberrypi/service
chmod +x kurulum.sh && ./kurulum.sh
```

## Test Sırası

1. `test/arduino/test_sensor_kalibrasyon` - Sensör kontrolü
2. `test/arduino/test_cizgi_takip` - Motor + sensör testi
3. `test/arduino/test_usb` + `test/raspberrypi/test_usb.py` - USB testi

## Dokümantasyon Referansları

- Donanım şemaları: `docs/pin_baglantilari.md`
- Hata çözümleri: `docs/sorun_giderme.md`
- Arduino detay: `arduino/README.md`
- Pi detay: `raspberrypi/README.md`
- Servis kurulum: `raspberrypi/service/README.md`
- Test talimatları: `test/README.md`
