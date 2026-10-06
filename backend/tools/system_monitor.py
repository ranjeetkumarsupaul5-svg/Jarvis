import os
import time
import psutil
from datetime import datetime


def get_system_monitor():
    """
    Return live system information for the JARVIS/ERA dashboard.
    """

    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.5)
        cpu_count = psutil.cpu_count(logical=True)

        # Memory
        memory = psutil.virtual_memory()

        # Disk
        disk_path = os.path.abspath(os.sep)
        disk = psutil.disk_usage(disk_path)

        # Battery
        battery = psutil.sensors_battery()

        battery_data = None
        if battery is not None:
            battery_data = {
                "percent": round(battery.percent, 1),
                "charging": battery.power_plugged,
                "time_left_seconds": (
                    None
                    if battery.secsleft in (
                        psutil.POWER_TIME_UNKNOWN,
                        psutil.POWER_TIME_UNLIMITED
                    )
                    else battery.secsleft
                )
            }

        # Uptime
        boot_time = psutil.boot_time()
        uptime_seconds = max(0, int(time.time() - boot_time))

        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        uptime = f"{hours}h {minutes}m {seconds}s"

        return {
            "success": True,
            "tool": "get_system_monitor",
            "data": {
                "cpu": {
                    "usage_percent": round(cpu_percent, 1),
                    "logical_cores": cpu_count
                },
                "memory": {
                    "usage_percent": round(memory.percent, 1),
                    "total_gb": round(memory.total / (1024 ** 3), 2),
                    "used_gb": round(memory.used / (1024 ** 3), 2),
                    "available_gb": round(memory.available / (1024 ** 3), 2)
                },
                "disk": {
                    "usage_percent": round(disk.percent, 1),
                    "total_gb": round(disk.total / (1024 ** 3), 2),
                    "used_gb": round(disk.used / (1024 ** 3), 2),
                    "free_gb": round(disk.free / (1024 ** 3), 2)
                },
                "battery": battery_data,
                "uptime": uptime,
                "timestamp": datetime.now().isoformat(timespec="seconds")
            }
        }

    except Exception as e:
        return {
            "success": False,
            "tool": "get_system_monitor",
            "message": "Unable to read system information.",
            "error": str(e)
        }