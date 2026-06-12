from .colors import *

LightTheme = {
    # Application Base
    "app_bg": APP_BG,
    "sidebar_bg": BLUE_900,
    "topbar_bg": WHITE,
    
    # Text
    "text_primary": BLUE_900,
    "text_secondary": GRAY_500,
    "text_muted": GRAY_400,
    "text_inverse": WHITE,
    
    # Cards
    "card_bg": WHITE,
    "card_bg_secondary": CARD_BG_SECONDARY,
    "card_border": BORDER_LIGHT,
    
    # Accents & Status
    "accent": GREEN_400,
    "success": GREEN_400,
    "success_dark": GREEN_700,
    "success_darker": GREEN_900,
    
    "warning": YELLOW_400,
    "warning_dark": YELLOW_800,
    
    "danger": ORANGE_500,
    "danger_light": RED_100,
    "danger_dark": RED_800,
    
    # Custom Components
    "progress_bg": BORDER_LIGHT,
    "progress_fill": GREEN_400,
    
    "score_pill_bg": FEEDBACK_CORRECT_BG,
    "score_pill_border": FEEDBACK_CORRECT_BORDER,
    "score_pill_text": GREEN_700,
    
    "badge_bg": GRAY_100,
    
    # Camera
    "camera_bg": GRAY_900,
    "camera_overlay_text": "rgba(255, 255, 255, 0.4)",
    
    "sidebar_hover": "rgba(255, 255, 255, 0.06)",
    "sidebar_active": "rgba(255, 255, 255, 0.1)",
    "sidebar_text_muted": "rgba(255, 255, 255, 0.55)",
    "sidebar_text_hover": "rgba(255, 255, 255, 0.8)",
}

DarkTheme = {
    # Application Base
    "app_bg": GRAY_950,
    "sidebar_bg": "#101426",
    "topbar_bg": GRAY_900,
    
    # Text
    "text_primary": GRAY_50,
    "text_secondary": GRAY_400,
    "text_muted": GRAY_500,
    "text_inverse": BLUE_900,
    
    # Cards
    "card_bg": GRAY_900,
    "card_bg_secondary": GRAY_800,
    "card_border": GRAY_800,
    
    # Accents & Status (slightly desaturated/adjusted for dark mode visibility)
    "accent": GREEN_400,
    "success": GREEN_400,
    "success_dark": GREEN_100,
    "success_darker": GREEN_100,
    
    "warning": YELLOW_400,
    "warning_dark": YELLOW_100,
    
    "danger": ORANGE_500,
    "danger_light": RED_800,
    "danger_dark": RED_100,
    
    # Custom Components
    "progress_bg": GRAY_800,
    "progress_fill": GREEN_400,
    
    "score_pill_bg": "rgba(74, 222, 128, 0.15)",
    "score_pill_border": "rgba(74, 222, 128, 0.3)",
    "score_pill_text": GREEN_400,
    
    "badge_bg": GRAY_800,
    
    # Camera
    "camera_bg": GRAY_950,
    "camera_overlay_text": "rgba(255, 255, 255, 0.4)",
    
    "sidebar_hover": "rgba(255, 255, 255, 0.06)",
    "sidebar_active": "rgba(255, 255, 255, 0.1)",
    "sidebar_text_muted": "rgba(255, 255, 255, 0.55)",
    "sidebar_text_hover": "rgba(255, 255, 255, 0.8)",
}

_CURRENT_THEME = LightTheme

def get_theme():
    return _CURRENT_THEME

def set_theme(is_dark: bool):
    global _CURRENT_THEME
    _CURRENT_THEME = DarkTheme if is_dark else LightTheme

def c(key: str) -> str:
    """Get color token from current theme."""
    return _CURRENT_THEME.get(key, "#FF00FF") # Magenta fallback
