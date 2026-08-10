# PNG -> JPEG Auto-Converter Windows Release & Web Installer Build Script
# Run this script to generate both offline setup ZIP and GitHub Web setup installer

import os
import sys
import shutil
import zipfile
import subprocess

print("==========================================================")
print(" PNG -> JPEG Auto-Converter Industry Standard Release Build")
print("==========================================================")

base_dir = os.path.dirname(os.path.abspath(__file__))
venv_python = os.path.join(base_dir, "venv", "Scripts", "python.exe")
venv_pyinstaller = os.path.join(base_dir, "venv", "Scripts", "pyinstaller.exe")

dist_dir = os.path.join(base_dir, "dist")
build_dir = os.path.join(base_dir, "build")

# 1. Build Standalone Portable Executable
print("\n[STEP 1] Building standalone portable executable...")
cmd1 = [
    venv_pyinstaller,
    "--noconfirm",
    "--onefile",
    "--windowed",
    "--exclude-module", "PySide6.QtNetwork",
    "--exclude-module", "PySide6.QtOpenGL",
    "--exclude-module", "PySide6.QtQml",
    "--exclude-module", "PySide6.QtQuick",
    "--exclude-module", "PySide6.QtSql",
    "--exclude-module", "PySide6.QtSvg",
    "--exclude-module", "PySide6.QtXml",
    "--exclude-module", "PySide6.QtPdf",
    "--exclude-module", "PySide6.Qt3DCore",
    "--exclude-module", "PySide6.QtDesigner",
    "--name", "PNG2JPEGConverter_Portable",
    "main.py"
]
subprocess.run(cmd1, check=True, cwd=base_dir)

# 2. Package Release ZIP for GitHub Releases
print("\n[STEP 2] Packaging release ZIP for GitHub Releases...")
portable_exe = os.path.join(dist_dir, "PNG2JPEGConverter_Portable.exe")
zip_output = os.path.join(dist_dir, "PNG2JPEGConverter_v1.0_Windows_Setup.zip")

with zipfile.ZipFile(zip_output, "w", zipfile.ZIP_DEFLATED) as z:
    z.write(portable_exe, arcname="PNG2JPEGConverter.exe")
    readme = """===========================================================
   PNG -> JPEG Auto-Converter (Background Watcher) v1.0
===========================================================
Continuous real-time image converter application for Windows 10 & 11.
"""
    z.writestr("README.txt", readme)

print(f" -> Release ZIP created: {zip_output} ({os.path.getsize(zip_output) / (1024*1024):.2f} MB)")

# 3. Build One-Click Web Installer Executable
print("\n[STEP 3] Building One-Click Web Setup Installer...")
cmd2 = [
    venv_pyinstaller,
    "--noconfirm",
    "--onefile",
    "--windowed",
    "--name", "PNG2JPEGConverter_Web_Setup",
    "installer_builder.py"
]
subprocess.run(cmd2, check=True, cwd=base_dir)

print("\n==========================================================")
print(" BUILD SUCCESSFUL!")
print(f" Installer: {os.path.join(dist_dir, 'PNG2JPEGConverter_Web_Setup.exe')}")
print(f" Release Zip: {zip_output}")
print("==========================================================")
