from PyQt6.QtWidgets import QWidget

class BasePage(QWidget):
    """
    Base class for all SignDesk pages managed by MainWindowShell.
    Enforces a strict lifecycle for persistent pages.
    """
    
    def __init__(self, parent=None, app=None, username: str = ""):
        super().__init__(parent)
        self.app = app
        self.username = username
        self.is_active = False

    def activate(self):
        """Called when the page is brought to the foreground."""
        self.is_active = True

    def deactivate(self):
        """Called when the page is hidden. Must pause timers and release resources."""
        self.is_active = False
