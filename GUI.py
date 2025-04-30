import sys
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QComboBox, QLabel, QFrame, QSplitter, 
                            QTabWidget, QGridLayout, QLCDNumber, QFileDialog, QMessageBox)
from PyQt5.QtCore import QTimer, Qt, pyqtSlot, QSize
from PyQt5.QtGui import QColor, QPalette, QFont
import pyqtgraph as pg
import random
import os

# Import non-GUI modules (no circular import)
from ECG_Processor import ECGProcessor
from Alarm_System import AlarmSystem
from Data_Loader import ECGDataLoader

class ECGMonitorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize processor and alarm
        self.processor = ECGProcessor()
        self.alarm = AlarmSystem()
        self.data_loader = ECGDataLoader(self)
        
        # Set up the interface
        self.setWindowTitle("ECG Monitoring System")
        self.setMinimumSize(1200, 800)
        self.setup_ui()
        
        # Initialize data and timer
        self.data_index = 0
        self.current_data = self.load_sample_data("normal")
        self.data_buffer = []
        
        # Set up timer for real-time updates (50ms = 20fps)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(50)
        
        # Patient info (would come from a database in a real system)
        self.patient_id = "P12345"
        self.patient_name = "John Doe"
        self.update_patient_info()

    def setup_ui(self):
        # Create central widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Create header with patient info and status
        header_layout = self.create_header()
        main_layout.addLayout(header_layout)
        
        # Create main content
        content = QSplitter(Qt.Horizontal)
        
        # Left panel with ECG display
        left_panel = self.create_ecg_panel()
        content.addWidget(left_panel)
        
        # Right panel with vital signs and controls
        right_panel = self.create_right_panel()
        content.addWidget(right_panel)
        
        # Set stretch factors
        content.setSizes([700, 300])
        main_layout.addWidget(content, 1)
        
        # Create footer with status and controls
        footer = self.create_footer()
        main_layout.addWidget(footer)
        
        # Set central widget
        self.setCentralWidget(central_widget)
        
        # Set stylesheet
        self.apply_stylesheet()

    def create_header(self):
        header = QHBoxLayout()
        
        # Patient info section
        self.patient_info_label = QLabel()
        self.patient_info_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.patient_info_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        
        # Status section
        self.status_label = QLabel("Status: Monitoring")
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.status_label.setStyleSheet("font-size: 14pt; color: green;")
        
        header.addWidget(self.patient_info_label, 1)
        header.addWidget(self.status_label, 1)
        
        return header

    def create_ecg_panel(self):
        # Create widget and layout
        ecg_panel = QWidget()
        layout = QVBoxLayout(ecg_panel)
        
        # Title
        title = QLabel("ECG Monitor")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        layout.addWidget(title)
        
        # Create plot widget
        self.ecg_plot = pg.PlotWidget()
        self.ecg_plot.setBackground('k')
        self.ecg_plot.showGrid(x=True, y=True, alpha=0.3)
        self.ecg_plot.setLabel('left', 'Amplitude (mV)')
        self.ecg_plot.setLabel('bottom', 'Time (s)')
        self.ecg_plot.setYRange(-1.5, 1.5)
        
        # Create plot line
        self.ecg_curve = self.ecg_plot.plot(pen=pg.mkPen(color='g', width=2))
        
        layout.addWidget(self.ecg_plot, 1)
        
        # Rhythm classification label
        self.rhythm_label = QLabel("Current Rhythm: Normal Sinus Rhythm")
        self.rhythm_label.setAlignment(Qt.AlignCenter)
        self.rhythm_label.setStyleSheet("font-size: 14pt; color: green; padding: 10px; border: 1px solid #ccc; border-radius: 5px;")
        layout.addWidget(self.rhythm_label)
        
        return ecg_panel

    def create_right_panel(self):
        panel = QTabWidget()
        
        # Vital signs tab
        vitals_tab = QWidget()
        vitals_layout = QGridLayout(vitals_tab)
        
        # Heart rate display
        hr_frame = self.create_vital_display("HR", "bpm", 75)
        vitals_layout.addWidget(hr_frame, 0, 0)
        
        # Blood pressure display
        bp_frame = self.create_vital_display("BP", "mmHg", "120/80")
        vitals_layout.addWidget(bp_frame, 0, 1)
        
        # Oxygen saturation display
        spo2_frame = self.create_vital_display("SpO2", "%", 98)
        vitals_layout.addWidget(spo2_frame, 1, 0)
        
        # Respiration rate display
        rr_frame = self.create_vital_display("RESP", "bpm", 16)
        vitals_layout.addWidget(rr_frame, 1, 1)
        
        # Temperature display
        temp_frame = self.create_vital_display("TEMP", "°C", 36.8)
        vitals_layout.addWidget(temp_frame, 2, 0, 1, 2)
        
        panel.addTab(vitals_tab, "Vital Signs")
        
        # Settings tab
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        
        # Data source selection
        data_source_layout = QHBoxLayout()
        data_source_layout.addWidget(QLabel("ECG Source:"))
        
        self.data_source = QComboBox()
        self.data_source.addItems(["Normal", "Ventricular Fibrillation", "Atrial Fibrillation", "Bradycardia"])
        self.data_source.currentTextChanged.connect(self.change_data_source)
        data_source_layout.addWidget(self.data_source)
        
        settings_layout.addLayout(data_source_layout)
        settings_layout.addStretch(1)
        
        panel.addTab(settings_tab, "Settings")
        
        return panel

    def create_vital_display(self, title, unit, value):
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        frame.setLineWidth(2)
        
        layout = QVBoxLayout(frame)
        
        # Title
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Value display
        if isinstance(value, str):
            value_label = QLabel(str(value))
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setStyleSheet("font-size: 20pt; font-weight: bold; color: white;")
            layout.addWidget(value_label)
        else:
            value_display = QLCDNumber()
            value_display.setDigitCount(5)
            value_display.setSegmentStyle(QLCDNumber.Flat)
            value_display.display(value)
            layout.addWidget(value_display)
        
        # Unit
        unit_label = QLabel(unit)
        unit_label.setAlignment(Qt.AlignCenter)
        unit_label.setStyleSheet("font-size: 10pt;")
        layout.addWidget(unit_label)
        
        return frame

    def create_footer(self):
        footer = QFrame()
        footer.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        footer.setMaximumHeight(60)
        
        layout = QHBoxLayout(footer)
        
        # Alarm controls
        alarm_label = QLabel("Alarm:")
        layout.addWidget(alarm_label)
        
        self.alarm_status = QLabel("ON")
        self.alarm_status.setStyleSheet("color: green; font-weight: bold;")
        layout.addWidget(self.alarm_status)
        
        alarm_toggle = QPushButton("Toggle Alarm")
        alarm_toggle.clicked.connect(self.toggle_alarm)
        layout.addWidget(alarm_toggle)
        
        # Add a load data button
        load_btn = QPushButton("Load Data")
        load_btn.clicked.connect(self.load_ecg_data)
        layout.addWidget(load_btn)
        
        layout.addStretch(1)
        
        # Print button
        print_btn = QPushButton("Print Report")
        print_btn.clicked.connect(self.print_report)
        layout.addWidget(print_btn)
        
        return footer
    
    def apply_stylesheet(self):
        dark_style = """
        QMainWindow, QWidget {
            background-color: #2D2D30;
            color: #FFFFFF;
        }
        
        QFrame {
            background-color: #252526;
            border-radius: 5px;
            padding: 5px;
        }
        
        QPushButton {
            background-color: #0078D7;
            color: white;
            border-radius: 5px;
            padding: 8px 16px;
            font-weight: bold;
        }
        
        QPushButton:hover {
            background-color: #0086F0;
        }
        
        QPushButton:pressed {
            background-color: #00497E;
        }
        
        QTabWidget::pane {
            border: 1px solid #3E3E42;
            background-color: #252526;
        }
        
        QTabBar::tab {
            background-color: #2D2D30;
            color: #FFFFFF;
            padding: 8px 16px;
        }
        
        QTabBar::tab:selected {
            background-color: #0078D7;
        }
        
        QComboBox {
            background-color: #333337;
            color: white;
            padding: 5px;
            border: 1px solid #3E3E42;
        }
        
        QLCDNumber {
            background-color: #000000;
            color: #00FF00;
            border: 1px solid #3E3E42;
        }
        """
        self.setStyleSheet(dark_style)
    
    def update_patient_info(self):
        self.patient_info_label.setText(f"Patient: {self.patient_name} (ID: {self.patient_id})")
    
    def load_sample_data(self, data_type):
        """Load sample data or generate synthetic data if files are not available"""
        # In a real application, you'd load actual data files
        # For this example, we'll generate synthetic data
        time = np.arange(0, 10, 0.01)
        
        if data_type == "normal":
            # Generate normal ECG-like signal
            frequency = 1.0  # 1 Hz for heart rate of 60 bpm
            amplitude = 1.0
            data = amplitude * np.sin(2 * np.pi * frequency * time)
            
            # Add QRS complex simulation
            for i in range(int(len(time)/100)):
                center = i * 100 + 50
                if center < len(data):
                    data[center-5:center] = np.linspace(0, 2, 5)
                    data[center:center+5] = np.linspace(2, -1, 5)
                    data[center+5:center+10] = np.linspace(-1, 0, 5)
            
        elif data_type == "vfib":
            # Ventricular Fibrillation - chaotic, rapid, irregular
            data = np.zeros_like(time)
            for i in range(1, 20):
                freq = 0.5 + i/3
                data += np.sin(2 * np.pi * freq * time) * np.random.uniform(0.05, 0.2)
        
        elif data_type == "afib":
            # Atrial Fibrillation - irregular rhythm with normal QRS
            data = np.zeros_like(time)
            
            # Irregular RR intervals
            rr_intervals = np.random.uniform(0.5, 1.5, int(len(time)/60))
            next_beat = 0
            
            for interval in rr_intervals:
                beat_time = next_beat
                next_beat += interval
                
                if int(beat_time * 100) >= len(time):
                    break
                
                # Create QRS complex
                center = int(beat_time * 100)
                qrs_width = 10
                if center+qrs_width < len(data):
                    data[center:center+3] = np.linspace(0, 2, 3)
                    data[center+3:center+6] = np.linspace(2, -1, 3)
                    data[center+6:center+qrs_width] = np.linspace(-1, 0, 4)
        
        elif data_type == "bradycardia":
            # Bradycardia - slow heart rate but normal morphology
            frequency = 0.5  # 0.5 Hz for heart rate of 30 bpm
            amplitude = 1.0
            data = amplitude * np.sin(2 * np.pi * frequency * time)
            
            # Add QRS complex simulation (but fewer of them)
            for i in range(int(len(time)/200)):  # Twice the interval of normal
                center = i * 200 + 100
                if center < len(data):
                    data[center-5:center] = np.linspace(0, 2, 5)
                    data[center:center+5] = np.linspace(2, -1, 5)
                    data[center+5:center+10] = np.linspace(-1, 0, 5)
        
        else:
            # Default to normal
            data = amplitude * np.sin(2 * np.pi * frequency * time)
        
        # Add some noise
        noise = np.random.normal(0, 0.05, len(data))
        data += noise
        
        return {'time': time, 'ecg': data}

    def update_plot(self):
        # Get next data point
        if self.data_index >= len(self.current_data['ecg']):
            self.data_index = 0
        
        # Add new point to buffer
        self.data_buffer.append(self.current_data['ecg'][self.data_index])
        
        # Keep buffer to reasonable size (10 seconds at 100 Hz)
        if len(self.data_buffer) > 1000:
            self.data_buffer.pop(0)
        
        # Update plot
        self.ecg_curve.setData(self.data_buffer)
        
        # Analyze rhythm every 2 seconds (200 points at 100 Hz)
        if self.data_index % 200 == 0 and len(self.data_buffer) >= 400:
            # In a real application, use the processor to analyze the actual data
            self.analyze_actual_rhythm()
        
        self.data_index += 1
    
    def analyze_rhythm(self):
        # In a real application, this would use sophisticated algorithms
        # Here we'll just use the known data source as a shortcut
        current_source = self.data_source.currentText().lower()
        
        if "ventricular" in current_source:
            rhythm_type = "Ventricular Fibrillation"
            self.update_rhythm_display(rhythm_type, "red", True)
        elif "atrial" in current_source:
            rhythm_type = "Atrial Fibrillation"
            self.update_rhythm_display(rhythm_type, "orange", True)
        elif "brady" in current_source:
            rhythm_type = "Bradycardia"
            self.update_rhythm_display(rhythm_type, "yellow", True)
        else:
            rhythm_type = "Normal Sinus Rhythm"
            self.update_rhythm_display(rhythm_type, "green", False)
    
    def update_rhythm_display(self, rhythm_text, color, alarm):
        self.rhythm_label.setText(f"Current Rhythm: {rhythm_text}")
        self.rhythm_label.setStyleSheet(f"font-size: 14pt; color: {color}; padding: 10px; border: 1px solid #ccc; border-radius: 5px;")
        
        if alarm and self.alarm.is_enabled():
            self.alarm.trigger_alarm(rhythm_text)
            # Flash the status label
            self.status_label.setText(f"ALERT: {rhythm_text} Detected!")
            self.status_label.setStyleSheet("font-size: 14pt; color: red; font-weight: bold;")
        else:
            self.status_label.setText("Status: Monitoring")
            self.status_label.setStyleSheet("font-size: 14pt; color: green;")
    
    def change_data_source(self, source_name):
        # Convert combobox text to lowercase key
        key = source_name.lower().replace(" ", "_")
        if "ventricular" in key:
            key = "vfib"
        elif "atrial" in key:
            key = "afib"
        elif "brady" in key:
            key = "bradycardia"
        else:
            key = "normal"
        
        # Load the new data
        self.current_data = self.load_sample_data(key)
        self.data_index = 0
        self.data_buffer = []  # Clear buffer for new data
    
    def toggle_alarm(self):
        if self.alarm.is_enabled():
            self.alarm.disable()
            self.alarm_status.setText("OFF")
            self.alarm_status.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.alarm.enable()
            self.alarm_status.setText("ON")
            self.alarm_status.setStyleSheet("color: green; font-weight: bold;")
    
    def print_report(self):
        # In a real app, this would generate a PDF report
        print("Printing ECG report...")
        self.status_label.setText("Status: Printing report...")
        # Simulate delay
        QTimer.singleShot(2000, lambda: self.status_label.setText("Status: Monitoring"))

    def load_ecg_data(self):
        """Load ECG data from file"""
        # Load the data
        data = self.data_loader.load_file()
        if data is not None:
            # Stop the timer temporarily
            self.timer.stop()
            
            # Replace current data with loaded data
            self.current_data = data
            self.data_index = 0
            self.data_buffer = []  # Clear buffer
            
            # Update file info display
            file_info = self.data_loader.get_file_info()
            info_text = f"File: {file_info['filename']} | Duration: {file_info['duration']} | Rate: {file_info['sampling_rate']}"
            self.status_label.setText(info_text)
            
            # Restart the timer
            self.timer.start(50)
        else:
            # Don't display anything if no file was loaded
            self.status_label.setText("Status: No file loaded")

    def analyze_actual_rhythm(self):
        """Analyze the actual ECG data"""
        if len(self.data_buffer) < 400:  # Need sufficient data for analysis
            return
        
        # Use the processor to analyze
        rhythm_type = self.processor.detect_rhythm(np.array(self.data_buffer[-400:]))
        
        # Update display based on detected rhythm
        if "Ventricular" in rhythm_type:
            self.update_rhythm_display(rhythm_type, "red", True)
        elif "Atrial" in rhythm_type:
            self.update_rhythm_display(rhythm_type, "orange", True)
        elif "Brady" in rhythm_type:
            self.update_rhythm_display(rhythm_type, "yellow", True)
        else:
            self.update_rhythm_display(rhythm_type, "green", False)