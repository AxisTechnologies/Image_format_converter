import sys
import os
import urllib.request
import zipfile
import subprocess
import shutil
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QProgressBar, QPushButton, QMessageBox
)
from PySide6.QtGui import QFont

# GitHub direct download link for AxisTechnologies repository
DEFAULT_GITHUB_ZIP_URL = "https://github.com/AxisTechnologies/Image_format_converter/releases/latest/download/PNG2JPEGConverter_v1.0_Windows_Setup.zip"

APP_NAME = "PNG → JPEG Auto-Converter"
INSTALL_DIR_NAME = "PNG2JPEGConverter"

class DownloadThread(QThread):
    progress_signal = Signal(int, int)  # downloaded, total
    status_signal = Signal(str)
    finished_signal = Signal(bool, str)

    def __init__(self, download_url: str, dest_path: str):
        super().__init__()
        self.download_url = download_url
        self.dest_path = dest_path

    def run(self):
        try:
            self.status_signal.emit("Downloading application package from GitHub...")
            
            def _progress_hook(count, block_size, total_size):
                downloaded = count * block_size
                self.progress_signal.emit(downloaded, total_size)

            urllib.request.urlretrieve(self.download_url, self.dest_path, _progress_hook)
            self.finished_signal.emit(True, self.dest_path)
        except Exception as e:
            self.finished_signal.emit(False, str(e))

class InstallerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} Web Installer")
        self.setFixedSize(500, 260)
        
        appdata_dir = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        self.install_dir = os.path.join(appdata_dir, INSTALL_DIR_NAME)
        self.temp_zip_path = os.path.join(os.environ.get("TEMP", "."), "png2jpeg_package.zip")

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel(f"📦 Setup - {APP_NAME}")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        self.lbl_status = QLabel("Click 'Install' to download and setup the application automatically.")
        self.lbl_status.setWordWrap(True)
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.btn_install = QPushButton("📥 Download & Install")
        self.btn_install.setHeight = 40
        self.btn_install.setStyleSheet("""
            QPushButton {
                background-color: #4F46E5;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #4338CA; }
        """)
        self.btn_install.clicked.connect(self.start_installation)
        layout.addWidget(self.btn_install)

    def start_installation(self):
        self.btn_install.setEnabled(False)
        
        # Check if local release zip exists (fallback for offline mode)
        local_zip = os.path.abspath(os.path.join("dist", "PNG2JPEGConverter_v1.0_Windows_Setup.zip"))
        if os.path.exists(local_zip):
            self.lbl_status.setText("Installing application from local bundle...")
            self.extract_and_create_shortcuts(local_zip)
            return

        self.download_thread = DownloadThread(DEFAULT_GITHUB_ZIP_URL, self.temp_zip_path)
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.status_signal.connect(self.lbl_status.setText)
        self.download_thread.finished_signal.connect(self.on_download_finished)
        self.download_thread.start()

    @Slot(int, int)
    def update_progress(self, downloaded, total):
        if total > 0:
            percent = int((downloaded / total) * 100)
            self.progress_bar.setValue(percent)
            self.lbl_status.setText(f"Downloading files... {percent}% ({downloaded // (1024*1024)}MB / {total // (1024*1024)}MB)")

    @Slot(bool, str)
    def on_download_finished(self, success, result_or_err):
        if not success:
            QMessageBox.critical(self, "Download Error", f"Failed to download package from GitHub:\n{result_or_err}")
            self.btn_install.setEnabled(True)
            return

        self.extract_and_create_shortcuts(self.temp_zip_path)

    def extract_and_create_shortcuts(self, zip_file_path: str):
        try:
            self.lbl_status.setText("Extracting application files...")
            os.makedirs(self.install_dir, exist_ok=True)

            with zipfile.ZipFile(zip_file_path, "r") as z:
                z.extractall(self.install_dir)

            exe_target = os.path.join(self.install_dir, "PNG2JPEGConverter.exe")

            # Create Desktop Shortcut via VBScript
            self.lbl_status.setText("Creating Desktop shortcut...")
            desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            shortcut_path = os.path.join(desktop_dir, "PNG2JPEG Auto-Converter.lnk")

            vbs_script = f"""
            Set WshShell = WScript.CreateObject("WScript.Shell")
            Set shortcut = WshShell.CreateShortcut("{shortcut_path}")
            shortcut.TargetPath = "{exe_target}"
            shortcut.WorkingDirectory = "{self.install_dir}"
            shortcut.Description = "PNG -> JPEG Auto Converter"
            shortcut.Save
            """
            vbs_file = os.path.join(os.environ.get("TEMP", "."), "create_shortcut.vbs")
            with open(vbs_file, "w", encoding="utf-8") as f:
                f.write(vbs_script)

            subprocess.run(["cscript", "//Nologo", vbs_file], check=True)

            self.progress_bar.setValue(100)
            self.lbl_status.setText("✅ Installation Complete!")

            reply = QMessageBox.information(
                self,
                "Installation Successful",
                f"{APP_NAME} has been installed successfully!\n\nLocation: {self.install_dir}\n\nA Desktop shortcut has been created.\nWould you like to run it now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                subprocess.Popen([exe_target], cwd=self.install_dir)

            self.close()

        except Exception as e:
            QMessageBox.critical(self, "Installation Error", f"Failed installing files: {e}")
            self.btn_install.setEnabled(True)

def main():
    app = QApplication(sys.argv)
    window = InstallerWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
