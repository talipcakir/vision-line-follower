#!/usr/bin/env python3
"""
Vision Line Follower - Seri Port Yönetimi ve Heartbeat
"""

import os
import time
import threading
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable, List

import serial

from .config import config

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"


@dataclass
class CommandResponse:
    success: bool
    response: str
    error: Optional[str] = None


class SerialManager:
    def __init__(self):
        self._serial: Optional[serial.Serial] = None
        self._state = ConnectionState.DISCONNECTED
        self._lock = threading.Lock()
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_running = False
        self._consecutive_failures = 0
        self._callbacks: List[Callable[[ConnectionState], None]] = []
        self._last_heartbeat: float = 0
        self._current_port: Optional[str] = None

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == ConnectionState.CONNECTED

    @property
    def current_port(self) -> Optional[str]:
        return self._current_port

    def on_state_change(self, callback: Callable[[ConnectionState], None]):
        self._callbacks.append(callback)

    def _notify_state_change(self, new_state: ConnectionState):
        if self._state != new_state:
            old_state = self._state
            self._state = new_state
            logger.info(f"Bağlantı durumu: {old_state.value} -> {new_state.value}")
            for callback in self._callbacks:
                try:
                    callback(new_state)
                except Exception as e:
                    logger.error(f"Callback hatası: {e}")

    def find_arduino(self) -> Optional[str]:
        for port in config.serial.possible_ports:
            try:
                if not os.path.exists(port) and not port.startswith('COM'):
                    continue

                logger.debug(f"Port deneniyor: {port}")
                test_serial = serial.Serial(port, config.serial.baud_rate, timeout=2)
                time.sleep(2)

                test_serial.reset_input_buffer()
                test_serial.reset_output_buffer()
                test_serial.write(b"PING\n")
                time.sleep(0.5)

                response = ""
                while test_serial.in_waiting > 0:
                    response += test_serial.readline().decode(errors='ignore')

                test_serial.close()

                if "PONG" in response:
                    logger.info(f"Arduino bulundu: {port}")
                    return port

            except Exception as e:
                logger.debug(f"Port {port} - Hata: {e}")

        return None

    def connect(self, port: Optional[str] = None) -> bool:
        with self._lock:
            if self._serial and self._serial.is_open:
                return True

            self._notify_state_change(ConnectionState.CONNECTING)

            if port is None:
                port = self.find_arduino()

            if port is None:
                logger.error("Arduino bulunamadı")
                self._notify_state_change(ConnectionState.DISCONNECTED)
                return False

            try:
                self._serial = serial.Serial(
                    port,
                    config.serial.baud_rate,
                    timeout=config.serial.timeout
                )
                time.sleep(2)
                self._current_port = port
                self._consecutive_failures = 0
                self._notify_state_change(ConnectionState.CONNECTED)
                logger.info(f"Arduino bağlantısı başarılı: {port}")
                return True

            except Exception as e:
                logger.error(f"Bağlantı hatası: {e}")
                self._serial = None
                self._notify_state_change(ConnectionState.DISCONNECTED)
                return False

    def disconnect(self):
        self.stop_heartbeat()
        with self._lock:
            if self._serial and self._serial.is_open:
                try:
                    self._serial.close()
                except Exception as e:
                    logger.error(f"Kapatma hatası: {e}")
            self._serial = None
            self._current_port = None
            self._notify_state_change(ConnectionState.DISCONNECTED)

    def send_command(self, command: str, timeout: float = 1.0) -> CommandResponse:
        with self._lock:
            if not self._serial or not self._serial.is_open:
                return CommandResponse(False, "", "Bağlantı yok")

            try:
                self._serial.reset_input_buffer()
                self._serial.write(f"{command}\n".encode())

                start_time = time.time()
                response_lines = []

                while time.time() - start_time < timeout:
                    if self._serial.in_waiting > 0:
                        line = self._serial.readline().decode(errors='ignore').strip()
                        if line:
                            response_lines.append(line)
                            if not line.startswith("DEBUG"):
                                break
                    time.sleep(0.01)

                response = "\n".join(response_lines)
                logger.debug(f"Komut: {command} -> Yanıt: {response}")
                return CommandResponse(True, response)

            except Exception as e:
                logger.error(f"Komut gönderme hatası: {e}")
                return CommandResponse(False, "", str(e))

    def _heartbeat_loop(self):
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
        with self._lock:
            if self._serial:
                try:
                    self._serial.close()
                except:
                    pass
                self._serial = None

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
        if self._heartbeat_running:
            return

        self._heartbeat_running = True
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        logger.info("Heartbeat başlatıldı")

    def stop_heartbeat(self):
        self._heartbeat_running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=3)
            self._heartbeat_thread = None
        logger.info("Heartbeat durduruldu")

    def get_status(self) -> dict:
        return {
            "state": self._state.value,
            "connected": self.is_connected,
            "port": self._current_port,
            "last_heartbeat": self._last_heartbeat,
            "consecutive_failures": self._consecutive_failures
        }


serial_manager = SerialManager()
