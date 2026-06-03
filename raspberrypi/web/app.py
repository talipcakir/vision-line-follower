#!/usr/bin/env python3
"""
Vision Line Follower - Web Yönetim Arayüzü
Ana Flask Uygulaması
"""

__version__ = "2.0.0"

import os
import sys
import time
import json
import logging
from logging.handlers import RotatingFileHandler
from functools import wraps

from flask import Flask, Response, request, jsonify, send_from_directory

from .config import config
from .serial_manager import serial_manager, ConnectionState
from .arduino_manager import arduino_manager
from .camera_manager import camera_manager

# ============================================================
#  LOGLAMA
# ============================================================

def setup_logging():
    log_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    level = getattr(logging, config.log_level.upper(), logging.INFO)

    logging.basicConfig(level=level, format=log_format, datefmt=date_format)

    if config.log_file:
        log_dir = os.path.dirname(config.log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        file_handler = RotatingFileHandler(
            config.log_file,
            maxBytes=5*1024*1024,
            backupCount=3
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        logging.getLogger().addHandler(file_handler)

setup_logging()
logger = logging.getLogger(__name__)

# ============================================================
#  FLASK UYGULAMASI
# ============================================================

app = Flask(__name__, static_folder='static')

# ============================================================
#  DURUM TAKİBİ
# ============================================================

last_command = None
last_command_time = 0

def update_last_command(cmd: str):
    global last_command, last_command_time
    last_command = cmd
    last_command_time = time.time()

# ============================================================
#  BAĞLANTI CALLBACK
# ============================================================

def on_connection_change(state: ConnectionState):
    logger.info(f"Bağlantı durumu değişti: {state.value}")
    if state == ConnectionState.DISCONNECTED:
        update_last_command("DISCONNECTED")

serial_manager.on_state_change(on_connection_change)

# ============================================================
#  WEB SAYFALARI
# ============================================================

@app.route('/')
def index():
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
        camera_manager.generate_frames(with_detection=True),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

# ============================================================
#  API: DURUM
# ============================================================

@app.route('/api/status')
def api_status():
    serial_status = serial_manager.get_status()
    camera_status = camera_manager.get_status()
    arduino_status = arduino_manager.get_status()

    result = serial_manager.send_command("CONFIG")
    robot_config = {"speed": 100, "kp": 1.0, "ki": 0.0, "kd": 0.5}

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
        "serial": serial_status,
        "camera": camera_status,
        "arduino": arduino_status,
        "robot": robot_config,
        "last_command": last_command,
        "last_command_time": last_command_time
    })

@app.route('/api/health')
def api_health():
    return jsonify({
        "healthy": True,
        "version": __version__
    })

# ============================================================
#  API: ROBOT KONTROLÜ
# ============================================================

@app.route('/api/control/start', methods=['POST'])
def api_control_start():
    result = serial_manager.send_command("GO")
    update_last_command("GO")

    return jsonify({
        "success": result.success,
        "response": result.response,
        "error": result.error
    })

@app.route('/api/control/stop', methods=['POST'])
def api_control_stop():
    result = serial_manager.send_command("STOP")
    update_last_command("STOP")

    return jsonify({
        "success": result.success,
        "response": result.response,
        "error": result.error
    })

@app.route('/api/command', methods=['POST'])
def api_command():
    data = request.get_json() or {}
    command = data.get('command', '').strip()

    if not command:
        return jsonify({"success": False, "error": "Komut boş olamaz"}), 400

    result = serial_manager.send_command(command)
    update_last_command(command)

    return jsonify({
        "success": result.success,
        "response": result.response,
        "error": result.error
    })

# ============================================================
#  API: KONFİGÜRASYON
# ============================================================

@app.route('/api/config', methods=['GET'])
def api_config_get():
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
    data = request.get_json() or {}
    speed = data.get('speed')

    if speed is None:
        return jsonify({"success": False, "error": "Hız değeri gerekli"}), 400

    try:
        speed = int(speed)
        speed = max(0, min(255, speed))
    except ValueError:
        return jsonify({"success": False, "error": "Geçersiz hız değeri"}), 400

    result = serial_manager.send_command(f"SPEED:{speed}")
    update_last_command(f"SPEED:{speed}")

    return jsonify({
        "success": result.success,
        "speed": speed,
        "response": result.response,
        "error": result.error
    })

@app.route('/api/config/pid', methods=['POST'])
def api_config_pid():
    data = request.get_json() or {}

    try:
        kp = float(data.get('kp', 1.0))
        ki = float(data.get('ki', 0.0))
        kd = float(data.get('kd', 0.5))
    except ValueError:
        return jsonify({"success": False, "error": "Geçersiz PID değerleri"}), 400

    kp = max(0, min(10, kp))
    ki = max(0, min(5, ki))
    kd = max(0, min(10, kd))

    result = serial_manager.send_command(f"PID:{kp:.2f},{ki:.2f},{kd:.2f}")
    update_last_command(f"PID:{kp:.2f},{ki:.2f},{kd:.2f}")

    return jsonify({
        "success": result.success,
        "kp": kp,
        "ki": ki,
        "kd": kd,
        "response": result.response,
        "error": result.error
    })

@app.route('/api/config/save', methods=['POST'])
def api_config_save():
    result = serial_manager.send_command("SAVE")
    update_last_command("SAVE")

    return jsonify({
        "success": result.success,
        "response": result.response,
        "error": result.error
    })

@app.route('/api/config/reset', methods=['POST'])
def api_config_reset():
    result = serial_manager.send_command("RESET")
    update_last_command("RESET")

    return jsonify({
        "success": result.success,
        "response": result.response,
        "error": result.error
    })

# ============================================================
#  API: SENSÖRLER
# ============================================================

@app.route('/api/sensors')
def api_sensors():
    result = serial_manager.send_command("SENSORS")

    if result.success and result.response.startswith("SENSORS:"):
        parts = result.response[8:].split(",")
        if len(parts) == 5:
            sensors = [int(p) for p in parts]
            return jsonify({
                "success": True,
                "sensors": sensors,
                "labels": ["Sol 2", "Sol 1", "Orta", "Sağ 1", "Sağ 2"]
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
    return jsonify(arduino_manager.get_status())

@app.route('/api/arduino/board')
def api_arduino_board():
    board = arduino_manager.detect_board()
    return jsonify({
        "detected": board.detected,
        "fqbn": board.fqbn,
        "port": board.port,
        "name": board.name,
        "error": board.error
    })

@app.route('/api/arduino/sketches')
def api_arduino_sketches():
    sketches = arduino_manager.list_sketches()
    return jsonify({
        "sketches": [
            {"name": s.name, "path": s.path, "description": s.description}
            for s in sketches
        ]
    })

@app.route('/api/arduino/upload', methods=['POST'])
def api_arduino_upload():
    data = request.get_json() or {}
    sketch_name = data.get('sketch')

    if not sketch_name:
        return jsonify({"success": False, "error": "Sketch adı gerekli"}), 400

    sketch_path = arduino_manager.get_sketch_path(sketch_name)
    if not sketch_path:
        return jsonify({"success": False, "error": f"Sketch bulunamadı: {sketch_name}"}), 404

    serial_manager.stop_heartbeat()
    serial_manager.disconnect()

    time.sleep(1)

    result = arduino_manager.upload(sketch_path)

    time.sleep(2)

    serial_manager.connect()
    serial_manager.start_heartbeat()

    return jsonify({
        "success": result.success,
        "message": result.message,
        "output": result.output,
        "error": result.error
    })

@app.route('/api/arduino/compile', methods=['POST'])
def api_arduino_compile():
    data = request.get_json() or {}
    sketch_name = data.get('sketch')

    if not sketch_name:
        return jsonify({"success": False, "error": "Sketch adı gerekli"}), 400

    sketch_path = arduino_manager.get_sketch_path(sketch_name)
    if not sketch_path:
        return jsonify({"success": False, "error": f"Sketch bulunamadı: {sketch_name}"}), 404

    result = arduino_manager.compile(sketch_path)

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
    if serial_manager.connect():
        serial_manager.start_heartbeat()
        return jsonify({"success": True, "port": serial_manager.current_port})
    return jsonify({"success": False, "error": "Bağlantı kurulamadı"})

@app.route('/api/disconnect', methods=['POST'])
def api_disconnect():
    serial_manager.disconnect()
    return jsonify({"success": True})

# ============================================================
#  SERVER-SENT EVENTS (SSE)
# ============================================================

@app.route('/api/events')
def api_events():
    def generate():
        last_state = None
        last_sensors = None

        while True:
            current_state = serial_manager.state.value
            if current_state != last_state:
                last_state = current_state
                yield f"event: connection\ndata: {json.dumps({'state': current_state})}\n\n"

            if serial_manager.is_connected:
                result = serial_manager.send_command("SENSORS")
                if result.success and result.response.startswith("SENSORS:"):
                    sensors = result.response[8:]
                    if sensors != last_sensors:
                        last_sensors = sensors
                        yield f"event: sensors\ndata: {json.dumps({'sensors': sensors.split(',')})}\n\n"

            detection = camera_manager.last_detection
            yield f"event: detection\ndata: {json.dumps({'red_detected': detection.red_detected})}\n\n"

            time.sleep(0.5)

    return Response(generate(), mimetype='text/event-stream')

# ============================================================
#  ANA PROGRAM
# ============================================================

def main():
    logger.info("=" * 50)
    logger.info(f"  VISION LINE FOLLOWER v{__version__}")
    logger.info("  Web Yönetim Arayüzü")
    logger.info("=" * 50)
    logger.info(f"Web: http://0.0.0.0:{config.web.port}")
    logger.info("=" * 50)

    if not camera_manager.start():
        logger.warning("Kamera başlatılamadı, simülasyon modu")

    if serial_manager.connect():
        serial_manager.start_heartbeat()
    else:
        logger.warning("Arduino bağlantısı kurulamadı")

    try:
        app.run(
            host=config.web.host,
            port=config.web.port,
            debug=config.web.debug,
            threaded=True,
            use_reloader=False
        )
    except KeyboardInterrupt:
        logger.info("Kapatılıyor...")
    finally:
        serial_manager.disconnect()
        camera_manager.stop()
        logger.info("Program sonlandı")


if __name__ == '__main__':
    main()
