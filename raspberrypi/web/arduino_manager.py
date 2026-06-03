#!/usr/bin/env python3
"""
Vision Line Follower - Arduino CLI Yönetimi
"""

import os
import subprocess
import logging
import shutil
from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class BoardInfo:
    detected: bool
    fqbn: Optional[str] = None
    port: Optional[str] = None
    name: Optional[str] = None
    error: Optional[str] = None


@dataclass
class SketchInfo:
    name: str
    path: str
    description: str = ""


@dataclass
class OperationResult:
    success: bool
    message: str
    output: str = ""
    error: str = ""


class ArduinoManager:
    def __init__(self):
        self._cli_path = config.arduino.cli_path
        self._fqbn = config.arduino.fqbn
        self._sketches_dir = os.path.abspath(config.arduino.sketches_dir)

    def is_cli_available(self) -> bool:
        return shutil.which(self._cli_path) is not None

    def get_cli_version(self) -> Optional[str]:
        try:
            result = subprocess.run(
                [self._cli_path, "version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.error(f"CLI versiyon hatası: {e}")
        return None

    def detect_board(self) -> BoardInfo:
        if not self.is_cli_available():
            return BoardInfo(False, error="arduino-cli bulunamadı")

        try:
            result = subprocess.run(
                [self._cli_path, "board", "list", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return BoardInfo(False, error=result.stderr)

            import json
            boards = json.loads(result.stdout)

            if not boards:
                return BoardInfo(False, error="Bağlı kart bulunamadı")

            for board in boards:
                port = board.get("port", {})
                matching = board.get("matching_boards", [])

                if matching:
                    return BoardInfo(
                        detected=True,
                        fqbn=matching[0].get("fqbn", self._fqbn),
                        port=port.get("address"),
                        name=matching[0].get("name", "Arduino")
                    )
                elif port.get("address"):
                    return BoardInfo(
                        detected=True,
                        fqbn=self._fqbn,
                        port=port.get("address"),
                        name="Arduino (varsayılan)"
                    )

            return BoardInfo(False, error="Uyumlu kart bulunamadı")

        except subprocess.TimeoutExpired:
            return BoardInfo(False, error="Zaman aşımı")
        except Exception as e:
            logger.error(f"Kart algılama hatası: {e}")
            return BoardInfo(False, error=str(e))

    def list_sketches(self) -> List[SketchInfo]:
        sketches = []

        if not os.path.exists(self._sketches_dir):
            logger.warning(f"Sketch dizini bulunamadı: {self._sketches_dir}")
            return sketches

        for item in os.listdir(self._sketches_dir):
            sketch_dir = os.path.join(self._sketches_dir, item)
            if not os.path.isdir(sketch_dir):
                continue

            ino_file = os.path.join(sketch_dir, f"{item}.ino")
            if os.path.exists(ino_file):
                description = self._extract_description(ino_file)
                sketches.append(SketchInfo(
                    name=item,
                    path=sketch_dir,
                    description=description
                ))

        test_dir = os.path.join(os.path.dirname(self._sketches_dir), "test", "arduino")
        if os.path.exists(test_dir):
            for item in os.listdir(test_dir):
                sketch_dir = os.path.join(test_dir, item)
                if not os.path.isdir(sketch_dir):
                    continue

                ino_file = os.path.join(sketch_dir, f"{item}.ino")
                if os.path.exists(ino_file):
                    description = self._extract_description(ino_file)
                    sketches.append(SketchInfo(
                        name=f"test/{item}",
                        path=sketch_dir,
                        description=f"[TEST] {description}"
                    ))

        return sketches

    def _extract_description(self, ino_path: str) -> str:
        try:
            with open(ino_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(2000)

                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith('//') and not line.startswith('//='):
                        desc = line.lstrip('/').strip()
                        if len(desc) > 10:
                            return desc[:100]
        except:
            pass
        return ""

    def compile(self, sketch_path: str) -> OperationResult:
        if not self.is_cli_available():
            return OperationResult(False, "arduino-cli bulunamadı")

        if not os.path.exists(sketch_path):
            return OperationResult(False, f"Sketch bulunamadı: {sketch_path}")

        try:
            logger.info(f"Derleniyor: {sketch_path}")

            result = subprocess.run(
                [
                    self._cli_path, "compile",
                    "--fqbn", self._fqbn,
                    sketch_path
                ],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                return OperationResult(
                    True,
                    "Derleme başarılı",
                    output=result.stdout
                )
            else:
                return OperationResult(
                    False,
                    "Derleme hatası",
                    output=result.stdout,
                    error=result.stderr
                )

        except subprocess.TimeoutExpired:
            return OperationResult(False, "Derleme zaman aşımı")
        except Exception as e:
            logger.error(f"Derleme hatası: {e}")
            return OperationResult(False, str(e))

    def upload(self, sketch_path: str, port: Optional[str] = None) -> OperationResult:
        if not self.is_cli_available():
            return OperationResult(False, "arduino-cli bulunamadı")

        if not os.path.exists(sketch_path):
            return OperationResult(False, f"Sketch bulunamadı: {sketch_path}")

        if port is None:
            board = self.detect_board()
            if not board.detected:
                return OperationResult(False, f"Kart bulunamadı: {board.error}")
            port = board.port

        try:
            logger.info(f"Yükleniyor: {sketch_path} -> {port}")

            result = subprocess.run(
                [
                    self._cli_path, "compile", "--upload",
                    "--fqbn", self._fqbn,
                    "--port", port,
                    sketch_path
                ],
                capture_output=True,
                text=True,
                timeout=config.arduino.upload_timeout
            )

            if result.returncode == 0:
                return OperationResult(
                    True,
                    f"Yükleme başarılı: {port}",
                    output=result.stdout
                )
            else:
                return OperationResult(
                    False,
                    "Yükleme hatası",
                    output=result.stdout,
                    error=result.stderr
                )

        except subprocess.TimeoutExpired:
            return OperationResult(False, "Yükleme zaman aşımı")
        except Exception as e:
            logger.error(f"Yükleme hatası: {e}")
            return OperationResult(False, str(e))

    def get_sketch_path(self, name: str) -> Optional[str]:
        for sketch in self.list_sketches():
            if sketch.name == name:
                return sketch.path
        return None

    def get_status(self) -> dict:
        cli_available = self.is_cli_available()
        return {
            "cli_available": cli_available,
            "cli_version": self.get_cli_version() if cli_available else None,
            "sketches_dir": self._sketches_dir,
            "fqbn": self._fqbn
        }


arduino_manager = ArduinoManager()
