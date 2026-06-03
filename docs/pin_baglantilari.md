# Pin Bağlantıları

Bu dosya robotun tüm donanım bağlantılarını içerir.

## Sistem Mimarisi

```
┌─────────────────┐         ┌─────────────────┐
│  Raspberry Pi   │         │    Arduino Uno  │
│                 │         │                 │
│  ┌───────────┐  │   USB   │                 │
│  │  Kamera   │  │ ──────> │  Seri Port      │
│  └───────────┘  │ (Seri)  │  (STOP/GO)      │
│                 │         │        │        │
│  Kırmızı algıla │         │        ▼        │
│  "STOP" gönder  │         │  Motor Kontrol  │
└─────────────────┘         │        │        │
                            │        ▼        │
                            │  ┌───────────┐  │
                            │  │  L298N    │  │
                            │  │  Sürücü   │  │
                            │  └───────────┘  │
                            │        │        │
                            │   ┌────┴────┐   │
                            │   ▼         ▼   │
                            │ Sol       Sağ   │
                            │ Motor     Motor │
                            └─────────────────┘
```

## Arduino Uno Pin Şeması

```
                    ┌─────────────────────┐
                    │     ARDUINO UNO     │
                    │                     │
    Sağ Motor PWM ──┤ D5            D12 ├── IR Sensör S5 (en sağ)
    Sol Motor PWM ──┤ D6            D11 ├── Sol Motor IN2
    IR Sensör S4 ───┤ D7            D10 ├── Sol Motor IN1
    Sağ Motor IN3 ──┤ D8             D9 ├── Sağ Motor IN4
                    │                    │
    IR Sensör S1 ───┤ D2            GND ├── L298N GND
    IR Sensör S2 ───┤ D3             5V ├── IR Sensör VCC
    IR Sensör S3 ───┤ D4            USB ├── Raspberry Pi (Seri)
                    │                    │
                    └────────────────────┘
```

## Motor Sürücü (L298N) → Arduino

| L298N Pin | Arduino Pin | Açıklama |
|-----------|-------------|----------|
| ENA | D6 | Sol motor hız (PWM) |
| IN1 | D10 | Sol motor yön A |
| IN2 | D11 | Sol motor yön B |
| ENB | D5 | Sağ motor hız (PWM) |
| IN3 | D8 | Sağ motor yön A |
| IN4 | D9 | Sağ motor yön B |
| GND | GND | Ortak toprak |

### Motor Yön Kontrolü

| IN1 | IN2 | Hareket |
|-----|-----|---------|
| HIGH | LOW | İleri |
| LOW | HIGH | Geri |
| LOW | LOW | Dur |

## IR Sensör Dizisi → Arduino

| Sensör | Arduino Pin | Konum |
|--------|-------------|-------|
| S1 | D2 | En sol |
| S2 | D3 | Hafif sol |
| S3 | D4 | Orta |
| S4 | D7 | Hafif sağ |
| S5 | D12 | En sağ |
| VCC | 5V | Güç |
| GND | GND | Toprak |

### Sensör Çıkışları

| Çıkış | Anlam |
|-------|-------|
| LOW (0) | Siyah çizgi algılandı |
| HIGH (1) | Beyaz zemin |

## Raspberry Pi → Arduino (USB Seri)

| Raspberry Pi | Arduino | Açıklama |
|--------------|---------|----------|
| USB Port | USB Port | Seri haberleşme |

### Seri Haberleşme Ayarları

| Parametre | Değer |
|-----------|-------|
| Port | `/dev/ttyACM0` veya `/dev/ttyUSB0` |
| Baud Rate | 9600 |
| Komutlar | `STOP`, `GO`, `PING`, `STATUS` |

## Güç Bağlantıları

| Bileşen | Güç Kaynağı | Voltaj |
|---------|-------------|--------|
| Arduino Uno | Pil | 7-12V |
| L298N + Motorlar | Pil (Arduino üzerinden) | 7-12V |
| Raspberry Pi | Power Bank | 5V |
| IR Sensörler | Arduino 5V | 5V |

**NOT:** USB kablosu sadece haberleşme için kullanılır, Arduino'ya güç vermez.

## Fiziksel Yerleşim

```
        ┌─────────────────────────────┐
        │         ROBOT ÖNÜ           │
        │                             │
        │   [S1] [S2] [S3] [S4] [S5]  │  <- IR Sensörler
        │                             │
        │  ┌─────┐         ┌─────┐    │
        │  │ SOL │         │ SAĞ │    │  <- Motorlar
        │  │MOTOR│         │MOTOR│    │
        │  └─────┘         └─────┘    │
        │                             │
        │      ┌───────────┐          │
        │      │  ARDUINO  │          │
        │      └───────────┘          │
        │                             │
        │      ┌───────────┐          │
        │      │  L298N    │          │
        │      └───────────┘          │
        │                             │
        │      ┌───────────┐          │
        │      │ RASPBERRY │          │
        │      │    PI     │          │
        │      └───────────┘          │
        │                             │
        │      [  KAMERA  ]           │  <- Öne bakacak şekilde
        │                             │
        └─────────────────────────────┘
                ROBOT ARKASI
```

## İlgili Dosyalar

- [Ana README](../README.md)
- [Sorun Giderme](sorun_giderme.md)
- [Arduino Kurulumu](../arduino/README.md)
- [Raspberry Pi Kurulumu](../raspberrypi/README.md)
