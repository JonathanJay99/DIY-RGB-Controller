"""
GUI — CustomTkinter-basierte Oberfläche für den RGB Controller.
Modernes Dark-Theme mit minimaler Ressourcennutzung.
"""

import threading
import tkinter as tk
from tkinter import colorchooser, messagebox, simpledialog
import logging
from typing import Optional

import customtkinter as ctk

from rgb_controller import RGBController
from effects import EffectEngine, EFFECT_NAMES
from profiles import ProfileManager, Profile

logger = logging.getLogger(__name__)

# Design-Konstanten
ACCENT_COLOR = "#6C63FF"
ACCENT_HOVER = "#5A52D5"
BG_DARK = "#1A1A2E"
BG_CARD = "#16213E"
BG_SIDEBAR = "#0F3460"
TEXT_PRIMARY = "#E0E0E0"
TEXT_SECONDARY = "#A0A0C0"
SUCCESS_COLOR = "#00D26A"
ERROR_COLOR = "#FF4757"
WARNING_COLOR = "#FFA502"


class QuickColorPicker(ctk.CTkFrame):
    """Grid an vordefinierten Farben plus Custom-Color Picker."""

    PRESET_COLORS = [
        (255, 0, 0),     # Rot
        (0, 255, 0),     # Grün
        (0, 0, 255),     # Blau
        (255, 255, 0),   # Gelb
        (0, 255, 255),   # Cyan
        (255, 0, 255),   # Magenta
        (255, 80, 0),    # Orange
        (0, 255, 128),   # Toxic Green
        (138, 43, 226),  # Lila
        (255, 255, 255), # Weiß
    ]

    def __init__(self, master, color: tuple = (255, 0, 0), label: str = "Primär",
                 on_change=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.color = color
        self.on_change = on_change

        # Label & Current Color Box
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", pady=(0, 6))
        
        self.label = ctk.CTkLabel(top_frame, text=label, font=("Segoe UI Semibold", 13), text_color=TEXT_PRIMARY)
        self.label.pack(side="left")

        self.current_preview = tk.Canvas(top_frame, width=24, height=24, bg=BG_CARD, highlightthickness=1, highlightbackground="#333")
        self.current_preview.pack(side="right")
        self.current_preview.bind("<Button-1>", self._pick_custom)

        # Quick Select Grid
        grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        grid_frame.pack()

        for i, rgb in enumerate(self.PRESET_COLORS):
            row = i // 5
            col = i % 5
            hex_color = "#{:02x}{:02x}{:02x}".format(*rgb)
            btn = ctk.CTkButton(grid_frame, text="", width=24, height=24, fg_color=hex_color, 
                                hover_color=hex_color, corner_radius=4,
                                command=lambda c=rgb: self._select_preset(c))
            btn.grid(row=row, column=col, padx=3, pady=3)

        # Custom Color Button im Grid
        custom_btn = ctk.CTkButton(grid_frame, text="🖌️", width=24, height=24, fg_color="#2D3436",
                                   hover_color="#636E72", corner_radius=4, command=self._pick_custom)
        custom_btn.grid(row=1, column=5, padx=3, pady=3)

        self._draw_current()

    def _select_preset(self, rgb: tuple):
        self.set_color(rgb)
        if self.on_change:
            self.on_change(rgb)

    def _draw_current(self):
        self.current_preview.delete("all")
        hex_color = "#{:02x}{:02x}{:02x}".format(*self.color)
        self.current_preview.create_rectangle(0, 0, 24, 24, fill=hex_color, outline="")

    def _pick_custom(self, _event=None):
        result = colorchooser.askcolor(
            initialcolor="#{:02x}{:02x}{:02x}".format(*self.color),
            title="Spezifische Farbe wählen"
        )
        if result and result[0]:
            self._select_preset((int(result[0][0]), int(result[0][1]), int(result[0][2])))

    def set_color(self, color: tuple):
        self.color = color
        self._draw_current()



class DeviceListItem(ctk.CTkFrame):
    """Ein Eintrag in der Geräteliste."""

    def __init__(self, master, device_info: dict, index: int, **kwargs):
        super().__init__(master, corner_radius=8, fg_color=BG_CARD, **kwargs)
        self.index = index

        # LED-Indikator
        self.indicator = ctk.CTkFrame(self, width=4, corner_radius=2, fg_color=ACCENT_COLOR)
        self.indicator.pack(side="left", fill="y", padx=(0, 8), pady=4)

        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=4, pady=6)

        name_label = ctk.CTkLabel(info_frame, text=device_info["name"],
                                  font=("Segoe UI Semibold", 13),
                                  text_color=TEXT_PRIMARY, anchor="w")
        name_label.pack(fill="x")

        detail_text = f"{device_info['type']}  •  {device_info['num_leds']} LEDs"
        detail_label = ctk.CTkLabel(info_frame, text=detail_text,
                                    font=("Segoe UI", 11),
                                    text_color=TEXT_SECONDARY, anchor="w")
        detail_label.pack(fill="x")


class RGBControllerGUI:
    """Haupt-GUI für den RGB Controller."""

    def __init__(self, controller: RGBController, effect_engine: EffectEngine,
                 profile_manager: ProfileManager, on_minimize_to_tray=None):
        self.controller = controller
        self.engine = effect_engine
        self.profile_manager = profile_manager
        self.on_minimize_to_tray = on_minimize_to_tray

        # CustomTkinter Setup
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("🎨 DIY RGB Controller")
        self.root.geometry("900x620")
        self.root.minsize(800, 550)
        self.root.configure(fg_color=BG_DARK)

        # Icon setzen (optional)
        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        # Schließen-Handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._load_profile_to_ui()

    def _build_ui(self):
        """Baut die gesamte UI auf."""
        # ─── Hauptlayout: Sidebar + Content ───
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # ─── Sidebar (Geräteliste) ───
        self.sidebar = ctk.CTkFrame(main_frame, width=260, corner_radius=12,
                                    fg_color=BG_SIDEBAR)
        self.sidebar.pack(side="left", fill="y", padx=(0, 10))
        self.sidebar.pack_propagate(False)

        sidebar_header = ctk.CTkLabel(self.sidebar, text="🖥️ Geräte",
                                      font=("Segoe UI Bold", 16),
                                      text_color=TEXT_PRIMARY)
        sidebar_header.pack(pady=(15, 5), padx=15, anchor="w")

        # Verbindungsstatus
        status_color = SUCCESS_COLOR if self.controller.connected else ERROR_COLOR
        status_text = f"● Verbunden — {len(self.controller.devices)} Geräte" if self.controller.connected else "● Nicht verbunden"
        self.status_label = ctk.CTkLabel(self.sidebar, text=status_text,
                                         font=("Segoe UI", 11),
                                         text_color=status_color)
        self.status_label.pack(pady=(0, 10), padx=15, anchor="w")

        # Scrollbare Geräteliste
        self.device_scroll = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent",
                                                    corner_radius=0)
        self.device_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self._populate_device_list()

        # Reconnect Button
        reconnect_btn = ctk.CTkButton(self.sidebar, text="🔄 Neu verbinden",
                                      font=("Segoe UI", 12),
                                      fg_color="#2D3436", hover_color="#636E72",
                                      corner_radius=8, height=35,
                                      command=self._reconnect)
        reconnect_btn.pack(pady=(0, 10), padx=15, fill="x")

        # ─── Content Bereich ───
        content = ctk.CTkFrame(main_frame, fg_color="transparent")
        content.pack(side="right", fill="both", expand=True)

        # ─── CARD 1: Profile ───
        profile_card = ctk.CTkFrame(content, corner_radius=12, fg_color=BG_CARD)
        profile_card.pack(fill="x", pady=(0, 10))

        header = ctk.CTkFrame(profile_card, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=15)

        profile_label = ctk.CTkLabel(header, text="Profil",
                                     font=("Segoe UI Bold", 14), text_color=TEXT_PRIMARY)
        profile_label.pack(side="left", padx=(0, 15))

        self.profile_var = ctk.StringVar(value=self.profile_manager.active_profile_name)
        self.profile_dropdown = ctk.CTkOptionMenu(
            header, variable=self.profile_var,
            values=self.profile_manager.get_profile_names(),
            font=("Segoe UI", 12), dropdown_font=("Segoe UI", 12),
            fg_color=ACCENT_COLOR, button_color=ACCENT_HOVER,
            button_hover_color="#4A42B0", corner_radius=8,
            command=self._on_profile_change,
            width=200,
        )
        self.profile_dropdown.pack(side="left")

        # Profil-Buttons
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right")

        save_btn = ctk.CTkButton(btn_frame, text="💾 Speichern", height=32,
                                 font=("Segoe UI", 12), fg_color="#2D3436",
                                 hover_color="#636E72", corner_radius=8,
                                 command=self._save_profile)
        save_btn.pack(side="left", padx=4)

        new_btn = ctk.CTkButton(btn_frame, text="➕", width=32, height=32,
                                font=("Segoe UI", 16), fg_color="#2D3436",
                                hover_color="#636E72", corner_radius=8,
                                command=self._new_profile)
        new_btn.pack(side="left", padx=4)

        del_btn = ctk.CTkButton(btn_frame, text="🗑️", width=32, height=32,
                                font=("Segoe UI", 16), fg_color="#2D3436",
                                hover_color=ERROR_COLOR, corner_radius=8,
                                command=self._delete_profile)
        del_btn.pack(side="left", padx=4)

        # ─── Mittlerer Bereich (2 Spalten Grid) ───
        mid_frame = ctk.CTkFrame(content, fg_color="transparent")
        mid_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        mid_frame.grid_columnconfigure(0, weight=1, uniform="a")
        mid_frame.grid_columnconfigure(1, weight=1, uniform="a")

        # ─── CARD 2: Effekte (Links) ───
        effect_card = ctk.CTkFrame(mid_frame, corner_radius=12, fg_color=BG_CARD)
        effect_card.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        effect_label = ctk.CTkLabel(effect_card, text="✨ Animation",
                                    font=("Segoe UI Bold", 14), text_color=TEXT_PRIMARY)
        effect_label.pack(anchor="w", padx=20, pady=(15, 10))

        self.effect_buttons_frame = ctk.CTkFrame(effect_card, fg_color="transparent")
        self.effect_buttons_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        self.effect_var = ctk.StringVar(value="Static")
        self.effect_btns = {}
        for i, name in enumerate(EFFECT_NAMES):
            btn = ctk.CTkButton(
                self.effect_buttons_frame, text=name,
                font=("Segoe UI", 13), height=40,
                fg_color="#2D3436", hover_color=ACCENT_HOVER,
                corner_radius=8,
                command=lambda n=name: self._select_effect(n),
            )
            btn.pack(fill="x", pady=4)
            self.effect_btns[name] = btn

        # ─── CARD 3: Farbe & Settings (Rechts) ───
        settings_card = ctk.CTkFrame(mid_frame, corner_radius=12, fg_color=BG_CARD)
        settings_card.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        color_label = ctk.CTkLabel(settings_card, text="🎨 Farben",
                                    font=("Segoe UI Bold", 14), text_color=TEXT_PRIMARY)
        color_label.pack(anchor="w", padx=20, pady=(15, 10))

        color_split = ctk.CTkFrame(settings_card, fg_color="transparent")
        color_split.pack(fill="x", padx=20)

        self.primary_preview = QuickColorPicker(color_split, label="Primär",
                                            on_change=self._on_primary_color_change)
        self.primary_preview.pack(fill="x", pady=(0, 10))

        self.secondary_preview = QuickColorPicker(color_split, color=(0, 0, 255),
                                              label="Sekundär",
                                              on_change=self._on_secondary_color_change)
        self.secondary_preview.pack(fill="x")

        sep = ctk.CTkFrame(settings_card, height=1, fg_color="#2D3436")
        sep.pack(fill="x", padx=20, pady=15)

        # Regler
        slider_frame = ctk.CTkFrame(settings_card, fg_color="transparent")
        slider_frame.pack(fill="x", padx=20, pady=(0, 15))

        brightness_label = ctk.CTkLabel(slider_frame, text="☀️ Helligkeit",
                                        font=("Segoe UI", 13), text_color=TEXT_PRIMARY)
        brightness_label.pack(anchor="w")

        self.brightness_var = ctk.DoubleVar(value=1.0)
        self.brightness_slider = ctk.CTkSlider(
            slider_frame, from_=0.0, to=1.0, variable=self.brightness_var,
            button_color=ACCENT_COLOR, button_hover_color=ACCENT_HOVER,
            progress_color=ACCENT_COLOR, fg_color="#2D3436",
            command=self._on_brightness_change
        )
        self.brightness_slider.pack(fill="x", pady=(4, 0))

        self.brightness_value_label = ctk.CTkLabel(slider_frame, text="100%",
                                                   font=("Segoe UI", 11),
                                                   text_color=TEXT_SECONDARY)
        self.brightness_value_label.pack(anchor="e", pady=(0, 10))

        speed_label = ctk.CTkLabel(slider_frame, text="⚡ Geschwindigkeit",
                                   font=("Segoe UI", 13), text_color=TEXT_PRIMARY)
        speed_label.pack(anchor="w")

        self.speed_var = ctk.DoubleVar(value=0.5)
        self.speed_slider = ctk.CTkSlider(
            slider_frame, from_=0.01, to=1.0, variable=self.speed_var,
            button_color=ACCENT_COLOR, button_hover_color=ACCENT_HOVER,
            progress_color=ACCENT_COLOR, fg_color="#2D3436",
            command=self._on_speed_change
        )
        self.speed_slider.pack(fill="x", pady=(4, 0))

        self.reverse_var = ctk.BooleanVar(value=False)
        self.reverse_check = ctk.CTkCheckBox(
            slider_frame, text="Richtung umkehren", variable=self.reverse_var,
            onvalue=True, offvalue=False,
            font=("Segoe UI", 11), text_color=TEXT_SECONDARY,
            fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER,
            command=self._on_reverse_change
        )
        self.reverse_check.pack(side="left", pady=(4, 0))

        self.speed_value_label = ctk.CTkLabel(slider_frame, text="50%",
                                              font=("Segoe UI", 11),
                                              text_color=TEXT_SECONDARY)
        self.speed_value_label.pack(side="right", anchor="e")

        # ─── CARD 4: Actions ───
        action_card = ctk.CTkFrame(content, corner_radius=12, fg_color=BG_CARD)
        action_card.pack(fill="x", pady=(0, 0))
        
        action_inner = ctk.CTkFrame(action_card, fg_color="transparent")
        action_inner.pack(fill="x", padx=20, pady=15)

        apply_btn = ctk.CTkButton(
            action_inner, text="▶️  Anwenden",
            font=("Segoe UI Semibold", 14), height=46,
            fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER,
            corner_radius=10, width=160,
            command=self._apply_effect,
        )
        apply_btn.pack(side="left", padx=(0, 10))

        stop_btn = ctk.CTkButton(
            action_inner, text="⏹  Stoppen",
            font=("Segoe UI Semibold", 13), height=46,
            fg_color="#2D3436", hover_color="#636E72",
            corner_radius=10, width=120,
            command=self._stop_effect,
        )
        stop_btn.pack(side="left", padx=(0, 10))

        off_btn = ctk.CTkButton(
            action_inner, text="💡 LEDs Aus",
            font=("Segoe UI Semibold", 13), height=46,
            fg_color="#2D3436", hover_color=ERROR_COLOR,
            corner_radius=10, width=120,
            command=self._turn_off,
        )
        off_btn.pack(side="left")

        if self.on_minimize_to_tray:
            tray_btn = ctk.CTkButton(
                action_inner, text="⬇ Minimieren",
                font=("Segoe UI Semibold", 13), height=46,
                fg_color=BG_SIDEBAR, hover_color="#184e8f",
                corner_radius=10, width=120,
                command=self._minimize_to_tray,
            )
            tray_btn.pack(side="right")

    def _populate_device_list(self):
        """Füllt die Geräteliste in der Sidebar."""
        for widget in self.device_scroll.winfo_children():
            widget.destroy()

        if not self.controller.connected:
            no_device = ctk.CTkLabel(self.device_scroll,
                                     text="Keine Geräte gefunden.\nStarte OpenRGB mit\naktivem SDK Server.",
                                     font=("Segoe UI", 11),
                                     text_color=TEXT_SECONDARY,
                                     justify="center")
            no_device.pack(pady=30)
            return

        for i, device in enumerate(self.controller.devices):
            info = self.controller.get_device_info(device)
            item = DeviceListItem(self.device_scroll, info, i)
            item.pack(fill="x", pady=3)

    def _load_profile_to_ui(self):
        """Lädt die Werte des aktiven Profils in die UI."""
        profile = self.profile_manager.get_active_profile()
        self.effect_var.set(profile.effect)
        self._highlight_effect_btn(profile.effect)
        self.primary_preview.set_color(tuple(profile.primary_color))
        self.secondary_preview.set_color(tuple(profile.secondary_color))
        self.brightness_var.set(profile.brightness)
        self.brightness_value_label.configure(text=f"{int(profile.brightness * 100)}%")
        self.speed_var.set(profile.speed)
        self.speed_value_label.configure(text=f"{int(profile.speed * 100)}%")
        
        # Lade reverse Richtung (falls vorhanden, abwärtskompatibel zu alten Profilen)
        rev = getattr(profile, "reverse_direction", False)
        self.reverse_var.set(rev)
        self.engine.set_reverse_direction(rev)

    def _highlight_effect_btn(self, active_name: str):
        """Highlighted den aktiven Effekt-Button."""
        for name, btn in self.effect_btns.items():
            if name == active_name:
                btn.configure(fg_color=ACCENT_COLOR)
            else:
                btn.configure(fg_color="#2D3436")

    # ─── Event Handlers ─────────────────────────────────────────────────

    def _select_effect(self, name: str):
        self.effect_var.set(name)
        self._highlight_effect_btn(name)
        # Live-Vorschau wenn Engine läuft
        if self.engine.is_running():
            self._apply_effect()

    def _on_primary_color_change(self, color: tuple):
        self.engine.set_primary_color(*color)

    def _on_secondary_color_change(self, color: tuple):
        self.engine.set_secondary_color(*color)

    def _on_brightness_change(self, value: float):
        self.brightness_value_label.configure(text=f"{int(value * 100)}%")
        self.engine.set_brightness(value)

    def _on_speed_change(self, value: float):
        self.speed_value_label.configure(text=f"{int(value * 100)}%")
        self.engine.set_speed(value)
        
    def _on_reverse_change(self):
        self.engine.set_reverse_direction(self.reverse_var.get())

    def _apply_effect(self):
        """Wendet den aktuellen Effekt an."""
        if not self.controller.connected:
            messagebox.showwarning("Nicht verbunden",
                                   "Keine Verbindung zu OpenRGB.\nBitte starte OpenRGB mit aktivem SDK Server.")
            return

        # Erst auf Direct Mode setzen
        self.controller.set_all_to_direct_mode()

        # Engine-Parameter setzen
        self.engine.set_effect(self.effect_var.get())
        self.engine.set_primary_color(*self.primary_preview.color)
        self.engine.set_secondary_color(*self.secondary_preview.color)
        self.engine.set_brightness(self.brightness_var.get())
        self.engine.set_speed(self.speed_var.get())
        self.engine.set_reverse_direction(self.reverse_var.get())

        # Starten
        self.engine.start()

    def _stop_effect(self):
        self.engine.stop()

    def _turn_off(self):
        self.engine.stop()
        if self.controller.connected:
            self.controller.set_all_to_direct_mode()
            self.controller.turn_off_all()

    def _reconnect(self):
        """Versucht eine neue Verbindung zu OpenRGB."""
        self.engine.stop()
        success = self.controller.reconnect()
        if success:
            self.status_label.configure(
                text=f"● Verbunden — {len(self.controller.devices)} Geräte",
                text_color=SUCCESS_COLOR,
            )
        else:
            self.status_label.configure(
                text="● Nicht verbunden",
                text_color=ERROR_COLOR,
            )
        self._populate_device_list()

    # ─── Profil-Verwaltung ───────────────────────────────────────────────

    def _on_profile_change(self, name: str):
        self.profile_manager.set_active_profile(name)
        self._load_profile_to_ui()
        if self.engine.is_running():
            self._apply_effect()

    def _save_profile(self):
        profile = self.profile_manager.get_active_profile()
        profile.effect = self.effect_var.get()
        profile.primary_color = list(self.primary_preview.color)
        profile.secondary_color = list(self.secondary_preview.color)
        profile.brightness = self.brightness_var.get()
        profile.speed = self.speed_var.get()
        profile.reverse_direction = self.reverse_var.get()
        self.profile_manager.save_profile(profile)
        messagebox.showinfo("Gespeichert", f"Profil '{profile.name}' gespeichert! ✅")

    def _new_profile(self):
        name = simpledialog.askstring("Neues Profil", "Name für das neue Profil:",
                                      parent=self.root)
        if name and name.strip():
            name = name.strip()
            self.profile_manager.create_profile(name)
            self.profile_manager.set_active_profile(name)
            self._update_profile_dropdown()
            self._load_profile_to_ui()

    def _delete_profile(self):
        name = self.profile_var.get()
        if name == "Default":
            messagebox.showwarning("Nicht möglich", "Das Default-Profil kann nicht gelöscht werden.")
            return
        if messagebox.askyesno("Profil löschen", f"Profil '{name}' wirklich löschen?"):
            self.profile_manager.delete_profile(name)
            self._update_profile_dropdown()
            self._load_profile_to_ui()

    def _update_profile_dropdown(self):
        names = self.profile_manager.get_profile_names()
        self.profile_dropdown.configure(values=names)
        self.profile_var.set(self.profile_manager.active_profile_name)

    # ─── Window-Management ───────────────────────────────────────────────

    def _minimize_to_tray(self):
        if self.on_minimize_to_tray:
            self.root.withdraw()
            self.on_minimize_to_tray()

    def _on_close(self):
        if self.on_minimize_to_tray:
            self._minimize_to_tray()
        else:
            self._quit()

    def _quit(self):
        self.engine.stop()
        self.controller.disconnect()
        self.root.destroy()

    def show(self):
        """Zeigt das Fenster."""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide(self):
        """Versteckt das Fenster."""
        self.root.withdraw()

    def run(self):
        """Startet die GUI-Mainloop."""
        self.root.mainloop()
