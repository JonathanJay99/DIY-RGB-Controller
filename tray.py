"""
System Tray — Minimiert die App in den System-Tray.
Bietet Schnellzugriff auf Profile, LEDs-Aus und Beenden.
"""

import threading
import logging
from typing import Optional, Callable

from PIL import Image, ImageDraw
import pystray

logger = logging.getLogger(__name__)


def _create_tray_icon_image() -> Image.Image:
    """Erstellt ein einfaches RGB-Icon für den Tray."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Drei überlappende Kreise in RGB
    draw.ellipse([4, 4, 34, 34], fill=(255, 50, 50, 220))
    draw.ellipse([18, 4, 48, 34], fill=(50, 255, 50, 220))
    draw.ellipse([11, 18, 41, 48], fill=(50, 50, 255, 220))
    # Overlap-Bereich aufhellen
    draw.ellipse([16, 12, 32, 28], fill=(255, 255, 255, 180))
    return img


class TrayManager:
    """Verwaltet das System-Tray-Icon und -Menü."""

    def __init__(
        self,
        on_show: Optional[Callable] = None,
        on_quit: Optional[Callable] = None,
        on_leds_off: Optional[Callable] = None,
        on_profile_change: Optional[Callable] = None,
        profile_names: Optional[list[str]] = None,
    ):
        self.on_show = on_show
        self.on_quit = on_quit
        self.on_leds_off = on_leds_off
        self.on_profile_change = on_profile_change
        self.profile_names = profile_names or []
        self.icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None

    def _build_menu(self) -> pystray.Menu:
        """Erstellt das Tray-Kontextmenü."""
        items = [
            pystray.MenuItem("🎨 DIY RGB Controller öffnen", self._on_show, default=True),
            pystray.Menu.SEPARATOR,
        ]

        # Profile als Untermenü
        if self.profile_names:
            profile_items = []
            for name in self.profile_names:
                profile_items.append(
                    pystray.MenuItem(name, lambda _, n=name: self._on_profile(n))
                )
            items.append(pystray.MenuItem("📁 Profil", pystray.Menu(*profile_items)))
            items.append(pystray.Menu.SEPARATOR)

        items.extend([
            pystray.MenuItem("💡 LEDs Aus", self._on_leds_off_click),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Beenden", self._on_quit_click),
        ])

        return pystray.Menu(*items)

    def start(self):
        """Startet das Tray-Icon im Hintergrund."""
        try:
            icon_image = _create_tray_icon_image()
            self.icon = pystray.Icon(
                name="DIY RGB Controller",
                icon=icon_image,
                title="DIY RGB Controller",
                menu=self._build_menu(),
            )
            self._thread = threading.Thread(target=self.icon.run, daemon=True)
            self._thread.start()
            logger.info("Tray-Icon gestartet.")
        except Exception as exc:
            logger.error("Fehler beim Starten des Tray-Icons: %s", exc)

    def stop(self):
        """Stoppt das Tray-Icon."""
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
        logger.info("Tray-Icon gestoppt.")

    def update_profiles(self, profile_names: list[str]):
        """Aktualisiert die Profilliste im Tray-Menü."""
        self.profile_names = profile_names
        if self.icon:
            self.icon.menu = self._build_menu()

    def _on_show(self, icon=None, item=None):
        if self.on_show:
            self.on_show()

    def _on_quit_click(self, icon=None, item=None):
        self.stop()
        if self.on_quit:
            self.on_quit()

    def _on_leds_off_click(self, icon=None, item=None):
        if self.on_leds_off:
            self.on_leds_off()

    def _on_profile(self, name: str):
        if self.on_profile_change:
            self.on_profile_change(name)
