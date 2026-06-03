#!/usr/bin/env python3
"""
SerialManager Unit Testleri
"""

import sys
import os
import time
import unittest
from unittest.mock import Mock, patch, MagicMock

# Proje yolunu ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'raspberrypi'))

from web.serial_manager import SerialManager, ConnectionState, CommandResponse


class TestSerialManager(unittest.TestCase):
    """SerialManager sınıfı için unit testler"""

    def setUp(self):
        """Her test öncesi çalışır"""
        self.manager = SerialManager()

    def tearDown(self):
        """Her test sonrası çalışır"""
        self.manager.disconnect()

    def test_initial_state(self):
        """Başlangıç durumu disconnected olmalı"""
        self.assertEqual(self.manager.state, ConnectionState.DISCONNECTED)
        self.assertFalse(self.manager.is_connected)
        self.assertIsNone(self.manager.current_port)

    @patch('web.serial_manager.serial.Serial')
    def test_connect_success(self, mock_serial):
        """Başarılı bağlantı testi"""
        mock_instance = MagicMock()
        mock_instance.is_open = True
        mock_serial.return_value = mock_instance

        with patch.object(self.manager, 'find_arduino', return_value='/dev/ttyACM0'):
            result = self.manager.connect()

        self.assertTrue(result)
        self.assertEqual(self.manager.state, ConnectionState.CONNECTED)

    def test_connect_no_arduino(self):
        """Arduino bulunamazsa bağlantı başarısız olmalı"""
        with patch.object(self.manager, 'find_arduino', return_value=None):
            result = self.manager.connect()

        self.assertFalse(result)
        self.assertEqual(self.manager.state, ConnectionState.DISCONNECTED)

    def test_send_command_not_connected(self):
        """Bağlantı yokken komut gönderimi hata döndürmeli"""
        result = self.manager.send_command("PING")

        self.assertFalse(result.success)
        self.assertEqual(result.error, "Bağlantı yok")

    @patch('web.serial_manager.serial.Serial')
    def test_send_command_success(self, mock_serial):
        """Başarılı komut gönderimi"""
        mock_instance = MagicMock()
        mock_instance.is_open = True
        mock_instance.in_waiting = 5
        mock_instance.readline.return_value = b"PONG\n"
        mock_serial.return_value = mock_instance

        self.manager._serial = mock_instance

        result = self.manager.send_command("PING")

        self.assertTrue(result.success)
        self.assertIn("PONG", result.response)

    def test_callback_registration(self):
        """Callback kayıt testi"""
        callback = Mock()
        self.manager.on_state_change(callback)

        # Durum değişikliği simüle et
        self.manager._notify_state_change(ConnectionState.CONNECTING)

        callback.assert_called_once_with(ConnectionState.CONNECTING)

    def test_get_status(self):
        """Status sözlüğü doğru formatta olmalı"""
        status = self.manager.get_status()

        self.assertIn('state', status)
        self.assertIn('connected', status)
        self.assertIn('port', status)
        self.assertIn('last_heartbeat', status)
        self.assertIn('consecutive_failures', status)


class TestCommandResponse(unittest.TestCase):
    """CommandResponse dataclass testleri"""

    def test_success_response(self):
        """Başarılı yanıt"""
        response = CommandResponse(True, "PONG")
        self.assertTrue(response.success)
        self.assertEqual(response.response, "PONG")
        self.assertIsNone(response.error)

    def test_error_response(self):
        """Hatalı yanıt"""
        response = CommandResponse(False, "", "Timeout")
        self.assertFalse(response.success)
        self.assertEqual(response.error, "Timeout")


if __name__ == '__main__':
    unittest.main(verbosity=2)
