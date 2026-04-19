import ctypes
import os
import time
from datetime import datetime

import psutil

from config import MAIN_DRIVE


class DEVMODEW(ctypes.Structure):
    _fields_ = [
        ("dmDeviceName", ctypes.c_wchar * 32),
        ("dmSpecVersion", ctypes.c_ushort),
        ("dmDriverVersion", ctypes.c_ushort),
        ("dmSize", ctypes.c_ushort),
        ("dmDriverExtra", ctypes.c_ushort),
        ("dmFields", ctypes.c_ulong),
        ("dmPositionX", ctypes.c_long),
        ("dmPositionY", ctypes.c_long),
        ("dmDisplayOrientation", ctypes.c_ulong),
        ("dmDisplayFixedOutput", ctypes.c_ulong),
        ("dmColor", ctypes.c_short),
        ("dmDuplex", ctypes.c_short),
        ("dmYResolution", ctypes.c_short),
        ("dmTTOption", ctypes.c_short),
        ("dmCollate", ctypes.c_short),
        ("dmFormName", ctypes.c_wchar * 32),
        ("dmLogPixels", ctypes.c_ushort),
        ("dmBitsPerPel", ctypes.c_ulong),
        ("dmPelsWidth", ctypes.c_ulong),
        ("dmPelsHeight", ctypes.c_ulong),
        ("dmDisplayFlags", ctypes.c_ulong),
        ("dmDisplayFrequency", ctypes.c_ulong),
        ("dmICMMethod", ctypes.c_ulong),
        ("dmICMIntent", ctypes.c_ulong),
        ("dmMediaType", ctypes.c_ulong),
        ("dmDitherType", ctypes.c_ulong),
        ("dmReserved1", ctypes.c_ulong),
        ("dmReserved2", ctypes.c_ulong),
        ("dmPanningWidth", ctypes.c_ulong),
        ("dmPanningHeight", ctypes.c_ulong),
    ]


def get_main_drive():
    if MAIN_DRIVE:
        return MAIN_DRIVE
    drive = os.path.splitdrive(os.getcwd())[0]
    return f"{drive}\\" if drive else "C:\\"


def get_refresh_rate():
    devmode = DEVMODEW()
    devmode.dmSize = ctypes.sizeof(DEVMODEW)
    if ctypes.windll.user32.EnumDisplaySettingsW(None, -1, ctypes.byref(devmode)):
        return int(devmode.dmDisplayFrequency or 0)
    return 0


_last_disk = {"time": None, "busy_time": None}
_last_net = {"time": None, "bytes": None}


def prime_metrics():
    psutil.cpu_percent(interval=None)
    disk = psutil.disk_io_counters()
    if disk:
        _last_disk["time"] = time.perf_counter()
        _last_disk["busy_time"] = getattr(disk, "busy_time", 0)

    net = psutil.net_io_counters()
    if net:
        _last_net["time"] = time.perf_counter()
        _last_net["bytes"] = net.bytes_recv + net.bytes_sent


def get_disk_active_percent():
    counters = psutil.disk_io_counters()
    if not counters or not hasattr(counters, "busy_time"):
        return 0.0

    now = time.perf_counter()
    busy_time = counters.busy_time
    last_time = _last_disk["time"]
    last_busy = _last_disk["busy_time"]

    _last_disk["time"] = now
    _last_disk["busy_time"] = busy_time

    if last_time is None or last_busy is None:
        return 0.0

    elapsed_ms = max((now - last_time) * 1000, 1)
    busy_delta = max(busy_time - last_busy, 0)
    return round(min((busy_delta / elapsed_ms) * 100, 100), 1)


def get_network_kbps():
    counters = psutil.net_io_counters()
    if not counters:
        return 0.0

    now = time.perf_counter()
    total_bytes = counters.bytes_recv + counters.bytes_sent
    last_time = _last_net["time"]
    last_bytes = _last_net["bytes"]

    _last_net["time"] = now
    _last_net["bytes"] = total_bytes

    if last_time is None or last_bytes is None:
        return 0.0

    elapsed = max(now - last_time, 0.001)
    bytes_per_sec = max(total_bytes - last_bytes, 0) / elapsed
    return round((bytes_per_sec * 8) / 1000, 1)


def collect_metrics():
    ram_percent = round(psutil.virtual_memory().percent, 1)
    disk_percent = get_disk_active_percent()
    current_time = datetime.now().strftime("%H:%M:%S")
    fps = get_refresh_rate()
    cpu_percent = round(psutil.cpu_percent(interval=None), 1)
    network_kbps = get_network_kbps()

    return {
        "cpu": cpu_percent,
        "ram": ram_percent,
        "disk": disk_percent,
        "fps": fps,
        "time": current_time,
        "network": network_kbps,
        "drive_used": round(psutil.disk_usage(get_main_drive()).percent, 1),
    }
