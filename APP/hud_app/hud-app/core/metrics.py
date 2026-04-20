import ctypes
import os
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


def prime_metrics():
    psutil.cpu_percent(interval=None)


def get_refresh_rate():
    devmode = DEVMODEW()
    devmode.dmSize = ctypes.sizeof(DEVMODEW)
    if ctypes.windll.user32.EnumDisplaySettingsW(None, -1, ctypes.byref(devmode)):
        return int(devmode.dmDisplayFrequency or 60)
    return 60


def collect_metrics():
    return {
        "fps": int(get_refresh_rate()),
        "cpu": int(round(psutil.cpu_percent(interval=None))),
        "ram": int(round(psutil.virtual_memory().percent)),
        "disk": int(round(psutil.disk_usage(get_main_drive()).percent)),
        "time": datetime.now().strftime("%H:%M:%S"),
    }
