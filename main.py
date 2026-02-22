"""
DIY RGB Controller — Leichtgewichtiger SignalRGB-Ersatz.
Steuert RGB-Hardware über das OpenRGB SDK.

Nutzung:
    python main.py                  Startet normal
    python main.py --tray           Startet minimiert im Tray
    python main.py --profile Name   Startet mit bestimmtem Profil
"""

import argparse
import logging
import sys
import threading
import atexit
import ctypes

from rgb_controller import RGBController
from effects import EffectEngine
from profiles import ProfileManager
from gui import RGBControllerGUI
from tray import TrayManager

# ─── Logging Setup ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def main():
    # ─── Argumente ───
    parser = argparse.ArgumentParser(description="DIY RGB Controller")
    parser.add_argument("--tray", action="store_true", help="Startet minimiert im System-Tray")
    parser.add_argument("--profile", type=str, default=None, help="Profil beim Start laden")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="OpenRGB Server Host")
    parser.add_argument("--port", type=int, default=6742, help="OpenRGB Server Port")
    args = parser.parse_args()

    logger.info("═══════════════════════════════════════════")
    logger.info("  DIY RGB Controller wird gestartet...")
    logger.info("═══════════════════════════════════════════")

    # ─── OpenRGB Verbindung ───
    controller = RGBController(host=args.host, port=args.port)
    connected = controller.connect()

    if connected:
        logger.info("✅ %d Geräte erkannt:", len(controller.devices))
        for i, dev in enumerate(controller.devices):
            info = controller.get_device_info(dev)
            logger.info("   [%d] %s (%s, %d LEDs)", i, info["name"], info["type"], info["num_leds"])
    else:
        logger.warning("⚠️  Keine Verbindung zu OpenRGB. Programm startet trotzdem (Offline-Modus).")

    # ─── Effekt-Engine ───
    engine = EffectEngine(controller)

    # ─── Profile ───
    profile_manager = ProfileManager()
    if args.profile:
        if args.profile in profile_manager.profiles:
            profile_manager.set_active_profile(args.profile)
            logger.info("Profil '%s' geladen.", args.profile)
        else:
            logger.warning("Profil '%s' nicht gefunden. Verwende '%s'.",
                           args.profile, profile_manager.active_profile_name)

    # Auto-Apply aktives Profil
    profile = profile_manager.get_active_profile()
    engine.set_effect(profile.effect)
    engine.set_primary_color(*profile.primary_color)
    engine.set_secondary_color(*profile.secondary_color)
    engine.set_brightness(profile.brightness)
    engine.set_speed(profile.speed)

    if connected:
        controller.set_all_to_direct_mode()
        engine.start()

    # ─── Tray Manager ───
    tray = None

    def on_minimize_to_tray():
        nonlocal tray
        if tray is None:
            tray = TrayManager(
                on_show=lambda: gui.root.after(0, gui.show),
                on_quit=lambda: gui.root.after(0, gui._quit),
                on_leds_off=lambda: gui.root.after(0, gui._turn_off),
                on_profile_change=lambda name: gui.root.after(0, lambda: gui._on_profile_change(name)),
                profile_names=profile_manager.get_profile_names(),
            )
            tray.start()
        else:
            tray.update_profiles(profile_manager.get_profile_names())

    # ─── GUI ───
    gui = RGBControllerGUI(controller, engine, profile_manager,
                           on_minimize_to_tray=on_minimize_to_tray)

    if args.tray:
        gui.hide()
        on_minimize_to_tray()
        logger.info("Gestartet im System-Tray.")

    # ─── Cleanup Logic ───
    def cleanup():
        logger.info("Fahre System herunter / Beende App... Schalte LEDs ab.")
        try:
            engine.stop()
            controller.turn_off_all()
            controller.disconnect()
            if tray:
                try:
                    tray.stop()
                except Exception:
                    pass
        except Exception as e:
            logger.error("Fehler beim Cleanup: %s", e)
    
    # Registriere für normalen Exit
    atexit.register(cleanup)
    
    # Registriere für Windows Shutdown (Logoff / Shutdown Events)
    try:
        CMPFUNC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)
        
        def console_ctrl_handler(ctrl_type):
            if ctrl_type in (0, 2, 5, 6): # CTRL_C, CTRL_CLOSE, CTRL_LOGOFF, CTRL_SHUTDOWN
                cleanup()
                return True
            return False
            
        # Halte Referenz lokal im main() scope, damit GC sie nicht löscht (als func attr)
        console_ctrl_handler.c_func = CMPFUNC(console_ctrl_handler)
        ctypes.windll.kernel32.SetConsoleCtrlHandler(console_ctrl_handler.c_func, True)
    except Exception as e:
        logger.warning("Konnte Windows Shutdown Handler nicht registrieren: %s", e)

    logger.info("GUI gestartet. Viel Spaß! 🎨")
    gui.run()

    # Wenn GUI ganz normal schließt (z.B. Rechtsklick -> Beenden)
    cleanup()
    logger.info("Auf Wiedersehen! 👋")


if __name__ == "__main__":
    main()
