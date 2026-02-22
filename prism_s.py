"""
Prism S Controller Integration
Ermöglicht die direkte Steuerung des PrismRGB Prism S USB-Controllers
über HID, sodass er wie ein OpenRGB Device behandelt werden kann.
"""
import hid
import threading
import logging
from typing import Optional
from openrgb.utils import RGBColor, DeviceType

logger = logging.getLogger(__name__)


class DummyMode:
    def __init__(self, name: str):
        self.name = name


class DummyLED:
    def __init__(self, name: str):
        self.name = name


class PrismSDevice:
    """Duck-Typed OpenRGB Device für den Prism S Controller."""
    
    def __init__(self, path: bytes):
        self.path = path
        self.name = "PrismRGB Prism S (Strimer)"
        self.type = DeviceType.LEDSTRIP
        self.device = hid.device()
        self.connected = False
        self._lock = threading.Lock()
        
        # LEDs: ATX (120) + GPU Triple 8 Pin (162) = 282
        self.num_leds = 282
        self.leds = [DummyLED(f"LED {i}") for i in range(self.num_leds)]
        self.modes = [DummyMode("Direct")]
        self.active_mode = 0
        
        # Aktueller Farb-Puffer
        self.colors = [RGBColor(0, 0, 0) for _ in range(self.num_leds)]
        self.last_keep_alive = 0
        
        self.connect()

    def connect(self):
        try:
            self.device.open_path(self.path)
            
            # Init Packet (Shutdown Color / Base config)
            packet = bytearray(65)
            packet[0] = 0x00
            packet[1] = 0xFE
            packet[2] = 0x01
            packet[3] = 0  # R
            packet[4] = 0  # G
            packet[5] = 0  # B
            packet[6] = 0x00 # Mos (0 für Triple 8 Pin)
            self.device.write(packet)
            
            self.connected = True
            logger.info("Prism S verbunden.")
        except Exception as e:
            logger.error("Fehler beim Verbinden mit Prism S: %s", e)
            self.connected = False

    def disconnect(self):
        if self.connected:
            try:
                self.device.close()
            except Exception:
                pass
            self.connected = False

    def set_mode(self, mode: str):
        """Ignoriert, da wir immer im Direct-Modus agieren."""
        pass

    def set_color(self, color: RGBColor):
        """Setzt alle LEDs auf eine Farbe."""
        with self._lock:
            for i in range(self.num_leds):
                self.colors[i] = color
            self._update_hardware()

    def set_colors(self, colors: list[RGBColor]):
        """Setzt individuelle Farben."""
        with self._lock:
            for i in range(min(self.num_leds, len(colors))):
                self.colors[i] = colors[i]
            self._update_hardware()

    def _update_hardware(self):
        """Übersetzt die Farben in das Prism S HID Protokoll und sendet sie."""
        if not self.connected:
            return
            
        try:
            import time
            if time.time() - getattr(self, "last_keep_alive", 0) > 1.5:
                # Keep-Alive Packet um Timeout des Strimers zu verhindern
                base_pack = bytearray(65)
                base_pack[0] = 0x00
                base_pack[1] = 0xFE
                # Strimer Fallback-Color auf 0,0,0 setzen, damit es visuell nicht aufblitzt
                base_pack[3] = 0
                base_pack[4] = 0
                base_pack[5] = 0
                base_pack[6] = 0x00 # Mos
                self.device.write(base_pack)
                self.last_keep_alive = time.time()

            # 1. ATX (120 LEDs) -> 360 bytes
            atx_bytes = bytearray(360)
            for i in range(120):
                c = self.colors[i]
                atx_bytes[i*3] = c.red
                atx_bytes[i*3+1] = c.green
                atx_bytes[i*3+2] = c.blue
                
            # 2. GPU (162 LEDs) -> 486 bytes
            gpu_bytes = bytearray(486)
            for i in range(162):
                c = self.colors[120 + i]
                gpu_bytes[i*3] = c.red
                gpu_bytes[i*3+1] = c.green
                gpu_bytes[i*3+2] = c.blue

            raw_send_data = bytearray()
            
            # ATX Payload 
            idx = 0
            for p in [0, 1, 2, 3, 4, 15]:
                raw_send_data.append(p)
                chunk_len = min(63, 360 - idx)
                for j in range(chunk_len):
                    raw_send_data.append(atx_bytes[idx + j])
                idx += chunk_len
                
            # Sequence 5 fix
            if len(raw_send_data) > 320:
                raw_send_data[320] = 0x05
                
            # GPU ersten 18 Bytes auffüllen
            for j in range(18):
                raw_send_data.append(gpu_bytes[j])
            
            # Restliche GPU Payloads
            idx = 18
            for p in range(6, 14):
                raw_send_data.append(p)
                chunk_len = min(63, 486 - idx)
                for j in range(chunk_len):
                    raw_send_data.append(gpu_bytes[idx + j])
                idx += chunk_len
                
            # Pakete versenden
            import time
            for i in range(0, len(raw_send_data), 64):
                chunk = raw_send_data[i:i+64]
                pack = bytearray(65)
                pack[0] = 0x00
                for j in range(len(chunk)):
                    pack[1+j] = chunk[j]
                self.device.write(pack)
                time.sleep(0.002) # 2ms Pause um USB-Puffer Overflow ("half on") zu vermeiden
                
        except Exception as e:
            logger.error("Fehler beim Senden an Prism S: %s", e)
            self.disconnect()


def find_prism_s_devices() -> list[PrismSDevice]:
    """Sucht nach Prism S Controllern und gibt Instanzen zurück."""
    found = []
    try:
        devices = hid.enumerate(0x16D0, 0x1294)
        for d in devices:
            if d['interface_number'] == 2:
                found.append(PrismSDevice(d['path']))
    except Exception as e:
        logger.error("Fehler bei HID-Suche nach Prism S: %s", e)
    return found
