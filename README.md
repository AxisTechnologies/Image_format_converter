# PNG → JPEG Auto-Converter (Background Watcher)

An enterprise-grade, high-performance Windows desktop application that continuously monitors designated folders in the background and automatically converts newly added images in real time across multiple formats (`PNG`, `JPEG`, `WebP`, `AVIF`, `BMP`, `TIFF`).

---

## ✨ Key Features

- ⚡ **Real-Time Directory Watcher**: Low-overhead Win32 directory observer (`ReadDirectoryChangesW`) detects file additions instantly.
- 🛡️ **File Lock Stability Guard**: Multi-stage polling verification ensures files being actively copied, uploaded, or written over a network stream are never processed prematurely.
- 🎨 **Multi-Format Support**: Real-time conversion between `PNG`, `JPEG`, `WebP`, `AVIF`, `BMP`, and `TIFF`.
- 💎 **Lossless-as-Possible Quality**: Configurable 1%–100% lossy/lossless quality modes with **4:4:4 chroma subsampling** at 100% quality.
- 📐 **Dimension & Aspect Ratio Engine**: Resizing modes (Original Size, Percentage, Fixed Width, Fixed Width × Height, Max Bounds) with aspect ratio constraints.
- 🖼️ **Alpha Compositing**: Automatic RGBA-over-canvas compositing (White, Black, or Custom Hex) when converting transparent images to formats without alpha support (e.g. JPEG).
- 📌 **System Tray & Autostart**: Runs silently in the system tray with automatic Windows boot startup registration (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`).
- 📁 **Subfolder Structure Replication**: Replicates relative input subfolder structures inside destination directories.

---

## 🚀 Download & Installation

### 1-Click Offline Setup Installer (Recommended)
Download and run the standalone installer:
👉 **[Download PNG2JPEGConverter_Installer.exe](https://github.com/AxisTechnologies/Image_format_converter/releases/latest/download/PNG2JPEGConverter_Installer.exe)**

* **Self-Contained & Offline**: Includes all application dependencies inside a single setup executable.
* **1-Click Installation**: Installs to `%LOCALAPPDATA%\PNG2JPEGConverter`, creates a **Desktop Shortcut**, and launches the app immediately.

---

## 🛠️ Build & Developer Instructions

### Prerequisites
- Python 3.11 or 3.12 (64-bit)
- Windows 10 or Windows 11

### Setup & Run locally
```bash
# 1. Clone the repository
git clone https://github.com/AxisTechnologies/Image_format_converter.git
cd Image_format_converter

# 2. Create virtual environment & install dependencies
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt

# 3. Run application
.\venv\Scripts\python.exe main.py
```

### Build Releases
To generate the single-file executable setup and portable release zip:
```bash
.\venv\Scripts\python.exe build_release.py
```
Outputs are saved in the `dist/` directory.

---

## ⚖️ License
Distributed under the MIT License. See `LICENSE` for more information.
