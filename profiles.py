"""
Profil-Manager — Speichert und lädt RGB-Profile als JSON.
"""

import json
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

PROFILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiles")
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def _ensure_profiles_dir():
    """Erstellt den Profil-Ordner falls nötig."""
    os.makedirs(PROFILES_DIR, exist_ok=True)


class Profile:
    """Ein RGB-Profil mit allen Einstellungen."""

    def __init__(self, name: str = "Default"):
        self.name = name
        self.effect: str = "Static"
        self.primary_color: list[int] = [255, 0, 0]
        self.secondary_color: list[int] = [0, 0, 255]
        self.brightness: float = 1.0
        self.speed: float = 0.5
        self.per_device: dict = {}  # device_name -> {effect, color, ...}

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "effect": self.effect,
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "brightness": self.brightness,
            "speed": self.speed,
            "per_device": self.per_device,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        profile = cls(data.get("name", "Default"))
        profile.effect = data.get("effect", "Static")
        profile.primary_color = data.get("primary_color", [255, 0, 0])
        profile.secondary_color = data.get("secondary_color", [0, 0, 255])
        profile.brightness = data.get("brightness", 1.0)
        profile.speed = data.get("speed", 0.5)
        profile.per_device = data.get("per_device", {})
        return profile


class ProfileManager:
    """Verwaltet RGB-Profile (Laden, Speichern, Auflisten)."""

    def __init__(self):
        _ensure_profiles_dir()
        self.profiles: dict[str, Profile] = {}
        self.active_profile_name: str = "Default"
        self._load_all()

    def _load_all(self):
        """Lädt alle Profile aus dem Profil-Ordner."""
        self.profiles.clear()
        if not os.path.exists(PROFILES_DIR):
            self._create_default()
            return

        found_any = False
        for filename in os.listdir(PROFILES_DIR):
            if filename.endswith(".json"):
                filepath = os.path.join(PROFILES_DIR, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    profile = Profile.from_dict(data)
                    self.profiles[profile.name] = profile
                    found_any = True
                    logger.info("Profil geladen: %s", profile.name)
                except Exception as exc:
                    logger.error("Fehler beim Laden von %s: %s", filepath, exc)

        if not found_any:
            self._create_default()

        # Letztes aktives Profil laden
        self._load_config()

    def _create_default(self):
        """Erstellt ein Standard-Profil."""
        default = Profile("Default")
        default.effect = "Rainbow"
        default.brightness = 1.0
        default.speed = 0.5
        self.profiles["Default"] = default
        self.save_profile(default)

    def _load_config(self):
        """Lädt die App-Konfiguration (letztes Profil etc.)."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                self.active_profile_name = config.get("active_profile", "Default")
            except Exception:
                self.active_profile_name = "Default"

    def _save_config(self):
        """Speichert die App-Konfiguration."""
        config = {"active_profile": self.active_profile_name}
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except Exception as exc:
            logger.error("Fehler beim Speichern der Konfiguration: %s", exc)

    def save_profile(self, profile: Profile):
        """Speichert ein Profil als JSON-Datei."""
        _ensure_profiles_dir()
        filepath = os.path.join(PROFILES_DIR, f"{profile.name}.json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)
            self.profiles[profile.name] = profile
            logger.info("Profil gespeichert: %s", profile.name)
        except Exception as exc:
            logger.error("Fehler beim Speichern von Profil %s: %s", profile.name, exc)

    def delete_profile(self, name: str) -> bool:
        """Löscht ein Profil. Default kann nicht gelöscht werden."""
        if name == "Default":
            logger.warning("Default-Profil kann nicht gelöscht werden.")
            return False
        filepath = os.path.join(PROFILES_DIR, f"{name}.json")
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
            self.profiles.pop(name, None)
            if self.active_profile_name == name:
                self.active_profile_name = "Default"
                self._save_config()
            logger.info("Profil gelöscht: %s", name)
            return True
        except Exception as exc:
            logger.error("Fehler beim Löschen von Profil %s: %s", name, exc)
            return False

    def get_active_profile(self) -> Profile:
        """Gibt das aktive Profil zurück."""
        return self.profiles.get(self.active_profile_name, Profile("Default"))

    def set_active_profile(self, name: str):
        """Setzt das aktive Profil."""
        if name in self.profiles:
            self.active_profile_name = name
            self._save_config()
            logger.info("Aktives Profil: %s", name)

    def get_profile_names(self) -> list[str]:
        """Gibt alle Profilnamen zurück."""
        return sorted(self.profiles.keys())

    def create_profile(self, name: str) -> Profile:
        """Erstellt ein neues Profil basierend auf dem aktiven."""
        active = self.get_active_profile()
        new_profile = Profile(name)
        new_profile.effect = active.effect
        new_profile.primary_color = list(active.primary_color)
        new_profile.secondary_color = list(active.secondary_color)
        new_profile.brightness = active.brightness
        new_profile.speed = active.speed
        self.save_profile(new_profile)
        return new_profile
