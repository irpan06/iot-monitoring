import psycopg2
import time
from flask import Flask, request, jsonify
from datetime import datetime
from zoneinfo import ZoneInfo

# --- KONFIGURASI DATABASE ---
PG_HOST = "localhost"
PG_PORT = 5432
PG_USER = "it_support_user"  # Ganti sesuai user Anda
PG_PASSWORD = "v1r"  # Ganti sesuai password Anda
PG_DATABASE = "hospital_iot_db"  # Ganti sesuai nama database Anda
# ----------------------------

# Zona waktu lokal (Asia/Jakarta = WIB)
LOCAL_TZ = ZoneInfo("Asia/Jakarta")

def local_timestamp():
    """Mengembalikan epoch detik berdasarkan waktu lokal (Asia/Jakarta)."""
    return int(datetime.now(LOCAL_TZ).timestamp())

# Inisialisasi aplikasi Flask
app = Flask(__name__)

# --- (A) Inisialisasi Database ---
def init_db():
    print("Menghubungkan ke database PostgreSQL...")
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            user=PG_USER,
            password=PG_PASSWORD,
            database=PG_DATABASE
        )
        cursor = conn.cursor()

        # Pastikan timezone database diatur ke Asia/Jakarta
        cursor.execute("SET TIMEZONE = 'Asia/Jakarta';")

        # Tabel devices
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            device_id TEXT PRIMARY KEY,
            last_seen BIGINT,
            status TEXT,
            message TEXT
        )
        ''')

        # Tabel device_history
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS device_history (
            id SERIAL PRIMARY KEY,
            device_id TEXT NOT NULL,
            timestamp BIGINT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'Asia/Jakarta')
        )
        ''')

        # Index
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_history_device_id 
        ON device_history(device_id)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_history_timestamp 
        ON device_history(timestamp DESC)
        ''')

        # Tabel tickets
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id TEXT PRIMARY KEY,
            device_id TEXT NOT NULL,
            status TEXT NOT NULL,
            issue_type TEXT NOT NULL,
            message TEXT,
            created_at BIGINT NOT NULL,
            updated_at BIGINT NOT NULL,
            resolved_at BIGINT,
            assigned_to TEXT,
            notes TEXT,
            is_active BOOLEAN DEFAULT TRUE
        )
        ''')

        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_tickets_device_id 
        ON tickets(device_id)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_tickets_active 
        ON tickets(is_active)
        ''')

        conn.commit()
        cursor.close()
        conn.close()
        print(f"Database '{PG_DATABASE}' siap digunakan (zona waktu Asia/Jakarta).")

    except psycopg2.OperationalError as e:
        print(f"GAGAL terhubung ke PostgreSQL: {e}")
        exit(1)
    except Exception as e:
        print(f"Error saat inisialisasi database: {e}")
        exit(1)

# --- (B) Auto-create Ticket ---
def create_ticket_if_needed(conn, device_id, status, message):
    if status not in ['error', 'offline']:
        return None

    cursor = conn.cursor()
    cursor.execute('''
        SELECT ticket_id FROM tickets 
        WHERE device_id = %s AND is_active = TRUE
        LIMIT 1
    ''', (device_id,))
    existing_ticket = cursor.fetchone()

    now = local_timestamp()
    if existing_ticket:
        cursor.execute('''
            UPDATE tickets 
            SET updated_at = %s, message = %s
            WHERE ticket_id = %s
        ''', (now, message, existing_ticket[0]))
        cursor.close()
        return existing_ticket[0]

    ticket_id = f"TKT-{now}-{device_id[-4:]}"
    issue_type = 'ERROR' if status == 'error' else 'OFFLINE'

    cursor.execute('''
        INSERT INTO tickets 
        (ticket_id, device_id, status, issue_type, message, created_at, updated_at, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
    ''', (ticket_id, device_id, status, issue_type, message, now, now))

    cursor.close()
    return ticket_id

# --- (C) Auto-resolve Ticket ---
def resolve_ticket_if_needed(conn, device_id, status):
    if status != 'online':
        return

    cursor = conn.cursor()
    cursor.execute('''
        SELECT ticket_id FROM tickets 
        WHERE device_id = %s AND is_active = TRUE
    ''', (device_id,))
    active_tickets = cursor.fetchall()

    now = local_timestamp()
    for ticket in active_tickets:
        cursor.execute('''
            UPDATE tickets 
            SET is_active = FALSE, 
                resolved_at = %s,
                updated_at = %s,
                status = 'resolved'
            WHERE ticket_id = %s
        ''', (now, now, ticket[0]))
        print(f"✅ Auto-resolved ticket: {ticket[0]} for device: {device_id}")

    cursor.close()

# --- (D) Endpoint Check-in ---
@app.route('/api/v1/checkin', methods=['POST'])
def device_checkin():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        status = data.get('status')
        message = data.get('message', '')

        if not device_id or not status:
            return jsonify({"error": "Data 'device_id' atau 'status' tidak lengkap"}), 400

        last_seen = local_timestamp()

        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT, user=PG_USER, 
            password=PG_PASSWORD, database=PG_DATABASE
        )
        cursor = conn.cursor()

        # Update devices
        upsert_query = """
        INSERT INTO devices (device_id, last_seen, status, message)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (device_id) DO UPDATE SET
            last_seen = EXCLUDED.last_seen,
            status = EXCLUDED.status,
            message = EXCLUDED.message;
        """
        cursor.execute(upsert_query, (device_id, last_seen, status, message))

        # Tambah ke device_history
        cursor.execute('''
            INSERT INTO device_history (device_id, timestamp, status, message)
            VALUES (%s, %s, %s, %s)
        ''', (device_id, last_seen, status, message))

        ticket_id = create_ticket_if_needed(conn, device_id, status, message)
        resolve_ticket_if_needed(conn, device_id, status)

        conn.commit()
        cursor.close()
        conn.close()

        response = {
            "success": True,
            "device": device_id,
            "local_time": datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
        }
        if ticket_id:
            response["ticket_created"] = ticket_id

        return jsonify(response), 200

    except Exception as e:
        print(f"Error pada /checkin: {e}")
        return jsonify({"error": str(e)}), 500

# --- (E) Endpoint Root ---
@app.route('/')
def index():
    now_str = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
    return f"IT Support API Server running on local time: {now_str}"

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
