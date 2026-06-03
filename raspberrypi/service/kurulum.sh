#!/bin/bash
# ============================================================
#  SERIT TAKIP ROBOTU - Otomatik Kurulum Scripti
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
NC='\033[0m' # No Color

# Log fonksiyonlari
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warning() { echo -e "${YELLOW}[UYARI]${NC} $1"; }
error() { echo -e "${RED}[HATA]${NC} $1"; }

echo ""
echo "============================================================"
echo "  SERIT TAKIP ROBOTU - Kurulum"
echo "============================================================"
echo ""

# ----- KONTROLLER -----

# Root kontrolu
if [ "$EUID" -eq 0 ]; then
    error "Bu script root olarak calistirilmamali!"
    error "Sudo sifreniz gerektiginde sorulacaktir."
    exit 1
fi

# Raspberry Pi kontrolu
if [ ! -f /proc/device-tree/model ]; then
    warning "Bu bir Raspberry Pi olmayabilir!"
    read -p "Devam etmek istiyor musunuz? (e/h): " answer
    if [ "$answer" != "e" ]; then
        exit 1
    fi
fi

# Script dizini
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
INSTALL_DIR="$HOME/vision-line-follower"

info "Script dizini: $SCRIPT_DIR"
info "Proje dizini: $PROJECT_DIR"
info "Kurulum dizini: $INSTALL_DIR"
echo ""

# ----- ADIM 1: PAKETLERI YUKLE -----

echo "============================================================"
echo "  ADIM 1: Gerekli paketler yukleniyor"
echo "============================================================"

info "Paket listesi guncelleniyor..."
sudo apt update

info "Python paketleri yukleniyor..."
sudo apt install -y python3-pip python3-opencv python3-flask python3-picamera2

info "Pip paketleri yukleniyor..."
pip3 install pyserial numpy --break-system-packages 2>/dev/null || pip3 install pyserial numpy

success "Paketler yuklendi"
echo ""

# ----- ADIM 2: SERI PORT YETKISI -----

echo "============================================================"
echo "  ADIM 2: Seri port yetkisi ayarlaniyor"
echo "============================================================"

if groups $USER | grep -q dialout; then
    success "Kullanici zaten dialout grubunda"
else
    info "Kullanici dialout grubuna ekleniyor..."
    sudo usermod -a -G dialout $USER
    warning "Yetki degisikligi icin yeniden baslama gerekli!"
    NEED_REBOOT=true
fi
echo ""

# ----- ADIM 3: DOSYALARI KOPYALA -----

echo "============================================================"
echo "  ADIM 3: Proje dosyalari kopyalaniyor"
echo "============================================================"

# Kurulum dizinini olustur
mkdir -p "$INSTALL_DIR"

# Ana dosyalari kopyala
info "gorsel_isleme.py kopyalaniyor..."
cp "$PROJECT_DIR/gorsel_isleme.py" "$INSTALL_DIR/"

info "baslatici.py kopyalaniyor..."
cp "$SCRIPT_DIR/baslatici.py" "$INSTALL_DIR/"

# Calistirma yetkisi ver
chmod +x "$INSTALL_DIR/baslatici.py"
chmod +x "$INSTALL_DIR/gorsel_isleme.py"

success "Dosyalar kopyalandi: $INSTALL_DIR"
echo ""

# ----- ADIM 4: SERVIS DOSYASINI KOPYALA -----

echo "============================================================"
echo "  ADIM 4: Systemd servisi kuruluyor"
echo "============================================================"

info "Servis dosyasi kopyalaniyor..."
sudo cp "$SCRIPT_DIR/serit_takip.service" /etc/systemd/system/

# Kullanici adini guncelle (pi degilse)
CURRENT_USER=$(whoami)
if [ "$CURRENT_USER" != "pi" ]; then
    warning "Kullanici adi 'pi' degil, servis dosyasi guncelleniyor..."
    sudo sed -i "s/User=pi/User=$CURRENT_USER/g" /etc/systemd/system/serit_takip.service
    sudo sed -i "s|/home/pi/|/home/$CURRENT_USER/|g" /etc/systemd/system/serit_takip.service
fi

info "Systemd yeniden yukleniyor..."
sudo systemctl daemon-reload

success "Servis kuruldu"
echo ""

# ----- ADIM 5: SERVISI ETKINLESTIR -----

echo "============================================================"
echo "  ADIM 5: Servis etkinlestiriliyor"
echo "============================================================"

info "Servis etkinlestiriliyor (acilista otomatik baslar)..."
sudo systemctl enable serit_takip.service

success "Servis etkinlestirildi"
echo ""

# ----- KURULUM TAMAMLANDI -----

echo "============================================================"
echo "  KURULUM TAMAMLANDI!"
echo "============================================================"
echo ""
success "Serit takip robotu servisi kuruldu."
echo ""
echo "Kullanim:"
echo "  Servisi baslat:     sudo systemctl start serit_takip.service"
echo "  Servisi durdur:     sudo systemctl stop serit_takip.service"
echo "  Durum kontrol:      sudo systemctl status serit_takip.service"
echo "  Loglari goruntule:  sudo journalctl -u serit_takip.service -f"
echo ""
echo "Web arayuzu (servis calisirken):"
echo "  http://$(hostname -I | awk '{print $1}'):5000"
echo ""

if [ "$NEED_REBOOT" = true ]; then
    echo "============================================================"
    warning "YENIDEN BASLATMA GEREKLI!"
    echo "============================================================"
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
        sleep 2
        sudo systemctl status serit_takip.service --no-pager
    fi
fi

echo ""
echo "Kurulum tamamlandi!"
