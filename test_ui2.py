import traceback

try:
    import customtkinter as ctk
    app = ctk.CTk()
    from modules.vision.ui import GestureDetectionPage
    GestureDetectionPage(app, app, "test")
except Exception as e:
    with open("err.txt", "w") as f:
        f.write(traceback.format_exc())
