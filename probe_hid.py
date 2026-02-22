"""Diagnose-Skript: Probt den DIY Controller via HID."""
import hid

# Alle HID-Geraete mit VID 16D0, PID 1294
devices = hid.enumerate(0x16D0, 0x1294)
print(f"{len(devices)} HID-Interface(s) gefunden:\n")
for d in devices:
    print(f"  Path: {d['path']}")
    print(f"  Product: {d['product_string']}")
    print(f"  Manufacturer: {d['manufacturer_string']}")
    print(f"  Serial: {d['serial_number']}")
    print(f"  Interface: {d['interface_number']}")
    print(f"  Usage Page: 0x{d['usage_page']:04X}")
    print(f"  Usage: 0x{d['usage']:04X}")
    print()

# Versuche das HID-Device zu oeffnen und Daten zu lesen
if devices:
    for d in devices:
        try:
            h = hid.Device(path=d["path"])
            print(f"Geoeffnet: {d['product_string']} (Interface {d['interface_number']})")
            print(f"  Manufacturer: {h.manufacturer}")
            print(f"  Product: {h.product}")
            print(f"  Serial: {h.serial}")

            # Feature Report lesen (Report ID 0)
            for report_id in range(0, 5):
                try:
                    feat = h.get_feature_report(report_id, 65)
                    if feat and any(b != 0 for b in feat):
                        print(f"  Feature Report {report_id}: {feat[:32].hex()}")
                except Exception:
                    pass

            # Versuche Daten zu lesen (non-blocking)
            h.nonblocking = True
            data = h.read(64)
            if data:
                print(f"  Read Data: {data.hex()}")
            else:
                print("  Read: Keine Daten")

            h.close()
        except Exception as e:
            print(f"  Fehler: {e}")
        print()
