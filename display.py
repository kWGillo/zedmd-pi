"""Proprietario esclusivo del pannello LED.

Un solo processo puo' pilotare i GPIO: tutto il rendering passa da qui.
Le sorgenti non disegnano mai direttamente, producono immagini PIL.
"""

import os
import threading


class Display:
    def __init__(self, cfg):
        panel = cfg["panel"]

        # Il catalogo dei profili di registro va indicato prima di creare la matrice.
        os.environ["SPWM_PROFILE_DIR"] = panel["profile_dir"]

        from rgbmatrix import RGBMatrix, RGBMatrixOptions

        options = RGBMatrixOptions()
        options.rows = panel["rows"]
        options.cols = panel["cols"]
        options.chain_length = panel["chain"]
        options.parallel = panel["parallel"]
        options.hardware_mapping = panel["hardware_mapping"]
        options.gpio_slowdown = panel["slowdown"]
        options.panel_type = panel["panel_type"]
        options.spwm_row_address_type = panel["spwm_row_address_type"]
        options.spwm_scan_rows = panel["spwm_scan_rows"]
        options.spwm_data_layout = panel["spwm_data_layout"]
        options.spwm_register_config = panel["spwm_register_config"]
        options.limit_refresh_rate_hz = panel["limit_refresh"]
        options.pwm_bits = panel["pwm_bits"]
        options.brightness = cfg["display"]["brightness"]
        # Senza questo la libreria perde l'accesso al catalogo profili.
        options.drop_privileges = False

        self.matrix = RGBMatrix(options=options)
        self.canvas = self.matrix.CreateFrameCanvas()
        self.width = panel["cols"] * panel["chain"]
        self.height = panel["rows"]
        self._lock = threading.Lock()

    def set_brightness(self, value):
        value = max(0, min(100, int(value)))
        with self._lock:
            self.matrix.brightness = value
        return value

    def show(self, image):
        """Mostra un'immagine PIL RGB della dimensione del display."""
        with self._lock:
            self.canvas.SetImage(image, 0, 0)
            self.canvas = self.matrix.SwapOnVSync(self.canvas)

    def clear(self):
        with self._lock:
            self.matrix.Clear()
