#!/usr/bin/env python3
"""
Vision Line Follower - Seri Port Yönetimi v2.2
Gelişmiş heartbeat, loglama ve komut geçmişi
"""

import os
import time
import threading
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Dict, Any
from collections import deque
from datetime import datetime

import serial
import serial.tools.list_ports

from .config import config

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class CommandResponse:
    """Komut yanıtı"""
    success: bool
    command: str
    response: str
    error: Optional[str] = None
    duration_ms: float = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class CommandLogEntry:
    """Komut log kaydı"""
    timestamp: str
    command: str
    response: str
    success: bool
    duration_ms: float


class SerialManager:
    """Singleton seri port yöneticisi"""

    _instance: Optional['SerialManager'] = None
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

        self._serial: Optional[serial.Serial] = None
        self._state = ConnectionState.DISCONNECTED
        self._serial_lock = threading.Lock()
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_running = False
        self._consecutive_failures = 0
        self._callbacks: List[Callable[[ConnectionState], None]] = []
        self._last_heartbeat: float = 0
        self._current_port: Optional[str] = None
        self._firmware_version: Optional[str] = None

        # Komut geçmişi
        self._command_history: deque = deque(maxlen=200)
        self._command_count = 0
        self._error_count = 0

        # İstatistikler
        self._connect_time: Optional[float] = None
        self._total_bytes_sent = 0
        self._total_bytes_received = 0

        self._initialized = True
        logger.info("SerialManager başlatıldı")

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == ConnectionState.CONNECTED

    @property
    def current_port(self) -> Optional[str]:
        return self._current_port

    @property
    def firmware_version(self) -> Optional[str]:
        return self._firmware_version

    def on_state_change(self, callback: Callable[[ConnectionState], None]):
        """Durum değişikliği callback'i ekle"""
        self._callbacks.append(callback)

    def _notify_state_change(self, new_state: ConnectionState):
        """Durum değişikliğini bildir"""
        if self._state != new_state:
            old_state = self._state
            self._state = new_state
            logger.info(f"Bağlantı durumu: {old_state.value} -> {new_state.value}")

            for callback in self._callbacks:
                try:
                    callback(new_state)
                except Exception as e:
                    logger.error(f"Callback hatası: {e}")

    def list_ports(self) -> List[Dict[str, str]]:
        """Mevcut seri portları listele"""
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                "device": port.device,
                "description": port.description,
                "hwid": port.hwid,
                "manufacturer": port.manufacturer or "Bilinmiyor"
            })
        return ports

    def find_arduino(self) -> Optional[str]:
        """Arduino'yu otomatik bul"""
        # Önce sistem portlarını kontrol et
        for port_info in serial.tools.list_ports.comports():
            desc = (port_info.description or "").lower()
            mfr = (port_info.manufacturer or "").lower()

            if any(x in desc or x in mfr for x in ['arduino', 'ch340', 'cp210', 'ftdi', 'usb serial']):
                logger.info(f"Arduino bulundu (otomatik): {port_info.device} - {port_info.description}")
                if self._test_port(port_info.device):
                    return port_info.device

        # Bilinen portları dene
        for port in config.serial.possible_ports:
            if self._test_port(port):
                return port

        return None

    def _test_port(self, port: str) -> bool:
        """Port üzerinde Arduino olup olmadığını test et"""
        try:
            # Linux'ta port var mı kontrol et
            if not port.startswith('COM') and not os.path.exists(port):
                return False

            logger.debug(f"Port test ediliyor: {port}")

            test_serial = serial.Serial(port, config.serial.baud_rate, timeout=3)
            time.sleep(2.5)  # Arduino reset süresi

            test_serial.reset_input_buffer()
            test_serial.reset_output_buffer()
            test_serial.write(b"PING\n")
            time.sleep(0.5)

            response = ""
            start = time.time()
            while time.time() - start < 2:
                if test_serial.in_waiting > 0:
                    response += test_serial.readline().decode(errors='ignore')
                    if "PONG" in response:
                        break
                time.sleep(0.05)

            test_serial.close()

            if "PONG" in response:
                logger.info(f"Arduino doğrulandı: {port}")
                return True

        except Exception as e:
            logger.debug(f"Port {port} test hatası: {e}")

        return False

    def connect(self, port: Optional[str] = None) -> bool:
        """Arduino'ya bağlan"""
        with self._serial_lock:
            if self._serial and self._serial.is_open:
                logger.warning("Zaten bağlı, önce bağlantı kesiliyor")
                self._close_serial()

            self._notify_state_change(ConnectionState.CONNECTING)

            if port is None:
                port = self.find_arduino()

            if port is None:
                logger.error("Arduino bulunamadı")
                self._notify_state_change(ConnectionState.DISCONNECTED)
                return False

            try:
                logger.info(f"Bağlanılıyor: {port} @ {config.serial.baud_rate} baud")

                self._serial = serial.Serial(
                    port,
                    config.serial.baud_rate,
                    timeout=config.serial.timeout
                )
                time.sleep(2.5)  # Arduino reset

                # Bufferları temizle
                self._serial.reset_input_buffer()
                self._serial.reset_output_buffer()

                # Bağlantı kontrolü
                result = self._send_raw("PING", timeout=2)
                if "PONG" not in result:
                    raise Exception(f"Arduino yanıt vermedi: {result}")

                # Firmware versiyonu al
                version_result = self._send_raw("VERSION", timeout=2)
                if "VERSION:" in version_result:
                    self._firmware_version = version_result.split("VERSION:")[-1].strip()
                    logger.info(f"Firmware: {self._firmware_version}")

                self._current_port = port
                self._connect_time = time.time()
                self._consecutive_failures = 0
                self._notify_state_change(ConnectionState.CONNECTED)

                logger.info(f"Arduino bağlantısı başarılı: {port}")
                return True

            except Exception as e:
                logger.error(f"Bağlantı hatası: {e}")
                self._close_serial()
                self._notify_state_change(ConnectionState.ERROR)
                return False

    def _close_serial(self):
        """Seri portu kapat"""
        if self._serial:
            try:
                self._serial.close()
            except Exception as e:
                logger.debug(f"Port kapatma hatası: {e}")
            finally:
                self._serial = None

    def disconnect(self):
        """Bağlantıyı kes"""
        self.stop_heartbeat()

        with self._serial_lock:
            if self._serial and self._serial.is_open:
                try:
                    # Robot durdur
                    self._send_raw("STOP", timeout=1)
                except:
                    pass

                self._close_serial()

            self._current_port = None
            self._firmware_version = None
            self._notify_state_change(ConnectionState.DISCONNECTED)
            logger.info("Bağlantı kesildi")

    def _send_raw(self, command: str, timeout: float = 1.0) -> str:
        """Ham komut gönder (lock olmadan, iç kullanım)"""
        if not self._serial or not self._serial.is_open:
            return ""

        try:
            cmd_bytes = f"{command}\n".encode()
            self._serial.write(cmd_bytes)
            self._total_bytes_sent += len(cmd_bytes)

            start_time = time.time()
            response_lines = []

            while time.time() - start_time < timeout:
                if self._serial.in_waiting > 0:
                    line = self._serial.readline().decode(errors='ignore').strip()
                    if line:
                        response_lines.append(line)
                        self._total_bytes_received += len(line)
                        # DEBUG satırlarını atla
                        if not line.startswith("DEBUG") and not line.startswith("ROBOT_READY"):
                            break
                time.sleep(0.01)

            return "\n".join(response_lines)

        except Exception as e:
            logger.debug(f"Raw komut hatası: {e}")
            return ""

    def send_command(self, command: str, timeout: float = 1.0) -> CommandResponse:
        """Komut gönder ve yanıt al"""
        start_time = time.time()

        with self._serial_lock:
            if not self._serial or not self._serial.is_open:
                return CommandResponse(
                    success=False,
                    command=command,
                    response="",
                    error="Bağlantı yok"
                )

            try:
                self._serial.reset_input_buffer()
                cmd_bytes = f"{command}\n".encode()
                self._serial.write(cmd_bytes)
                self._total_bytes_sent += len(cmd_bytes)

                response_lines = []
                while time.time() - start_time < timeout:
                    if self._serial.in_waiting > 0:
                        line = self._serial.readline().decode(errors='ignore').strip()
                        if line:
                            response_lines.append(line)
                            self._total_bytes_received += len(line)
                            if not line.startswith("DEBUG"):
                                break
                    time.sleep(0.01)

                duration_ms = (time.time() - start_time) * 1000
                response = "\n".join(response_lines)

                result = CommandResponse(
                    success=True,
                    command=command,
                    response=response,
                    duration_ms=duration_ms
                )

                self._log_command(result)
                self._command_count += 1

                logger.debug(f"Komut: {command} -> {response} ({duration_ms:.1f}ms)")
                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                self._error_count += 1

                result = CommandResponse(
                    success=False,
                    command=command,
                    response="",
                    error=str(e),
                    duration_ms=duration_ms
                )

                self._log_command(result)
                logger.error(f"Komut hatası: {command} - {e}")
                return result

    def _log_command(self, result: CommandResponse):
        """Komutu geçmişe ekle"""
        entry = CommandLogEntry(
            timestamp=datetime.now().strftime("%H:%M:%S.%f")[:-3],
            command=result.command,
            response=result.response[:100] if result.response else result.error or "",
            success=result.success,
            duration_ms=round(result.duration_ms, 1)
        )
        self._command_history.append(entry)

    def get_command_history(self, limit: int = 50) -> List[Dict]:
        """Komut geçmişini al"""
        history = list(self._command_history)[-limit:]
        return [
            {
                "timestamp": h.timestamp,
                "command": h.command,
                "response": h.response,
                "success": h.success,
                "duration_ms": h.duration_ms
            }
            for h in reversed(history)
        ]

    # Heartbeat
    def _heartbeat_loop(self):
        """Heartbeat döngüsü"""
        while self._heartbeat_running:
            time.sleep(config.heartbeat.interval)

            if not self._heartbeat_running:
                break

            result = self.send_command("PING", timeout=config.heartbeat.timeout)

            if result.success and "PONG" in result.response:
                self._consecutive_failures = 0
                self._last_heartbeat = time.time()

                if self._state == ConnectionState.RECONNECTING:
                    self._notify_state_change(ConnectionState.CONNECTED)
            else:
                self._consecutive_failures += 1
                logger.warning(f"Heartbeat başarısız ({self._consecutive_failures}/{config.heartbeat.max_failures})")

                if self._consecutive_failures >= config.heartbeat.max_failures:
                    logger.error("Bağlantı koptu, yeniden bağlanılıyor...")
                    self._notify_state_change(ConnectionState.RECONNECTING)
                    self._attempt_reconnect()

    def _attempt_reconnect(self):
        """Yeniden bağlanma denemesi"""
        with self._serial_lock:
            self._close_serial()

        for attempt in range(3):
            if not self._heartbeat_running:
                break

            logger.info(f"Yeniden bağlanma denemesi {attempt + 1}/3")
            time.sleep(2)

            if self.connect():
                self._consecutive_failures = 0
                return

        logger.error("Yeniden bağlanma başarısız")
        self._notify_state_change(ConnectionState.DISCONNECTED)

    def start_heartbeat(self):
        """Heartbeat'i başlat"""
        if self._heartbeat_running:
            return

        self._heartbeat_running = True
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        logger.info("Heartbeat başlatıldı")

    def stop_heartbeat(self):
        """Heartbeat'i durdur"""
        self._heartbeat_running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=3)
            self._heartbeat_thread = None
        logger.info("Heartbeat durduruldu")

    def get_status(self) -> Dict[str, Any]:
        """Detaylı durum bilgisi"""
        uptime = 0
        if self._connect_time and self.is_connected:
            uptime = time.time() - self._connect_time

        return {
            "state": self._state.value,
            "connected": self.is_connected,
            "port": self._current_port,
            "firmware_version": self._firmware_version,
            "baud_rate": config.serial.baud_rate,
            "last_heartbeat": self._last_heartbeat,
            "consecutive_failures": self._consecutive_failures,
            "heartbeat_running": self._heartbeat_running,
            "uptime_seconds": round(uptime, 1),
            "command_count": self._command_count,
            "error_count": self._error_count,
            "bytes_sent": self._total_bytes_sent,
            "bytes_received": self._total_bytes_received
        }


serial_manager = SerialManager()
