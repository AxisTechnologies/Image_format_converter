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

# 3. Build 100% Self-Contained Standalone Offline Windows Setup Installer
print("\n[STEP 3] Building 100% Self-Contained Standalone Offline Setup Installer...")
installer_exe = os.path.join(dist_dir, "PNG2JPEGConverter_Installer.exe")
cmd3 = [
    venv_pyinstaller,
    "--noconfirm",
    "--onefile",
    "--windowed",
    "--add-data", f"{zip_output};.",
    "--name", "PNG2JPEGConverter_Installer",
    "installer_builder.py"
]
subprocess.run(cmd3, check=True, cwd=base_dir)

# 4. Build Native 12 KB Web Installer (Optional Helper)
print("\n[STEP 4] Compiling Native 12 KB Windows Setup Installer...")
csc_path = r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
native_exe = os.path.join(dist_dir, "PNG2JPEGConverter_Setup.exe")

if os.path.exists(csc_path):
    cmd4 = [
        csc_path,
        "/target:winexe",
        f"/out:{native_exe}",
        "/reference:System.Windows.Forms.dll",
        "/reference:System.Drawing.dll",
        "/reference:System.IO.Compression.dll",
        "/reference:System.IO.Compression.FileSystem.dll",
        "installer_native.cs"
    ]
    subprocess.run(cmd4, check=True, cwd=base_dir)

print("\n==========================================================")
print(" BUILD SUCCESSFUL!")
print(f" Standalone Offline Installer: {installer_exe} ({os.path.getsize(installer_exe) / (1024*1024):.2f} MB)")
print(f" Standalone Portable App: {portable_exe} ({os.path.getsize(portable_exe) / (1024*1024):.2f} MB)")
if os.path.exists(native_exe):
    print(f" Native Web Installer: {native_exe} ({os.path.getsize(native_exe) / 1024:.2f} KB)")
print("==========================================================")
