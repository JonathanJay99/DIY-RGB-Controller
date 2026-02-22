import hid
import time

def send_prism_color(r, g, b):
    # Finde das Gerät
    devices = hid.enumerate(0x16D0, 0x1294)
    target = None
    for d in devices:
        if d['interface_number'] == 2:
            target = d['path']
            break
            
    if not target:
        print("Prism S nicht gefunden!")
        return

    try:
        dev = hid.device()
        dev.open_path(target)
        print("Verbindung zu Prism S hergestellt.")
        
        # Sende Save_Settings equivalent (0x00, 0xFE, 0x01, r, g, b, 0x01)
        # Dies setzt zumindest einen Basis-Modus/Farbe
        packet = bytearray(65)
        packet[0] = 0x00 # Report ID
        packet[1] = 0xFE
        packet[2] = 0x01
        packet[3] = r
        packet[4] = g
        packet[5] = b
        packet[6] = 0x01 # Mos (Triple 8 Pin)
        dev.write(packet)
        print("Save_Settings Paket gesendet.")
        
        time.sleep(0.05)
        
        # Render-Logik:
        # ATX (24 Pin) ist 120 LEDs = 360 Bytes RGB = aufgeteilt in Packets (0..5 oder 15)
        # Triple 8 Pin ist 162 LEDs = 486 Bytes RGB = aufgeteilt in Packets 6..13
        
        # Testen: Alles auf Rot
        atx_leds = 120
        gpu_leds = 162
        rgb_data_atx = [r, g, b] * atx_leds
        rgb_data_gpu = [r, g, b] * gpu_leds
        
        # Baue payloads
        send_data = []
        
        # ATX Packets (0..4 und 15)
        idx = 0
        for p in [0, 1, 2, 3, 4, 15]:
            packet = [p]
            chunk_size = min(63, len(rgb_data_atx) - idx)
            packet.extend(rgb_data_atx[idx : idx + chunk_size])
            idx += chunk_size
            
            # pad auf 64 bytes
            while len(packet) < 64:
                packet.append(0)
            send_data.extend(packet)

        # GPU Packets:
        # GPU Start Offset in SendData ist index 320 laut JS.
        # SendData ATX ist 6 Packets * 64 = 384 bytes.
        # Wait, the JS says: `if(GPUCable) { if(SendData.length === 0) { ... } else { SendData[320] = 0x05; } }`
        send_data[320] = 0x05
        
        # Die ersten 18 bytes vom GPU RGB in das letzte ATX Paket??
        # Nein, JS sagt:
        # RGBData = getTripleGPUColors()
        # SendData.push(...RGBData.splice(0, 18)) -> Dies füllt das Paket 15 (ATX) auf, weil Paket 15 nur 46 bytes ATX RGB hatte!
        # Ah! Paket 15 beginnt bei Index 320 (5 * 64 = 320).
        # Paket 15 ist: `15`, gefolgt von restlichen 45 bytes ATX RGB (360-315 = 45 bytes). Also Bytes [1..45].
        # 46 bytes sind belegt. Es bleiben 64-46 = 18 bytes frei. 
        # Da kommen die ersten 18 Bytes GPU RGB rein!
        
        # GPU packete (6..13)
        idx_gpu = 18
        for p in range(6, 14):
            packet = [p]
            chunk_size = min(63, len(rgb_data_gpu) - idx_gpu)
            if chunk_size > 0:
                packet.extend(rgb_data_gpu[idx_gpu : idx_gpu + chunk_size])
                idx_gpu += chunk_size
            while len(packet) < 64:
                packet.append(0)
            send_data.extend(packet)
            
        print(f"Gesamte Payload Länge: {len(send_data)} (Sollte Vielfaches von 64 sein, ist {len(send_data)//64} Pakete)")
        
        # Sende Pakete
        for i in range(0, len(send_data), 64):
            chunk = send_data[i:i+64]
            pack = bytearray(65)
            pack[0] = 0x00 # Report ID
            for j in range(64):
                pack[j+1] = chunk[j]
            dev.write(pack)
            
        print("Alle Farbdaten gesendet!")
        dev.close()
        
    except Exception as e:
        print(f"Fehler: {e}")

if __name__ == '__main__':
    send_prism_color(0, 255, 0) # Green
