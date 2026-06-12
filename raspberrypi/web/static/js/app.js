// ============================================================
//  Vision Line Follower - Web Arayüz v2.1
//  Gelişmiş kontrol, HSV kalibrasyon ve detaylı loglama
// ============================================================

const API_BASE = '';

// Durum değişkenleri
let isConnected = false;
let robotRunning = false;
let eventSource = null;
let logEntries = [];

// ============================================================
//  SAYFA YÜKLENDIĞINDE
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    log('Sistem başlatılıyor...', 'info');

    // Tab yönetimi
    setupTabs();

    // İlk durumu al
    fetchStatus();
    refreshPorts();
    refreshSketches();
    loadHSVSettings();

    // SSE bağlantısı
    connectSSE();

    // Periyodik güncelleme
    setInterval(fetchStatus, 5000);
    setInterval(fetchSensors, 500);
    setInterval(updateUptime, 1000);

    // Video yükleme kontrolü
    setupVideoHandlers();

    log('Sistem hazır', 'info');
});

// ============================================================
//  TAB YÖNETİMİ
// ============================================================

function setupTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;

            // Aktif tab'ı değiştir
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            document.getElementById(`tab-${tabId}`).classList.add('active');

            // Log tab'ına geçince geçmişi yükle
            if (tabId === 'logs') {
                refreshCommandHistory();
                refreshDetectionHistory();
            }
        });
    });
}

// ============================================================
//  VIDEO HANDLERS
// ============================================================

function setupVideoHandlers() {
    const video = document.getElementById('videoFeed');
    const overlay = document.getElementById('videoOverlay');

    video.onload = () => overlay.classList.add('hidden');
    video.onerror = () => overlay.classList.remove('hidden');

    // Kalibrasyon videosu
    const calVideo = document.getElementById('calibrationVideo');
    if (calVideo) {
        calVideo.onload = () => {};
        calVideo.onerror = () => {};
    }
}

function takeSnapshot() {
    window.open('/api/snapshot', '_blank');
    log('Anlık görüntü alındı', 'info');
}

async function restartCamera() {
    log('Kamera yeniden başlatılıyor...', 'info');
    const result = await apiCall('/api/camera/restart', 'POST');
    if (result.success) {
        log('Kamera yeniden başlatıldı', 'response');
        // Video'yu yeniden yükle
        const video = document.getElementById('videoFeed');
        video.src = '/video_feed?' + Date.now();
    } else {
        log(`Kamera hatası: ${result.error}`, 'error');
    }
}

// ============================================================
//  API ÇAĞRILARI
// ============================================================

async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' }
    };

    // POST isteklerinde her zaman body gönder
    if (method === 'POST') {
        options.body = JSON.stringify(data || {});
    } else if (data) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        return await response.json();
    } catch (error) {
        console.error('API Hatası:', error);
        return { success: false, error: error.message };
    }
}

// ============================================================
//  DURUM GÜNCELLEME
// ============================================================

let startTime = Date.now();

async function fetchStatus() {
    const status = await apiCall('/api/status');

    if (status.version) {
        document.getElementById('versionBadge').textContent = `v${status.version}`;
        document.getElementById('footerVersion').textContent = status.version;
        document.getElementById('sysVersion').textContent = status.version;
    }

    if (status.serial) {
        updateConnectionStatus(status.serial.state, status.serial.port);
        isConnected = status.serial.connected;

        // Arduino tab bilgileri
        document.getElementById('serialState').textContent = status.serial.state;
        document.getElementById('serialPort').textContent = status.serial.port || '-';
        document.getElementById('serialFirmware').textContent = status.serial.firmware_version || '-';
        document.getElementById('firmwareVersion').textContent = status.serial.firmware_version || '-';
        document.getElementById('serialBaud').textContent = status.serial.baud_rate;
        document.getElementById('serialUptime').textContent = formatDuration(status.serial.uptime_seconds);
        document.getElementById('serialCmdCount').textContent = status.serial.command_count;
    }

    if (status.robot) {
        document.getElementById('speedSlider').value = status.robot.speed;
        document.getElementById('speedValue').textContent = status.robot.speed;
        document.getElementById('inputKp').value = status.robot.kp;
        document.getElementById('inputKi').value = status.robot.ki;
        document.getElementById('inputKd').value = status.robot.kd;
    }

    if (status.arduino) {
        document.getElementById('cliStatus').textContent =
            status.arduino.cli_available ? '✓ Kurulu' : '✗ Yok';
    }

    if (status.camera) {
        document.getElementById('sysFps').textContent = status.camera.fps;
        document.getElementById('sysFrames').textContent = status.camera.frame_count;
        document.getElementById('sysDetections').textContent = status.camera.detection_count;
    }

    if (status.uptime) {
        document.getElementById('sysUptime').textContent = formatDuration(status.uptime);
    }

    if (status.request_count) {
        document.getElementById('sysRequests').textContent = status.request_count;
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

function updateUptime() {
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    document.getElementById('uptime').textContent = `Oturum: ${formatDuration(elapsed)}`;
}

function formatDuration(seconds) {
    if (!seconds || seconds < 0) return '-';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) return `${h}s ${m}d ${s}sn`;
    if (m > 0) return `${m}d ${s}sn`;
    return `${s}sn`;
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
    statusText.className = 'value ' + (running ? 'running' : 'stopped');

    document.getElementById('btnStart').disabled = running;
    document.getElementById('btnStop').disabled = !running;
}

// ============================================================
//  HIZ & PID AYARLARI
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
        document.getElementById('sensorError').textContent = result.error || '0';
        document.getElementById('lineDetected').textContent = result.line_detected ? 'Evet' : 'Hayır';
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
//  HSV KALİBRASYON
// ============================================================

async function loadHSVSettings() {
    const result = await apiCall('/api/hsv');
    if (!result.success) return;

    document.getElementById('detectionEnabled').checked = result.enabled;
    document.getElementById('autoStopEnabled').checked = result.auto_stop;
    document.getElementById('detectionStatusText').textContent = result.enabled ? 'Açık' : 'Kapalı';

    // Red1
    setSliderValue('red1HMin', result.red1.h_min);
    setSliderValue('red1HMax', result.red1.h_max);
    setSliderValue('red1SMin', result.red1.s_min);
    setSliderValue('red1VMin', result.red1.v_min);

    // Red2
    setSliderValue('red2HMin', result.red2.h_min);
    setSliderValue('red2HMax', result.red2.h_max);
    setSliderValue('red2SMin', result.red2.s_min);
    setSliderValue('red2VMin', result.red2.v_min);

    // Other
    setSliderValue('minArea', result.min_area);
    setSliderValue('blurKernel', result.blur_kernel);
}

function setSliderValue(id, value) {
    const slider = document.getElementById(id);
    if (slider) {
        slider.value = value;
        const valueSpan = slider.parentElement.querySelector('.value');
        if (valueSpan) valueSpan.textContent = value;
    }
}

function updateHSVLabel(input) {
    const valueSpan = input.parentElement.querySelector('.value');
    if (valueSpan) valueSpan.textContent = input.value;
}

async function toggleDetection() {
    const enabled = document.getElementById('detectionEnabled').checked;
    const result = await apiCall('/api/hsv/toggle', 'POST', { enabled });
    if (result.success) {
        document.getElementById('detectionStatusText').textContent = result.enabled ? 'Açık' : 'Kapalı';
        log(`Renk algılama: ${result.enabled ? 'AÇIK' : 'KAPALI'}`, 'info');
    }
}

async function toggleAutoStop() {
    const enabled = document.getElementById('autoStopEnabled').checked;
    await apiCall('/api/hsv', 'POST', { auto_stop: enabled });
    log(`Otomatik durdurma: ${enabled ? 'AÇIK' : 'KAPALI'}`, 'info');
}

async function applyHSV() {
    const data = {
        red1: {
            h_min: parseInt(document.getElementById('red1HMin').value),
            h_max: parseInt(document.getElementById('red1HMax').value),
            s_min: parseInt(document.getElementById('red1SMin').value),
            s_max: 255,
            v_min: parseInt(document.getElementById('red1VMin').value),
            v_max: 255
        },
        red2: {
            h_min: parseInt(document.getElementById('red2HMin').value),
            h_max: parseInt(document.getElementById('red2HMax').value),
            s_min: parseInt(document.getElementById('red2SMin').value),
            s_max: 255,
            v_min: parseInt(document.getElementById('red2VMin').value),
            v_max: 255
        },
        min_area: parseInt(document.getElementById('minArea').value),
        blur_kernel: parseInt(document.getElementById('blurKernel').value)
    };

    log('HSV ayarları uygulanıyor...', 'info');
    const result = await apiCall('/api/hsv', 'POST', data);

    if (result.success) {
        log('HSV ayarları güncellendi', 'response');
    } else {
        log(`Hata: ${result.error}`, 'error');
    }
}

async function saveHSV() {
    const result = await apiCall('/api/hsv/save', 'POST');
    if (result.success) {
        log('HSV ayarları kaydedildi', 'response');
    } else {
        log(`Hata: ${result.error}`, 'error');
    }
}

async function resetHSV() {
    const result = await apiCall('/api/hsv/reset', 'POST');
    if (result.success) {
        log('HSV varsayılan ayarlara döndü', 'response');
        loadHSVSettings();
    } else {
        log(`Hata: ${result.error}`, 'error');
    }
}

// ============================================================
//  ARDUINO YÖNETİMİ
// ============================================================

async function connectArduino() {
    log('Arduino\'ya bağlanılıyor...', 'info');
    const result = await apiCall('/api/connect', 'POST');

    if (result.success) {
        log(`Bağlantı başarılı: ${result.port}`, 'response');
        fetchStatus();
    } else {
        log(`Bağlantı hatası: ${result.error}`, 'error');
    }
}

async function disconnectArduino() {
    log('Bağlantı kesiliyor...', 'info');
    await apiCall('/api/disconnect', 'POST');
    log('Bağlantı kesildi', 'response');
    fetchStatus();
}

async function refreshPorts() {
    const result = await apiCall('/api/arduino/ports');
    const container = document.getElementById('portList');

    if (result.ports && result.ports.length > 0) {
        container.innerHTML = result.ports.map(port => `
            <div class="port-item">
                <div class="device">${port.device}</div>
                <div class="description">${port.description} - ${port.manufacturer}</div>
            </div>
        `).join('');
    } else {
        container.innerHTML = '<p class="muted">Port bulunamadı</p>';
    }
}

async function refreshSketches() {
    const result = await apiCall('/api/arduino/sketches');
    const select = document.getElementById('sketchSelect');

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
        if (result.output) log(result.output, 'info');
    }
}

async function uploadSketch() {
    const sketch = document.getElementById('sketchSelect').value;
    if (!sketch) {
        log('Lütfen bir sketch seçin', 'error');
        return;
    }

    if (!confirm(`"${sketch}" Arduino'ya yüklenecek. Devam edilsin mi?`)) {
        return;
    }

    log(`Yükleniyor: ${sketch}...`, 'info');
    showProgress(true, 'Yükleniyor...');

    const result = await apiCall('/api/arduino/upload', 'POST', { sketch });
    showProgress(false);

    if (result.success) {
        log('Yükleme başarılı!', 'response');
        setTimeout(fetchStatus, 3000);
    } else {
        log(`Yükleme hatası: ${result.error}`, 'error');
        if (result.output) log(result.output, 'info');
    }
}

function showProgress(show, text = '') {
    const progress = document.getElementById('uploadProgress');
    const progressText = document.getElementById('progressText');
    const progressFill = document.getElementById('progressFill');

    if (show) {
        progress.classList.add('active');
        progressText.textContent = text;
        progressFill.style.width = '100%';
    } else {
        progress.classList.remove('active');
    }
}

// ============================================================
//  TERMİNAL
// ============================================================

async function sendCommand() {
    const input = document.getElementById('commandInput');
    const command = input.value.trim().toUpperCase();

    if (!command) return;

    log(`> ${command}`, 'command');
    input.value = '';

    const result = await apiCall('/api/command', 'POST', { command });

    if (result.success) {
        log(result.response, 'response');
        if (result.duration_ms) {
            log(`(${result.duration_ms}ms)`, 'info');
        }
    } else {
        log(`Hata: ${result.error}`, 'error');
    }
}

function quickCommand(cmd) {
    document.getElementById('commandInput').value = cmd;
    sendCommand();
}

function log(message, type = 'info') {
    const terminal = document.getElementById('terminal');
    if (!terminal) return;

    const line = document.createElement('div');
    line.className = `terminal-line ${type}`;

    const timestamp = new Date().toLocaleTimeString('tr-TR');
    line.textContent = `[${timestamp}] ${message}`;

    terminal.appendChild(line);
    terminal.scrollTop = terminal.scrollHeight;

    // Maksimum 200 satır
    while (terminal.children.length > 200) {
        terminal.removeChild(terminal.firstChild);
    }
}

// ============================================================
//  LOG VİEWER
// ============================================================

function addLogEntry(entry) {
    logEntries.push(entry);

    // Maksimum 500 kayıt
    if (logEntries.length > 500) {
        logEntries.shift();
    }

    renderLogs();
}

function renderLogs() {
    const viewer = document.getElementById('logViewer');
    if (!viewer) return;

    const filter = document.getElementById('logLevelFilter').value;
    const filtered = filter ? logEntries.filter(e => e.level === filter) : logEntries;

    viewer.innerHTML = filtered.slice(-100).map(entry => `
        <div class="log-entry">
            <span class="timestamp">${entry.timestamp}</span>
            <span class="level ${entry.level}">${entry.level}</span>
            <span class="message">${entry.message}</span>
        </div>
    `).join('');

    if (document.getElementById('autoScrollLogs').checked) {
        viewer.scrollTop = viewer.scrollHeight;
    }
}

function filterLogs() {
    renderLogs();
}

function clearLogs() {
    logEntries = [];
    renderLogs();
}

async function refreshCommandHistory() {
    const result = await apiCall('/api/logs/command-history');
    const container = document.getElementById('commandHistory');

    if (result.history && result.history.length > 0) {
        container.innerHTML = result.history.slice(0, 30).map(h => `
            <div class="history-item">
                <span class="time">${h.timestamp}</span>
                <span class="cmd">${h.command}</span>
                <span class="resp">${h.response}</span>
                <span class="time">${h.duration_ms}ms</span>
            </div>
        `).join('');
    } else {
        container.innerHTML = '<p class="muted">Komut geçmişi boş</p>';
    }
}

async function refreshDetectionHistory() {
    const result = await apiCall('/api/logs/detection-history');
    const container = document.getElementById('detectionHistory');

    if (result.history && result.history.length > 0) {
        container.innerHTML = result.history.slice(-20).reverse().map(h => `
            <div class="history-item">
                <span class="time">${h.timestamp}</span>
                <span>Alan: ${h.area}px</span>
                <span>Konum: ${h.position}</span>
                <span>Güven: ${h.confidence}</span>
            </div>
        `).join('');
    } else {
        container.innerHTML = '<p class="muted">Algılama geçmişi boş</p>';
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
        updateConnectionStatus(data.state, data.port);
        isConnected = data.state === 'connected';
    });

    eventSource.addEventListener('sensors', (event) => {
        const data = JSON.parse(event.data);
        if (data.sensors) {
            updateSensorDisplay(data.sensors);
        }
    });

    eventSource.addEventListener('detection', (event) => {
        const data = JSON.parse(event.data);
        const detValue = document.getElementById('detectionValue');
        if (data.red_detected) {
            detValue.textContent = `Algılandı (${data.area}px, ${(data.confidence * 100).toFixed(0)}%)`;
            detValue.classList.add('detected');
            updateRobotStatus(false);
        } else {
            detValue.textContent = 'Yok';
            detValue.classList.remove('detected');
        }
    });

    eventSource.addEventListener('log', (event) => {
        const entry = JSON.parse(event.data);
        addLogEntry(entry);
    });

    eventSource.addEventListener('auto_stop', (event) => {
        log('Otomatik durdurma: Kırmızı algılandı', 'warning');
        updateRobotStatus(false);
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
