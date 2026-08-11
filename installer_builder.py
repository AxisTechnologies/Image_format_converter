import os
import sys
import urllib.request
import zipfile
import subprocess
import shutil
import tkinter as tk
from tkinter import ttk, messagebox
import threading

DEFAULT_GITHUB_ZIP_URL = "https://github.com/AxisTechnologies/Image_format_converter/releases/latest/download/PNG2JPEGConverter_v1.0_Windows_Setup.zip"
APP_NAME = "PNG -> JPEG Auto-Converter"
INSTALL_DIR_NAME = "PNG2JPEGConverter"

class UltraLightInstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} Setup")
        self.root.geometry("460x220")
        self.root.resizable(False, False)
        
        # Windows AppData Installation Target
        appdata_dir = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        self.install_dir = os.path.join(appdata_dir, INSTALL_DIR_NAME)
        self.temp_zip_path = os.path.join(os.environ.get("TEMP", "."), "png2jpeg_pkg.zip")

        # Styling
        self.root.configure(bg="#0F172A")
        
        title_lbl = tk.Label(root, text=f"Setup - {APP_NAME}", font=("Segoe UI", 12, "bold"), fg="#F8FAFC", bg="#0F172A")
        title_lbl.pack(anchor="w", padx=20, pady=(20, 5))

        self.status_lbl = tk.Label(root, text="Click 'Install' to download & setup the application automatically.", font=("Segoe UI", 9), fg="#94A3B8", bg="#0F172A", wr=420, justify="left")
        self.status_lbl.pack(anchor="w", padx=20, pady=(0, 15))

        # Progress bar
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TProgressbar", thickness=12, troughcolor='#1E293B', background='#4F46E5')
        
        self.progress = ttk.Progressbar(root, style="TProgressbar", orient="horizontal", length=420, mode="determinate")
        self.progress.pack(padx=20, pady=(0, 20))

        # Install button
        self.install_btn = tk.Button(root, text="Install Application", font=("Segoe UI", 10, "bold"), fg="#FFFFFF", bg="#4F46E5", activebackground="#4338CA", activeforeground="#FFFFFF", bd=0, padx=20, pady=8, cursor="hand2", command=self.start_install_thread)
        self.install_btn.pack(pady=(0, 15))

    def start_install_thread(self):
        self.install_btn.config(state="disabled")
        threading.Thread(target=self.run_installation, daemon=True).start()

    def update_status(self, text, val=None):
        def _update():
            self.status_lbl.config(text=text)
            if val is not None:
                self.progress['value'] = val
        self.root.after(0, _update)

    def run_installation(self):
        try:
            # Priority 1: Check for embedded application payload inside installer bundle
            bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            embedded_exe = os.path.join(bundle_dir, "PNG2JPEGConverter.exe")
            embedded_zip = os.path.join(bundle_dir, "PNG2JPEGConverter_v1.0_Windows_Setup.zip")

            os.makedirs(self.install_dir, exist_ok=True)
            exe_target = os.path.join(self.install_dir, "PNG2JPEGConverter.exe")

            if os.path.exists(embedded_exe):
                self.update_status("Installing application files...", 50)
                shutil.copy2(embedded_exe, exe_target)
            elif os.path.exists(embedded_zip):
                self.update_status("Extracting embedded package...", 50)
                with zipfile.ZipFile(embedded_zip, 'r') as z:
                    z.extractall(self.install_dir)
            else:
                # Check local adjacent zip or download from web
                installer_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
                adjacent_zip = os.path.join(installer_dir, "PNG2JPEGConverter_v1.0_Windows_Setup.zip")
                dist_zip = os.path.abspath(os.path.join("dist", "PNG2JPEGConverter_v1.0_Windows_Setup.zip"))

                local_zip_path = None
                if os.path.exists(adjacent_zip):
                    local_zip_path = adjacent_zip
                elif os.path.exists(dist_zip):
                    local_zip_path = dist_zip

                target_zip = self.temp_zip_path

                if local_zip_path:
                    self.update_status("Installing from local release package...", 50)
                    target_zip = local_zip_path
                else:
                    self.update_status("Downloading application files from GitHub...", 10)
                    req = urllib.request.Request(DEFAULT_GITHUB_ZIP_URL, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                    })
                    with urllib.request.urlopen(req) as resp, open(target_zip, 'wb') as out_f:
                        total_size = int(resp.headers.get('Content-Length', 0))
                        downloaded = 0
                        block_size = 8192
                        while True:
                            buf = resp.read(block_size)
                            if not buf:
                                break
                            downloaded += len(buf)
                            out_f.write(buf)
                            if total_size > 0:
                                pct = int((downloaded / total_size) * 60) + 10
                                self.update_status(f"Downloading... {downloaded // (1024*1024)}MB / {total_size // (1024*1024)}MB", pct)

                self.update_status("Extracting files...", 80)
                with zipfile.ZipFile(target_zip, 'r') as z:
                    z.extractall(self.install_dir)

            # Create Desktop Shortcut
            self.update_status("Creating Desktop shortcut...", 90)
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

            self.update_status("✅ Installation Complete!", 100)

            def _prompt_success():
                ans = messagebox.askyesno("Installation Complete", f"{APP_NAME} installed successfully!\n\nA Desktop shortcut has been created.\n\nWould you like to run the application now?")
                if ans:
                    subprocess.Popen([exe_target], cwd=self.install_dir)
                self.root.destroy()

            self.root.after(0, _prompt_success)

        except Exception as e:
            self.update_status(f"Installation Error: {e}")
            self.root.after(0, lambda: messagebox.showerror("Installation Error", f"Failed to install files:\n{e}"))
            self.root.after(0, lambda: self.install_btn.config(state="normal"))

def main():
    root = tk.Tk()
    app = UltraLightInstallerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
