import requests
import random
import time

# Pastikan URL ini menunjuk ke tempat 'api.py' Anda berjalan.
API_URL = "http://127.0.0.1:5000/api/v1/checkin"

# Interval waktu antar siklus pemantauan (detik)
SIKLUS_TUNGGU = 10  

DEVICES = [
    "BED-MONITOR-101-ICU", "BED-MONITOR-102-ICU", "BED-MONITOR-103-ICU",
    "INFUSION-PUMP-201-A", "INFUSION-PUMP-202-A", "INFUSION-PUMP-203-B",
    "TEMP-SENSOR-RUANG-OBAT", "TEMP-SENSOR-SERVER-ROOM",
    "VENTILATOR-301-ICU", "VENTILATOR-302-ICU",
    "MRI-MACHINE-MAIN", "CT-SCANNER-01"
]

# Menyimpan status terakhir tiap perangkat
device_states = {}

print("Inisialisasi status awal perangkat...")
for device in DEVICES:
    device_states[device] = {
        "status": "online",
        "message": "System OK"
    }
print(f"Inisialisasi selesai. {len(DEVICES)} perangkat dalam status 'online'.")
print(f"Memulai simulasi pemantauan real-time ke {API_URL}")
print("Tekan CTRL+C untuk berhenti.\n")

# ===== SIMULATOR LOOP =====
while True:
    print(f"\n--- Siklus baru ({time.strftime('%H:%M:%S')}) ---")

    # Ambil subset perangkat acak untuk disimulasikan (tidak semuanya sekaligus)
    subset = random.sample(DEVICES, k=random.randint(4, len(DEVICES)))  

    for device_id in subset:
        current_state = device_states[device_id]
        rand_val = random.random()

        # Logika realistis: tidak terlalu stabil tapi tetap masuk akal
        if current_state["status"] == "online":
            if rand_val < 0.1:  # 10% kemungkinan error ringan
                current_state["status"] = "error"
                current_state["message"] = random.choice([
                    "Battery Low (15%)", "Sensor Error 502", "Temperature Drift"
                ])
                print(f"💥 ERROR: {device_id} mengalami masalah")
            elif 0.1 <= rand_val < 0.15:  # 5% kemungkinan offline
                current_state["status"] = "offline"
                current_state["message"] = "Connection Lost"
                print(f"🔌 OFFLINE: {device_id} kehilangan koneksi")

        elif current_state["status"] == "error":
            if rand_val < 0.3:  # 30% kemungkinan pulih
                current_state["status"] = "online"
                current_state["message"] = "System OK"
                print(f"✅ RECOVERED: {device_id} kembali normal")
            elif rand_val > 0.95:  # 5% kemungkinan jadi offline total
                current_state["status"] = "offline"
                current_state["message"] = "Critical Failure"
                print(f"🚨 CRITICAL: {device_id} gagal total")

        elif current_state["status"] == "offline":
            if rand_val < 0.4:  # 40% kemungkinan pulih
                current_state["status"] = "online"
                current_state["message"] = "System OK"
                print(f"🔁 RECONNECTED: {device_id} kembali online")

        # Simpan perubahan
        device_states[device_id] = current_state

        # Kirim status ke API
        payload = {
            "device_id": device_id,
            "status": current_state["status"],
            "message": current_state["message"]
        }
        try:
            requests.post(API_URL, json=payload, timeout=3)
        except requests.exceptions.ConnectionError:
            print("❌ Tidak bisa menghubungi API. Pastikan 'api.py' aktif.")
        except Exception as e:
            print(f"⚠️ Error mengirim data: {e}")

        # Tambahkan sedikit jeda acak antar perangkat untuk efek 'live'
        time.sleep(random.uniform(0.1, 0.3))

    print(f"--- Siklus selesai. Menunggu {SIKLUS_TUNGGU} detik... ---")
    time.sleep(SIKLUS_TUNGGU)
