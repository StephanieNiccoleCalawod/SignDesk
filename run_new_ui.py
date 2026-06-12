import sys
import os

# Add the project root to the python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from PyQt6.QtWidgets import QApplication
from theme.styles import build_qss
from theme.themes import set_theme
from components.layout.shell import MainWindowShell
from modules.vision.ui import CameraPracticePage

def main():
    app = QApplication(sys.argv)
    
    # Initialize light theme
    set_theme(is_dark=False)
    app.setStyleSheet(build_qss())
    
    # Create shell
    shell = MainWindowShell(app=app)
    
    # Initialize pages
    camera_page = CameraPracticePage(app=app, username="TestUser")
    
    # Register pages with shell
    shell.add_page("camera", camera_page)
    
    # Navigate to camera practice by default
    shell.navigate("camera")
    
    shell.setWindowTitle("SignDesk UI Refactor - Camera Practice Validation")
    shell.resize(1000, 650)
    shell.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
