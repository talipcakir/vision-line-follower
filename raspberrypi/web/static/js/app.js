// ============================================================
//  Vision Line Follower - Web Arayüz JavaScript
// ============================================================

// API Base URL
const API_BASE = '';

// Durum değişkenleri
let isConnected = false;
let robotRunning = false;
let eventSource = null;

// ============================================================
//  SAYFA YÜKLENDIĞINDE
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    log('Sayfa yüklendi', 'info');

    // İlk durumu al
    fetchStatus();

    // Sketch listesini yükle
    refreshSketches();

    // SSE bağlantısı kur
    connectSSE();

    // Periyodik güncelleme
    setInterval(fetchStatus, 5000);
    setInterval(fetchSensors, 500);

    // Video yüklendiğinde overlay'i gizle
    const video = document.getElementById('videoFeed');
    video.onload = () => {
        document.getElementById('videoOverlay').classList.add('hidden');
    };
    video.onerror = () => {
        document.getElementById('videoOverlay').classList.remove('hidden');
    };
});

// ============================================================
//  API ÇAĞRILARI
// ============================================================

async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };

    if (data) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('API Hatası:', error);
        return { success: false, error: error.message };
    }
}

// ============================================================
//  DURUM GÜNCELLEME
// ============================================================

async function fetchStatus() {
    const status = await apiCall('/api/status');

    if (status.serial) {
        updateConnectionStatus(status.serial.state, status.serial.port);
        isConnected = status.serial.connected;
    }

    if (status.robot) {
        document.getElementById('speedSlider').value = status.robot.speed;
        document.getElementById('speedValue').textContent = status.robot.speed;
        document.getElementById('inputKp').value = status.robot.kp;
        document.getElementById('inputKi').value = status.robot.ki;
        document.getElementById('inputKd').value = status.robot.kd;
    }

    if (status.arduino) {
        document.getElementById('arduinoCli').textContent =
            status.arduino.cli_available ? '✓ Kurulu' : '✗ Yok';
    }

    if (status.version) {
        document.getElementById('version').textContent = status.version;
    }

    // Board bilgisini al
    const board = await apiCall('/api/arduino/board');
    if (board.detected) {
        document.getElementById('arduinoBoard').textContent = board.name || 'Arduino';
        document.getElementById('arduinoPort').textContent = board.port || '-';
    } else {
        document.getElementById('arduinoBoard').textContent = 'Bulunamadı';
        document.getElementById('arduinoPort').textContent = '-';
    }
}

function updateConnectionStatus(state, port) {
    const statusEl = document.getElementById('connectionStatus');
    const dot = statusEl.querySelector('.status-dot');
    const text = statusEl.querySelector('.status-text');

    dot.className = 'status-dot';

    switch (state) {
        case 'connected':
            dot.classList.add('connected');
            text.textContent = `Bağlı (${port || 'USB'})`;
            break;
        case 'connecting':
        case 'reconnecting':
            dot.classList.add('connecting');
            text.textContent = 'Bağlanıyor...';
            break;
        default:
            dot.classList.add('disconnected');
            text.textContent = 'Bağlantı Yok';
    }
}

// ============================================================
//  ROBOT KONTROLÜ
// ============================================================

async function startRobot() {
    log('> GO', 'command');
    const result = await apiCall('/api/control/start', 'POST');

    if (result.success) {
        log(result.response, 'response');
        updateRobotStatus(true);
    } else {
        log(`Hata: ${result.error}`, 'error');
    }
}

async function stopRobot() {
    log('> STOP', 'command');
    const result = await apiCall('/api/control/stop', 'POST');

    if (result.success) {
        log(result.response, 'response');
        updateRobotStatus(false);
    } else {
        log(`Hata: ${result.error}`, 'error');
    }
}

function updateRobotStatus(running) {
    robotRunning = running;
    const statusText = document.getElementById('robotStatusText');
    statusText.textContent = running ? 'Çalışıyor' : 'Durdu';
    statusText.className = 'status-value ' + (running ? 'running' : 'stopped');

    document.getElementById('btnStart').disabled = running;
    document.getElementById('btnStop').disabled = !running;
}

// ============================================================
//  HIZ AYARI
// ============================================================

function updateSpeedLabel(value) {
    document.getElementById('speedValue').textContent = value;
}

async function applySpeed() {
    const speed = parseInt(document.getElementById('speedSlider').value);
    log(`> SPEED:${speed}`, 'command');

    const result = await apiCall('/api/config/speed', 'POST', { speed });

    if (result.success) {
        log(result.response, 'response');
    } else {
        log(`Hata: ${result.error}`, 'error');
    }
}

// ============================================================
//  PID AYARLARI
// ============================================================

async function applyPID() {
    const kp = parseFloat(document.getElementById('inputKp').value);
    const ki = parseFloat(document.getElementById('inputKi').value);
    const kd = parseFloat(document.getElementById('inputKd').value);

    log(`> PID:${kp},${ki},${kd}`, 'command');

    const result = await apiCall('/api/config/pid', 'POST', { kp, ki, kd });

    if (result.success) {
        log(result.response, 'response');
    } else {
        log(`Hata: ${result.error}`, 'error');
    }
}

async function savePID() {
    log('> SAVE', 'command');
    const result = await apiCall('/api/config/save', 'POST');

    if (result.success) {
        log('Ayarlar EEPROM\'a kaydedildi', 'response');
    } else {
        log(`Hata: ${result.error}`, 'error');
    }
}

async function resetPID() {
    log('> RESET', 'command');
    const result = await apiCall('/api/config/reset', 'POST');

    if (result.success) {
        log('Varsayılan ayarlara dönüldü', 'response');
        fetchStatus();
    } else {
        log(`Hata: ${result.error}`, 'error');
    }
}

// ============================================================
//  SENSÖRLER
// ============================================================

async function fetchSensors() {
    if (!isConnected) return;

    const result = await apiCall('/api/sensors');

    if (result.success && result.sensors) {
        updateSensorDisplay(result.sensors);
    }
}

function updateSensorDisplay(sensors) {
    for (let i = 0; i < 5; i++) {
        const sensorEl = document.getElementById(`sensor${i}`);
        if (sensorEl) {
            if (parseInt(sensors[i]) === 1) {
                sensorEl.classList.add('active');
            } else {
                sensorEl.classList.remove('active');
            }
        }
    }
}

// ============================================================
//  ARDUINO YÖNETİMİ
// ============================================================

async function refreshSketches() {
    const result = await apiCall('/api/arduino/sketches');
    const select = document.getElementById('sketchSelect');

    // Mevcut seçenekleri temizle
    select.innerHTML = '<option value="">-- Sketch Seçin --</option>';

    if (result.sketches) {
        result.sketches.forEach(sketch => {
            const option = document.createElement('option');
            option.value = sketch.name;
            option.textContent = sketch.name;
            if (sketch.description) {
                option.title = sketch.description;
            }
            select.appendChild(option);
        });
    }
}

async function compileSketch() {
    const sketch = document.getElementById('sketchSelect').value;

    if (!sketch) {
        log('Lütfen bir sketch seçin', 'error');
        return;
    }

    log(`Derleniyor: ${sketch}...`, 'info');
    showProgress(true, 'Derleniyor...');

    const result = await apiCall('/api/arduino/compile', 'POST', { sketch });

    showProgress(false);

    if (result.success) {
        log('Derleme başarılı!', 'response');
    } else {
        log(`Derleme hatası: ${result.error}`, 'error');
        if (result.output) {
            log(result.output, 'info');
        }
    }
}

async function uploadSketch() {
    const sketch = document.getElementById('sketchSelect').value;

    if (!sketch) {
        log('Lütfen bir sketch seçin', 'error');
        return;
    }

    if (!confirm(`"${sketch}" Arduino\'ya yüklenecek. Devam edilsin mi?`)) {
        return;
    }

    log(`Yükleniyor: ${sketch}...`, 'info');
    showProgress(true, 'Yükleniyor...');

    const result = await apiCall('/api/arduino/upload', 'POST', { sketch });

    showProgress(false);

    if (result.success) {
        log('Yükleme başarılı!', 'response');
        // Bağlantı durumunu güncelle
        setTimeout(fetchStatus, 3000);
    } else {
        log(`Yükleme hatası: ${result.error}`, 'error');
        if (result.output) {
            log(result.output, 'info');
        }
    }
}

function showProgress(show, text = '') {
    const progress = document.getElementById('uploadProgress');
    const progressText = document.getElementById('progressText');

    if (show) {
        progress.style.display = 'block';
        progressText.textContent = text;
        document.getElementById('progressFill').style.width = '100%';
    } else {
        progress.style.display = 'none';
    }
}

// ============================================================
//  TERMİNAL
// ============================================================

async function sendCommand() {
    const input = document.getElementById('commandInput');
    const command = input.value.trim();

    if (!command) return;

    log(`> ${command}`, 'command');
    input.value = '';

    const result = await apiCall('/api/command', 'POST', { command });

    if (result.success) {
        log(result.response, 'response');
    } else {
        log(`Hata: ${result.error}`, 'error');
    }
}

function log(message, type = 'info') {
    const terminal = document.getElementById('terminal');
    const line = document.createElement('div');
    line.className = `terminal-line ${type}`;

    const timestamp = new Date().toLocaleTimeString('tr-TR');
    line.textContent = `[${timestamp}] ${message}`;

    terminal.appendChild(line);
    terminal.scrollTop = terminal.scrollHeight;

    // Maksimum 100 satır tut
    while (terminal.children.length > 100) {
        terminal.removeChild(terminal.firstChild);
    }
}

// ============================================================
//  SERVER-SENT EVENTS
// ============================================================

function connectSSE() {
    if (eventSource) {
        eventSource.close();
    }

    eventSource = new EventSource('/api/events');

    eventSource.addEventListener('connection', (event) => {
        const data = JSON.parse(event.data);
        updateConnectionStatus(data.state);

        if (data.state === 'connected') {
            isConnected = true;
        } else if (data.state === 'disconnected') {
            isConnected = false;
        }
    });

    eventSource.addEventListener('sensors', (event) => {
        const data = JSON.parse(event.data);
        if (data.sensors) {
            updateSensorDisplay(data.sensors);
        }
    });

    eventSource.addEventListener('detection', (event) => {
        const data = JSON.parse(event.data);
        if (data.red_detected) {
            updateRobotStatus(false);
        }
    });

    eventSource.onerror = () => {
        console.log('SSE bağlantısı koptu, yeniden bağlanılıyor...');
        setTimeout(connectSSE, 3000);
    };
}

// ============================================================
//  SAYFA KAPATILDIĞINDA
// ============================================================

window.addEventListener('beforeunload', () => {
    if (eventSource) {
        eventSource.close();
    }
});
