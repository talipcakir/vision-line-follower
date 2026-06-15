#!/usr/bin/env python3
"""
Vision Line Follower - Kamera Yönetimi v2.2
Dinamik HSV kalibrasyonu, çoklu kamera desteği ve gelişmiş görüntü işleme
"""

import time
import threading
import logging
import os
from typing import Optional, Generator, Tuple, Dict, Any, List, Callable
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime

import cv2
import numpy as np

from .config import config

logger = logging.getLogger(__name__)

# PiCamera2 kontrolü
try:
    from picamera2 import Picamera2
    PICAMERA_AVAILABLE = True
except ImportError:
    PICAMERA_AVAILABLE = False
    logger.info("picamera2 bulunamadı, USB kamera veya simülasyon modu kullanılacak")


def find_available_cameras() -> List[Dict[str, Any]]:
    """Sistemdeki tüm kameraları bul"""
    cameras = []

    # 1. PiCamera kontrolü - /dev/video0 genelde CSI kamera
    if PICAMERA_AVAILABLE:
        # CSI kamera genelde mevcut
        cameras.append({
            "index": -1,
            "type": "picamera",
            "name": "Raspberry Pi Camera (CSI)",
            "available": True
        })
        logger.info("PiCamera modu aktif")

    # 2. USB/Video4Linux kameraları kontrol et (CSI kamera da /dev/video0 olabilir)
    for i in range(10):
        device_path = f"/dev/video{i}"
        if os.path.exists(device_path):
            # PiCamera varsa /dev/video0'ı atla (CSI olabilir)
            if PICAMERA_AVAILABLE and i == 0:
                continue
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    ret, frame = cap.read()
                    cap.release()
                    if ret and frame is not None:
                        cameras.append({
                            "index": i,
                            "type": "usb",
                            "name": f"USB Camera /dev/video{i}",
                            "device": device_path,
                            "available": True
                        })
                        logger.info(f"USB kamera bulundu: /dev/video{i}")
            except Exception as e:
                logger.debug(f"Kamera {i} kontrol hatası: {e}")

    if not cameras:
        logger.warning("Hiç kamera bulunamadı, simülasyon modu kullanılacak")

    return cameras


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


# Callback tipi
DetectionCallback = Callable[[DetectionResult], None]


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
        self._camera_type: Optional[str] = None  # "picamera", "usb", "simulation"
        self._camera_index: int = -1
        self._usb_capture: Optional[cv2.VideoCapture] = None
        self._running = False
        self._frame_lock = threading.Lock()
        self._current_frame: Optional[np.ndarray] = None
        self._detection_result = DetectionResult()
        self._stats = CameraStats()
        self._start_time: Optional[float] = None
        self._available_cameras: List[Dict] = []

        # FPS hesaplama
        self._frame_times: deque = deque(maxlen=30)
        self._last_frame_time = time.time()

        # Log geçmişi
        self._detection_log: deque = deque(maxlen=100)

        # Algılama callback'leri
        self._detection_callbacks: List[DetectionCallback] = []
        self._last_callback_triggered: float = 0
        self._callback_cooldown: float = 1.0  # 1 saniye cooldown

        # Sürekli algılama thread'i
        self._detection_thread: Optional[threading.Thread] = None
        self._detection_running = False

        self._initialized = True
        logger.info("CameraManager başlatıldı")

    def on_detection(self, callback: DetectionCallback):
        """Kırmızı algılandığında çağrılacak callback ekle"""
        self._detection_callbacks.append(callback)
        logger.info(f"Algılama callback'i eklendi, toplam: {len(self._detection_callbacks)}")

    def start_detection_loop(self):
        """Sürekli kırmızı algılama döngüsünü başlat (web sayfası açık olmasa da çalışır)"""
        if self._detection_running:
            return

        self._detection_running = True
        self._detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
        self._detection_thread.start()
        logger.info("Kırmızı algılama döngüsü başlatıldı")

    def stop_detection_loop(self):
        """Algılama döngüsünü durdur"""
        self._detection_running = False
        if self._detection_thread:
            self._detection_thread.join(timeout=2)
            self._detection_thread = None
        logger.info("Kırmızı algılama döngüsü durduruldu")

    def _detection_loop(self):
        """Arka planda sürekli kırmızı algılama yap"""
        logger.info("Algılama thread'i çalışıyor...")

        while self._detection_running:
            if not self._running:
                time.sleep(0.5)
                continue

            if not config.color_detection.enabled:
                time.sleep(0.5)
                continue

            try:
                frame = self.capture_frame()
                if frame is not None:
                    _, result = self.detect_color(frame)

            except Exception as e:
                logger.error(f"Algılama döngüsü hatası: {e}")

            time.sleep(0.1)  # 10 FPS algılama

    def _trigger_detection_callbacks(self, result: DetectionResult):
        """Tüm callback'leri çağır (cooldown ile)"""
        current_time = time.time()
        if current_time - self._last_callback_triggered < self._callback_cooldown:
            return

        self._last_callback_triggered = current_time

        for callback in self._detection_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Algılama callback hatası: {e}")

    def start(self, camera_index: Optional[int] = None) -> bool:
        """Kamerayı başlat - otomatik olarak mevcut kameraları dener"""
        if self._running:
            logger.warning("Kamera zaten çalışıyor")
            return True

        # Mevcut kameraları bul
        self._available_cameras = find_available_cameras()
        logger.info(f"Bulunan kameralar: {len(self._available_cameras)}")

        # Belirli bir kamera istendiyse
        if camera_index is not None:
            return self._start_camera_by_index(camera_index)

        # Sırayla dene
        for cam_info in self._available_cameras:
            if self._try_start_camera(cam_info):
                return True

        # Hiçbir kamera bulunamadı
        logger.warning("Hiçbir kamera başlatılamadı")
        self._camera_type = None
        self._running = False
        return False

    def _start_camera_by_index(self, index: int) -> bool:
        """Belirli indeksteki kamerayı başlat"""
        for cam_info in self._available_cameras:
            if cam_info["index"] == index:
                return self._try_start_camera(cam_info)
        return False

    def _try_start_camera(self, cam_info: Dict) -> bool:
        """Belirli bir kamerayı başlatmayı dene"""
        try:
            if cam_info["type"] == "picamera":
                logger.info("PiCamera başlatılıyor...")
                self._camera = Picamera2()
                cam_config = self._camera.create_preview_configuration(
                    main={"size": (config.camera.width, config.camera.height), "format": "RGB888"}
                )
                self._camera.configure(cam_config)
                self._camera.start()
                time.sleep(2)

                # Test frame al
                test_frame = self._camera.capture_array()
                if test_frame is None:
                    raise Exception("PiCamera'dan frame alınamadı")

                self._camera_type = "picamera"
                self._camera_index = -1
                logger.info(f"PiCamera başlatıldı: {config.camera.width}x{config.camera.height}")

            elif cam_info["type"] == "usb":
                logger.info(f"USB kamera başlatılıyor: {cam_info['index']}")
                self._usb_capture = cv2.VideoCapture(cam_info["index"])
                self._usb_capture.set(cv2.CAP_PROP_FRAME_WIDTH, config.camera.width)
                self._usb_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, config.camera.height)
                self._usb_capture.set(cv2.CAP_PROP_FPS, config.camera.fps)

                if not self._usb_capture.isOpened():
                    raise Exception("USB kamera açılamadı")

                ret, frame = self._usb_capture.read()
                if not ret or frame is None:
                    raise Exception("USB kameradan frame alınamadı")

                self._camera_type = "usb"
                self._camera_index = cam_info["index"]
                logger.info(f"USB kamera başlatıldı: {cam_info['name']}")

            self._running = True
            self._start_time = time.time()
            self._stats = CameraStats()
            return True

        except Exception as e:
            logger.error(f"Kamera başlatma hatası ({cam_info['name']}): {e}", exc_info=True)
            self._cleanup_camera()
            return False

    def _cleanup_camera(self):
        """Kamera kaynaklarını temizle"""
        if self._camera:
            try:
                self._camera.stop()
                self._camera.close()
            except:
                pass
            self._camera = None

        if self._usb_capture:
            try:
                self._usb_capture.release()
            except:
                pass
            self._usb_capture = None

    def stop(self):
        """Kamerayı durdur"""
        self._running = False
        self.stop_detection_loop()
        self._cleanup_camera()
        self._camera_type = None
        logger.info("Kamera durduruldu")

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
            frame = None

            if self._camera_type == "picamera" and self._camera:
                try:
                    frame = self._camera.capture_array()
                    if frame is not None:
                        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                except Exception as e:
                    logger.error(f"PiCamera frame hatası: {e}")
                    self._stats.errors += 1
                    return None

            elif self._camera_type == "usb" and self._usb_capture:
                ret, frame = self._usb_capture.read()
                if not ret or frame is None:
                    logger.warning("USB kameradan frame alınamadı")
                    self._stats.errors += 1
                    return None

            if frame is None:
                return None

            with self._frame_lock:
                self._current_frame = frame.copy()

            self._update_fps()
            self._stats.frame_count += 1
            return frame

        except Exception as e:
            logger.error(f"Frame yakalama hatası: {e}")
            self._stats.errors += 1
            return None

    def _generate_error_frame(self) -> np.ndarray:
        """Kamera yok/hata frame'i"""
        frame = np.zeros((config.camera.height, config.camera.width, 3), dtype=np.uint8)
        frame[:] = (30, 30, 30)

        cv2.putText(
            frame, "KAMERA YOK",
            (config.camera.width // 2 - 100, config.camera.height // 2 - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 200), 2
        )
        cv2.putText(
            frame, "Kamera baglantisini kontrol edin",
            (config.camera.width // 2 - 150, config.camera.height // 2 + 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1
        )

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

                # Callback'leri tetikle (auto_stop aktifse)
                if config.color_detection.auto_stop and self._detection_callbacks:
                    self._trigger_detection_callbacks(result)

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
        error_count = 0
        max_errors = 5
        error_frame_sent = False

        while True:
            # Kamera çalışmıyorsa hata frame'i gönder
            if not self._running:
                if not error_frame_sent:
                    frame = self._generate_error_frame()
                    try:
                        encode_params = [cv2.IMWRITE_JPEG_QUALITY, config.camera.jpeg_quality]
                        ret, buffer = cv2.imencode('.jpg', frame, encode_params)
                        if ret:
                            yield (
                                b'--frame\r\n'
                                b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'
                            )
                            error_frame_sent = True
                    except Exception:
                        pass
                time.sleep(1)
                continue

            error_frame_sent = False
            frame = self.capture_frame()

            if frame is None:
                error_count += 1
                if error_count > max_errors:
                    # Çok fazla hata, hata frame'i göster
                    frame = self._generate_error_frame()
                    error_count = 0
                else:
                    time.sleep(0.1)
                    continue
            else:
                error_count = 0

            try:
                if with_detection:
                    frame, detection = self.detect_color(frame)
                else:
                    detection = None

                if show_overlay:
                    frame = self._add_overlay(frame, detection)

                # JPEG encode
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, config.camera.jpeg_quality]
                ret, buffer = cv2.imencode('.jpg', frame, encode_params)

                if not ret:
                    continue

                frame_bytes = buffer.tobytes()

                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
                )

            except Exception as e:
                logger.error(f"Frame encode hatası: {e}")

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
        cv2.putText(frame, "v2.2", (width - 40, height - 10),
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

    def get_available_cameras(self) -> List[Dict]:
        """Mevcut kameraların listesi"""
        return self._available_cameras

    def get_status(self) -> Dict[str, Any]:
        """Detaylı kamera durumu"""
        uptime = 0
        if self._start_time:
            uptime = time.time() - self._start_time

        return {
            "running": self._running,
            "camera_type": self._camera_type,
            "camera_index": self._camera_index,
            "fps": round(self._stats.fps, 1),
            "width": config.camera.width,
            "height": config.camera.height,
            "picamera_available": PICAMERA_AVAILABLE,
            "camera_available": self._camera_type is not None,
            "available_cameras": len(self._available_cameras),
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
