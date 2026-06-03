#!/usr/bin/env python3
"""
ArduinoManager Unit Testleri
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import json

# Proje yolunu ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'raspberrypi'))

from web.arduino_manager import ArduinoManager, BoardInfo, SketchInfo, OperationResult


class TestArduinoManager(unittest.TestCase):
    """ArduinoManager sınıfı için unit testler"""

    def setUp(self):
        """Her test öncesi çalışır"""
        self.manager = ArduinoManager()

    @patch('shutil.which')
    def test_cli_available_true(self, mock_which):
        """arduino-cli kurulu ise True döner"""
        mock_which.return_value = '/usr/bin/arduino-cli'
        self.assertTrue(self.manager.is_cli_available())

    @patch('shutil.which')
    def test_cli_available_false(self, mock_which):
        """arduino-cli kurulu değilse False döner"""
        mock_which.return_value = None
        self.assertFalse(self.manager.is_cli_available())

    @patch('subprocess.run')
    @patch('shutil.which')
    def test_get_cli_version(self, mock_which, mock_run):
        """CLI versiyon bilgisi alınabilmeli"""
        mock_which.return_value = '/usr/bin/arduino-cli'
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='arduino-cli  Version: 0.35.0\n'
        )

        version = self.manager.get_cli_version()

        self.assertIsNotNone(version)
        self.assertIn('0.35.0', version)

    @patch('subprocess.run')
    @patch('shutil.which')
    def test_detect_board_success(self, mock_which, mock_run):
        """Kart algılama başarılı"""
        mock_which.return_value = '/usr/bin/arduino-cli'
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([{
                "port": {"address": "/dev/ttyACM0"},
                "matching_boards": [{"fqbn": "arduino:avr:uno", "name": "Arduino Uno"}]
            }])
        )

        board = self.manager.detect_board()

        self.assertTrue(board.detected)
        self.assertEqual(board.port, "/dev/ttyACM0")
        self.assertEqual(board.fqbn, "arduino:avr:uno")

    @patch('shutil.which')
    def test_detect_board_no_cli(self, mock_which):
        """CLI yoksa hata döner"""
        mock_which.return_value = None

        board = self.manager.detect_board()

        self.assertFalse(board.detected)
        self.assertIn("bulunamadı", board.error)

    @patch('subprocess.run')
    @patch('shutil.which')
    def test_compile_success(self, mock_which, mock_run):
        """Derleme başarılı"""
        mock_which.return_value = '/usr/bin/arduino-cli'
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='Sketch uses 1234 bytes\n'
        )

        with patch('os.path.exists', return_value=True):
            result = self.manager.compile('/path/to/sketch')

        self.assertTrue(result.success)
        self.assertEqual(result.message, "Derleme başarılı")

    @patch('subprocess.run')
    @patch('shutil.which')
    def test_compile_failure(self, mock_which, mock_run):
        """Derleme hatası"""
        mock_which.return_value = '/usr/bin/arduino-cli'
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout='',
            stderr='error: something went wrong'
        )

        with patch('os.path.exists', return_value=True):
            result = self.manager.compile('/path/to/sketch')

        self.assertFalse(result.success)
        self.assertIn("hata", result.message.lower())

    def test_compile_sketch_not_found(self):
        """Sketch bulunamazsa hata"""
        result = self.manager.compile('/nonexistent/path')

        self.assertFalse(result.success)
        self.assertIn("bulunamadı", result.message)

    def test_get_status(self):
        """Status sözlüğü doğru formatta olmalı"""
        status = self.manager.get_status()

        self.assertIn('cli_available', status)
        self.assertIn('sketches_dir', status)
        self.assertIn('fqbn', status)


class TestDataClasses(unittest.TestCase):
    """Dataclass testleri"""

    def test_board_info_detected(self):
        """BoardInfo detected=True"""
        board = BoardInfo(
            detected=True,
            fqbn="arduino:avr:uno",
            port="/dev/ttyACM0",
            name="Arduino Uno"
        )
        self.assertTrue(board.detected)
        self.assertEqual(board.name, "Arduino Uno")

    def test_board_info_not_detected(self):
        """BoardInfo detected=False"""
        board = BoardInfo(detected=False, error="Kart bulunamadı")
        self.assertFalse(board.detected)
        self.assertIsNotNone(board.error)

    def test_sketch_info(self):
        """SketchInfo oluşturma"""
        sketch = SketchInfo(
            name="test_sketch",
            path="/path/to/sketch",
            description="Test açıklaması"
        )
        self.assertEqual(sketch.name, "test_sketch")
        self.assertEqual(sketch.description, "Test açıklaması")

    def test_operation_result_success(self):
        """OperationResult başarılı"""
        result = OperationResult(True, "İşlem başarılı", output="Done")
        self.assertTrue(result.success)
        self.assertEqual(result.output, "Done")

    def test_operation_result_failure(self):
        """OperationResult başarısız"""
        result = OperationResult(False, "Hata", error="Detay")
        self.assertFalse(result.success)
        self.assertEqual(result.error, "Detay")


if __name__ == '__main__':
    unittest.main(verbosity=2)
