import sys
import os
import logging
from PySide6.QtCore import Qt, QSize, Slot
from PySide6.QtCore import Qt, QSize, Slot, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSlider, QComboBox, QCheckBox, QSpinBox,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QFrame, QMessageBox, QSystemTrayIcon, QMenu, QColorDialog
)
from PySide6.QtGui import QIcon, QFont, QColor, QAction

from config_manager import ConfigManager
from processed_tracker import ProcessedTracker
from folder_watcher import FolderWatcherService
from conversion_manager import ConversionManager
from autostart_manager import set_autostart_windows

logger = logging.getLogger("PNG2JPEG.UI")

STYLESHEET = """
QMainWindow, QWidget {
    background-color: #121824;
    color: #E2E8F0;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}

QGroupBox {
    border: 1px solid #2D3748;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
    color: #6366F1;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

QLineEdit, QComboBox, QSpinBox {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    color: #F8FAFC;
    selection-background-color: #4F46E5;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #6366F1;
}

QPushButton {
    background-color: #4F46E5;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #4338CA;
}

QPushButton:pressed {
    background-color: #3730A3;
}

QPushButton#secondaryBtn {
    background-color: #334155;
    color: #F8FAFC;
}

QPushButton#secondaryBtn:hover {
    background-color: #475569;
}

QPushButton#dangerBtn {
    background-color: #DC2626;
}

QPushButton#dangerBtn:hover {
    background-color: #B91C1C;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #334155;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #6366F1;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #818CF8;
    border: 2px solid #FFFFFF;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}

QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #475569;
    background-color: #1E293B;
}

QCheckBox::indicator:checked {
    background-color: #4F46E5;
    border: 1px solid #6366F1;
}

QTableWidget {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 6px;
    gridline-color: #334155;
}

QHeaderView::section {
    background-color: #0F172A;
    color: #94A3B8;
    padding: 6px;
    font-weight: bold;
    border: none;
}

QFrame#statusCard {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 12px;
}
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PNG → JPEG Auto-Converter (Background Watcher)")
        self.setMinimumSize(820, 680)
        self.resize(850, 720)

        # Managers initialization
        self.config = ConfigManager()
        self.tracker = ProcessedTracker(self.config.config_dir)
        self.conversion_mgr = ConversionManager(self.tracker)
        self.watcher = FolderWatcherService(self.on_png_file_detected)

        # Connect conversion manager signals
        self.conversion_mgr.conversion_started.connect(self.log_started)
        self.conversion_mgr.conversion_success.connect(self.log_success)
        self.conversion_mgr.conversion_skipped.connect(self.log_skipped)
        self.conversion_mgr.conversion_failed.connect(self.log_failed)
        self.conversion_mgr.stats_updated.connect(self.update_stats_ui)

        # Periodic Poll Timer (fallback scanning)
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(3000)
        self.poll_timer.timeout.connect(self.periodic_poll_check)

        self.init_ui()
        self.init_system_tray()
        self.apply_stored_config()

        self.setAcceptDrops(True)

        self.init_ui()
        self.init_system_tray()
        self.apply_stored_config()

        # Connect UI controls to auto-sync settings in real-time
        self.format_combo.currentIndexChanged.connect(self.auto_sync_settings)
        self.quality_slider.valueChanged.connect(self.auto_sync_settings)
        self.size_combo.currentIndexChanged.connect(self.auto_sync_settings)
        self.percent_spin.valueChanged.connect(self.auto_sync_settings)
        self.width_spin.valueChanged.connect(self.auto_sync_settings)
        self.height_spin.valueChanged.connect(self.auto_sync_settings)
        self.aspect_cb.toggled.connect(self.auto_sync_settings)
        self.bg_combo.currentIndexChanged.connect(self.auto_sync_settings)
        self.existing_combo.currentIndexChanged.connect(self.auto_sync_settings)
        self.subfolders_cb.toggled.connect(self.on_subfolders_toggled)

        # Start conversion manager thread pool
        self.conversion_mgr.start()

        # Auto-start monitoring if folders are configured
        if self.config.get("source_folder") and self.config.get("output_folder"):
            self.start_monitoring()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # --- 1. Header Section ---
        header_layout = QHBoxLayout()
        title_label = QLabel("🖼️ PNG → JPEG Auto-Converter")
        title_font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #F8FAFC;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        self.status_badge = QLabel("● PAUSED")
        self.status_badge.setStyleSheet("color: #F59E0B; font-weight: bold; background: #3B270C; padding: 4px 10px; border-radius: 12px;")
        header_layout.addWidget(self.status_badge)
        main_layout.addLayout(header_layout)

        # --- 2. Folder Configuration Group ---
        folder_group = QGroupBox("Folder Configuration")
        folder_layout = QVBoxLayout(folder_group)

        # Target Folder
        target_layout = QHBoxLayout()
        target_label = QLabel("Target Folder (PNG Source):")
        target_label.setFixedWidth(170)
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Select folder containing input PNG images...")
        target_browse_btn = QPushButton("Browse...")
        target_browse_btn.setObjectName("secondaryBtn")
        target_browse_btn.clicked.connect(self.browse_target_folder)
        target_layout.addWidget(target_label)
        target_layout.addWidget(self.target_input)
        target_layout.addWidget(target_browse_btn)
        folder_layout.addLayout(target_layout)

        # Output Folder
        output_layout = QHBoxLayout()
        output_label = QLabel("Output Folder (JPEG Destination):")
        output_label.setFixedWidth(170)
        self.output_input = QLineEdit()
        self.output_input.setPlaceholderText("Select folder where converted JPEG images will be saved...")
        output_browse_btn = QPushButton("Browse...")
        output_browse_btn.setObjectName("secondaryBtn")
        output_browse_btn.clicked.connect(self.browse_output_folder)
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_input)
        output_layout.addWidget(output_browse_btn)
        folder_layout.addLayout(output_layout)

        main_layout.addWidget(folder_group)

        # --- 3. Conversion & Image Settings Group ---
        settings_group = QGroupBox("Conversion & Image Settings")
        settings_layout = QVBoxLayout(settings_group)

        # Format Row
        format_layout = QHBoxLayout()
        fmt_title = QLabel("Target Output Format:")
        fmt_title.setFixedWidth(170)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["JPEG", "PNG", "WEBP", "AVIF", "BMP"])
        self.format_combo.currentIndexChanged.connect(self.on_format_changed)

        format_layout.addWidget(fmt_title)
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        settings_layout.addLayout(format_layout)

        # Quality Row
        quality_layout = QHBoxLayout()
        self.quality_title = QLabel("JPEG / WebP Quality:")
        self.quality_title.setFixedWidth(170)
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(100)
        self.quality_slider.valueChanged.connect(self.on_quality_changed)

        self.quality_label = QLabel("100% (Maximum Quality / Lossless-as-Possible)")
        self.quality_label.setFixedWidth(280)
        self.quality_label.setStyleSheet("color: #38BDF8; font-weight: bold;")
        
        quality_layout.addWidget(self.quality_title)
        quality_layout.addWidget(self.quality_slider)
        quality_layout.addWidget(self.quality_label)
        settings_layout.addLayout(quality_layout)

        # Sizing Mode Row
        size_layout = QHBoxLayout()
        size_title = QLabel("Image Dimension:")
        size_title.setFixedWidth(170)
        self.size_combo = QComboBox()
        self.size_combo.addItems([
            "Original Size",
            "Percentage",
            "Fixed Width",
            "Fixed Width x Height",
            "Max Width / Height"
        ])
        self.size_combo.currentIndexChanged.connect(self.on_size_mode_changed)
        
        self.percent_spin = QSpinBox()
        self.percent_spin.setRange(1, 500)
        self.percent_spin.setValue(100)
        self.percent_spin.setSuffix("%")
        self.percent_spin.setFixedWidth(80)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 10000)
        self.width_spin.setValue(1920)
        self.width_spin.setPrefix("W: ")
        self.width_spin.setSuffix(" px")
        self.width_spin.setFixedWidth(110)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 10000)
        self.height_spin.setValue(1080)
        self.height_spin.setPrefix("H: ")
        self.height_spin.setSuffix(" px")
        self.height_spin.setFixedWidth(110)

        self.aspect_cb = QCheckBox("Maintain Aspect Ratio")
        self.aspect_cb.setChecked(True)

        size_layout.addWidget(size_title)
        size_layout.addWidget(self.size_combo)
        size_layout.addWidget(self.percent_spin)
        size_layout.addWidget(self.width_spin)
        size_layout.addWidget(self.height_spin)
        size_layout.addWidget(self.aspect_cb)
        size_layout.addStretch()
        settings_layout.addLayout(size_layout)

        # Transparency & Collision Policy Row
        policy_layout = QHBoxLayout()
        bg_title = QLabel("Transparent Canvas:")
        bg_title.setFixedWidth(140)
        self.bg_combo = QComboBox()
        self.bg_combo.addItems(["White", "Black", "Custom"])
        self.bg_combo.currentIndexChanged.connect(self.on_bg_mode_changed)

        self.custom_color_btn = QPushButton("Color...")
        self.custom_color_btn.setFixedWidth(75)
        self.custom_color_btn.setObjectName("secondaryBtn")
        self.custom_color_btn.clicked.connect(self.pick_custom_color)
        self.custom_color_btn.setVisible(False)
        self.selected_color_hex = "#FFFFFF"

        existing_title = QLabel("Existing File Policy:")
        self.existing_combo = QComboBox()
        self.existing_combo.addItems(["Create Numbered Copy (_1, _2)", "Skip Existing", "Replace Existing"])

        policy_layout.addWidget(bg_title)
        policy_layout.addWidget(self.bg_combo)
        policy_layout.addWidget(self.custom_color_btn)
        policy_layout.addSpacing(20)
        policy_layout.addWidget(existing_title)
        policy_layout.addWidget(self.existing_combo)
        policy_layout.addStretch()
        settings_layout.addLayout(policy_layout)

        # Checkboxes Options Row
        options_layout = QHBoxLayout()
        self.startup_scan_cb = QCheckBox("Scan existing PNGs on startup")
        self.subfolders_cb = QCheckBox("Include Subfolders")
        self.autostart_cb = QCheckBox("Start with Windows")
        self.minimized_cb = QCheckBox("Start Minimized to Tray")

        options_layout.addWidget(self.startup_scan_cb)
        options_layout.addWidget(self.subfolders_cb)
        options_layout.addWidget(self.autostart_cb)
        options_layout.addWidget(self.minimized_cb)
        options_layout.addStretch()
        settings_layout.addLayout(options_layout)

        main_layout.addWidget(settings_group)

        # --- 4. Live Monitoring Cards & Action Bar ---
        card_frame = QFrame()
        card_frame.setObjectName("statusCard")
        card_layout = QHBoxLayout(card_frame)

        self.lbl_processed = QLabel("Processed: 0")
        self.lbl_success = QLabel("Successful: 0")
        self.lbl_success.setStyleSheet("color: #10B981; font-weight: bold;")
        self.lbl_skipped = QLabel("Skipped: 0")
        self.lbl_skipped.setStyleSheet("color: #F59E0B; font-weight: bold;")
        self.lbl_failed = QLabel("Failed: 0")
        self.lbl_failed.setStyleSheet("color: #EF4444; font-weight: bold;")

        card_layout.addWidget(self.lbl_processed)
        card_layout.addWidget(self.lbl_success)
        card_layout.addWidget(self.lbl_skipped)
        card_layout.addWidget(self.lbl_failed)
        card_layout.addStretch()

        self.convert_files_btn = QPushButton("📂 Convert File(s)...")
        self.convert_files_btn.setObjectName("secondaryBtn")
        self.convert_files_btn.clicked.connect(self.convert_manual_files)

        self.toggle_btn = QPushButton("▶ Start Monitoring")
        self.toggle_btn.clicked.connect(self.toggle_monitoring)
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setObjectName("secondaryBtn")
        self.save_btn.clicked.connect(self.save_current_settings)

        card_layout.addWidget(self.convert_files_btn)
        card_layout.addWidget(self.toggle_btn)
        card_layout.addWidget(self.save_btn)
        main_layout.addWidget(card_frame)

        # --- 5. Activity Log Table ---
        log_label = QLabel("Activity Log:")
        log_label.setStyleSheet("font-weight: bold; color: #94A3B8;")
        main_layout.addWidget(log_label)

        self.log_table = QTableWidget(0, 4)
        self.log_table.setHorizontalHeaderLabels(["Time", "Status", "Source PNG File", "Details / Destination"])
        self.log_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.log_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.log_table.verticalHeader().setVisible(False)
        main_layout.addWidget(self.log_table)

        self.setStyleSheet(STYLESHEET)
        self.on_size_mode_changed(0)

    def init_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        # Create standard fallback icon
        pixmap = QIcon.fromTheme("image-x-generic").pixmap(32, 32)
        self.tray_icon.setIcon(QIcon(pixmap))
        self.tray_icon.setToolTip("PNG → JPEG Auto-Converter")

        tray_menu = QMenu()
        show_action = QAction("Open Dashboard", self)
        show_action.triggered.connect(self.show_normal_window)
        
        self.tray_toggle_action = QAction("Pause Monitoring", self)
        self.tray_toggle_action.triggered.connect(self.toggle_monitoring)
        
        scan_action = QAction("Process Target Folder Now", self)
        scan_action.triggered.connect(self.trigger_manual_scan)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.quit_app)

        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(self.tray_toggle_action)
        tray_menu.addAction(scan_action)
        tray_menu.addSeparator()
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def show_normal_window(self):
        self.show()
        self.activateWindow()
        self.raise_()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show_normal_window()

    def closeEvent(self, event):
        """Minimize to tray on window close button."""
        if self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                "PNG → JPEG Auto-Converter",
                "Application is still running in the background system tray.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            event.ignore()
        else:
            event.accept()

    def quit_app(self):
        self.watcher.stop_monitoring()
        self.conversion_mgr.stop()
        QApplication.quit()

    # --- Config Management UI Helpers ---
    def apply_stored_config(self):
        self.target_input.setText(self.config.get("source_folder", ""))
        self.output_input.setText(self.config.get("output_folder", ""))
        
        fmt_val = self.config.get("target_output_format", "JPEG")
        fmt_idx = self.format_combo.findText(fmt_val)
        if fmt_idx >= 0:
            self.format_combo.setCurrentIndex(fmt_idx)

        self.quality_slider.setValue(self.config.get("jpeg_quality", 100))
        
        mode = self.config.get("resize_mode", "Original Size")
        idx = self.size_combo.findText(mode)
        if idx >= 0:
            self.size_combo.setCurrentIndex(idx)
        
        self.percent_spin.setValue(self.config.get("resize_percent", 100))
        self.width_spin.setValue(self.config.get("custom_width", 1920))
        self.height_spin.setValue(self.config.get("custom_height", 1080))
        self.aspect_cb.setChecked(self.config.get("maintain_aspect_ratio", True))
        
        bg_val = self.config.get("transparency_color", "White")
        bg_idx = self.bg_combo.findText(bg_val)
        if bg_idx >= 0:
            self.bg_combo.setCurrentIndex(bg_idx)
        self.selected_color_hex = self.config.get("custom_color_hex", "#FFFFFF")

        exist_val = self.config.get("existing_file_policy", "Create Numbered Copy")
        if exist_val == "Create Numbered Copy":
            ex_idx = 0
        elif exist_val == "Skip":
            ex_idx = 1
        elif exist_val == "Replace":
            ex_idx = 2
        else:
            ex_idx = 0
        self.existing_combo.setCurrentIndex(ex_idx)

        self.startup_scan_cb.setChecked(self.config.get("process_existing_on_startup", True))
        self.subfolders_cb.setChecked(self.config.get("include_subfolders", False))
        self.autostart_cb.setChecked(self.config.get("start_with_windows", False))
        self.minimized_cb.setChecked(self.config.get("start_minimized", False))

    def collect_settings_from_ui(self) -> dict:
        combo_text = self.existing_combo.currentText()
        if "Numbered" in combo_text:
            policy_val = "Create Numbered Copy"
        elif "Skip" in combo_text:
            policy_val = "Skip"
        elif "Replace" in combo_text:
            policy_val = "Replace"
        else:
            policy_val = "Create Numbered Copy"

        return {
            "source_folder": self.target_input.text().strip(),
            "output_folder": self.output_input.text().strip(),
            "target_output_format": self.format_combo.currentText(),
            "allowed_input_extensions": [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".avif"],
            "jpeg_quality": self.quality_slider.value(),
            "resize_mode": self.size_combo.currentText(),
            "resize_percent": self.percent_spin.value(),
            "custom_width": self.width_spin.value(),
            "custom_height": self.height_spin.value(),
            "maintain_aspect_ratio": self.aspect_cb.isChecked(),
            "transparency_color": self.bg_combo.currentText(),
            "custom_color_hex": self.selected_color_hex,
            "existing_file_policy": policy_val,
            "process_existing_on_startup": self.startup_scan_cb.isChecked(),
            "include_subfolders": self.subfolders_cb.isChecked(),
            "preserve_subfolder_structure": True,
            "start_with_windows": self.autostart_cb.isChecked(),
            "start_minimized": self.minimized_cb.isChecked()
        }

    def on_format_changed(self, index):
        fmt = self.format_combo.currentText()
        is_lossy = fmt in ("JPEG", "WEBP", "AVIF")
        self.quality_slider.setEnabled(is_lossy)
        self.quality_title.setEnabled(is_lossy)
        self.quality_label.setEnabled(is_lossy)

    def save_current_settings(self):
        settings = self.collect_settings_from_ui()
        self.config.update_dict(settings)
        self.conversion_mgr.update_settings(settings)
        set_autostart_windows(settings["start_with_windows"])
        QMessageBox.information(self, "Settings Saved", "Application settings saved successfully!")

    # --- UI Event Handlers ---
    def browse_target_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Target/Source PNG Folder")
        if folder:
            self.target_input.setText(folder)

    def browse_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output JPEG Destination Folder")
        if folder:
            self.output_input.setText(folder)

    def on_quality_changed(self, val):
        if val == 100:
            self.quality_label.setText("100% (Maximum Quality / Lossless-as-Possible)")
        else:
            self.quality_label.setText(f"{val}% Quality / Compression")

    def on_size_mode_changed(self, index):
        mode = self.size_combo.currentText()
        self.percent_spin.setVisible(mode == "Percentage")
        self.width_spin.setVisible(mode in ("Fixed Width", "Fixed Width x Height", "Max Width / Height"))
        self.height_spin.setVisible(mode in ("Fixed Width x Height", "Max Width / Height"))
        self.aspect_cb.setVisible(mode in ("Fixed Width", "Fixed Width x Height", "Max Width / Height"))

    def on_bg_mode_changed(self, index):
        self.custom_color_btn.setVisible(self.bg_combo.currentText() == "Custom")

    def pick_custom_color(self):
        color = QColorDialog.getColor(QColor(self.selected_color_hex), self, "Select Transparent Background Color")
        if color.isValid():
            self.selected_color_hex = color.name()

    def validate_folders(self) -> bool:
        src = self.target_input.text().strip()
        out = self.output_input.text().strip()

        if not src or not os.path.exists(src):
            QMessageBox.warning(self, "Validation Error", "Target PNG source folder does not exist!")
            return False
        
        if not out:
            QMessageBox.warning(self, "Validation Error", "Output JPEG destination folder is required!")
            return False

        try:
            os.makedirs(out, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "Validation Error", f"Cannot create output directory: {e}")
            return False

        if os.path.normpath(src).lower() == os.path.normpath(out).lower():
            QMessageBox.critical(self, "Validation Error", "Target Folder and Output Folder cannot be the same directory!")
            return False

        return True

    def toggle_monitoring(self):
        if self.watcher.is_monitoring:
            self.stop_monitoring()
        else:
            self.start_monitoring()

    def start_monitoring(self):
        if not self.validate_folders():
            return

        settings = self.collect_settings_from_ui()
        self.config.update_dict(settings)
        self.conversion_mgr.update_settings(settings)

        src = settings["source_folder"]
        recursive = settings["include_subfolders"]
        allowed = settings["allowed_input_extensions"]

        if self.watcher.start_monitoring(src, allowed_exts=allowed, include_subfolders=recursive):
            self.status_badge.setText("● MONITORING")
            self.status_badge.setStyleSheet("color: #10B981; font-weight: bold; background: #064E3B; padding: 4px 10px; border-radius: 12px;")
            self.toggle_btn.setText("⏸ Pause Monitoring")
            self.toggle_btn.setObjectName("dangerBtn")
            self.toggle_btn.setStyle(self.toggle_btn.style())
            self.tray_toggle_action.setText("Pause Monitoring")
            self.poll_timer.start()

            if settings["process_existing_on_startup"]:
                self.conversion_mgr.scan_folder_and_enqueue(src, recursive=recursive)

    def stop_monitoring(self):
        self.poll_timer.stop()
        self.watcher.stop_monitoring()
        self.status_badge.setText("● PAUSED")
        self.status_badge.setStyleSheet("color: #F59E0B; font-weight: bold; background: #3B270C; padding: 4px 10px; border-radius: 12px;")
        self.toggle_btn.setText("▶ Resume Monitoring")
        self.toggle_btn.setObjectName("")
        self.toggle_btn.setStyle(self.toggle_btn.style())
        self.tray_toggle_action.setText("Resume Monitoring")

    def auto_sync_settings(self):
        settings = self.collect_settings_from_ui()
        self.conversion_mgr.update_settings(settings)

    def on_subfolders_toggled(self, checked: bool):
        self.auto_sync_settings()
        if self.watcher.is_monitoring:
            src = self.target_input.text().strip()
            allowed = [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".avif"]
            self.watcher.start_monitoring(src, allowed_exts=allowed, include_subfolders=checked)

    def periodic_poll_check(self):
        if self.watcher.is_monitoring:
            settings = self.collect_settings_from_ui()
            self.conversion_mgr.update_settings(settings)
            src = settings.get("source_folder", "")
            recursive = settings.get("include_subfolders", False)
            if src and os.path.exists(src):
                self.conversion_mgr.scan_folder_and_enqueue(src, recursive=recursive)

    def convert_manual_files(self):
        out_folder = self.output_input.text().strip()
        if not out_folder:
            QMessageBox.warning(self, "Output Folder Required", "Please select an Output Folder destination first before selecting files.")
            return

        os.makedirs(out_folder, exist_ok=True)
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Image Files to Convert",
            "",
            "Image Files (*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.tif *.avif);;All Files (*)"
        )

        if files:
            settings = self.collect_settings_from_ui()
            self.config.update_dict(settings)
            self.conversion_mgr.update_settings(settings)
            for f in files:
                self.conversion_mgr.enqueue_file(f, force=True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return
        
        out_folder = self.output_input.text().strip()
        if not out_folder:
            QMessageBox.warning(self, "Output Folder Required", "Please select an Output Folder destination first before dropping files.")
            return

        os.makedirs(out_folder, exist_ok=True)
        settings = self.collect_settings_from_ui()
        self.config.update_dict(settings)
        self.conversion_mgr.update_settings(settings)

        allowed = [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".avif"]
        count = 0
        for url in urls:
            local_path = url.toLocalFile()
            if os.path.isfile(local_path) and os.path.splitext(local_path)[1].lower() in allowed:
                self.conversion_mgr.enqueue_file(local_path, force=True)
                count += 1
            elif os.path.isdir(local_path):
                self.conversion_mgr.scan_folder_and_enqueue(local_path, recursive=self.subfolders_cb.isChecked(), force=True)

    def trigger_manual_scan(self):
        if self.validate_folders():
            src = self.target_input.text().strip()
            recursive = self.subfolders_cb.isChecked()
            self.conversion_mgr.scan_folder_and_enqueue(src, recursive=recursive)

    def on_png_file_detected(self, file_path: str):
        self.conversion_mgr.enqueue_file(file_path)

    # --- Logging Table Slots ---
    def _add_log_row(self, status: str, status_color: str, source_path: str, details: str):
        import datetime
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        row = self.log_table.rowCount()
        self.log_table.insertRow(row)

        time_item = QTableWidgetItem(now_str)
        status_item = QTableWidgetItem(status)
        status_item.setForeground(QColor(status_color))
        status_item.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        
        src_item = QTableWidgetItem(source_path)
        det_item = QTableWidgetItem(details)

        self.log_table.setItem(row, 0, time_item)
        self.log_table.setItem(row, 1, status_item)
        self.log_table.setItem(row, 2, src_item)
        self.log_table.setItem(row, 3, det_item)
        self.log_table.scrollToBottom()

    @Slot(str)
    def log_started(self, source_path: str):
        self._add_log_row("PROCESSING", "#38BDF8", source_path, "Converting PNG to JPEG...")

    @Slot(str, str)
    def log_success(self, source_path: str, out_path: str):
        self._add_log_row("SUCCESS", "#10B981", source_path, f"Saved -> {out_path}")

    @Slot(str, str)
    def log_skipped(self, source_path: str, reason: str):
        self._add_log_row("SKIPPED", "#F59E0B", source_path, reason)

    @Slot(str, str)
    def log_failed(self, source_path: str, err: str):
        self._add_log_row("FAILED", "#EF4444", source_path, f"Error: {err}")

    @Slot(dict)
    def update_stats_ui(self, stats: dict):
        self.lbl_processed.setText(f"Processed: {stats['processed']}")
        self.lbl_success.setText(f"Successful: {stats['success']}")
        self.lbl_skipped.setText(f"Skipped: {stats['skipped']}")
        self.lbl_failed.setText(f"Failed: {stats['failed']}")

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    window = MainWindow()
    if not window.config.get("start_minimized", False):
        window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
