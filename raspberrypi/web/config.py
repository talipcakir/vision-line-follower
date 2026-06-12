#!/usr/bin/env python3
"""
Vision Line Follower - Konfigürasyon Modülü v2.1
Dinamik HSV kalibrasyonu ve gelişmiş ayarlar
"""

import os
import json
import threading
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "settings.json"


def _get_env(key: str, default: str, type_func=str):
    value = os.environ.get(key, default)
    try:
        return type_func(value)
    except (ValueError, TypeError):
        return type_func(default)


def _load_env_file():
    env_paths = [
        os.path.join(os.path.dirname(__file__), '..', '.env'),
        os.path.join(os.path.dirname(__file__), '.env'),
    ]
    for env_file in env_paths:
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ.setdefault(key.strip(), value.strip())
            break


_load_env_file()


@dataclass
class SerialConfig:
    port: str = field(default_factory=lambda: _get_env('SERIAL_PORT', '/dev/ttyACM0'))
    baud_rate: int = field(default_factory=lambda: _get_env('BAUD_RATE', '9600', int))
    timeout: float = field(default_factory=lambda: _get_env('SERIAL_TIMEOUT', '1.0', float))
    possible_ports: List[str] = field(default_factory=lambda: [
        '/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyUSB0', '/dev/ttyUSB1',
        'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8'
    ])


@dataclass
class HeartbeatConfig:
    interval: float = field(default_factory=lambda: _get_env('HEARTBEAT_INTERVAL', '2.0', float))
    timeout: float = field(default_factory=lambda: _get_env('HEARTBEAT_TIMEOUT', '5.0', float))
    max_failures: int = field(default_factory=lambda: _get_env('HEARTBEAT_MAX_FAILURES', '3', int))


@dataclass
class CameraConfig:
    width: int = field(default_factory=lambda: _get_env('CAMERA_WIDTH', '640', int))
    height: int = field(default_factory=lambda: _get_env('CAMERA_HEIGHT', '480', int))
    fps: int = field(default_factory=lambda: _get_env('CAMERA_FPS', '30', int))
    jpeg_quality: int = field(default_factory=lambda: _get_env('JPEG_QUALITY', '85', int))


@dataclass
class HSVRange:
    """Tek bir HSV renk aralığı"""
    h_min: int = 0
    h_max: int = 10
    s_min: int = 120
    s_max: int = 255
    v_min: int = 70
    v_max: int = 255

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'HSVRange':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ColorDetectionConfig:
    """Renk algılama konfigürasyonu - dinamik olarak değiştirilebilir"""
    enabled: bool = True
    auto_stop: bool = True

    red1: HSVRange = field(default_factory=lambda: HSVRange(
        h_min=0, h_max=10, s_min=120, s_max=255, v_min=70, v_max=255
    ))
    red2: HSVRange = field(default_factory=lambda: HSVRange(
        h_min=170, h_max=180, s_min=120, s_max=255, v_min=70, v_max=255
    ))

    min_area: int = 1500
    blur_kernel: int = 5
    erode_iterations: int = 2
    dilate_iterations: int = 2

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "auto_stop": self.auto_stop,
            "red1": self.red1.to_dict(),
            "red2": self.red2.to_dict(),
            "min_area": self.min_area,
            "blur_kernel": self.blur_kernel,
            "erode_iterations": self.erode_iterations,
            "dilate_iterations": self.dilate_iterations
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ColorDetectionConfig':
        cfg = cls()
        cfg.enabled = data.get("enabled", True)
        cfg.auto_stop = data.get("auto_stop", True)
        cfg.min_area = data.get("min_area", 1500)
        cfg.blur_kernel = data.get("blur_kernel", 5)
        cfg.erode_iterations = data.get("erode_iterations", 2)
        cfg.dilate_iterations = data.get("dilate_iterations", 2)
        if "red1" in data:
            cfg.red1 = HSVRange.from_dict(data["red1"])
        if "red2" in data:
            cfg.red2 = HSVRange.from_dict(data["red2"])
        return cfg


@dataclass
class ArduinoConfig:
    cli_path: str = field(default_factory=lambda: _get_env('ARDUINO_CLI_PATH', 'arduino-cli'))
    fqbn: str = field(default_factory=lambda: _get_env('ARDUINO_FQBN', 'arduino:avr:uno'))
    sketches_dir: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(__file__), '..', '..', 'arduino'
    ))
    upload_timeout: int = field(default_factory=lambda: _get_env('ARDUINO_UPLOAD_TIMEOUT', '120', int))


@dataclass
class WebConfig:
    host: str = field(default_factory=lambda: _get_env('WEB_HOST', '0.0.0.0'))
    port: int = field(default_factory=lambda: _get_env('WEB_PORT', '5000', int))
    debug: bool = field(default_factory=lambda: _get_env('WEB_DEBUG', 'false', lambda x: x.lower() == 'true'))


@dataclass
class RobotConfig:
    default_speed: int = field(default_factory=lambda: _get_env('DEFAULT_SPEED', '100', int))
    default_kp: float = field(default_factory=lambda: _get_env('DEFAULT_KP', '1.0', float))
    default_ki: float = field(default_factory=lambda: _get_env('DEFAULT_KI', '0.0', float))
    default_kd: float = field(default_factory=lambda: _get_env('DEFAULT_KD', '0.5', float))
    min_speed: int = 0
    max_speed: int = 255


@dataclass
class LogConfig:
    level: str = field(default_factory=lambda: _get_env('LOG_LEVEL', 'DEBUG'))
    file: str = field(default_factory=lambda: _get_env('LOG_FILE', '/var/log/vision-line-follower/app.log'))
    max_bytes: int = 10 * 1024 * 1024  # 10 MB
    backup_count: int = 5
    console_enabled: bool = True
    detailed_format: bool = True


class Config:
    """Ana konfigürasyon sınıfı - thread-safe ve persistent"""

    _instance: Optional['Config'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.serial = SerialConfig()
        self.heartbeat = HeartbeatConfig()
        self.camera = CameraConfig()
        self.color_detection = ColorDetectionConfig()
        self.arduino = ArduinoConfig()
        self.web = WebConfig()
        self.robot = RobotConfig()
        self.log = LogConfig()

        self._load_settings()
        self._initialized = True

    def _load_settings(self):
        """Kaydedilmiş ayarları yükle"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)

                if "color_detection" in data:
                    self.color_detection = ColorDetectionConfig.from_dict(data["color_detection"])

                if "log_level" in data:
                    self.log.level = data["log_level"]

            except Exception as e:
                print(f"Ayar dosyası yüklenemedi: {e}")

    def save_settings(self):
        """Ayarları dosyaya kaydet"""
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "color_detection": self.color_detection.to_dict(),
                "log_level": self.log.level
            }

            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=2)

            return True
        except Exception as e:
            print(f"Ayar dosyası kaydedilemedi: {e}")
            return False

    def update_color_detection(self, **kwargs) -> bool:
        """Renk algılama ayarlarını güncelle"""
        with self._lock:
            try:
                if "red1" in kwargs:
                    self.color_detection.red1 = HSVRange.from_dict(kwargs["red1"])
                if "red2" in kwargs:
                    self.color_detection.red2 = HSVRange.from_dict(kwargs["red2"])
                if "min_area" in kwargs:
                    self.color_detection.min_area = int(kwargs["min_area"])
                if "enabled" in kwargs:
                    self.color_detection.enabled = bool(kwargs["enabled"])
                if "auto_stop" in kwargs:
                    self.color_detection.auto_stop = bool(kwargs["auto_stop"])
                if "blur_kernel" in kwargs:
                    self.color_detection.blur_kernel = int(kwargs["blur_kernel"])
                if "erode_iterations" in kwargs:
                    self.color_detection.erode_iterations = int(kwargs["erode_iterations"])
                if "dilate_iterations" in kwargs:
                    self.color_detection.dilate_iterations = int(kwargs["dilate_iterations"])
                return True
            except Exception as e:
                print(f"Ayar güncellenemedi: {e}")
                return False

    def get_hsv_arrays(self):
        """NumPy array formatında HSV değerlerini döndür"""
        import numpy as np

        cd = self.color_detection
        lower_red1 = np.array([cd.red1.h_min, cd.red1.s_min, cd.red1.v_min])
        upper_red1 = np.array([cd.red1.h_max, cd.red1.s_max, cd.red1.v_max])
        lower_red2 = np.array([cd.red2.h_min, cd.red2.s_min, cd.red2.v_min])
        upper_red2 = np.array([cd.red2.h_max, cd.red2.s_max, cd.red2.v_max])

        return lower_red1, upper_red1, lower_red2, upper_red2


config = Config()
