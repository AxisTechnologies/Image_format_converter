import sys
import os
import urllib.request
import zipfile
import subprocess
import shutil
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QProgressBar, QPushButton, QMessageBox, QLineEdit
)
from PySide6.QtGui import QFont

DEFAULT_GITHUB_ZIP_URL = "https://github.com/AxisTechnologies/Image_format_converter/releases/latest/download/PNG2JPEGConverter_v1.0_Windows_Setup.zip"
APP_NAME = "PNG → JPEG Auto-Converter"
INSTALL_DIR_NAME = "PNG2JPEGConverter"

class DownloadThread(QThread):
    progress_signal = Signal(int, int)
    status_signal = Signal(str)
    finished_signal = Signal(bool, str)

    def __init__(self, download_url: str, dest_path: str, token: str = ""):
        super().__init__()
        self.download_url = download_url
        self.dest_path = dest_path
        self.token = token

    def run(self):
        try:
            self.status_signal.emit("Connecting to GitHub release...")
            req = urllib.request.Request(self.download_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            })
            if self.token:
                req.add_header("Authorization", f"token {self.token}")
                req.add_header("Accept", "application/octet-stream")

            with urllib.request.urlopen(req) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                block_size = 8192

                with open(self.dest_path, 'wb') as out_file:
                    while True:
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        downloaded += len(buffer)
                        out_file.write(buffer)
                        self.progress_signal.emit(downloaded, total_size)

            self.finished_signal.emit(True, self.dest_path)
        except Exception as e:
            self.finished_signal.emit(False, str(e))

class InstallerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} Installer")
        self.setFixedSize(520, 320)
        
        appdata_dir = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        self.install_dir = os.path.join(appdata_dir, INSTALL_DIR_NAME)
        self.temp_zip_path = os.path.join(os.environ.get("TEMP", "."), "png2jpeg_package.zip")

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel(f"📦 Setup - {APP_NAME}")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        self.lbl_status = QLabel("Click 'Install' to setup application automatically on your PC.")
        self.lbl_status.setWordWrap(True)
        layout.addWidget(self.lbl_status)

        # Personal Access Token input for Private Repositories (Optional)
        token_lbl = QLabel("GitHub Personal Access Token (Required if repository is Private):")
        token_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setPlaceholderText("ghp_xxxxxxxxxxxxxxxxxxxx (Leave empty for Public repo / offline setup)")
        layout.addWidget(token_lbl)
        layout.addWidget(self.token_input)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.btn_install = QPushButton("📥 Install Application")
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
        
        # Priority 1: Check embedded/local release zip package adjacent to installer
        installer_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        adjacent_zip = os.path.join(installer_dir, "PNG2JPEGConverter_v1.0_Windows_Setup.zip")
        dist_zip = os.path.abspath(os.path.join("dist", "PNG2JPEGConverter_v1.0_Windows_Setup.zip"))
        
        local_zip_path = None
        if os.path.exists(adjacent_zip):
            local_zip_path = adjacent_zip
        elif os.path.exists(dist_zip):
            local_zip_path = dist_zip

        if local_zip_path:
            self.lbl_status.setText("Installing application from local release package...")
            self.progress_bar.setValue(50)
            self.extract_and_create_shortcuts(local_zip_path)
            return

        # Priority 2: Web download from GitHub Releases
        token = self.token_input.text().strip()
        self.download_thread = DownloadThread(DEFAULT_GITHUB_ZIP_URL, self.temp_zip_path, token=token)
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
            err_text = str(result_or_err)
            if "404" in err_text:
                msg = ("GitHub download link returned 404 Not Found.\n\n"
                       "If 'AxisTechnologies/Image_format_converter' is a PRIVATE repository, please:\n"
                       "1. Make the repository PUBLIC or publish a Release on GitHub.\n"
                       "2. OR enter a GitHub Personal Access Token in the installer token box.\n"
                       "3. OR place 'PNG2JPEGConverter_v1.0_Windows_Setup.zip' in the same folder as this installer.")
            else:
                msg = f"Failed to download package from GitHub:\n{result_or_err}"

            QMessageBox.critical(self, "Download Error", msg)
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
