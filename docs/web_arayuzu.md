# Web Yönetim Arayüzü

## Genel Bakış

Vision Line Follower v2.2, tarayıcı üzerinden robot kontrolü sağlayan bir web arayüzü içerir.

## Özellikler

### Robot Kontrolü
- **Başlat/Durdur**: Tek tıkla robot kontrolü
- **Hız Ayarı**: Slider ile 0-255 arası hız
- **PID Parametreleri**: Kp, Ki, Kd değerlerini ayarla
- **Ayarları Kaydet**: EEPROM'a kalıcı kayıt

### Canlı İzleme
- **Video Akışı**: Kamera görüntüsü (MJPEG)
- **Kırmızı Algılama**: Otomatik işaretleme
- **Sensör Değerleri**: 5 IR sensör durumu
- **Bağlantı Durumu**: Heartbeat göstergesi

### Arduino Yönetimi
- **Sketch Listesi**: Mevcut sketch'leri görüntüle
- **Derleme**: Sketch'i derle
- **Yükleme**: Arduino'ya yükle
- **Kart Algılama**: Bağlı kartı tespit et

## Erişim

```
http://<raspberry-pi-ip>:5000
```

Raspberry Pi'nin IP adresini bulmak için:
```bash
hostname -I
```

## Arayüz Bölümleri

### Üst Bar
- Logo ve başlık
- Bağlantı durumu göstergesi (yeşil/sarı/kırmızı)

### Sol Panel - Video
- Canlı kamera görüntüsü
- Kırmızı nesne algılandığında çerçeve

### Sağ Panel - Kontroller
1. **Robot Kontrolü**: Başlat/Durdur butonları
2. **Hız Ayarı**: Slider ve uygula butonu
3. **PID Ayarları**: Kp/Ki/Kd input alanları
4. **Sensörler**: 5 IR sensör görsel gösterimi

### Alt Panel - Arduino
- Kart bilgisi
- Sketch seçici
- Derle/Yükle butonları

### Terminal
- Komut gönderme
- Yanıt görüntüleme
- Hata mesajları

## API Kullanımı

### Durum Sorgulama
```bash
curl http://pi:5000/api/status
```

### Hız Ayarlama
```bash
curl -X POST http://pi:5000/api/config/speed \
  -H "Content-Type: application/json" \
  -d '{"speed": 120}'
```

### PID Ayarlama
```bash
curl -X POST http://pi:5000/api/config/pid \
  -H "Content-Type: application/json" \
  -d '{"kp": 1.5, "ki": 0.0, "kd": 0.8}'
```

### Sensör Okuma
```bash
curl http://pi:5000/api/sensors
```

### Sketch Yükleme
```bash
curl -X POST http://pi:5000/api/arduino/upload \
  -H "Content-Type: application/json" \
  -d '{"sketch": "serit_takip_robotu_v2"}'
```

## Server-Sent Events (SSE)

Gerçek zamanlı güncellemeler için:
```javascript
const eventSource = new EventSource('/api/events');

eventSource.addEventListener('connection', (e) => {
  const data = JSON.parse(e.data);
  console.log('Bağlantı:', data.state);
});

eventSource.addEventListener('sensors', (e) => {
  const data = JSON.parse(e.data);
  console.log('Sensörler:', data.sensors);
});
```

## Sorun Giderme

### Video Görünmüyor
1. Kamera bağlı mı kontrol et
2. `libcamera-hello` çalışıyor mu?
3. Başka uygulama kamerayı kullanıyor mu?

### Bağlantı Kurulamıyor
1. Arduino USB ile bağlı mı?
2. Port yetkisi var mı? (`sudo usermod -a -G dialout $USER`)
3. Doğru port: `ls /dev/tty*`

### Yükleme Başarısız
1. arduino-cli kurulu mu?
2. Arduino core yüklü mü? (`arduino-cli core install arduino:avr`)
3. Port meşgul mü?

## Güvenlik Notları

- Web arayüzü sadece yerel ağda erişilebilir
- Kimlik doğrulama yok (iç ağ için tasarlandı)
- Dış ağa açmayın

## Mobil Uyumluluk

Arayüz responsive tasarıma sahip:
- Masaüstü: Tam görünüm
- Tablet: 2 sütunlu
- Mobil: Tek sütunlu
