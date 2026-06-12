from .themes import c
from .typography import FONT_FAMILY, SIZE_BASE

def build_qss() -> str:
    """Generate global QSS using the current theme tokens."""
    return f"""
        * {{
            font-family: {FONT_FAMILY};
        }}

        QWidget {{
            background-color: {c("app_bg")};
            color: {c("text_primary")};
            font-size: {SIZE_BASE}px;
        }}

        /* Scrollbars */
        QScrollBar:vertical {{
            background: {c("app_bg")};
            width: 8px;
            margin: 0;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {c("card_border")};
            border-radius: 4px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {c("text_muted")};
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        
        QScrollBar:horizontal {{
            background: {c("app_bg")};
            height: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal {{
            background: {c("card_border")};
            border-radius: 4px;
            min-width: 30px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {c("text_muted")};
        }}
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{
            width: 0;
        }}

        /* Scroll area */
        QScrollArea {{
            border: none;
            background-color: transparent;
        }}
        
        /* Dialogs and Popups */
        QDialog, QMessageBox {{
            background-color: {c("card_bg")};
        }}
    """
