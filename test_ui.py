import sys
import traceback
import os
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
try:
    import customtkinter as ctk
    app = ctk.CTk()
    from modules.vision.ui import GestureDetectionPage
    GestureDetectionPage(app, app, 'test')
except Exception as e:
    traceback.print_exc()
