import sys
import os
import winreg
import logging

logger = logging.getLogger("PNG2JPEG.Autostart")

REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "PNG2JPEGAutoConverter"

def set_autostart_windows(enable: bool) -> bool:
    """
    Enables or disables automatic startup with Windows by adding/removing
    an entry in the CurrentUser Registry Run key.
    """
    if sys.platform != "win32":
        return False

    exe_path = sys.executable
    if getattr(sys, 'frozen', False):
        exe_path = sys.executable
    else:
        # Running as python script
        main_script = os.path.abspath(sys.argv[0])
        exe_path = f'"{sys.executable}" "{main_script}" --minimized'

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_ALL_ACCESS)
        if enable:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
            logger.info(f"Registered Windows startup key: {APP_NAME} -> {exe_path}")
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
                logger.info(f"Removed Windows startup key: {APP_NAME}")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        logger.error(f"Failed to set Windows autostart: {e}")
        return False
