#!/usr/bin/env python3
"""
Vision Line Follower - Kamera Yönetimi v2.1
Dinamik HSV kalibrasyonu ve gelişmiş görüntü işleme
"""

import time
import threading
import logging
from typing import Optional, Generator, Tuple, Dict, Any
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime

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
    """Algılama sonucu"""
    red_detected: bool = False
    area: int = 0
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    center_x: int = 0
    center_y: int = 0
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class CameraStats:
    """Kamera istatistikleri"""
    fps: float = 0.0
    frame_count: int = 0
    detection_count: int = 0
    last_detection_time: Optional[float] = None
    uptime: float = 0.0
    errors: int = 0


class CameraManager:
    """Singleton kamera yöneticisi"""

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
        self._detection_result = DetectionResult()
        self._stats = CameraStats()
        self._start_time: Optional[float] = None

        # FPS hesaplama
        self._frame_times: deque = deque(maxlen=30)
        self._last_frame_time = time.time()

        # Log geçmişi
        self._detection_log: deque = deque(maxlen=100)

        self._initialized = True
        logger.info("CameraManager başlatıldı")

    def start(self) -> bool:
        """Kamerayı başlat"""
        if self._running:
            logger.warning("Kamera zaten çalışıyor")
            return True

        try:
            if PICAMERA_AVAILABLE:
                self._camera = Picamera2()
                cam_config = self._camera.create_preview_configuration(
                    main={"size": (config.camera.width, config.camera.height)}
                )
                self._camera.configure(cam_config)
                self._camera.start()
                time.sleep(2)  # Stabilizasyon
                logger.info(f"PiCamera başlatıldı: {config.camera.width}x{config.camera.height}")
            else:
                logger.info("Simülasyon modu: PiCamera yok")

            self._running = True
            self._start_time = time.time()
            self._stats = CameraStats()
            return True

        except Exception as e:
            logger.error(f"Kamera başlatma hatası: {e}", exc_info=True)
            self._stats.errors += 1
            return False

    def stop(self):
        """Kamerayı durdur"""
        self._running = False
        if self._camera:
            try:
                self._camera.stop()
                logger.info("Kamera durduruldu")
            except Exception as e:
                logger.error(f"Kamera durdurma hatası: {e}")
            finally:
                self._camera = None

    def restart(self) -> bool:
        """Kamerayı yeniden başlat"""
        logger.info("Kamera yeniden başlatılıyor...")
        self.stop()
        time.sleep(1)
        return self.start()

    def capture_frame(self) -> Optional[np.ndarray]:
        """Tek kare yakala"""
        if not self._running:
            return None

        try:
            if self._camera and PICAMERA_AVAILABLE:
                frame = self._camera.capture_array()
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            else:
                frame = self._generate_test_frame()

            with self._frame_lock:
                self._current_frame = frame.copy()

            self._update_fps()
            self._stats.frame_count += 1
            return frame

        except Exception as e:
            logger.error(f"Frame yakalama hatası: {e}")
            self._stats.errors += 1
            return None

    def _generate_test_frame(self) -> np.ndarray:
        """Test frame'i oluştur (simülasyon modu)"""
        frame = np.zeros((config.camera.height, config.camera.width, 3), dtype=np.uint8)
        frame[:] = (40, 40, 50)

        # Grid çiz
        for i in range(0, config.camera.width, 50):
            cv2.line(frame, (i, 0), (i, config.camera.height), (60, 60, 70), 1)
        for i in range(0, config.camera.height, 50):
            cv2.line(frame, (0, i), (config.camera.width, i), (60, 60, 70), 1)

        # Başlık
        cv2.putText(
            frame, "SIMULASYON MODU",
            (config.camera.width // 2 - 120, config.camera.height // 2 - 20),
            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 200, 255), 2
        )
        cv2.putText(
            frame, "PiCamera bulunamadi - Test goruntusu",
            (config.camera.width // 2 - 180, config.camera.height // 2 + 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1
        )

        # Animasyonlu test objesi
        t = time.time() % 10
        test_x = int(100 + t * 40)
        test_y = config.camera.height // 2 + 80

        # Kırmızı test dikdörtgeni
        cv2.rectangle(frame, (test_x, test_y), (test_x + 60, test_y + 40), (0, 0, 200), -1)
        cv2.putText(frame, "TEST", (test_x + 5, test_y + 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        return frame

    def _update_fps(self):
        """FPS hesapla"""
        current_time = time.time()
        self._frame_times.append(current_time)

        if len(self._frame_times) >= 2:
            elapsed = self._frame_times[-1] - self._frame_times[0]
            if elapsed > 0:
                self._stats.fps = (len(self._frame_times) - 1) / elapsed

    def detect_color(self, frame: np.ndarray) -> Tuple[np.ndarray, DetectionResult]:
        """Kırmızı renk algılama (dinamik HSV değerleri ile)"""
        result = DetectionResult()

        if not config.color_detection.enabled:
            return frame, result

        try:
            # Blur uygula
            blur_size = config.color_detection.blur_kernel
            if blur_size > 0 and blur_size % 2 == 1:
                blurred = cv2.GaussianBlur(frame, (blur_size, blur_size), 0)
            else:
                blurred = frame

            # HSV dönüşümü
            hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

            # Dinamik HSV değerlerini al
            lower1, upper1, lower2, upper2 = config.get_hsv_arrays()

            # Maskeleri oluştur
            mask1 = cv2.inRange(hsv, lower1, upper1)
            mask2 = cv2.inRange(hsv, lower2, upper2)
            mask = mask1 + mask2

            # Morfolojik işlemler
            erode_iter = config.color_detection.erode_iterations
            dilate_iter = config.color_detection.dilate_iterations

            if erode_iter > 0:
                mask = cv2.erode(mask, None, iterations=erode_iter)
            if dilate_iter > 0:
                mask = cv2.dilate(mask, None, iterations=dilate_iter)

            # Konturları bul
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # En büyük kırmızı alanı bul
            min_area = config.color_detection.min_area
            largest_contour = None
            largest_area = 0

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > min_area and area > largest_area:
                    largest_area = area
                    largest_contour = cnt

            if largest_contour is not None:
                x, y, w, h = cv2.boundingRect(largest_contour)
                center_x = x + w // 2
                center_y = y + h // 2

                # Güven skoru (alan / min_area oranı)
                confidence = min(1.0, largest_area / (min_area * 10))

                result = DetectionResult(
                    red_detected=True,
                    area=int(largest_area),
                    x=x, y=y, width=w, height=h,
                    center_x=center_x, center_y=center_y,
                    confidence=confidence,
                    timestamp=time.time()
                )

                # Görsel işaretleme
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 3)
                cv2.circle(frame, (center_x, center_y), 5, (0, 255, 255), -1)

                label = f"KIRMIZI [{int(largest_area)}px] {confidence*100:.0f}%"
                cv2.putText(frame, label, (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                # İstatistik güncelle
                self._stats.detection_count += 1
                self._stats.last_detection_time = time.time()

                # Log'a ekle
                self._log_detection(result)

            self._detection_result = result

        except Exception as e:
            logger.error(f"Renk algılama hatası: {e}", exc_info=True)
            self._stats.errors += 1

        return frame, result

    def _log_detection(self, result: DetectionResult):
        """Algılamayı log'a kaydet"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "area": result.area,
            "position": f"({result.center_x}, {result.center_y})",
            "confidence": f"{result.confidence*100:.1f}%"
        }
        self._detection_log.append(log_entry)

    def generate_frames(self, with_detection: bool = True,
                        show_overlay: bool = True) -> Generator[bytes, None, None]:
        """MJPEG video stream oluştur"""
        while self._running:
            frame = self.capture_frame()
            if frame is None:
                time.sleep(0.1)
                continue

            if with_detection:
                frame, detection = self.detect_color(frame)

            if show_overlay:
                frame = self._add_overlay(frame, detection if with_detection else None)

            # JPEG encode
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, config.camera.jpeg_quality]
            _, buffer = cv2.imencode('.jpg', frame, encode_params)
            frame_bytes = buffer.tobytes()

            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
            )

            # FPS limit
            time.sleep(1 / config.camera.fps)

    def _add_overlay(self, frame: np.ndarray,
                     detection: Optional[DetectionResult] = None) -> np.ndarray:
        """Bilgi overlay'i ekle"""
        height, width = frame.shape[:2]

        # Üst bilgi barı
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (width, 40), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)

        # Durum
        if detection and detection.red_detected:
            status = "DURDU - KIRMIZI ALGILANDI"
            color = (0, 0, 255)
        else:
            status = "AKTIF"
            color = (0, 255, 0)

        cv2.putText(frame, f"Durum: {status}", (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # FPS
        cv2.putText(frame, f"FPS: {self._stats.fps:.1f}", (width - 100, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        # Alt bilgi barı
        cv2.rectangle(frame, (0, height - 30), (width, height), (0, 0, 0), -1)

        # Algılama bilgisi
        if config.color_detection.enabled:
            det_text = f"Renk Algilama: ACIK | Min Alan: {config.color_detection.min_area}"
        else:
            det_text = "Renk Algilama: KAPALI"

        cv2.putText(frame, det_text, (10, height - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)

        # Versiyon
        cv2.putText(frame, "v2.1", (width - 40, height - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)

        return frame

    def capture_snapshot(self) -> Optional[bytes]:
        """Anlık görüntü al (JPEG)"""
        frame = self.capture_frame()
        if frame is None:
            return None

        frame, _ = self.detect_color(frame)
        frame = self._add_overlay(frame, self._detection_result)

        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        return buffer.tobytes()

    def get_color_histogram(self, frame: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """HSV histogram analizi (kalibrasyon için)"""
        if frame is None:
            with self._frame_lock:
                if self._current_frame is None:
                    return {"error": "Frame yok"}
                frame = self._current_frame.copy()

        try:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # Merkez bölge
            h, w = frame.shape[:2]
            roi = hsv[h//4:3*h//4, w//4:3*w//4]

            # Histogram hesapla
            h_hist = cv2.calcHist([roi], [0], None, [180], [0, 180]).flatten()
            s_hist = cv2.calcHist([roi], [1], None, [256], [0, 256]).flatten()
            v_hist = cv2.calcHist([roi], [2], None, [256], [0, 256]).flatten()

            # Normalize et
            h_hist = (h_hist / h_hist.max() * 100).astype(int).tolist()
            s_hist = (s_hist / s_hist.max() * 100).astype(int).tolist()
            v_hist = (v_hist / v_hist.max() * 100).astype(int).tolist()

            # Dominant değerler
            h_dominant = int(np.argmax(cv2.calcHist([roi], [0], None, [180], [0, 180])))
            s_dominant = int(np.argmax(cv2.calcHist([roi], [1], None, [256], [0, 256])))
            v_dominant = int(np.argmax(cv2.calcHist([roi], [2], None, [256], [0, 256])))

            return {
                "h_histogram": h_hist[::10],  # 18 değer
                "s_histogram": s_hist[::16],  # 16 değer
                "v_histogram": v_hist[::16],  # 16 değer
                "dominant": {
                    "h": h_dominant,
                    "s": s_dominant,
                    "v": v_dominant
                },
                "timestamp": time.time()
            }

        except Exception as e:
            logger.error(f"Histogram hatası: {e}")
            return {"error": str(e)}

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def fps(self) -> float:
        return self._stats.fps

    @property
    def last_detection(self) -> DetectionResult:
        return self._detection_result

    @property
    def detection_log(self) -> list:
        return list(self._detection_log)

    def get_status(self) -> Dict[str, Any]:
        """Detaylı kamera durumu"""
        uptime = 0
        if self._start_time:
            uptime = time.time() - self._start_time

        return {
            "running": self._running,
            "fps": round(self._stats.fps, 1),
            "width": config.camera.width,
            "height": config.camera.height,
            "picamera_available": PICAMERA_AVAILABLE,
            "simulation_mode": not PICAMERA_AVAILABLE,
            "detection_enabled": config.color_detection.enabled,
            "auto_stop_enabled": config.color_detection.auto_stop,
            "red_detected": self._detection_result.red_detected,
            "frame_count": self._stats.frame_count,
            "detection_count": self._stats.detection_count,
            "last_detection_time": self._stats.last_detection_time,
            "uptime_seconds": round(uptime, 1),
            "errors": self._stats.errors,
            "hsv_config": config.color_detection.to_dict()
        }


camera_manager = CameraManager()
