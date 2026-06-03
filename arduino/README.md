# Arduino Kodları

Bu klasör Arduino Uno için yazılmış kodları içerir.

## Klasör Yapısı

```
arduino/
├── README.md                    # Bu dosya
└── serit_takip_robotu/          # Ana proje
    └── serit_takip_robotu.ino   # Ana kod
```

## Ana Kod: serit_takip_robotu

Bu kod robotun ana beynidir. Şu işlevleri yapar:

1. **IR Sensör Okuma**: 5 kanallı sensör dizisinden çizgi konumunu okur
2. **Motor Kontrolü**: L298N sürücü ile motorları yönlendirir
3. **USB Haberleşme**: Raspberry Pi'dan STOP/GO komutlarını alır

### Yükleme

1. Arduino IDE'yi açın
2. `serit_takip_robotu/serit_takip_robotu.ino` dosyasını açın
3. **Tools > Board > Arduino Uno** seçin
4. **Tools > Port** ile doğru COM portunu seçin
5. **Upload** butonuna tıklayın

### Pin Bağlantıları

| Bileşen | Pinler |
|---------|--------|
| Sol Motor | D6 (PWM), D10, D11 |
| Sağ Motor | D5 (PWM), D8, D9 |
| IR Sensörler | D2, D3, D4, D7, D12 |

Detaylı şema: [docs/pin_baglantilari.md](../docs/pin_baglantilari.md)

### Hız Ayarı

`serit_takip_robotu.ino` dosyasında `baseSpeed` değerini değiştirin:

```cpp
int baseSpeed = 90;  // 0-255 arası (varsayılan: 90)
```

| Değer | Hız |
|-------|-----|
| 60 | Yavaş |
| 90 | Normal |
| 120 | Hızlı |

### Seri Komutlar

Arduino şu komutları kabul eder:

| Komut | Cevap | Açıklama |
|-------|-------|----------|
| `PING` | `PONG` | Bağlantı testi |
| `STOP` | `OK_STOPPED` | Motorları durdur |
| `GO` | `OK_RUNNING` | Çizgi takibe devam |
| `STATUS` | `STATUS_STOPPED` veya `STATUS_RUNNING` | Durum sorgula |

### Debug

Serial Monitor'ü açarak (9600 baud) robot durumunu izleyebilirsiniz.

## Test Kodları

Test ve kalibrasyon kodları için: [test/README.md](../test/README.md)

## İlgili Dosyalar

- [Ana README](../README.md) - Proje genel bakış
- [Pin Bağlantıları](../docs/pin_baglantilari.md) - Donanım şemaları
- [Sorun Giderme](../docs/sorun_giderme.md) - Hata çözümleri
- [Raspberry Pi](../raspberrypi/README.md) - Pi tarafı kurulum
- [Test Dosyaları](../test/README.md) - Test ve kalibrasyon
