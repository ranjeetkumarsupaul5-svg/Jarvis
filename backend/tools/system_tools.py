import ctypes
from datetime import datetime
import os
import platform
import shutil
import subprocess
import time
import webbrowser
import pyautogui

from backend.config import SCREENSHOTS_DIR


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def _get_ram_info():
    """
    Get RAM statistics using Windows native API.
    """
    try:
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        total_gb = round(stat.ullTotalPhys / (1024 ** 3), 2)
        avail_gb = round(stat.ullAvailPhys / (1024 ** 3), 2)
        used_gb = round(total_gb - avail_gb, 2)
        return {
            "total_gb": total_gb,
            "available_gb": avail_gb,
            "used_gb": used_gb,
            "percent_used": stat.dwMemoryLoad
        }
    except Exception:
        return {"total_gb": 0, "available_gb": 0, "used_gb": 0, "percent_used": 0}


def _launch_browser_url(url: str, app_name: str = "") -> dict:
    """
    Open a web URL in browser, reusing active browser tabs when possible.
    """
    if not url:
        return {
            "success": False,
            "message": "No URL provided.",
            "data": None,
            "error": "EmptyURL"
        }

    display_name = app_name.strip() if app_name else url
    import urllib.parse
    parsed = urllib.parse.urlparse(url)
    domain_parts = [p for p in parsed.netloc.lower().split(".") if p and p not in ("www", "com", "in", "org", "net", "io", "co", "app")]
    search_keys = list(dict.fromkeys([display_name.lower().strip()] + domain_parts))

    browser_nav_code = r'''
$TargetUrl = __TARGET_URL__
$SearchKeys = __SEARCH_KEYS__

Add-Type @'
using System;
using System.Runtime.InteropServices;
public class WinNav {
    [DllImport("user32.dll")]
    public static extern IntPtr OpenDesktop(string lpszDesktop, uint dwFlags, bool fInherit, uint dwDesiredAccess);
    [DllImport("user32.dll")]
    public static extern bool SetThreadDesktop(IntPtr hDesktop);
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")]
    public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, int dwExtraInfo);
    [DllImport("user32.dll")]
    public static extern bool EnumDesktopWindows(IntPtr hDesktop, EnumWindowsProc lpfn, IntPtr lParam);
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder lpString, int nMaxCount);

    public static void Activate(IntPtr hwnd) {
        keybd_event(0x12, 0, 0, 0);
        ShowWindow(hwnd, 9);
        SetForegroundWindow(hwnd);
        keybd_event(0x12, 0, 2, 0);
    }

    public static void SendCtrlT() {
        keybd_event(0x11, 0, 0, 0);
        keybd_event(0x54, 0, 0, 0);
        keybd_event(0x54, 2, 0, 0);
        keybd_event(0x11, 2, 0, 0);
    }

    public static void SendCtrlV() {
        keybd_event(0x11, 0, 0, 0);
        keybd_event(0x56, 0, 0, 0);
        keybd_event(0x56, 2, 0, 0);
        keybd_event(0x11, 2, 0, 0);
    }

    public static void SendEnter() {
        keybd_event(0x0D, 0, 0, 0);
        keybd_event(0x0D, 2, 0, 0);
    }
}
'@

$h = [WinNav]::OpenDesktop("Default", 0, $false, [uint32]0x1FF)
if ($h -ne [IntPtr]::Zero) { [WinNav]::SetThreadDesktop($h) }

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$browserHwnds = @()
$enumProc = [WinNav+EnumWindowsProc]{
    param($hwnd, $lParam)
    if ([WinNav]::IsWindowVisible($hwnd)) {
        $sb = New-Object System.Text.StringBuilder 256
        [WinNav]::GetWindowText($hwnd, $sb, 256) | Out-Null
        $t = $sb.ToString()
        if (($t -match "Brave|Google Chrome|Zen") -and ($t -notmatch "Jarvis")) {
            $script:browserHwnds += $hwnd
        }
    }
    return $true
}
[WinNav]::EnumDesktopWindows($h, $enumProc, [IntPtr]::Zero)

$sortedHwnds = $browserHwnds | Sort-Object {
    $sb = New-Object System.Text.StringBuilder 256
    [WinNav]::GetWindowText($_, $sb, 256) | Out-Null
    $t = $sb.ToString()
    if ($t -match "Brave") { return 1 }
    if ($t -match "Chrome") { return 2 }
    return 3
}

function Clean-TabTitle($title) {
    $t = $title.Trim()
    $t = [regex]::Replace($t, "\s*-\s*Memory usage.*$", "", [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    $t = [regex]::Replace($t, "^\(\d+\+?\)\s*", "")
    return $t.Trim().ToLower()
}

function Match-TabTitle($rawTitle, $key) {
    if (-not $key) { return $false }
    $clean = Clean-TabTitle $rawTitle
    $k = [regex]::Escape($key.Trim().ToLower())
    if ($clean -eq $key.Trim().ToLower()) { return $true }
    if ($clean -match "^$k\b") { return $true }
    if ($clean -match "[-•|–·]\s*$k$") { return $true }
    if ($clean -match "\b$k\s+search\b") { return $true }
    return $false
}

# Step 1: Check if an existing tab in any browser matches any of SearchKeys
foreach ($hwnd in $sortedHwnds) {
    try {
        $el = [System.Windows.Automation.AutomationElement]::FromHandle($hwnd)
        if ($el -eq $null) { continue }
        $tabCond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::TabItem)
        $tabs = $el.FindAll([System.Windows.Automation.TreeScope]::Descendants, $tabCond)
        foreach ($tab in $tabs) {
            $rawTitle = $tab.Current.Name
            foreach ($k in $SearchKeys) {
                if (Match-TabTitle $rawTitle $k) {
                    $sel = $tab.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern) -as [System.Windows.Automation.SelectionItemPattern]
                    if ($sel -ne $null) {
                        $sel.Select()
                        [WinNav]::Activate($hwnd)
                        exit 0
                    }
                }
            }
        }
    } catch {}
}

# Step 2: Open new tab and navigate in best running browser
if ($sortedHwnds.Count -gt 0) {
    $targetHwnd = $sortedHwnds[0]
    [WinNav]::Activate($targetHwnd)

    # 2a: Try UIAutomation New Tab button & Address bar
    try {
        $el = [System.Windows.Automation.AutomationElement]::FromHandle($targetHwnd)
        if ($el -ne $null) {
            $btnCond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Button)
            $btns = $el.FindAll([System.Windows.Automation.TreeScope]::Descendants, $btnCond)
            $newTabBtn = $null
            foreach ($b in $btns) {
                if ($b.Current.Name -match "^New Tab$|^Add new tab$") {
                    $newTabBtn = $b
                    break
                }
            }
            if ($newTabBtn -ne $null) {
                $inv = $newTabBtn.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern) -as [System.Windows.Automation.InvokePattern]
                if ($inv -ne $null) {
                    $inv.Invoke()
                    Start-Sleep -Milliseconds 400

                    $editCond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Edit)
                    $edits = $el.FindAll([System.Windows.Automation.TreeScope]::Descendants, $editCond)
                    $addrEdit = $null
                    foreach ($e in $edits) {
                        if ($e.Current.Name -match "Address and search bar|Search or enter address") {
                            $addrEdit = $e
                            break
                        }
                    }
                    if ($addrEdit -ne $null) {
                        $addrEdit.SetFocus()
                        $valPat = $addrEdit.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern) -as [System.Windows.Automation.ValuePattern]
                        if ($valPat -ne $null) {
                            $valPat.SetValue($TargetUrl)
                            Start-Sleep -Milliseconds 200
                            [WinNav]::SendEnter()
                            [WinNav]::Activate($targetHwnd)
                            exit 0
                        }
                    }
                }
            }
        }
    } catch {}

    # 2b: Keyboard fallback
    try {
        Set-Clipboard -Value $TargetUrl -ErrorAction SilentlyContinue
        [WinNav]::Activate($targetHwnd)
        Start-Sleep -Milliseconds 200
        [WinNav]::SendCtrlT()
        Start-Sleep -Milliseconds 350
        [WinNav]::SendCtrlV()
        Start-Sleep -Milliseconds 150
        [WinNav]::SendEnter()
        exit 0
    } catch {}
}

exit 1
'''
    nav_success = False
    try:
        import json
        ps_script = browser_nav_code.replace(
            "__TARGET_URL__", json.dumps(url)
        ).replace(
            "__SEARCH_KEYS__", "@(" + ", ".join(f'"{k}"' for k in search_keys) + ")"
        )
        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            timeout=8
        )
        if res.returncode == 0:
            nav_success = True
    except Exception:
        pass

    if not nav_success:
        browser_exe = None
        for path in [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Zen Browser\zen.exe",
        ]:
            if os.path.exists(path):
                browser_exe = path
                break

        if browser_exe:
            subprocess.Popen([browser_exe, url])
        else:
            try:
                os.startfile(url)
            except Exception:
                webbrowser.open(url)

    return {
        "success": True,
        "message": f"Opening {display_name} in web browser.",
        "data": {"target": url, "type": "web_shortcut"},
        "error": None
    }


def open_application(app_name: str):
    """
    Open a desktop application or registered web shortcut.
    """
    if not app_name or not app_name.strip():
        return {
            "success": False,
            "message": "No application name provided.",
            "data": None,
            "error": "EmptyAppName"
        }

    app_name = app_name.lower().strip()
    import re
    # Strip common natural language fillers
    for filler in ["for me", "please", "right now", "now", "app", "application", "window"]:
        app_name = re.sub(rf"\b{filler}\b", "", app_name, flags=re.IGNORECASE).strip()

    # 1. Direct URL handling: allow commands such as "open reddit.com" or "open https://..."
    direct_url = app_name.strip()
    if re.match(r"^(https?://|www\.)", direct_url, re.IGNORECASE) or re.match(
        r"^[a-z0-9][a-z0-9.-]+\.[a-z]{2,}([/:?#].*)?$",
        direct_url,
        re.IGNORECASE,
    ):
        if not re.match(r"^https?://", direct_url, re.IGNORECASE):
            direct_url = "https://" + direct_url
        return _launch_browser_url(direct_url, app_name)

    # 2. Built-in popular Windows executable shortcuts
    built_in_apps = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "paint": "mspaint.exe",
        "mspaint": "mspaint.exe",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "cmd": "cmd.exe",
        "terminal": "wt.exe",
        "command prompt": "cmd.exe",
        "powershell": "powershell.exe",
        "task manager": "taskmgr.exe",
        "taskmgr": "taskmgr.exe",
        "control panel": "control.exe",
        "settings": "start ms-settings:",
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "edge": "msedge.exe",
        "microsoft edge": "msedge.exe",
        "vscode": "code",
        "code": "code",
        "spotify": "spotify.exe",
    }

    # Match against built-in applications (exact or partial keyword)
    matched_target = None
    matched_name = app_name
    if app_name in built_in_apps:
        matched_target = built_in_apps[app_name]
    else:
        for k, v in built_in_apps.items():
            if k in app_name.split():
                matched_target = v
                matched_name = k
                break

    if matched_target:
        try:
            target = matched_target[6:].strip() if matched_target.startswith("start ") else matched_target
            if matched_name == "notepad" or target == "notepad.exe":
                try:
                    os.startfile(r"shell:AppsFolder\Microsoft.WindowsNotepad_8wekyb3d8bbwe!App")
                except Exception:
                    os.startfile(target)
            elif hasattr(os, "startfile"):
                try:
                    os.startfile(target)
                except Exception as sf_err:
                    proc = subprocess.Popen(target, shell=True)
                    try:
                        ret = proc.wait(timeout=0.2)
                        if ret != 0:
                            raise sf_err
                    except subprocess.TimeoutExpired:
                        pass
            else:
                proc = subprocess.Popen(target, shell=True)
                try:
                    ret = proc.wait(timeout=0.2)
                    if ret != 0:
                        raise RuntimeError(f"Process failed with exit code {ret}")
                except subprocess.TimeoutExpired:
                    pass

            return {
                "success": True,
                "message": f"Opening {matched_name}.",
                "data": {"target": matched_target, "type": "system_app"},
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to launch {matched_name}: {str(e)}",
                "data": None,
                "error": str(e)
            }

    # 3. Check sys_command table in jarvis.db
    try:
        from backend.db import get_db_connection
        with get_db_connection() as c:
            row = c.execute("SELECT path FROM sys_command WHERE LOWER(name) = ? OR LOWER(name) LIKE ?", (app_name, f"%{app_name}%")).fetchone()
            if row and row["path"]:
                path = row["path"]
                os.startfile(path)
                return {
                    "success": True,
                    "message": f"Opening {app_name}.",
                    "data": {"target": path, "type": "db_sys_command"},
                    "error": None
                }

            # 4. Check web_command table in jarvis.db
            web_row = c.execute("SELECT url FROM web_command WHERE LOWER(name) = ? OR LOWER(name) LIKE ?", (app_name, f"%{app_name}%")).fetchone()
            if web_row and web_row["url"]:
                return _launch_browser_url(web_row["url"], app_name)
    except Exception as e:
        print(f"Warning during DB app search: {e}")

    # 5. Safe PATH check without popping up blocking Windows error boxes
    found_exe = shutil.which(app_name)
    if found_exe:
        try:
            if hasattr(os, "startfile"):
                try:
                    os.startfile(found_exe)
                except Exception as sf_err:
                    proc = subprocess.Popen(found_exe, shell=True)
                    try:
                        ret = proc.wait(timeout=0.2)
                        if ret != 0:
                            raise sf_err
                    except subprocess.TimeoutExpired:
                        pass
            else:
                proc = subprocess.Popen(found_exe, shell=True)
                try:
                    ret = proc.wait(timeout=0.2)
                    if ret != 0:
                        raise RuntimeError(f"Process failed with exit code {ret}")
                except subprocess.TimeoutExpired:
                    pass

            return {
                "success": True,
                "message": f"Opening {app_name}.",
                "data": {"target": found_exe, "type": "path_executable"},
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error launching {app_name}: {str(e)}",
                "data": None,
                "error": str(e)
            }

    # 6. Generic web resolution: if single-token name, open https://www.<app_name>.com
    if re.match(r"^[a-zA-Z0-9_-]+$", app_name):
        candidate_url = f"https://www.{app_name}.com"
        return _launch_browser_url(candidate_url, app_name)

    # 7. Multi-word unmapped target: search and open in browser
    import urllib.parse
    search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(app_name)}"
    return _launch_browser_url(search_url, app_name)


def get_system_info():
    """
    Return comprehensive system, CPU, RAM, and storage diagnostics.
    """
    ram = _get_ram_info()

    # Disk usage
    try:
        disk = shutil.disk_usage("C:\\")
        total_disk_gb = round(disk.total / (1024 ** 3), 1)
        free_disk_gb = round(disk.free / (1024 ** 3), 1)
        used_disk_gb = round(disk.used / (1024 ** 3), 1)
        disk_pct = round((disk.used / disk.total) * 100, 1)
    except Exception:
        total_disk_gb, free_disk_gb, used_disk_gb, disk_pct = 0, 0, 0, 0

    now = datetime.now()

    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": platform.python_version(),
        "hostname": platform.node(),
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "ram": ram,
        "disk": {
            "drive": "C:",
            "total_gb": total_disk_gb,
            "free_gb": free_disk_gb,
            "used_gb": used_disk_gb,
            "percent_used": disk_pct
        }
    }

    summary = (
        f"OS: {info['os']} {info['os_version']} | RAM: {ram['used_gb']}/{ram['total_gb']} GB ({ram['percent_used']}%) | "
        f"Disk: {used_disk_gb}/{total_disk_gb} GB ({disk_pct}%)"
    )

    return {
        "success": True,
        "message": summary,
        "data": info,
        "error": None
    }


def take_screenshot():
    """
    Capture the current desktop screen and save to disk.
    """
    try:
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        filename = datetime.now().strftime("screenshot_%Y%m%d_%H%M%S.png")
        file_path = SCREENSHOTS_DIR / filename

        screenshot = pyautogui.screenshot()
        screenshot.save(str(file_path))

        return {
            "success": True,
            "message": f"Screenshot saved successfully at {file_path}",
            "data": {"path": str(file_path), "filename": filename},
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Screenshot failed: {str(e)}",
            "data": None,
            "error": str(e)
        }


def get_screen_size():
    """
    Return current desktop display resolution.
    """
    try:
        width, height = pyautogui.size()
        return {
            "success": True,
            "message": f"Display resolution is {width}x{height}",
            "data": {"width": width, "height": height},
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to get screen size: {str(e)}",
            "data": None,
            "error": str(e)
        }


def minimize_all_windows():
    """
    Minimize all desktop windows using Windows shortcut.
    """
    try:
        # Use native Windows keyboard event for Win+D (Win=0x5B, D=0x44)
        user32 = ctypes.windll.user32
        user32.keybd_event(0x5B, 0, 0, 0)
        user32.keybd_event(0x44, 0, 0, 0)
        user32.keybd_event(0x44, 0, 2, 0)
        user32.keybd_event(0x5B, 0, 2, 0)
        return {
            "success": True,
            "message": "All windows minimized.",
            "data": None,
            "error": None
        }
    except Exception as e:
        # Fallback to PyAutoGUI with failsafe protection
        try:
            old_failsafe = pyautogui.FAILSAFE
            pyautogui.FAILSAFE = False
            pyautogui.hotkey("win", "d")
            pyautogui.FAILSAFE = old_failsafe
            return {
                "success": True,
                "message": "All windows minimized.",
                "data": None,
                "error": None
            }
        except Exception as inner_e:
            return {
                "success": False,
                "message": f"Unable to minimize windows: {str(inner_e)}",
                "data": None,
                "error": str(inner_e)
            }


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_byte),
        ("BatteryFlag", ctypes.c_byte),
        ("BatteryLifePercent", ctypes.c_byte),
        ("SystemStatusFlag", ctypes.c_byte),
        ("BatteryLifeTime", ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong),
    ]


def get_battery_status():
    """
    Get current laptop battery percentage and AC charging state.
    """
    try:
        status = SYSTEM_POWER_STATUS()
        if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
            is_charging = (status.ACLineStatus == 1)
            percent = int(status.BatteryLifePercent)
            charging_str = "plugged in" if is_charging else "on battery power"

            if percent == 255:
                # Desktop or battery status unknown
                msg = f"Device is {charging_str} (desktop power supply)."
                pct_val = 100
            else:
                msg = f"Battery is at {percent}%, {charging_str}."
                pct_val = percent

            return {
                "success": True,
                "message": msg,
                "data": {
                    "percent": pct_val,
                    "is_charging": is_charging,
                    "ac_line_status": status.ACLineStatus
                },
                "error": None
            }
        return {
            "success": False,
            "message": "Unable to query power status.",
            "data": None,
            "error": "GetSystemPowerStatusFailed"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Battery check error: {str(e)}",
            "data": None,
            "error": str(e)
        }


def control_volume(action: str = "up", steps: int = 2):
    """
    Control master volume (action: 'up', 'down', 'mute', 'unmute').
    """
    action = action.lower().strip()
    user32 = ctypes.windll.user32

    VK_VOLUME_MUTE = 0xAD
    VK_VOLUME_DOWN = 0xAE
    VK_VOLUME_UP = 0xAF

    try:
        if action in ["mute", "unmute"]:
            user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
            user32.keybd_event(VK_VOLUME_MUTE, 0, 2, 0)
            return {
                "success": True,
                "message": f"Toggled audio mute.",
                "data": {"action": action},
                "error": None
            }
        elif action in ["up", "increase", "raise"]:
            for _ in range(max(1, min(steps, 10))):
                user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
                user32.keybd_event(VK_VOLUME_UP, 0, 2, 0)
            return {
                "success": True,
                "message": f"Volume increased.",
                "data": {"action": "up", "steps": steps},
                "error": None
            }
        elif action in ["down", "decrease", "lower"]:
            for _ in range(max(1, min(steps, 10))):
                user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
                user32.keybd_event(VK_VOLUME_DOWN, 0, 2, 0)
            return {
                "success": True,
                "message": f"Volume decreased.",
                "data": {"action": "down", "steps": steps},
                "error": None
            }
        else:
            return {
                "success": False,
                "message": f"Unknown volume action: '{action}'. Use up, down, or mute.",
                "data": None,
                "error": "InvalidAction"
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Volume control failed: {str(e)}",
            "data": None,
            "error": str(e)
        }


def lock_workstation():
    """
    Lock the Windows workstation.
    """
    try:
        res = ctypes.windll.user32.LockWorkStation()
        if res:
            return {
                "success": True,
                "message": "Workstation locked.",
                "data": None,
                "error": None
            }
        return {
            "success": False,
            "message": "Failed to lock workstation.",
            "data": None,
            "error": "LockWorkStationFailed"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Lock workstation error: {str(e)}",
            "data": None,
            "error": str(e)
        }


def get_active_window():
    """
    Inspect the title and handle of the currently focused foreground window.
    """
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value

        return {
            "success": True,
            "message": f"Active window: '{title}'" if title else "No active window title found.",
            "data": {"title": title, "hwnd": hwnd},
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Unable to inspect active window: {str(e)}",
            "data": None,
            "error": str(e)
        }

