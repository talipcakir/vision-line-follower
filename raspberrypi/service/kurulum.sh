#!/bin/bash
# ============================================================
#  VISION LINE FOLLOWER v2.2 - Tek Tuşla Kurulum
# ============================================================
#
#  Bu script tek komutla:
#  1. Tüm bağımlılıkları yükler
#  2. Arduino CLI kurar
#  3. Seri port yetkilerini ayarlar
#  4. Kamera ayarlarını yapar
#  5. Systemd servisini kurar
#  6. Projeyi başlatır
#
#  KULLANIM:
#  chmod +x kurulum.sh && ./kurulum.sh
#
# ============================================================

set -e

# Renkler
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Fonksiyonlar
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warning() { echo -e "${YELLOW}[UYARI]${NC} $1"; }
error() { echo -e "${RED}[HATA]${NC} $1"; exit 1; }
header() { echo -e "\n${CYAN}============================================================${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}============================================================${NC}"; }

# ============================================================
#  KONTROLLER
# ============================================================

header "VISION LINE FOLLOWER v2.2 - Kurulum Başlıyor"

# Root kontrolü
if [ "$EUID" -eq 0 ]; then
    error "Bu scripti root olarak çalıştırmayın! Normal kullanıcı olarak çalıştırın."
fi

# Raspberry Pi kontrolü
if [ ! -f /proc/device-tree/model ]; then
    warning "Bu bir Raspberry Pi değil gibi görünüyor. Devam ediliyor..."
else
    MODEL=$(cat /proc/device-tree/model)
    info "Cihaz: $MODEL"
fi

# Dizinleri belirle
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RASPBERRYPI_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$RASPBERRYPI_DIR")"
INSTALL_DIR="$HOME/vision-line-follower"
LOG_DIR="/var/log/vision-line-follower"

info "Proje dizini: $PROJECT_DIR"
info "Kurulum dizini: $INSTALL_DIR"

# ============================================================
#  ADIM 1: SİSTEM GÜNCELLEMESİ
# ============================================================

header "ADIM 1/7: Sistem Güncelleniyor"

info "Paket listesi güncelleniyor..."
sudo apt update || error "apt update başarısız"

info "Temel paketler yükleniyor..."
sudo apt install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    git \
    curl \
    || error "Temel paket kurulumu başarısız"

success "Sistem güncellendi"

# ============================================================
#  ADIM 2: PYTHON BAĞIMLILIKLARI
# ============================================================

header "ADIM 2/7: Python Bağımlılıkları Yükleniyor"

# Sistem Python paketleri (apt ile - daha stabil)
info "Python paketleri yükleniyor (apt)..."
sudo apt install -y \
    python3-flask \
    python3-numpy \
    python3-serial \
    python3-opencv \
    || error "Python paket kurulumu başarısız"

# PiCamera2 (varsa)
if sudo apt-cache show python3-picamera2 &> /dev/null; then
    info "PiCamera2 yükleniyor..."
    sudo apt install -y python3-picamera2 python3-libcamera || true
    success "PiCamera2 yüklendi"
else
    warning "PiCamera2 bulunamadı - USB kamera kullanılabilir"
fi

success "Python bağımlılıkları yüklendi"

# ============================================================
#  ADIM 3: ARDUINO CLI
# ============================================================

header "ADIM 3/7: Arduino CLI Kuruluyor"

if command -v arduino-cli &> /dev/null; then
    CLI_VERSION=$(arduino-cli version 2>/dev/null | head -1)
    success "Arduino CLI zaten kurulu: $CLI_VERSION"
else
    info "Arduino CLI indiriliyor..."

    # Temiz kurulum
    mkdir -p "$HOME/.local/bin"

    # İndir ve kur
    curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR="$HOME/.local/bin" sh || error "Arduino CLI indirilemedi"

    # PATH'e ekle
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
        export PATH="$HOME/.local/bin:$PATH"
    fi

    success "Arduino CLI kuruldu"
fi

# Arduino AVR core
info "Arduino AVR core kontrol ediliyor..."
if ! arduino-cli core list 2>/dev/null | grep -q "arduino:avr"; then
    info "Arduino AVR core yükleniyor..."
    arduino-cli core update-index
    arduino-cli core install arduino:avr || warning "AVR core yüklenemedi"
fi

success "Arduino CLI hazır"

# ============================================================
#  ADIM 4: YETKİLER
# ============================================================

header "ADIM 4/7: Yetkiler Ayarlanıyor"

NEED_REBOOT=false

# dialout grubu (seri port)
if groups $USER | grep -q dialout; then
    success "Seri port yetkisi mevcut"
else
    info "Seri port yetkisi ekleniyor..."
    sudo usermod -a -G dialout $USER
    NEED_REBOOT=true
    warning "Seri port için yeniden başlatma gerekecek"
fi

# video grubu (kamera)
if groups $USER | grep -q video; then
    success "Kamera yetkisi mevcut"
else
    info "Kamera yetkisi ekleniyor..."
    sudo usermod -a -G video $USER
fi

# i2c grubu (sensörler için)
if groups $USER | grep -q i2c; then
    success "I2C yetkisi mevcut"
else
    info "I2C yetkisi ekleniyor..."
    sudo usermod -a -G i2c $USER 2>/dev/null || true
fi

# Log dizini
info "Log dizini oluşturuluyor..."
sudo mkdir -p "$LOG_DIR"
sudo chown $USER:$USER "$LOG_DIR"
sudo chmod 755 "$LOG_DIR"

success "Yetkiler ayarlandı"

# ============================================================
#  ADIM 5: PROJE DOSYALARI
# ============================================================

header "ADIM 5/7: Proje Dosyaları Kopyalanıyor"

# Eğer farklı dizindeyse kopyala
if [ "$PROJECT_DIR" != "$INSTALL_DIR" ]; then
    info "Proje kopyalanıyor: $INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"

    # Mevcut dosyaları yedekle
    if [ -d "$INSTALL_DIR/raspberrypi" ]; then
        warning "Mevcut kurulum bulundu, yedekleniyor..."
        BACKUP_DIR="$HOME/vision-line-follower-backup-$(date +%Y%m%d-%H%M%S)"
        mv "$INSTALL_DIR" "$BACKUP_DIR"
        info "Yedek: $BACKUP_DIR"
    fi

    cp -r "$PROJECT_DIR"/* "$INSTALL_DIR/"
    success "Dosyalar kopyalandı"
else
    success "Proje dizini zaten doğru konumda"
fi

# Çalıştırma yetkisi
chmod +x "$INSTALL_DIR/raspberrypi/service/kurulum.sh" 2>/dev/null || true

# ============================================================
#  ADIM 6: SYSTEMD SERVİSİ
# ============================================================

header "ADIM 6/7: Systemd Servisi Kuruluyor"

SERVICE_FILE="/etc/systemd/system/serit_takip.service"
SOURCE_SERVICE="$INSTALL_DIR/raspberrypi/service/serit_takip.service"

# Servis dosyasını oluştur
info "Servis dosyası oluşturuluyor..."

sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=Vision Line Follower - Web Yonetim Arayuzu v2.2
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$INSTALL_DIR/raspberrypi
ExecStart=/usr/bin/python3 -m web.app
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONPATH=$INSTALL_DIR/raspberrypi
Environment=LOG_LEVEL=INFO
Environment=LOG_FILE=$LOG_DIR/app.log
StandardOutput=journal
StandardError=journal
SyslogIdentifier=vision-line-follower
KillMode=control-group
KillSignal=SIGTERM
TimeoutStopSec=10

[Install]
WantedBy=multi-user.target
EOF

# Systemd yükle
sudo systemctl daemon-reload
sudo systemctl enable serit_takip.service

success "Servis kuruldu ve etkinleştirildi"

# ============================================================
#  ADIM 7: DOĞRULAMA
# ============================================================

header "ADIM 7/7: Kurulum Doğrulanıyor"

ERRORS=0

# Python modülleri
info "Python modülleri kontrol ediliyor..."
python3 -c "import flask" 2>/dev/null || { warning "flask bulunamadı"; ((ERRORS++)); }
python3 -c "import serial" 2>/dev/null || { warning "pyserial bulunamadı"; ((ERRORS++)); }
python3 -c "import numpy" 2>/dev/null || { warning "numpy bulunamadı"; ((ERRORS++)); }
python3 -c "import cv2" 2>/dev/null || { warning "opencv bulunamadı"; ((ERRORS++)); }

if [ $ERRORS -eq 0 ]; then
    success "Tüm Python modülleri mevcut"
else
    warning "$ERRORS modül eksik - bazı özellikler çalışmayabilir"
fi

# Proje dosyaları
info "Proje dosyaları kontrol ediliyor..."
[ -f "$INSTALL_DIR/raspberrypi/web/app.py" ] || { error "app.py bulunamadı!"; }
[ -f "$INSTALL_DIR/raspberrypi/web/config.py" ] || { error "config.py bulunamadı!"; }
[ -f "$INSTALL_DIR/raspberrypi/web/serial_manager.py" ] || { error "serial_manager.py bulunamadı!"; }
[ -f "$INSTALL_DIR/raspberrypi/web/camera_manager.py" ] || { error "camera_manager.py bulunamadı!"; }
success "Tüm proje dosyaları mevcut"

# ============================================================
#  SONUÇ
# ============================================================

header "KURULUM TAMAMLANDI!"

IP_ADDR=$(hostname -I 2>/dev/null | awk '{print $1}')
[ -z "$IP_ADDR" ] && IP_ADDR="localhost"

echo ""
success "Vision Line Follower v2.2 başarıyla kuruldu!"
echo ""
echo -e "${CYAN}Servis Komutları:${NC}"
echo "  Başlat:        sudo systemctl start serit_takip"
echo "  Durdur:        sudo systemctl stop serit_takip"
echo "  Yeniden:       sudo systemctl restart serit_takip"
echo "  Durum:         sudo systemctl status serit_takip"
echo "  Log izle:      journalctl -u serit_takip -f"
echo ""
echo -e "${CYAN}Web Arayüzü:${NC}"
echo "  http://${IP_ADDR}:5000"
echo ""
echo -e "${CYAN}v2.2 Özellikler:${NC}"
echo "  - Akıllı çizgi arama (kaybolunca geri döner)"
echo "  - Kırmızı algılayınca otomatik durdurma"
echo "  - HSV kalibrasyon (web üzerinden)"
echo "  - Arduino sketch yükleme"
echo "  - Gerçek zamanlı sensör izleme"
echo ""

# Yeniden başlatma gerekli mi?
if [ "$NEED_REBOOT" = true ]; then
    echo ""
    warning "UYARI: Seri port yetkisi için yeniden başlatma gerekli!"
    echo ""
    read -p "Şimdi yeniden başlatmak ister misiniz? (e/h): " answer
    if [ "$answer" = "e" ] || [ "$answer" = "E" ]; then
        info "Yeniden başlatılıyor..."
        sudo reboot
    else
        echo ""
        warning "Manuel olarak yeniden başlatın: sudo reboot"
        echo "Ardından servisi başlatın: sudo systemctl start serit_takip"
    fi
else
    echo ""
    read -p "Servisi şimdi başlatmak ister misiniz? (e/h): " answer
    if [ "$answer" = "e" ] || [ "$answer" = "E" ]; then
        info "Servis başlatılıyor..."
        sudo systemctl start serit_takip
        sleep 3

        if systemctl is-active --quiet serit_takip; then
            echo ""
            success "Servis çalışıyor!"
            echo ""
            echo -e "${GREEN}Web arayüzü hazır: http://${IP_ADDR}:5000${NC}"
        else
            echo ""
            warning "Servis başlatılamadı. Log kontrol edin:"
            echo "  journalctl -u serit_takip -n 50"
        fi
    fi
fi

echo ""
success "Kurulum tamamlandı!"
