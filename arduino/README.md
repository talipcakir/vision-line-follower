# Arduino Firmware v2.1

Bu klasör Arduino Uno için yazılmış çizgi takip firmware'ini içerir.

## Özellikler

- **PID Kontrol**: Yumuşak ve hassas çizgi takibi
- **Akıllı Çizgi Arama**: Çizgi kaybolunca geri dönüp zigzag arama
- **Web Entegrasyonu**: Pi'den hız/PID ayarları
- **EEPROM**: Ayarları kalıcı saklama
- **Heartbeat**: Bağlantı kontrolü

## Firmware Yükleme

### Arduino CLI ile (Önerilen)

```bash
arduino-cli compile --upload --fqbn arduino:avr:uno arduino/serit_takip_robotu_v2
```

### Arduino IDE ile

1. `serit_takip_robotu_v2/serit_takip_robotu_v2.ino` dosyasını açın
2. **Tools > Board > Arduino Uno** seçin
3. **Tools > Port** ile doğru COM portunu seçin
4. **Upload** butonuna tıklayın

### Web Arayüzünden

1. http://<pi-ip>:5000 adresine gidin
2. Arduino sekmesine tıklayın
3. Sketch seçin ve "Yükle" butonuna basın

## Pin Bağlantıları

### Motor Pinleri (L298N)
| Motor | PWM | Yön A | Yön B |
|-------|-----|-------|-------|
| Sol | D6 | D10 | D11 |
| Sağ | D5 | D8 | D9 |

### IR Sensör Pinleri
| Sensör | Pin | Konum |
|--------|-----|-------|
| S1 | D2 | En sol |
| S2 | D3 | Sol |
| S3 | D4 | Orta |
| S4 | D7 | Sağ |
| S5 | D12 | En sağ |

## Seri Komutlar

| Komut | Yanıt | Açıklama |
|-------|-------|----------|
| `PING` | `PONG` | Bağlantı testi |
| `STOP` | `OK_STOPPED` | Robotu durdur |
| `GO` | `OK_RUNNING` | Robota devam et |
| `STATUS` | `STATUS_*` | Durum sorgula |
| `VERSION` | `VERSION:2.1.0` | Firmware versiyonu |
| `SPEED:<0-255>` | `OK_SPEED:<n>` | Hız ayarla |
| `PID:<Kp>,<Ki>,<Kd>` | `OK_PID:...` | PID parametreleri |
| `SENSORS` | `SENSORS:s1,s2,s3,s4,s5` | Sensör değerleri |
| `CONFIG` | `CONFIG:speed,Kp,Ki,Kd` | Mevcut ayarlar |
| `SAVE` | `OK_SAVED` | EEPROM'a kaydet |
| `LOAD` | `OK_LOADED` | EEPROM'dan yükle |
| `RESET` | `OK_RESET` | Varsayılana dön |

## PID Ayarları

| Parametre | Varsayılan | Aralık | Açıklama |
|-----------|------------|--------|----------|
| **Kp** | 1.0 | 0-10 | Anlık hata tepkisi |
| **Ki** | 0.0 | 0-5 | Birikmiş hata düzeltme |
| **Kd** | 0.5 | 0-10 | Hata değişim hızı |
| **baseSpeed** | 100 | 0-255 | Temel motor hızı |

### Ayar İpuçları

- **Robot sallanıyorsa**: Kd artırın
- **Keskin dönüş yapamıyorsa**: Kp artırın
- **Çizgiyi kaybediyorsa**: Hızı azaltın

## Çizgi Arama Algoritması

Robot çizgiyi kaybettiğinde:

1. **İlk 500ms**: Son bilinen yöne dönmeye devam eder
2. **500ms sonra**: Geri gider (300ms)
3. **Sonra**: Zigzag arama yapar (her fazda daha geniş açı)
4. **6 faz sonra**: Tekrar geri gidip ters yöne arar

## Test

Serial Monitor'ü açarak (9600 baud) robot durumunu izleyebilirsiniz:

```
Sensörler: 00100 -> ILERI
Sensörler: 01100 -> SOL
Sensörler: 00000 -> ARAMA
```

## Sorun Giderme

### Motorlar ters dönüyor
Motor kablolarını L298N üzerinde ters çevirin veya IN1/IN2 değerlerini değiştirin.

### Sensör ters çalışıyor
Bazı sensörler siyahta 0 yerine 1 verir. Kodda sensör okuma mantığını kontrol edin.

### Çizgiyi bulamıyor
- IR sensör yüksekliğini kontrol edin (yerden 1-2 cm)
- Çizgi kontrastını artırın (mat siyah, parlak beyaz)
