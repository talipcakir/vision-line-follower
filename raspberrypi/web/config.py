#!/usr/bin/env python3
"""
Vision Line Follower - Konfigürasyon Modülü
"""

import os
from dataclasses import dataclass, field
from typing import List

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
        'COM3', 'COM4', 'COM5', 'COM6'
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


@dataclass
class RedDetectionConfig:
    red1_h_min: int = field(default_factory=lambda: _get_env('RED1_H_MIN', '0', int))
    red1_h_max: int = field(default_factory=lambda: _get_env('RED1_H_MAX', '10', int))
    red1_s_min: int = field(default_factory=lambda: _get_env('RED1_S_MIN', '120', int))
    red1_v_min: int = field(default_factory=lambda: _get_env('RED1_V_MIN', '70', int))
    red2_h_min: int = field(default_factory=lambda: _get_env('RED2_H_MIN', '170', int))
    red2_h_max: int = field(default_factory=lambda: _get_env('RED2_H_MAX', '180', int))
    red2_s_min: int = field(default_factory=lambda: _get_env('RED2_S_MIN', '120', int))
    red2_v_min: int = field(default_factory=lambda: _get_env('RED2_V_MIN', '70', int))
    min_area: int = field(default_factory=lambda: _get_env('MIN_DETECTION_AREA', '1500', int))


@dataclass
class ArduinoConfig:
    cli_path: str = field(default_factory=lambda: _get_env('ARDUINO_CLI_PATH', 'arduino-cli'))
    fqbn: str = field(default_factory=lambda: _get_env('ARDUINO_FQBN', 'arduino:avr:uno'))
    sketches_dir: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(__file__), '..', '..', 'arduino'
    ))
    upload_timeout: int = field(default_factory=lambda: _get_env('ARDUINO_UPLOAD_TIMEOUT', '60', int))


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
class Config:
    serial: SerialConfig = field(default_factory=SerialConfig)
    heartbeat: HeartbeatConfig = field(default_factory=HeartbeatConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    red_detection: RedDetectionConfig = field(default_factory=RedDetectionConfig)
    arduino: ArduinoConfig = field(default_factory=ArduinoConfig)
    web: WebConfig = field(default_factory=WebConfig)
    robot: RobotConfig = field(default_factory=RobotConfig)
    log_level: str = field(default_factory=lambda: _get_env('LOG_LEVEL', 'INFO'))
    log_file: str = field(default_factory=lambda: _get_env('LOG_FILE', ''))


config = Config()
