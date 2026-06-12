#!/usr/bin/env python3
"""
Vision Line Follower - Web Yönetim Arayüzü v2.1
Gelişmiş kontrol, HSV kalibrasyonu ve detaylı loglama
"""

__version__ = "2.1.0"

import os
import sys
import time
import json
import queue
import logging
import threading
from logging.handlers import RotatingFileHandler
from datetime import datetime
from collections import deque
from typing import Dict, Any, Optional

from flask import Flask, Response, request, jsonify, send_from_directory

from .config import config
from .serial_manager import serial_manager, ConnectionState
from .arduino_manager import arduino_manager
from .camera_manager import camera_manager


# ============================================================
#  GELİŞMİŞ LOGLAMA
# ============================================================

class WebLogHandler(logging.Handler):
    """Web arayüzüne log gönderen handler"""

    def __init__(self, max_entries: int = 500):
        super().__init__()
        self.log_entries: deque = deque(maxlen=max_entries)
        self.subscribers: list = []
        self._lock = threading.Lock()

    def emit(self, record):
        try:
            entry = {
                "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
                "level": record.levelname,
                "logger": record.name,
                "message": self.format(record),
                "module": record.module,
                "line": record.lineno
            }

            with self._lock:
                self.log_entries.append(entry)

                # SSE subscriber'lara gönder
                for q in self.subscribers[:]:
                    try:
                        q.put_nowait(entry)
                    except queue.Full:
                        pass

        except Exception:
            pass

    def get_entries(self, limit: int = 100, level: Optional[str] = None) -> list:
        with self._lock:
            entries = list(self.log_entries)

        if level:
            entries = [e for e in entries if e["level"] == level.upper()]

        return entries[-limit:]

    def subscribe(self) -> queue.Queue:
        q = queue.Queue(maxsize=50)
        with self._lock:
            self.subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue):
        with self._lock:
            if q in self.subscribers:
                self.subscribers.remove(q)


web_log_handler = WebLogHandler()


def setup_logging():
    """Loglama sistemini kur"""
    log_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    level = getattr(logging, config.log.level.upper(), logging.DEBUG)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Formatter
    formatter = logging.Formatter(log_format, date_format)

    # Console handler
    if config.log.console_enabled:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler
    if config.log.file:
        try:
            log_dir = os.path.dirname(config.log.file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)

            file_handler = RotatingFileHandler(
                config.log.file,
                maxBytes=config.log.max_bytes,
                backupCount=config.log.backup_count
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            print(f"Log dosyası oluşturulamadı: {e}")

    # Web log handler
    web_log_handler.setLevel(level)
    web_log_handler.setFormatter(logging.Formatter('%(message)s'))
    root_logger.addHandler(web_log_handler)


setup_logging()
logger = logging.getLogger(__name__)


# ============================================================
#  FLASK UYGULAMASI
# ============================================================

app = Flask(__name__, static_folder='static')
app.config['JSON_AS_ASCII'] = False


# ============================================================
#  DURUM TAKİBİ
# ============================================================

class AppState:
    """Uygulama durumu"""

    def __init__(self):
        self.last_command: Optional[str] = None
        self.last_command_time: float = 0
        self.robot_running: bool = False
        self.start_time: float = time.time()
        self.request_count: int = 0

    def update_command(self, cmd: str):
        self.last_command = cmd
        self.last_command_time = time.time()

    def get_uptime(self) -> float:
        return time.time() - self.start_time


app_state = AppState()


# ============================================================
#  BAĞLANTI CALLBACK
# ============================================================

def on_connection_change(state: ConnectionState):
    logger.info(f"Arduino bağlantı durumu: {state.value}")
    if state == ConnectionState.DISCONNECTED:
        app_state.robot_running = False
        app_state.update_command("DISCONNECTED")


serial_manager.on_state_change(on_connection_change)


# ============================================================
#  WEB SAYFALARI
# ============================================================

@app.route('/')
def index():
    app_state.request_count += 1
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder, path)


# ============================================================
#  VİDEO AKIŞI
# ============================================================

@app.route('/video_feed')
def video_feed():
    return Response(
        camera_manager.generate_frames(with_detection=True, show_overlay=True),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/video_raw')
def video_raw():
    """Overlay'siz ham video akışı"""
    return Response(
        camera_manager.generate_frames(with_detection=False, show_overlay=False),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/api/snapshot')
def api_snapshot():
    """Anlık görüntü"""
    snapshot = camera_manager.capture_snapshot()
    if snapshot:
        return Response(snapshot, mimetype='image/jpeg')
    return jsonify({"error": "Görüntü alınamadı"}), 500


# ============================================================
#  API: GENEL DURUM
# ============================================================

@app.route('/api/status')
def api_status():
    """Tam sistem durumu"""
    serial_status = serial_manager.get_status()
    camera_status = camera_manager.get_status()
    arduino_status = arduino_manager.get_status()

    # Robot konfigürasyonu
    robot_config = {
        "speed": config.robot.default_speed,
        "kp": config.robot.default_kp,
        "ki": config.robot.default_ki,
        "kd": config.robot.default_kd
    }

    if serial_manager.is_connected:
        result = serial_manager.send_command("CONFIG")
        if result.success and result.response.startswith("CONFIG:"):
            parts = result.response[7:].split(",")
            if len(parts) == 4:
                robot_config = {
                    "speed": int(parts[0]),
                    "kp": float(parts[1]),
                    "ki": float(parts[2]),
                    "kd": float(parts[3])
                }

    return jsonify({
        "version": __version__,
        "uptime": round(app_state.get_uptime(), 1),
        "request_count": app_state.request_count,
        "serial": serial_status,
        "camera": camera_status,
        "arduino": arduino_status,
        "robot": robot_config,
        "last_command": app_state.last_command,
        "last_command_time": app_state.last_command_time,
        "color_detection": config.color_detection.to_dict()
    })


@app.route('/api/health')
def api_health():
    """Sağlık kontrolü"""
    return jsonify({
        "healthy": True,
        "version": __version__,
        "uptime": round(app_state.get_uptime(), 1),
        "serial_connected": serial_manager.is_connected,
        "camera_running": camera_manager.is_running
    })


# ============================================================
#  API: ROBOT KONTROLÜ
# ============================================================

@app.route('/api/control/start', methods=['POST'])
def api_control_start():
    """Robotu başlat"""
    logger.info("Robot başlatılıyor...")
    result = serial_manager.send_command("GO")
    app_state.update_command("GO")

    if result.success:
        app_state.robot_running = True

    return jsonify({
        "success": result.success,
        "response": result.response,
        "error": result.error,
        "robot_running": app_state.robot_running
    })


@app.route('/api/control/stop', methods=['POST'])
def api_control_stop():
    """Robotu durdur"""
    logger.info("Robot durduruluyor...")
    result = serial_manager.send_command("STOP")
    app_state.update_command("STOP")
    app_state.robot_running = False

    return jsonify({
        "success": result.success,
        "response": result.response,
        "error": result.error,
        "robot_running": app_state.robot_running
    })


@app.route('/api/command', methods=['POST'])
def api_command():
    """Manuel komut gönder"""
    data = request.get_json(silent=True) or {}
    command = data.get('command', '').strip().upper()

    if not command:
        return jsonify({"success": False, "error": "Komut boş olamaz"}), 400

    logger.info(f"Manuel komut: {command}")
    result = serial_manager.send_command(command)
    app_state.update_command(command)

    return jsonify({
        "success": result.success,
        "command": command,
        "response": result.response,
        "error": result.error,
        "duration_ms": round(result.duration_ms, 1)
    })


# ============================================================
#  API: KONFİGÜRASYON
# ============================================================

@app.route('/api/config', methods=['GET'])
def api_config_get():
    """Mevcut konfigürasyonu al"""
    result = serial_manager.send_command("CONFIG")

    if result.success and result.response.startswith("CONFIG:"):
        parts = result.response[7:].split(",")
        if len(parts) == 4:
            return jsonify({
                "success": True,
                "speed": int(parts[0]),
                "kp": float(parts[1]),
                "ki": float(parts[2]),
                "kd": float(parts[3])
            })

    return jsonify({
        "success": False,
        "error": result.error or "Yapılandırma alınamadı"
    })


@app.route('/api/config/speed', methods=['POST'])
def api_config_speed():
    """Hız ayarla"""
    data = request.get_json(silent=True) or {}
    speed = data.get('speed')

    if speed is None:
        return jsonify({"success": False, "error": "Hız değeri gerekli"}), 400

    try:
        speed = max(0, min(255, int(speed)))
    except ValueError:
        return jsonify({"success": False, "error": "Geçersiz hız değeri"}), 400

    logger.info(f"Hız ayarlanıyor: {speed}")
    result = serial_manager.send_command(f"SPEED:{speed}")
    app_state.update_command(f"SPEED:{speed}")

    return jsonify({
        "success": result.success,
        "speed": speed,
        "response": result.response,
        "error": result.error
    })


@app.route('/api/config/pid', methods=['POST'])
def api_config_pid():
    """PID parametrelerini ayarla"""
    data = request.get_json(silent=True) or {}

    try:
        kp = max(0, min(10, float(data.get('kp', 1.0))))
        ki = max(0, min(5, float(data.get('ki', 0.0))))
        kd = max(0, min(10, float(data.get('kd', 0.5))))
    except ValueError:
        return jsonify({"success": False, "error": "Geçersiz PID değerleri"}), 400

    logger.info(f"PID ayarlanıyor: Kp={kp}, Ki={ki}, Kd={kd}")
    result = serial_manager.send_command(f"PID:{kp:.2f},{ki:.2f},{kd:.2f}")
    app_state.update_command(f"PID:{kp:.2f},{ki:.2f},{kd:.2f}")

    return jsonify({
        "success": result.success,
        "kp": kp, "ki": ki, "kd": kd,
        "response": result.response,
        "error": result.error
    })


@app.route('/api/config/save', methods=['POST'])
def api_config_save():
    """Ayarları EEPROM'a kaydet"""
    logger.info("Ayarlar EEPROM'a kaydediliyor...")
    result = serial_manager.send_command("SAVE")
    app_state.update_command("SAVE")

    return jsonify({
        "success": result.success,
        "response": result.response,
        "error": result.error
    })


@app.route('/api/config/reset', methods=['POST'])
def api_config_reset():
    """Varsayılan ayarlara dön"""
    logger.info("Varsayılan ayarlara dönülüyor...")
    result = serial_manager.send_command("RESET")
    app_state.update_command("RESET")

    return jsonify({
        "success": result.success,
        "response": result.response,
        "error": result.error
    })


# ============================================================
#  API: HSV KALİBRASYONU
# ============================================================

@app.route('/api/hsv', methods=['GET'])
def api_hsv_get():
    """Mevcut HSV ayarlarını al"""
    return jsonify({
        "success": True,
        "enabled": config.color_detection.enabled,
        "auto_stop": config.color_detection.auto_stop,
        "red1": config.color_detection.red1.to_dict(),
        "red2": config.color_detection.red2.to_dict(),
        "min_area": config.color_detection.min_area,
        "blur_kernel": config.color_detection.blur_kernel,
        "erode_iterations": config.color_detection.erode_iterations,
        "dilate_iterations": config.color_detection.dilate_iterations
    })


@app.route('/api/hsv', methods=['POST'])
def api_hsv_set():
    """HSV ayarlarını güncelle"""
    data = request.get_json(silent=True) or {}

    logger.info(f"HSV ayarları güncelleniyor: {data}")

    if config.update_color_detection(**data):
        return jsonify({
            "success": True,
            "message": "HSV ayarları güncellendi",
            "current": config.color_detection.to_dict()
        })
    else:
        return jsonify({"success": False, "error": "Ayar güncellenemedi"}), 400


@app.route('/api/hsv/save', methods=['POST'])
def api_hsv_save():
    """HSV ayarlarını dosyaya kaydet"""
    if config.save_settings():
        logger.info("HSV ayarları kaydedildi")
        return jsonify({"success": True, "message": "Ayarlar kaydedildi"})
    else:
        return jsonify({"success": False, "error": "Kayıt başarısız"}), 500


@app.route('/api/hsv/reset', methods=['POST'])
def api_hsv_reset():
    """HSV ayarlarını varsayılana döndür"""
    from .config import HSVRange, ColorDetectionConfig

    config.color_detection = ColorDetectionConfig()
    logger.info("HSV ayarları sıfırlandı")

    return jsonify({
        "success": True,
        "message": "Varsayılan ayarlara dönüldü",
        "current": config.color_detection.to_dict()
    })


@app.route('/api/hsv/toggle', methods=['POST'])
def api_hsv_toggle():
    """Renk algılamayı aç/kapat"""
    data = request.get_json(silent=True) or {}
    enabled = data.get('enabled')

    if enabled is None:
        enabled = not config.color_detection.enabled

    config.color_detection.enabled = bool(enabled)
    logger.info(f"Renk algılama: {'AÇIK' if enabled else 'KAPALI'}")

    return jsonify({
        "success": True,
        "enabled": config.color_detection.enabled
    })


@app.route('/api/hsv/histogram')
def api_hsv_histogram():
    """Canlı HSV histogram verisi"""
    histogram = camera_manager.get_color_histogram()
    return jsonify(histogram)


# ============================================================
#  API: SENSÖRLER
# ============================================================

@app.route('/api/sensors')
def api_sensors():
    """Sensör değerlerini al"""
    result = serial_manager.send_command("SENSORS")

    if result.success and result.response.startswith("SENSORS:"):
        parts = result.response[8:].split(",")
        if len(parts) == 5:
            sensors = [int(p) for p in parts]

            # Hata hesapla
            weights = [-2, -1, 0, 1, 2]
            total = sum(sensors)
            if total > 0:
                error = sum(s * w for s, w in zip(sensors, weights)) / total
            else:
                error = 0

            return jsonify({
                "success": True,
                "sensors": sensors,
                "labels": ["Sol 2", "Sol 1", "Orta", "Sağ 1", "Sağ 2"],
                "error": round(error, 2),
                "line_detected": total > 0
            })

    return jsonify({
        "success": False,
        "sensors": [0, 0, 0, 0, 0],
        "error": result.error or "Sensör verisi alınamadı"
    })


# ============================================================
#  API: ARDUINO YÖNETİMİ
# ============================================================

@app.route('/api/arduino/status')
def api_arduino_status():
    """Arduino CLI durumu"""
    status = arduino_manager.get_status()
    board = arduino_manager.detect_board()

    return jsonify({
        **status,
        "board": {
            "detected": board.detected,
            "fqbn": board.fqbn,
            "port": board.port,
            "name": board.name,
            "error": board.error
        }
    })


@app.route('/api/arduino/ports')
def api_arduino_ports():
    """Mevcut seri portları listele"""
    ports = serial_manager.list_ports()
    return jsonify({"ports": ports})


@app.route('/api/arduino/sketches')
def api_arduino_sketches():
    """Sketch listesi"""
    sketches = arduino_manager.list_sketches()
    return jsonify({
        "sketches": [
            {"name": s.name, "path": s.path, "description": s.description}
            for s in sketches
        ]
    })


@app.route('/api/arduino/compile', methods=['POST'])
def api_arduino_compile():
    """Sketch derle"""
    data = request.get_json(silent=True) or {}
    sketch_name = data.get('sketch')

    if not sketch_name:
        return jsonify({"success": False, "error": "Sketch adı gerekli"}), 400

    sketch_path = arduino_manager.get_sketch_path(sketch_name)
    if not sketch_path:
        return jsonify({"success": False, "error": f"Sketch bulunamadı: {sketch_name}"}), 404

    logger.info(f"Derleniyor: {sketch_name}")
    result = arduino_manager.compile(sketch_path)

    return jsonify({
        "success": result.success,
        "message": result.message,
        "output": result.output,
        "error": result.error
    })


@app.route('/api/arduino/upload', methods=['POST'])
def api_arduino_upload():
    """Sketch yükle"""
    data = request.get_json(silent=True) or {}
    sketch_name = data.get('sketch')

    if not sketch_name:
        return jsonify({"success": False, "error": "Sketch adı gerekli"}), 400

    sketch_path = arduino_manager.get_sketch_path(sketch_name)
    if not sketch_path:
        return jsonify({"success": False, "error": f"Sketch bulunamadı: {sketch_name}"}), 404

    logger.info(f"Yükleniyor: {sketch_name}")

    # Seri bağlantıyı kapat
    serial_manager.stop_heartbeat()
    serial_manager.disconnect()
    time.sleep(1)

    result = arduino_manager.upload(sketch_path)

    # Bağlantıyı yeniden kur
    time.sleep(3)
    if serial_manager.connect():
        serial_manager.start_heartbeat()

    return jsonify({
        "success": result.success,
        "message": result.message,
        "output": result.output,
        "error": result.error
    })


# ============================================================
#  API: BAĞLANTI
# ============================================================

@app.route('/api/connect', methods=['POST'])
def api_connect():
    """Arduino'ya bağlan"""
    data = request.get_json(silent=True) or {}
    port = data.get('port')

    logger.info(f"Bağlanılıyor: {port or 'otomatik'}")

    if serial_manager.connect(port):
        serial_manager.start_heartbeat()
        return jsonify({
            "success": True,
            "port": serial_manager.current_port,
            "firmware": serial_manager.firmware_version
        })

    return jsonify({"success": False, "error": "Bağlantı kurulamadı"})


@app.route('/api/disconnect', methods=['POST'])
def api_disconnect():
    """Bağlantıyı kes"""
    logger.info("Bağlantı kesiliyor...")
    serial_manager.disconnect()
    return jsonify({"success": True})


# ============================================================
#  API: LOG
# ============================================================

@app.route('/api/logs')
def api_logs():
    """Log kayıtlarını al"""
    limit = request.args.get('limit', 100, type=int)
    level = request.args.get('level')

    entries = web_log_handler.get_entries(limit=limit, level=level)
    return jsonify({"logs": entries})


@app.route('/api/logs/command-history')
def api_command_history():
    """Komut geçmişi"""
    limit = request.args.get('limit', 50, type=int)
    history = serial_manager.get_command_history(limit=limit)
    return jsonify({"history": history})


@app.route('/api/logs/detection-history')
def api_detection_history():
    """Algılama geçmişi"""
    return jsonify({"history": camera_manager.detection_log})


# ============================================================
#  SERVER-SENT EVENTS (SSE)
# ============================================================

@app.route('/api/events')
def api_events():
    """Gerçek zamanlı event stream"""

    def generate():
        last_state = None
        last_sensors = None
        last_detection = None
        sensor_interval = 0
        log_queue = web_log_handler.subscribe()

        try:
            while True:
                # Log eventi
                try:
                    while True:
                        log_entry = log_queue.get_nowait()
                        yield f"event: log\ndata: {json.dumps(log_entry)}\n\n"
                except queue.Empty:
                    pass

                # Bağlantı durumu
                current_state = serial_manager.state.value
                if current_state != last_state:
                    last_state = current_state
                    yield f"event: connection\ndata: {json.dumps({'state': current_state, 'port': serial_manager.current_port})}\n\n"

                # Sensör değerleri (her 500ms)
                sensor_interval += 1
                if sensor_interval >= 5 and serial_manager.is_connected:
                    sensor_interval = 0
                    result = serial_manager.send_command("SENSORS")
                    if result.success and result.response.startswith("SENSORS:"):
                        sensors = result.response[8:]
                        if sensors != last_sensors:
                            last_sensors = sensors
                            yield f"event: sensors\ndata: {json.dumps({'sensors': sensors.split(',')})}\n\n"

                # Algılama durumu
                detection = camera_manager.last_detection
                if detection.red_detected != (last_detection.red_detected if last_detection else False):
                    last_detection = detection
                    yield f"event: detection\ndata: {json.dumps({'red_detected': detection.red_detected, 'area': detection.area, 'confidence': detection.confidence})}\n\n"

                    # Otomatik durdurma
                    if detection.red_detected and config.color_detection.auto_stop:
                        if serial_manager.is_connected:
                            serial_manager.send_command("STOP")
                            app_state.robot_running = False
                            yield f"event: auto_stop\ndata: {json.dumps({'reason': 'red_detected'})}\n\n"

                time.sleep(0.1)

        finally:
            web_log_handler.unsubscribe(log_queue)

    return Response(generate(), mimetype='text/event-stream')


# ============================================================
#  API: KAMERA KONTROLÜ
# ============================================================

@app.route('/api/camera/restart', methods=['POST'])
def api_camera_restart():
    """Kamerayı yeniden başlat"""
    logger.info("Kamera yeniden başlatılıyor...")
    if camera_manager.restart():
        return jsonify({"success": True, "message": "Kamera yeniden başlatıldı"})
    return jsonify({"success": False, "error": "Kamera başlatılamadı"})


@app.route('/api/camera/status')
def api_camera_status():
    """Kamera durumu"""
    return jsonify(camera_manager.get_status())


# ============================================================
#  ANA PROGRAM
# ============================================================

def main():
    """Ana fonksiyon"""
    logger.info("=" * 60)
    logger.info(f"  VISION LINE FOLLOWER v{__version__}")
    logger.info("  Web Yönetim Arayüzü - Gelişmiş Kontrol")
    logger.info("=" * 60)
    logger.info(f"Web Arayüz: http://0.0.0.0:{config.web.port}")
    logger.info(f"Log Seviyesi: {config.log.level}")
    if config.log.file:
        logger.info(f"Log Dosyası: {config.log.file}")
    logger.info("=" * 60)

    # Kamera başlat
    if not camera_manager.start():
        logger.warning("Kamera başlatılamadı, simülasyon modunda")

    # Arduino bağlantısı
    if serial_manager.connect():
        serial_manager.start_heartbeat()
        logger.info("Arduino bağlandı ve heartbeat başlatıldı")
    else:
        logger.warning("Arduino bağlantısı kurulamadı - bağlantı bekleniyor")

    try:
        app.run(
            host=config.web.host,
            port=config.web.port,
            debug=config.web.debug,
            threaded=True,
            use_reloader=False
        )
    except KeyboardInterrupt:
        logger.info("Kullanıcı tarafından durduruldu")
    finally:
        logger.info("Sistem kapatılıyor...")
        serial_manager.disconnect()
        camera_manager.stop()
        logger.info("Program sonlandı")


if __name__ == '__main__':
    main()
