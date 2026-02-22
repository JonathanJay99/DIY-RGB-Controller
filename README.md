# 🎨 DIY RGB Controller

Leichtgewichtiger Ersatz für SignalRGB. Steuert deine RGB-Hardware über [OpenRGB](https://openrgb.org/).

## Voraussetzungen

1. **Python 3.11+** installiert
2. **OpenRGB** installiert und gestartet
   - Download: [openrgb.org](https://openrgb.org/)
   - SDK Server aktivieren: `Settings → SDK Server → Enable`
   - Standard-Port: `6820`

## Installation

```bash
cd C:\Pfad\zu\deinem\RGB-Controller
pip install -r requirements.txt
```

## Starten

```bash
# Normal starten
python main.py

# Minimiert im System-Tray starten
python main.py --tray

# Mit bestimmtem Profil starten
python main.py --profile MeinProfil
```

## Features

- 🎨 **6 Effekte:** Static, Breathing, Rainbow, Color Cycle, Wave, Spectrum
- 💾 **Profile:** Speichere und lade deine Lieblings-Einstellungen
- 🖥️ **Geräte-Übersicht:** Zeigt alle erkannten RGB-Geräte
- ⬇️ **System Tray:** Läuft unauffällig im Hintergrund
- ⚡ **Minimal CPU/RAM:** Kein Electron, kein Web-Overhead

## Unterstützte Hardware

Da dieses Tool auf OpenRGB basiert, wird **jede Hardware unterstützt, die auch von OpenRGB unterstützt wird**.

Eine vollständige und aktuelle Liste aller kompatiblen Mainboards, RAM-Module, Lüfter, GPUs und Peripheriegeräte findest du direkt auf der OpenRGB-Website:
👉 [OpenRGB Supported Devices](https://openrgb.org/devices.html)

## Autostart (Optional)

1. Drücke `Win + R`, tippe `shell:startup`, Enter
2. Erstelle eine Verknüpfung zu: `pythonw C:\Pfad\zu\deinem\RGB-Controller\main.py --tray`
