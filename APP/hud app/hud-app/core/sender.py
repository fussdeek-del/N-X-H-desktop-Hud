import time

from config import SERIAL_BAUDRATE, SERIAL_PORT, SERIAL_RETRY_SECONDS

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None


class SerialSender:
    def __init__(self):
        self.connection = None
        self.last_attempt = 0.0

    def send(self, line):
        if self._write_serial(line):
            return
        print(line, end="")

    def close(self):
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None

    def _write_serial(self, line):
        if serial is None:
            return False

        if not self.connection and not self._connect():
            return False

        try:
            self.connection.write(line.encode("ascii"))
            return True
        except Exception:
            self.close()
            return False

    def _connect(self):
        now = time.monotonic()
        if now - self.last_attempt < SERIAL_RETRY_SECONDS:
            return False

        self.last_attempt = now
        for port_name in self._candidate_ports():
            try:
                self.connection = serial.Serial(port=port_name, baudrate=SERIAL_BAUDRATE, timeout=0, write_timeout=0)
                return True
            except Exception:
                self.connection = None
        return False

    def _candidate_ports(self):
        if SERIAL_PORT:
            return [SERIAL_PORT]
        if list_ports is None:
            return []

        preferred = []
        fallback = []
        for port in list_ports.comports():
            text = " ".join(
                part for part in (port.device, port.description, port.manufacturer) if part
            ).lower()
            if any(token in text for token in ("rp2040", "pico", "tinyusb", "cdc", "usb serial")):
                preferred.append(port.device)
            else:
                fallback.append(port.device)
        return preferred + fallback
