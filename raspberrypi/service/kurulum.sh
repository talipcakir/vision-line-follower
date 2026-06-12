#!/bin/bash
# ============================================================
#  VISION LINE FOLLOWER v2.1 - Otomatik Kurulum Scripti
# ============================================================
#
#  KULLANIM:
#  chmod +x kurulum.sh
#  ./kurulum.sh
#
# ============================================================

set -e  # Hata durumunda dur

# Renkli cikti
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Log fonksiyonlari
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warning() { echo -e "${YELLOW}[UYARI]${NC} $1"; }
error() { echo -e "${RED}[HATA]${NC} $1"; }
header() { echo -e "${CYAN}$1${NC}"; }

echo ""
header "============================================================"
header "  VISION LINE FOLLOWER v2.1 - Kurulum"
header "  Web Yonetim Arayuzu + HSV Kalibrasyon"
header "============================================================"
echo ""

# ----- KONTROLLER -----

# Root kontrolu
if [ "$EUID" -eq 0 ]; then
    error "Bu script root olarak calistirilmamali!"
    error "Sudo sifreniz gerektiginde sorulacaktir."
    exit 1
fi

# Script dizini
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
RASPBERRYPI_DIR="$(dirname "$SCRIPT_DIR")"
INSTALL_DIR="$HOME/vision-line-follower"
LOG_DIR="/var/log/vision-line-follower"

info "Script dizini: $SCRIPT_DIR"
info "Proje dizini: $PROJECT_DIR"
info "Kurulum dizini: $INSTALL_DIR"
echo ""

# ----- ADIM 1: PAKETLERI YUKLE -----

header "============================================================"
header "  ADIM 1: Gerekli paketler yukleniyor"
header "============================================================"

info "Paket listesi guncelleniyor..."
sudo apt update

info "Python paketleri yukleniyor..."
sudo apt install -y \
    python3-pip \
    python3-opencv \
    python3-flask \
    python3-numpy \
    python3-serial

# PiCamera2 kurulumu (varsa)
if sudo apt-cache show python3-picamera2 &> /dev/null; then
    info "PiCamera2 yukleniyor..."
    sudo apt install -y python3-picamera2
else
    warning "python3-picamera2 bulunamadi (simülasyon modu kullanilacak)"
fi

success "Paketler yuklendi"
echo ""

# ----- ADIM 2: ARDUINO CLI KURULUMU -----

header "============================================================"
header "  ADIM 2: Arduino CLI kuruluyor"
header "============================================================"

if command -v arduino-cli &> /dev/null; then
    success "Arduino CLI zaten kurulu"
    arduino-cli version
else
    info "Arduino CLI indiriliyor..."
    curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh

    # PATH'e ekle
    if [ -f "$HOME/bin/arduino-cli" ]; then
        sudo mv "$HOME/bin/arduino-cli" /usr/local/bin/
        success "Arduino CLI /usr/local/bin/'e taşındı"
    fi

    # PATH kontrolu
    if [[ ":$PATH:" != *":/usr/local/bin:"* ]]; then
        echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.bashrc
        export PATH="/usr/local/bin:$PATH"
    fi

    info "Arduino AVR core yukleniyor..."
    arduino-cli core install arduino:avr

    success "Arduino CLI kuruldu"
fi
echo ""

# ----- ADIM 3: SERI PORT YETKISI -----

header "============================================================"
header "  ADIM 3: Seri port yetkisi ayarlaniyor"
header "============================================================"

NEED_REBOOT=false

if groups $USER | grep -q dialout; then
    success "Kullanici zaten dialout grubunda"
else
    info "Kullanici dialout grubuna ekleniyor..."
    sudo usermod -a -G dialout $USER
    warning "Yetki degisikligi icin yeniden baslama gerekli!"
    NEED_REBOOT=true
fi

# Video grubu (kamera erişimi)
if groups $USER | grep -q video; then
    success "Kullanici zaten video grubunda"
else
    info "Kullanici video grubuna ekleniyor..."
    sudo usermod -a -G video $USER
fi

echo ""

# ----- ADIM 4: LOG DIZINI -----

header "============================================================"
header "  ADIM 4: Log dizini olusturuluyor"
header "============================================================"

info "Log dizini: $LOG_DIR"
sudo mkdir -p "$LOG_DIR"
sudo chown $USER:$USER "$LOG_DIR"
sudo chmod 755 "$LOG_DIR"

success "Log dizini hazir"
echo ""

# ----- ADIM 5: DOSYALARI KOPYALA -----

header "============================================================"
header "  ADIM 5: Proje dosyalari kopyalaniyor"
header "============================================================"

# Kurulum dizinini olustur
mkdir -p "$INSTALL_DIR"

# Tum projeyi kopyala
info "Proje dosyalari kopyalaniyor..."
cp -r "$PROJECT_DIR"/* "$INSTALL_DIR/"

# Calistirma yetkisi ver
chmod +x "$INSTALL_DIR/raspberrypi/service/kurulum.sh"

success "Dosyalar kopyalandi: $INSTALL_DIR"
echo ""

# ----- ADIM 6: SERVIS DOSYASINI KOPYALA -----

header "============================================================"
header "  ADIM 6: Systemd servisi kuruluyor"
header "============================================================"

info "Servis dosyasi kopyalaniyor..."
sudo cp "$SCRIPT_DIR/serit_takip.service" /etc/systemd/system/

# Kullanici adini guncelle (pi degilse)
CURRENT_USER=$(whoami)
CURRENT_HOME=$HOME

if [ "$CURRENT_USER" != "pi" ]; then
    warning "Kullanici adi 'pi' degil, servis dosyasi guncelleniyor..."
    sudo sed -i "s/User=pi/User=$CURRENT_USER/g" /etc/systemd/system/serit_takip.service
    sudo sed -i "s/Group=pi/Group=$CURRENT_USER/g" /etc/systemd/system/serit_takip.service
    sudo sed -i "s|/home/pi/|$CURRENT_HOME/|g" /etc/systemd/system/serit_takip.service
fi

info "Systemd yeniden yukleniyor..."
sudo systemctl daemon-reload

success "Servis kuruldu"
echo ""

# ----- ADIM 7: SERVISI ETKINLESTIR -----

header "============================================================"
header "  ADIM 7: Servis etkinlestiriliyor"
header "============================================================"

info "Servis etkinlestiriliyor (acilista otomatik baslar)..."
sudo systemctl enable serit_takip.service

success "Servis etkinlestirildi"
echo ""

# ----- KURULUM TAMAMLANDI -----

header "============================================================"
header "  KURULUM TAMAMLANDI!"
header "============================================================"
echo ""
success "Vision Line Follower v2.1 kuruldu."
echo ""

echo "Servis Komutlari:"
echo "  Baslat:        sudo systemctl start serit_takip.service"
echo "  Durdur:        sudo systemctl stop serit_takip.service"
echo "  Yeniden:       sudo systemctl restart serit_takip.service"
echo "  Durum:         sudo systemctl status serit_takip.service"
echo "  Log izle:      sudo journalctl -u serit_takip.service -f"
echo ""

IP_ADDR=$(hostname -I | awk '{print $1}')
echo "Web Arayuzu (servis calisirken):"
echo "  http://${IP_ADDR}:5000"
echo ""

echo "v2.1 Ozellikleri:"
echo "  - HSV kalibrasyon (web uzerinden)"
echo "  - Detaylı loglama ve debug"
echo "  - Arduino sketch yukleme"
echo "  - PID kontrol ayarlari"
echo "  - Canli sensor izleme"
echo "  - Otomatik yeniden baglanti"
echo ""

if [ "$NEED_REBOOT" = true ]; then
    header "============================================================"
    warning "YENIDEN BASLATMA GEREKLI!"
    header "============================================================"
    echo ""
    read -p "Simdi yeniden baslatmak ister misiniz? (e/h): " answer
    if [ "$answer" = "e" ]; then
        info "Yeniden baslatiliyor..."
        sudo reboot
    else
        warning "Seri port yetkisi icin manuel olarak yeniden baslatin:"
        echo "  sudo reboot"
    fi
else
    read -p "Servisi simdi baslatmak ister misiniz? (e/h): " answer
    if [ "$answer" = "e" ]; then
        info "Servis baslatiliyor..."
        sudo systemctl start serit_takip.service
        sleep 3
        echo ""
        sudo systemctl status serit_takip.service --no-pager
        echo ""
        success "Web arayuzu hazir: http://${IP_ADDR}:5000"
    fi
fi

echo ""
success "Kurulum tamamlandi!"
