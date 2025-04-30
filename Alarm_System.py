from PyQt5.QtCore import QTimer, pyqtSignal, QObject
from PyQt5.QtMultimedia import QSound
import os

class AlarmSystem(QObject):
    alarm_triggered = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.enabled = True
        self.active_alarm = None
        self.alarm_timer = QTimer()
        self.alarm_timer.timeout.connect(self.repeat_alarm)
    
    def is_enabled(self):
        return self.enabled
    
    def enable(self):
        self.enabled = True
    
    def disable(self):
        self.enabled = False
        if self.active_alarm:
            self.stop_alarm()
    
    def trigger_alarm(self, alarm_type):
        if not self.enabled:
            return
        
        # Set alarm severity based on type
        if "Ventricular" in alarm_type:
            severity = "high"
        elif "Atrial" in alarm_type or "Brady" in alarm_type:
            severity = "medium"
        else:
            severity = "low"
        
        self.active_alarm = {
            "type": alarm_type,
            "severity": severity
        }
        
        # Play alarm sound
        self.play_alarm_sound(severity)
        
        # Start repeating alarm if high severity
        if severity == "high":
            if not self.alarm_timer.isActive():
                self.alarm_timer.start(3000)  # Repeat every 3 seconds
        
        # Emit signal for notification
        self.alarm_triggered.emit(alarm_type)
    
    def stop_alarm(self):
        self.active_alarm = None
        if self.alarm_timer.isActive():
            self.alarm_timer.stop()
    
    def repeat_alarm(self):
        if self.active_alarm and self.active_alarm["severity"] == "high":
            self.play_alarm_sound(self.active_alarm["severity"])
    
    def play_alarm_sound(self, severity):
        # In a real app, you would play actual sound files
        print(f"ALARM: {severity.upper()} alarm triggered!")
        
        # This would play sound in a real implementation
        # sound_file = f"sounds/{severity}_alarm.wav"
        # if os.path.exists(sound_file):
        #     QSound.play(sound_file)