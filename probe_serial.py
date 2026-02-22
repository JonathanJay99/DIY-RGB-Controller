"""Diagnose-Skript: Probt den seriellen Controller auf COM3."""
import serial
import time

s = serial.Serial("COM3", 115200, timeout=3)
time.sleep(2)

# Boot-Daten lesen
if s.in_waiting > 0:
    data = s.read(s.in_waiting)
    print(f"Boot-Daten ({len(data)} bytes): {data!r}")
else:
    print("Keine Boot-Daten")

# Verschiedene Protokolle testen
tests = [
    ("Adalight", b"Ada"),
    ("tpm2 Discovery", bytes([0xC9, 0xDA, 0x01, 0x00, 0x00, 0x36])),
    ("WLED v", b"v"),
    ("Newline", b"\r\n"),
    ("?", b"?"),
    ("help", b"help\r\n"),
    ("AT", b"AT\r\n"),
    ("0x00 padding", b"\x00" * 10),
]

for name, data_send in tests:
    s.reset_input_buffer()
    s.write(data_send)
    time.sleep(0.5)
    if s.in_waiting > 0:
        resp = s.read(s.in_waiting)
        print(f"{name}: Antwort ({len(resp)} bytes): {resp!r}")
    else:
        print(f"{name}: Keine Antwort")

s.close()
print("Done.")
