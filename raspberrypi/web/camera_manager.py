#!/usr/bin/env python3
"""
Vision Line Follower - Kamera Yönetimi
"""

import time
import threading
import logging
from typing import Optional, Generator, Tuple
from dataclasses import dataclass

import cv2
import numpy as np

from .config import config

logger = logging.getLogger(__name__)

try:
    from picamera2 import Picamera2
    PICAMERA_AVAILABLE = True
except ImportError:
    PICAMERA_AVAILABLE = False
    logger.warning("picamera2 bulunamadı, simülasyon modu kullanılacak")


@dataclass
class DetectionResult:
    red_detected: bool
    area: int = 0
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0


class CameraManager:
    _instance: Optional['CameraManager'] = None
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

        self._camera = None
        self._running = False
        self._frame_lock = threading.Lock()
        self._current_frame: Optional[np.ndarray] = None
        self._detection_result = DetectionResult(False)
        self._frame_count = 0
        self._fps = 0.0
        self._last_fps_time = time.time()
        self._initialized = True

        self._setup_hsv_ranges()

    def _setup_hsv_ranges(self):
        cfg = config.red_detection
        self._lower_red1 = np.array([cfg.red1_h_min, cfg.red1_s_min, cfg.red1_v_min])
        self._upper_red1 = np.array([cfg.red1_h_max, 255, 255])
        self._lower_red2 = np.array([cfg.red2_h_min, cfg.red2_s_min, cfg.red2_v_min])
        self._upper_red2 = np.array([cfg.red2_h_max, 255, 255])
        self._min_area = cfg.min_area

    def start(self) -> bool:
        if self._running:
            return True

        try:
            if PICAMERA_AVAILABLE:
                self._camera = Picamera2()
                cam_config = self._camera.create_preview_configuration(
                    main={"size": (config.camera.width, config.camera.height)}
                )
                self._camera.configure(cam_config)
                self._camera.start()
                time.sleep(2)
                logger.info(f"PiCamera başlatıldı: {config.camera.width}x{config.camera.height}")
            else:
                logger.info("Simülasyon modu: PiCamera yok")

            self._running = True
            return True

        except Exception as e:
            logger.error(f"Kamera başlatma hatası: {e}")
            return False

    def stop(self):
        self._running = False
        if self._camera:
            try:
                self._camera.stop()
            except:
                pass
            self._camera = None
        logger.info("Kamera durduruldu")

    def capture_frame(self) -> Optional[np.ndarray]:
        if not self._running:
            return None

        try:
            if self._camera and PICAMERA_AVAILABLE:
                frame = self._camera.capture_array()
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            else:
                frame = self._generate_test_frame()

            with self._frame_lock:
                self._current_frame = frame

            self._update_fps()
            return frame

        except Exception as e:
            logger.error(f"Frame yakalama hatası: {e}")
            return None

    def _generate_test_frame(self) -> np.ndarray:
        frame = np.zeros((config.camera.height, config.camera.width, 3), dtype=np.uint8)
        frame[:] = (50, 50, 50)

        cv2.putText(
            frame, "SIMULASYON MODU",
            (config.camera.width // 2 - 100, config.camera.height // 2),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2
        )
        cv2.putText(
            frame, "PiCamera bulunamadi",
            (config.camera.width // 2 - 90, config.camera.height // 2 + 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1
        )

        return frame

    def _update_fps(self):
        self._frame_count += 1
        current_time = time.time()
        elapsed = current_time - self._last_fps_time

        if elapsed >= 1.0:
            self._fps = self._frame_count / elapsed
            self._frame_count = 0
            self._last_fps_time = current_time

    def detect_red(self, frame: np.ndarray) -> Tuple[np.ndarray, DetectionResult]:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        mask_red1 = cv2.inRange(hsv, self._lower_red1, self._upper_red1)
        mask_red2 = cv2.inRange(hsv, self._lower_red2, self._upper_red2)
        mask_red = mask_red1 + mask_red2

        mask_red = cv2.erode(mask_red, None, iterations=2)
        mask_red = cv2.dilate(mask_red, None, iterations=2)

        contours, _ = cv2.findContours(
            mask_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        result = DetectionResult(False)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > self._min_area:
                x, y, w, h = cv2.boundingRect(cnt)
                result = DetectionResult(
                    red_detected=True,
                    area=int(area),
                    x=x, y=y, width=w, height=h
                )

                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 3)
                cv2.putText(
                    frame, "KIRMIZI - DURDU",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2
                )
                break

        self._detection_result = result
        return frame, result

    def generate_frames(self, with_detection: bool = True) -> Generator[bytes, None, None]:
        while self._running:
            frame = self.capture_frame()
            if frame is None:
                time.sleep(0.1)
                continue

            if with_detection:
                frame, detection = self.detect_red(frame)

                status = "DURDU" if detection.red_detected else "CALISIYOR"
                color = (0, 0, 255) if detection.red_detected else (0, 255, 0)
                cv2.putText(
                    frame, f"Durum: {status}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2
                )

            cv2.putText(
                frame, f"FPS: {self._fps:.1f}",
                (10, config.camera.height - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (128, 128, 128), 1
            )

            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frame_bytes = buffer.tobytes()

            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
            )

            time.sleep(1 / config.camera.fps)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def last_detection(self) -> DetectionResult:
        return self._detection_result

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "fps": round(self._fps, 1),
            "width": config.camera.width,
            "height": config.camera.height,
            "picamera_available": PICAMERA_AVAILABLE,
            "red_detected": self._detection_result.red_detected
        }


camera_manager = CameraManager()
