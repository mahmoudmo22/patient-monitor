import sys
from PyQt5.QtWidgets import QApplication
from GUI import ECGMonitorGUI  # Make sure this filename is correct

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ECGMonitorGUI()
    window.show()
    sys.exit(app.exec_())