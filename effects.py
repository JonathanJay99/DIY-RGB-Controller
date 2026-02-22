"""
Effekt-Engine — Berechnet RGB-Animationen in einem eigenen Thread.
Alle Effekte sind CPU-schonend implementiert mit konfigurierbarer FPS-Rate.
"""

import colorsys
import math
import threading
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Verfügbare Effekte
EFFECT_NAMES = [
    "Static",
    "Breathing",
    "Rainbow",
    "Color Cycle",
    "Wave",
    "Spectrum",
]


def _hsv_to_rgb(h: float, s: float = 1.0, v: float = 1.0) -> tuple[int, int, int]:
    """Konvertiert HSV (0-1 Bereich) zu RGB (0-255 Bereich)."""
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


class EffectEngine:
    """Berechnet und wendet RGB-Effekte an."""

    def __init__(self, controller):
        self.controller = controller
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

        # Effekt-Parameter
        self.effect_name: str = "Static"
        self.primary_color: tuple[int, int, int] = (255, 0, 0)
        self.secondary_color: tuple[int, int, int] = (0, 0, 255)
        self.brightness: float = 1.0  # 0.0 - 1.0
        self.speed: float = 0.5       # 0.0 - 1.0
        self.reverse_direction: bool = False
        self.fps: int = 30
        self.active_devices: list[int] = []  # Geräte-Indizes die gesteuert werden

        # Interner State
        self._frame: int = 0

    def start(self):
        """Startet den Effekt-Thread."""
        if self._running:
            self.stop()
        self._running = True
        self._frame = 0
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Effekt-Engine gestartet: %s", self.effect_name)

    def stop(self):
        """Stoppt den Effekt-Thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        logger.info("Effekt-Engine gestoppt.")

    def is_running(self) -> bool:
        return self._running

    def set_effect(self, name: str):
        """Wechselt den aktiven Effekt."""
        if name in EFFECT_NAMES:
            with self._lock:
                self.effect_name = name
                self._frame = 0
            logger.info("Effekt gewechselt zu: %s", name)

    def set_primary_color(self, r: int, g: int, b: int):
        with self._lock:
            self.primary_color = (r, g, b)

    def set_secondary_color(self, r: int, g: int, b: int):
        with self._lock:
            self.secondary_color = (r, g, b)

    def set_brightness(self, value: float):
        with self._lock:
            self.brightness = max(0.0, min(1.0, value))

    def set_speed(self, value: float):
        with self._lock:
            self.speed = max(0.01, min(1.0, value))

    def set_reverse_direction(self, reverse: bool):
        with self._lock:
            self.reverse_direction = reverse

    def _apply_brightness(self, color: tuple[int, int, int]) -> tuple[int, int, int]:
        """Wendet Helligkeit auf eine Farbe an."""
        return (
            int(color[0] * self.brightness),
            int(color[1] * self.brightness),
            int(color[2] * self.brightness),
        )

    def _run_loop(self):
        """Haupt-Render-Loop — läuft im eigenen Thread."""
        while self._running:
            frame_start = time.monotonic()

            try:
                with self._lock:
                    effect = self.effect_name
                    devices = list(self.active_devices) if self.active_devices else list(
                        range(len(self.controller.devices))
                    )

                # Motherboards filtern um Flackern zu vermeiden (nur jedes 3. Frame updaten)
                update_devices = []
                for idx in devices:
                    if idx < len(self.controller.devices):
                        dev = self.controller.devices[idx]
                        is_mb = hasattr(dev, "type") and dev.type == 0 # 0 = Motherboard
                        # Wenn Motherboard, update nur alle 3 Frames (etwa 10 FPS bei 30 FPS target)
                        if is_mb and self._frame % 3 != 0:
                            continue
                        update_devices.append(idx)

                # Für statische Effekte brauchen wir keinen Loop (außer Prism S, der braucht Continuous Updates)
                if effect == "Static":
                    self._apply_static(update_devices)
                    
                    # Überprüfe ob ein Prism S dabei ist (braucht ständige Updates sonst geht er aus)
                    has_prism = any(getattr(self.controller.devices[idx], "name", "") == "PrismRGB Prism S (Strimer)" for idx in update_devices if idx < len(self.controller.devices))
                    
                    if not has_prism:
                        while self._running and self.effect_name == "Static":
                            time.sleep(0.5)
                        continue
                    # Falls Prism S vorhanden, rennt der Loop mit normalen FPS weiter und befeuert den Strimer!
                    self._apply_static(devices)
                    # Static braucht keine ständige Aktualisierung
                    continue

                # Animierte Effekte
                if effect == "Breathing":
                    self._apply_breathing(update_devices)
                elif effect == "Rainbow":
                    self._apply_rainbow(update_devices)
                elif effect == "Color Cycle":
                    self._apply_color_cycle(update_devices)
                elif effect == "Wave":
                    self._apply_wave(update_devices)
                elif effect == "Spectrum":
                    self._apply_spectrum(update_devices)

                self._frame += 1

            except Exception as exc:
                logger.error("Effekt-Engine Fehler: %s", exc)

            # FPS-Begrenzung
            elapsed = time.monotonic() - frame_start
            target_delay = 1.0 / self.fps
            if elapsed < target_delay:
                time.sleep(target_delay - elapsed)

    # ─── Effekt-Implementierungen ────────────────────────────────────────

    def _apply_static(self, devices: list[int]):
        """Setzt alle LEDs auf die Primärfarbe."""
        color = self._apply_brightness(self.primary_color)
        for dev_idx in devices:
            self.controller.set_device_color(dev_idx, color)

    def _apply_breathing(self, devices: list[int]):
        """Sanftes Ein-/Ausblenden der Primärfarbe."""
        # Sinus-Welle für weiches Pulsieren, Geschwindigkeit beeinflusst Frequenz
        t = self._frame / self.fps
        frequency = 0.3 + self.speed * 1.5
        intensity = (math.sin(t * frequency * 2 * math.pi) + 1) / 2

        color = (
            int(self.primary_color[0] * intensity * self.brightness),
            int(self.primary_color[1] * intensity * self.brightness),
            int(self.primary_color[2] * intensity * self.brightness),
        )
        for dev_idx in devices:
            self.controller.set_device_color(dev_idx, color)

    def _apply_rainbow(self, devices: list[int]):
        """Regenbogen über alle LEDs jedes Geräts verteilt."""
        dir_mult = -1.0 if self.reverse_direction else 1.0
        t = self._frame / self.fps * self.speed * 0.5 * dir_mult

        for dev_idx in devices:
            if dev_idx >= len(self.controller.devices):
                continue
            device = self.controller.devices[dev_idx]
            num_leds = len(device.leds)
            if num_leds == 0:
                continue

            colors = []
            for i in range(num_leds):
                hue = (i / max(num_leds, 1) + t) % 1.0
                rgb = _hsv_to_rgb(hue, 1.0, self.brightness)
                colors.append(rgb)
            self.controller.set_device_colors(dev_idx, colors)

    def _apply_color_cycle(self, devices: list[int]):
        """Langsamer Farbwechsel — alle LEDs gleiche Farbe, Hue rotiert."""
        dir_mult = -1.0 if self.reverse_direction else 1.0
        t = self._frame / self.fps * self.speed * 0.2 * dir_mult
        hue = t % 1.0
        color = _hsv_to_rgb(hue, 1.0, self.brightness)

        for dev_idx in devices:
            self.controller.set_device_color(dev_idx, color)

    def _apply_wave(self, devices: list[int]):
        """Farbwelle — wandernder Gradient über die LEDs."""
        dir_mult = -1.0 if self.reverse_direction else 1.0
        t = self._frame / self.fps * self.speed * dir_mult

        for dev_idx in devices:
            if dev_idx >= len(self.controller.devices):
                continue
            device = self.controller.devices[dev_idx]
            num_leds = len(device.leds)
            if num_leds == 0:
                continue

            colors = []
            for i in range(num_leds):
                phase = (i / max(num_leds, 1)) * 2 * math.pi + t * 3
                # Interpolation zwischen Primär- und Sekundärfarbe
                blend = (math.sin(phase) + 1) / 2
                r = int((self.primary_color[0] * blend + self.secondary_color[0] * (1 - blend)) * self.brightness)
                g = int((self.primary_color[1] * blend + self.secondary_color[1] * (1 - blend)) * self.brightness)
                b = int((self.primary_color[2] * blend + self.secondary_color[2] * (1 - blend)) * self.brightness)
                colors.append((r, g, b))
            self.controller.set_device_colors(dev_idx, colors)

    def _apply_spectrum(self, devices: list[int]):
        """Spektrum-Animation — Regenbogen-Welle die sich über alle Geräte bewegt."""
        dir_mult = -1.0 if self.reverse_direction else 1.0
        t = self._frame / self.fps * self.speed * 0.3 * dir_mult
        total_leds = 0
        device_led_offsets = []

        for dev_idx in devices:
            if dev_idx >= len(self.controller.devices):
                device_led_offsets.append((dev_idx, 0, 0))
                continue
            device = self.controller.devices[dev_idx]
            num = len(device.leds)
            device_led_offsets.append((dev_idx, total_leds, num))
            total_leds += num

        if total_leds == 0:
            return

        for dev_idx, offset, num_leds in device_led_offsets:
            if num_leds == 0:
                continue
            colors = []
            for i in range(num_leds):
                global_pos = offset + i
                hue = (global_pos / max(total_leds, 1) + t) % 1.0
                rgb = _hsv_to_rgb(hue, 1.0, self.brightness)
                colors.append(rgb)
            self.controller.set_device_colors(dev_idx, colors)
