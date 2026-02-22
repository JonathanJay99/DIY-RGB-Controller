"""
RGB Controller — OpenRGB SDK Verbindung & Geräte-Management.
Lightweight Wrapper um die OpenRGB Python Library.
"""

import threading
import time
import logging
import json
import os
from typing import Optional

from openrgb import OpenRGBClient
from openrgb.utils import RGBColor, DeviceType

logger = logging.getLogger(__name__)


# Gerätetyp-Labels für die GUI
DEVICE_TYPE_LABELS = {
    DeviceType.MOTHERBOARD: "Motherboard",
    DeviceType.DRAM: "RAM",
    DeviceType.GPU: "GPU",
    DeviceType.COOLER: "Kühler",
    DeviceType.LEDSTRIP: "LED Strip",
    DeviceType.KEYBOARD: "Tastatur",
    DeviceType.MOUSE: "Maus",
    DeviceType.MOUSEMAT: "Mauspad",
    DeviceType.HEADSET: "Headset",
    DeviceType.HEADSET_STAND: "Headset-Ständer",
    DeviceType.GAMEPAD: "Gamepad",
    DeviceType.LIGHT: "Licht",
    DeviceType.SPEAKER: "Lautsprecher",
    DeviceType.UNKNOWN: "Unbekannt",
}


class RGBController:
    """Verwaltet die Verbindung zum OpenRGB SDK Server und steuert alle Geräte."""

    def __init__(self, host: str = "127.0.0.1", port: int = 6742):
        self.host = host
        self.port = port
        self.client: Optional[OpenRGBClient] = None
        self.devices: list = []
        self.connected = False
        self._lock = threading.Lock()
        
        # Lade externe Konfiguration (z.B. für Geräte-spezifische Overrides per User)
        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Lädt hardware-spezifische Settings aus einer config.json Datei."""
        default_config = {
            "razer_controller_zones": [60, 60, 50, 40, 35, 80]
        }
        if not os.path.exists(self.config_file):
            try:
                with open(self.config_file, "w", encoding="utf-8") as f:
                    json.dump(default_config, f, indent=4)
                return default_config
            except Exception as e:
                logger.error("Konnte config.json nicht erstellen: %s", e)
                return default_config
                
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Fehler beim Lesen der config.json: %s", e)
            return default_config

    def connect(self) -> bool:
        """Verbindet zum OpenRGB SDK Server. Gibt True bei Erfolg zurück."""
        try:
            self.client = OpenRGBClient(self.host, self.port, name="DIY RGB Controller")
            
            # Razer Chroma Controller Auto-Resize via config.json
            for device in self.client.devices:
                if "Razer" in device.name and "Controller" in device.name:
                    try:
                        sizes = self.config.get("razer_controller_zones", [])
                        if not sizes:
                            continue
                        for i, size in enumerate(sizes):
                            if i < len(device.zones):
                                device.zones[i].resize(size)
                    except Exception as e:
                        logger.error("Fehler beim Resizen der Razer Zonen: %s", e)
            
            self.client.update()
            self.devices = list(self.client.devices)
            
            # Lokale HID Controller suchen
            import prism_s
            prism_devices = prism_s.find_prism_s_devices()
            self.devices.extend(prism_devices)

            self.connected = True
            logger.info(
                "Verbunden mit OpenRGB Server (%s:%d) — %d Geräte gefunden",
                self.host, self.port, len(self.devices),
            )
            return True
        except ConnectionRefusedError:
            logger.error(
                "Verbindung zu OpenRGB fehlgeschlagen. Ist der SDK Server aktiv? (%s:%d)",
                self.host, self.port,
            )
            self.connected = False
            return False
        except Exception as exc:
            logger.error("OpenRGB Verbindungsfehler: %s", exc)
            self.connected = False
            return False

    def disconnect(self):
        """Trennt die Verbindung zum OpenRGB Server."""
        with self._lock:
            if self.client:
                try:
                    self.client.disconnect()
                except Exception:
                    pass
                self.client = None
                self.devices = []
                self.connected = False
                logger.info("Verbindung zu OpenRGB getrennt.")

    def reconnect(self) -> bool:
        """Versucht eine erneute Verbindung."""
        self.disconnect()
        time.sleep(1)
        return self.connect()

    def get_devices(self) -> list:
        """Gibt alle erkannten Geräte zurück."""
        if not self.connected:
            return []
        return self.devices

    def get_device_info(self, device) -> dict:
        """Gibt Infos über ein Gerät als Dict zurück (für GUI)."""
        device_type = DEVICE_TYPE_LABELS.get(device.type, "Unbekannt")
        return {
            "name": device.name,
            "type": device_type,
            "num_leds": len(device.leds),
            "modes": [m.name for m in device.modes],
            "active_mode": device.active_mode,
        }

    def set_device_color(self, device_index: int, color: tuple[int, int, int]):
        """Setzt alle LEDs eines Geräts auf eine Farbe (R, G, B)."""
        with self._lock:
            if not self.connected or device_index >= len(self.devices):
                return
            try:
                device = self.devices[device_index]
                rgb = RGBColor(*color)
                device.set_color(rgb)
            except Exception as exc:
                logger.error("Fehler beim Setzen der Farbe für Gerät %d: %s", device_index, exc)

    def set_device_colors(self, device_index: int, colors: list[tuple[int, int, int]]):
        """Setzt individuelle LED-Farben für ein Gerät."""
        with self._lock:
            if not self.connected or device_index >= len(self.devices):
                return
            try:
                device = self.devices[device_index]
                rgb_colors = [RGBColor(*c) for c in colors]
                device.set_colors(rgb_colors)
            except Exception as exc:
                logger.error("Fehler beim Setzen der Farben für Gerät %d: %s", device_index, exc)

    def set_device_mode(self, device_index: int, mode_name: str):
        """Setzt den Modus eines Geräts (z.B. 'Direct', 'Static')."""
        with self._lock:
            if not self.connected or device_index >= len(self.devices):
                return
            try:
                device = self.devices[device_index]
                device.set_mode(mode_name)
            except Exception as exc:
                logger.error("Fehler beim Setzen des Modus für Gerät %d: %s", device_index, exc)

    def set_all_color(self, color: tuple[int, int, int]):
        """Setzt alle Geräte auf eine Farbe."""
        for i in range(len(self.devices)):
            self.set_device_color(i, color)

    def turn_off_all(self):
        """Schaltet alle LEDs aus (schwarz)."""
        self.set_all_color((0, 0, 0))

    def set_all_to_direct_mode(self):
        """Setzt alle Geräte auf 'Direct' Modus für Software-Kontrolle."""
        for i, device in enumerate(self.devices):
            for mode in device.modes:
                if mode.name.lower() == "direct":
                    self.set_device_mode(i, "Direct")
                    break
