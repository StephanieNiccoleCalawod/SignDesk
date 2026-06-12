from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget
from PyQt6.QtCore import pyqtSignal

from .sidebar import Sidebar
from components.base_page import BasePage
from theme.themes import c
from core.theme import ThemeSignal

class MainWindowShell(QWidget):
    """
    The main application shell that manages the persistent Sidebar 
    and the central QStackedWidget for page navigation.
    """
    
    logout_requested = pyqtSignal()
    
    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        self.app = app
        self.setStyleSheet(f"background-color: {c('app_bg')};")
        
        try:
            ThemeSignal.instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass
        
        self.pages = {}
        
        # Main Layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = Sidebar(self)
        self.sidebar.navigation_requested.connect(self._navigate_to)
        self.sidebar.logout_requested.connect(self.logout_requested.emit)
        self.layout.addWidget(self.sidebar)
        
        # Main Content Area
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        self.stacked_widget = QStackedWidget()
        self.content_layout.addWidget(self.stacked_widget)
        
        self.layout.addWidget(self.content_area, stretch=1)
        
        self.current_page_key = None

    def add_page(self, key: str, page: BasePage):
        """Register a page with the shell."""
        self.pages[key] = page
        self.stacked_widget.addWidget(page)
        
    def navigate(self, key: str):
        """External navigation trigger."""
        self.sidebar.set_active_item(key)
        self._navigate_to(key)

    def _navigate_to(self, key: str):
        if key not in self.pages:
            print(f"[Shell] Page '{key}' not registered yet.")
            return
            
        if self.current_page_key == key:
            return
            
        # Deactivate current
        if self.current_page_key and self.current_page_key in self.pages:
            if hasattr(self.pages[self.current_page_key], "deactivate"):
                self.pages[self.current_page_key].deactivate()
            
        # Hide the persistent sidebar only for the settings page
        if key == "settings":
            self.sidebar.hide()
        else:
            self.sidebar.show()

        # Activate new
        self.current_page_key = key
        self.stacked_widget.setCurrentWidget(self.pages[key])
        if hasattr(self.pages[key], "activate"):
            self.pages[key].activate()

    def _on_theme_changed(self, is_dark: bool):
        self.setStyleSheet(f"background-color: {c('app_bg')};")
