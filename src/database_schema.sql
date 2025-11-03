-- ====================================================
-- Hospital IoT Monitoring System - Database Schema
-- ====================================================
-- Database: hospital_iot_db
-- Description: Schema untuk sistem monitoring perangkat IoT rumah sakit
--              dengan fitur history tracking dan ticketing system
-- ====================================================

-- Drop existing tables if needed (uncomment jika ingin reset)
-- DROP TABLE IF EXISTS device_history CASCADE;
-- DROP TABLE IF EXISTS tickets CASCADE;
-- DROP TABLE IF EXISTS devices CASCADE;

-- ====================================================
-- 1. TABEL DEVICES
-- ====================================================
-- Menyimpan status terkini dari setiap perangkat
-- ====================================================

CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    last_seen BIGINT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('online', 'error', 'offline')),
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index untuk query yang lebih cepat
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen DESC);

COMMENT ON TABLE devices IS 'Tabel utama yang menyimpan status terkini dari semua perangkat IoT';
COMMENT ON COLUMN devices.device_id IS 'ID unik perangkat (Primary Key)';
COMMENT ON COLUMN devices.last_seen IS 'Unix timestamp terakhir kali perangkat check-in';
COMMENT ON COLUMN devices.status IS 'Status perangkat: online, error, atau offline';
COMMENT ON COLUMN devices.message IS 'Pesan status atau deskripsi kondisi perangkat';

-- ====================================================
-- 2. TABEL DEVICE_HISTORY
-- ====================================================
-- Menyimpan SEMUA perubahan status perangkat untuk audit trail
-- ====================================================

CREATE TABLE IF NOT EXISTS device_history (
    id SERIAL PRIMARY KEY,
    device_id TEXT NOT NULL,
    timestamp BIGINT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('online', 'error', 'offline')),
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index untuk query history berdasarkan device dan waktu
CREATE INDEX IF NOT EXISTS idx_history_device_id ON device_history(device_id);
CREATE INDEX IF NOT EXISTS idx_history_timestamp ON device_history(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_history_status ON device_history(status);
CREATE INDEX IF NOT EXISTS idx_history_device_time ON device_history(device_id, timestamp DESC);

-- Foreign key relationship (optional, bisa diaktifkan jika diperlukan)
-- ALTER TABLE device_history ADD CONSTRAINT fk_device_history_device 
-- FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE;

COMMENT ON TABLE device_history IS 'History log dari semua perubahan status perangkat untuk analisis dan audit';
COMMENT ON COLUMN device_history.id IS 'Auto-increment ID untuk setiap record history';
COMMENT ON COLUMN device_history.device_id IS 'ID perangkat yang mengalami perubahan status';
COMMENT ON COLUMN device_history.timestamp IS 'Unix timestamp saat perubahan terjadi';
COMMENT ON COLUMN device_history.status IS 'Status perangkat saat itu';
COMMENT ON COLUMN device_history.message IS 'Deskripsi atau pesan terkait status';

-- ====================================================
-- 3. TABEL TICKETS
-- ====================================================
-- Sistem ticketing untuk tracking issues dan penanganan
-- ====================================================

CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('error', 'offline', 'resolved')),
    issue_type TEXT NOT NULL CHECK (issue_type IN ('ERROR', 'OFFLINE')),
    message TEXT,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    resolved_at BIGINT,
    assigned_to TEXT,
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE
);

-- Index untuk query tickets
CREATE INDEX IF NOT EXISTS idx_tickets_device_id ON tickets(device_id);
CREATE INDEX IF NOT EXISTS idx_tickets_active ON tickets(is_active);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_created ON tickets(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tickets_issue_type ON tickets(issue_type);
CREATE INDEX IF NOT EXISTS idx_tickets_assigned ON tickets(assigned_to) WHERE assigned_to IS NOT NULL;

-- Foreign key relationship (optional)
-- ALTER TABLE tickets ADD CONSTRAINT fk_tickets_device 
-- FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE;

COMMENT ON TABLE tickets IS 'Sistem ticketing untuk tracking dan manajemen issues perangkat';
COMMENT ON COLUMN tickets.ticket_id IS 'ID unik ticket (format: TKT-timestamp-devicecode)';
COMMENT ON COLUMN tickets.device_id IS 'ID perangkat yang mengalami masalah';
COMMENT ON COLUMN tickets.status IS 'Status ticket: error, offline, atau resolved';
COMMENT ON COLUMN tickets.issue_type IS 'Tipe masalah: ERROR atau OFFLINE';
COMMENT ON COLUMN tickets.message IS 'Deskripsi masalah yang terjadi';
COMMENT ON COLUMN tickets.created_at IS 'Unix timestamp saat ticket dibuat';
COMMENT ON COLUMN tickets.updated_at IS 'Unix timestamp terakhir kali ticket diupdate';
COMMENT ON COLUMN tickets.resolved_at IS 'Unix timestamp saat ticket diselesaikan';
COMMENT ON COLUMN tickets.assigned_to IS 'Nama teknisi yang ditugaskan menangani ticket';
COMMENT ON COLUMN tickets.notes IS 'Catatan tambahan dari teknisi atau sistem';
COMMENT ON COLUMN tickets.is_active IS 'Status aktif ticket (TRUE = masih open, FALSE = resolved)';

-- ====================================================
-- 4. VIEWS (Optional - untuk kemudahan query)
-- ====================================================

-- View untuk melihat devices dengan ticket aktif mereka
CREATE OR REPLACE VIEW devices_with_active_tickets AS
SELECT 
    d.device_id,
    d.status AS current_status,
    d.last_seen,
    d.message AS current_message,
    t.ticket_id,
    t.issue_type,
    t.assigned_to,
    t.created_at AS ticket_created_at
FROM devices d
LEFT JOIN tickets t ON d.device_id = t.device_id AND t.is_active = TRUE
WHERE d.status IN ('error', 'offline');

COMMENT ON VIEW devices_with_active_tickets IS 'View yang menampilkan perangkat bermasalah dengan ticket aktif mereka';

-- View untuk statistik perangkat
CREATE OR REPLACE VIEW device_statistics AS
SELECT 
    COUNT(*) AS total_devices,
    COUNT(*) FILTER (WHERE status = 'online') AS online_count,
    COUNT(*) FILTER (WHERE status = 'error') AS error_count,
    COUNT(*) FILTER (WHERE status = 'offline') AS offline_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'online') / NULLIF(COUNT(*), 0), 2) AS uptime_percentage
FROM devices;

COMMENT ON VIEW device_statistics IS 'Statistik real-time status semua perangkat';

-- View untuk statistik ticket
CREATE OR REPLACE VIEW ticket_statistics AS
SELECT 
    COUNT(*) AS total_tickets,
    COUNT(*) FILTER (WHERE is_active = TRUE) AS active_tickets,
    COUNT(*) FILTER (WHERE is_active = FALSE) AS resolved_tickets,
    COUNT(*) FILTER (WHERE issue_type = 'ERROR') AS error_tickets,
    COUNT(*) FILTER (WHERE issue_type = 'OFFLINE') AS offline_tickets,
    ROUND(100.0 * COUNT(*) FILTER (WHERE is_active = FALSE) / NULLIF(COUNT(*), 0), 2) AS resolution_rate
FROM tickets;

COMMENT ON VIEW ticket_statistics IS 'Statistik ticketing system';

-- ====================================================
-- 5. FUNCTIONS (Optional - untuk automasi)
-- ====================================================

-- Function untuk menghitung uptime device dalam periode tertentu
CREATE OR REPLACE FUNCTION calculate_device_uptime(
    p_device_id TEXT,
    p_hours INTEGER DEFAULT 24
)
RETURNS NUMERIC AS $$
DECLARE
    v_total_records INTEGER;
    v_online_records INTEGER;
    v_uptime_pct NUMERIC;
BEGIN
    SELECT 
        COUNT(*),
        COUNT(*) FILTER (WHERE status = 'online')
    INTO v_total_records, v_online_records
    FROM device_history
    WHERE device_id = p_device_id
      AND timestamp >= EXTRACT(EPOCH FROM NOW() - (p_hours || ' hours')::INTERVAL);
    
    IF v_total_records = 0 THEN
        RETURN 0;
    END IF;
    
    v_uptime_pct := ROUND(100.0 * v_online_records / v_total_records, 2);
    RETURN v_uptime_pct;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION calculate_device_uptime IS 'Menghitung persentase uptime device dalam periode tertentu (default 24 jam)';

-- ====================================================
-- 6. SAMPLE QUERIES (untuk testing)
-- ====================================================

-- Query 1: Lihat semua devices dengan status terkini
-- SELECT * FROM devices ORDER BY device_id;

-- Query 2: Lihat history device tertentu (10 record terakhir)
-- SELECT * FROM device_history 
-- WHERE device_id = 'BED-MONITOR-101-ICU' 
-- ORDER BY timestamp DESC LIMIT 10;

-- Query 3: Lihat semua active tickets
-- SELECT * FROM tickets WHERE is_active = TRUE ORDER BY created_at DESC;

-- Query 4: Statistik perangkat
-- SELECT * FROM device_statistics;

-- Query 5: Statistik tickets
-- SELECT * FROM ticket_statistics;

-- Query 6: Devices dengan masalah dan ticket aktif
-- SELECT * FROM devices_with_active_tickets;

-- Query 7: Hitung uptime device tertentu dalam 24 jam terakhir
-- SELECT calculate_device_uptime('BED-MONITOR-101-ICU', 24);

-- Query 8: Top 5 devices dengan masalah terbanyak
-- SELECT device_id, COUNT(*) as issue_count
-- FROM device_history
-- WHERE status IN ('error', 'offline')
--   AND timestamp >= EXTRACT(EPOCH FROM NOW() - INTERVAL '7 days')
-- GROUP BY device_id
-- ORDER BY issue_count DESC
-- LIMIT 5;

-- Query 9: Rata-rata response time resolving tickets
-- SELECT 
--     AVG(resolved_at - created_at) / 60 as avg_resolution_minutes
-- FROM tickets
-- WHERE resolved_at IS NOT NULL;

-- Query 10: Ticket yang belum di-assign
-- SELECT * FROM tickets 
-- WHERE is_active = TRUE AND assigned_to IS NULL
-- ORDER BY created_at;

-- ====================================================
-- 7. MAINTENANCE (Optional)
-- ====================================================

-- Untuk membersihkan history lama (lebih dari 90 hari)
-- DELETE FROM device_history 
-- WHERE created_at < NOW() - INTERVAL '90 days';

-- Untuk archive resolved tickets lama (lebih dari 30 hari)
-- UPDATE tickets 
-- SET notes = COALESCE(notes, '') || E'\n[ARCHIVED] ' || NOW()::TEXT
-- WHERE is_active = FALSE 
--   AND resolved_at < EXTRACT(EPOCH FROM NOW() - INTERVAL '30 days');

-- ====================================================
-- SELESAI
-- ====================================================
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO it_support_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO it_support_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO it_support_user;