import streamlit as st
import psycopg2
import pandas as pd
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import plotly.graph_objects as go
import plotly.express as px


# Konfigurasi Database
PG_HOST = "localhost"
PG_PORT = 5432
PG_USER = "it_support_user"
PG_PASSWORD = "v1r"
PG_DATABASE = "hospital_iot_db"

# Konfigurasi Timezone
LOCAL_TZ = ZoneInfo("Asia/Jakarta")

# Konfigurasi Page
delay = 10
st.set_page_config(
    page_title="Hospital IoT Monitoring System",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk tampilan profesional
st.markdown("""
<style>
    .main {
        background-color: #f0f2f6;
    }
    
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .hospital-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .status-online {
        background-color: #10b981;
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
    
    .status-error {
        background-color: #ef4444;
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
    
    .status-offline {
        background-color: #6b7280;
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
    
    .status-resolved {
        background-color: #3b82f6;
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
    
    .category-header {
        background-color: #ffffff;
        padding: 10px 15px;
        border-left: 4px solid #2a5298;
        margin: 15px 0;
        border-radius: 5px;
        font-weight: bold;
        color: #1e3c72;
    }
    
    .alert-critical {
        background-color: #fef2f2;
        border-left: 4px solid #ef4444;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Fungsi helper untuk mendapatkan waktu sekarang di timezone lokal
def get_local_now():
    """Mengembalikan datetime sekarang dalam timezone lokal (Asia/Jakarta)"""
    return datetime.now(LOCAL_TZ)

# Fungsi untuk mengambil data dari database
@st.cache_data(ttl=5)
def get_device_data():
    try:
        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT, user=PG_USER,
            password=PG_PASSWORD, database=PG_DATABASE
        )
        query = "SELECT * FROM devices ORDER BY device_id"
        df = pd.read_sql(query, conn)
        conn.close()
        
        if not df.empty:
            # Convert timestamp ke timezone lokal
            df['last_seen_time'] = pd.to_datetime(df['last_seen'], unit='s', utc=True).dt.tz_convert(LOCAL_TZ)
            df['time_ago'] = df['last_seen_time'].apply(
                lambda x: f"{int((get_local_now() - x).total_seconds())}s ago"
            )
        return df
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return pd.DataFrame()

# Fungsi untuk mengambil tickets dari database
@st.cache_data(ttl=5)
def get_tickets_from_db(active_only=True):
    try:
        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT, user=PG_USER,
            password=PG_PASSWORD, database=PG_DATABASE
        )
        if active_only:
            query = """
                SELECT ticket_id, device_id, status, issue_type, message, 
                       created_at, updated_at, resolved_at, assigned_to, notes, is_active
                FROM tickets
                WHERE is_active = TRUE
                ORDER BY created_at DESC
            """
        else:
            query = """
                SELECT ticket_id, device_id, status, issue_type, message, 
                       created_at, updated_at, resolved_at, assigned_to, notes, is_active
                FROM tickets
                ORDER BY created_at DESC
            """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error fetching tickets: {e}")
        return pd.DataFrame()

# Fungsi untuk mengambil history device
@st.cache_data(ttl=5)
def get_device_history(device_id, limit=100):
    try:
        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT, user=PG_USER,
            password=PG_PASSWORD, database=PG_DATABASE
        )
        query = """
            SELECT device_id, timestamp, status, message, created_at
            FROM device_history
            WHERE device_id = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """
        df = pd.read_sql(query, conn, params=(device_id, limit))
        conn.close()
        
        if not df.empty:
            # Convert timestamp ke timezone lokal
            df['timestamp_dt'] = pd.to_datetime(df['timestamp'], unit='s', utc=True).dt.tz_convert(LOCAL_TZ)
        return df
    except Exception as e:
        st.error(f"Error fetching history: {e}")
        return pd.DataFrame()

# Fungsi untuk update ticket
def update_ticket(ticket_id, field, value):
    try:
        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT, user=PG_USER,
            password=PG_PASSWORD, database=PG_DATABASE
        )
        cursor = conn.cursor()
        
        # Gunakan timestamp lokal
        now_timestamp = int(get_local_now().timestamp())
        
        if field == 'assigned_to':
            cursor.execute("""
                UPDATE tickets 
                SET assigned_to = %s, updated_at = %s
                WHERE ticket_id = %s
            """, (value, now_timestamp, ticket_id))
        elif field == 'notes':
            cursor.execute("""
                UPDATE tickets 
                SET notes = COALESCE(notes, '') || %s, updated_at = %s
                WHERE ticket_id = %s
            """, (f"\n{get_local_now().strftime('%Y-%m-%d %H:%M:%S')}: {value}", now_timestamp, ticket_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error updating ticket: {e}")
        return False

# Fungsi untuk kategorisasi perangkat
def categorize_device(device_id):
    if "BED-MONITOR" in device_id:
        return "Patient Monitoring", "🛏️"
    elif "INFUSION-PUMP" in device_id:
        return "Infusion Systems", "💉"
    elif "TEMP-SENSOR" in device_id:
        return "Environmental Sensors", "🌡️"
    elif "VENTILATOR" in device_id:
        return "Respiratory Equipment", "🫁"
    elif "MRI" in device_id or "CT-SCANNER" in device_id:
        return "Imaging Systems", "📷"
    else:
        return "Other Devices", "⚙️"

# Inisialisasi session state
if 'page' not in st.session_state:
    st.session_state.page = "Monitoring Overview"

# Header Dashboard
st.markdown("""
<div class="hospital-header">
    <h1>🏥 Hospital IoT Monitoring System</h1>
    <p style="margin:0; font-size: 1.1em;">Real-time Device Health & Status Monitoring with History Tracking</p>
</div>
""", unsafe_allow_html=True)

# Sidebar untuk navigasi dan kontrol
with st.sidebar:
    st.title('Navigation')
    st.subheader("ℹ️ System Information")
    # Gunakan waktu lokal untuk sidebar
    st.info(f"**Last Update:** {get_local_now().strftime('%H:%M:%S')}")
    st.info(f"**Date:** {get_local_now().strftime('%d %B %Y')}")
    st.info(f"**Timezone:** Asia/Jakarta (WIB)")
    st.info(f"**Current Page:** {st.session_state.page}")
    st.markdown('---')
    # Navigation buttons
    if st.button("📊 Monitoring Overview", use_container_width=True):
        st.session_state.page = "Monitoring Overview"
        st.rerun()
    
    if st.button("🎫 Active Tickets", use_container_width=True):
        st.session_state.page = "Active Tickets"
        st.rerun()
    
    if st.button("📜 Ticket History", use_container_width=True):
        st.session_state.page = "Ticket History"
        st.rerun()
    
    if st.button("📈 Device History", use_container_width=True):
        st.session_state.page = "Device History"
        st.rerun()
    
    st.markdown("---")
    st.subheader("⚙️ Controls")
    
    auto_refresh = st.checkbox(f"Auto-refresh ({delay}s)", value=True)
    
    if st.button("🔄 Manual Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    

# Ambil data dari database
df = get_device_data()
tickets_df = get_tickets_from_db(active_only=True)

# ==================== TOAST TICKET FEATURE ====================

# Inisialisasi session state untuk tracking perubahan status perangkat
if 'previous_errors' not in st.session_state:
    st.session_state.previous_errors = set()

# Jika data tidak kosong, lakukan pengecekan perubahan status
if not df.empty:
    current_errors = set(df[(df['status'] == 'error') | (df['status'] == 'offline')]['device_id'])
    new_errors = current_errors - st.session_state.previous_errors
    resolved = st.session_state.previous_errors - current_errors

    # Tampilkan toast untuk perangkat baru error/offline
    for device_id in new_errors:
        row = df[df['device_id'] == device_id].iloc[0]
        issue_type = row['status'].upper()
        message = row['message']
        st.toast(f"🚨 NEW {issue_type} DETECTED\nDevice: {device_id}\nIssue: {message}", icon="⚠️")

    # Tampilkan toast untuk perangkat yang sudah kembali normal
    for device_id in resolved:
        st.toast(f"✅ RESOLVED\nDevice {device_id} is back online.", icon="✅")

    # Update state
    st.session_state.previous_errors = current_errors
# ===============================================================

if df.empty:
    st.warning("⚠️ No device data available. Please ensure the simulator is running.")
else:
    # Hitung statistik
    total_devices = len(df)
    online_count = len(df[df['status'] == 'online'])
    error_count = len(df[df['status'] == 'error'])
    offline_count = len(df[df['status'] == 'offline'])
    
    # ========== PAGE: MONITORING OVERVIEW ==========
    if st.session_state.page == "Monitoring Overview":
        # KPI Metrics di bagian atas
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                label="📱 Total Devices",
                value=total_devices
            )
        
        with col2:
            st.metric(
                label="✅ Online",
                value=online_count
            )
        
        with col3:
            st.metric(
                label="⚠️ Error",
                value=error_count
            )
        
        with col4:
            st.metric(
                label="🔌 Offline",
                value=offline_count
            )
        
        with col5:
            st.metric(
                label="🎫 Active Tickets",
                value=len(tickets_df)
            )
        
        st.markdown("---")
        
        # Alert untuk perangkat kritis
        if error_count > 0 or offline_count > 0:
            critical_devices = df[(df['status'] == 'error') | (df['status'] == 'offline')]
            st.markdown(f"""
            <div class="alert-critical">
                <strong>🚨 CRITICAL ALERT:</strong> {len(critical_devices)} device(s) require immediate attention!
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Tambahkan kategori ke dataframe
        df['category'], df['icon'] = zip(*df['device_id'].apply(categorize_device))
        
        # Visualisasi Status Distribution by Category
        st.subheader("📊 Device Status Distribution by Category")
        
        category_colors = {
            'Patient Monitoring': '#2563eb',
            'Infusion Systems': '#1e40af',
            'Environmental Sensors': '#0891b2',
            'Respiratory Equipment': '#0d9488',
            'Imaging Systems': '#475569',
            'Other Devices': '#64748b'
        }
        
        col_chart1, col_chart2, col_chart3 = st.columns(3)
        
        # Chart 1: Online Devices by Category
        with col_chart1:
            st.markdown("##### ✅ Online Devices")
            online_df = df[df['status'] == 'online']
            online_by_category = online_df['category'].value_counts()
            
            if not online_by_category.empty:
                colors_list = [category_colors.get(cat, '#94a3b8') for cat in online_by_category.index]
                
                fig_online = go.Figure(data=[go.Pie(
                    labels=online_by_category.index,
                    values=online_by_category.values,
                    hole=0.5,
                    marker=dict(colors=colors_list),
                    textinfo='value',
                    textfont=dict(size=16, color='white', family='Arial Black'),
                    hovertemplate='<b>%{label}</b><br>Devices: %{value}<br>%{percent}<extra></extra>'
                )])
                
                fig_online.update_layout(
                    showlegend=True,
                    height=400,
                    margin=dict(t=10, b=80, l=10, r=10),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    legend=dict(
                        orientation="v",
                        yanchor="bottom",
                        y=-0.5,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=10)
                    )
                )
                
                fig_online.add_annotation(
                    text=f"<b>{online_count}</b>",
                    x=0.5, y=0.5,
                    font=dict(size=28, color='#10b981', family='Arial Black'),
                    showarrow=False
                )
                
                st.plotly_chart(fig_online, use_container_width=True)
            else:
                st.info("No online devices")
        
        # Chart 2: Error Devices by Category
        with col_chart2:
            st.markdown("##### ⚠️ Error Devices")
            error_df = df[df['status'] == 'error']
            error_by_category = error_df['category'].value_counts()
            
            if not error_by_category.empty:
                colors_list = [category_colors.get(cat, '#94a3b8') for cat in error_by_category.index]
                
                fig_error = go.Figure(data=[go.Pie(
                    labels=error_by_category.index,
                    values=error_by_category.values,
                    hole=0.5,
                    marker=dict(colors=colors_list),
                    textinfo='value',
                    textfont=dict(size=16, color='white', family='Arial Black'),
                    hovertemplate='<b>%{label}</b><br>Devices: %{value}<br>%{percent}<extra></extra>'
                )])
                
                fig_error.update_layout(
                    showlegend=True,
                    height=400,
                    margin=dict(t=10, b=80, l=10, r=10),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    legend=dict(
                        orientation="v",
                        yanchor="bottom",
                        y=-0.5,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=10)
                    )
                )
                
                fig_error.add_annotation(
                    text=f"<b>{error_count}</b>",
                    x=0.5, y=0.5,
                    font=dict(size=28, color='#ef4444', family='Arial Black'),
                    showarrow=False
                )
                
                st.plotly_chart(fig_error, use_container_width=True)
            else:
                st.info("No error devices")
        
        # Chart 3: Offline Devices by Category
        with col_chart3:
            st.markdown("##### 🔌 Offline Devices")
            offline_df = df[df['status'] == 'offline']
            offline_by_category = offline_df['category'].value_counts()
            
            if not offline_by_category.empty:
                colors_list = [category_colors.get(cat, '#94a3b8') for cat in offline_by_category.index]
                
                fig_offline = go.Figure(data=[go.Pie(
                    labels=offline_by_category.index,
                    values=offline_by_category.values,
                    hole=0.5,
                    marker=dict(colors=colors_list),
                    textinfo='value',
                    textfont=dict(size=16, color='white', family='Arial Black'),
                    hovertemplate='<b>%{label}</b><br>Devices: %{value}<br>%{percent}<extra></extra>'
                )])
                
                fig_offline.update_layout(
                    showlegend=True,
                    height=400,
                    margin=dict(t=10, b=80, l=10, r=10),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    legend=dict(
                        orientation="v",
                        yanchor="bottom",
                        y=-0.5,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=10)
                    )
                )
                
                fig_offline.add_annotation(
                    text=f"<b>{offline_count}</b>",
                    x=0.5, y=0.5,
                    font=dict(size=28, color='#6b7280', family='Arial Black'),
                    showarrow=False
                )
                
                st.plotly_chart(fig_offline, use_container_width=True)
            else:
                st.info("No offline devices")
        
        st.markdown("---")
        
        # Daftar perangkat berdasarkan kategori dalam TABS
        st.subheader("🏥 Device Status by Category")
        
        categories = sorted(df['category'].unique())
        device_tabs = st.tabs([f"{df[df['category']==cat].iloc[0]['icon']} {cat}" for cat in categories])
        
        for idx, category in enumerate(categories):
            with device_tabs[idx]:
                category_devices = df[df['category'] == category]
                
                num_devices = len(category_devices)
                cols_per_row = 3
                
                for i in range(0, num_devices, cols_per_row):
                    cols = st.columns(cols_per_row)
                    
                    for j in range(cols_per_row):
                        if i + j < num_devices:
                            row = category_devices.iloc[i + j]
                            
                            with cols[j]:
                                if row['status'] == 'online':
                                    status_badge = '<span class="status-online">● ONLINE</span>'
                                    border_color = '#10b981'
                                    ticket_section = ""
                                elif row['status'] == 'error':
                                    status_badge = '<span class="status-error">● ERROR</span>'
                                    border_color = '#ef4444'
                                    device_tickets = tickets_df[tickets_df['device_id'] == row['device_id']]
                                    if not device_tickets.empty:
                                        ticket_id = device_tickets.iloc[0]['ticket_id']
                                        ticket_section = f'<div style="margin-top: auto;"><div style="background-color: #fef2f2; padding: 5px; border-radius: 4px; font-size: 0.8em;"><strong>🎫 Ticket:</strong> {ticket_id}</div></div>'
                                    else:
                                        ticket_section = ""
                                else:
                                    status_badge = '<span class="status-offline">● OFFLINE</span>'
                                    border_color = '#6b7280'
                                    device_tickets = tickets_df[tickets_df['device_id'] == row['device_id']]
                                    if not device_tickets.empty:
                                        ticket_id = device_tickets.iloc[0]['ticket_id']
                                        ticket_section = f'<div style="margin-top: auto;"><div style="background-color: #f3f4f6; padding: 5px; border-radius: 4px; font-size: 0.8em;"><strong>🎫 Ticket:</strong> {ticket_id}</div></div>'
                                    else:
                                        ticket_section = ""
                                
                                st.markdown(f"""
                                <div style="background-color: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid {border_color}; box-shadow: 0 2px 4px rgba(0,0,0,0.1); height: 180px; display: flex; flex-direction: column;">
                                    <div style="font-weight: bold; margin-bottom: 10px; font-size: 0.95em; color: #1e3c72;">{row['device_id']}</div>
                                    <div style="margin-bottom: 8px;">{status_badge}</div>
                                    <div style="color: #6b7280; font-size: 0.85em; margin-bottom: 5px;">
                                        ⏱️ {row['time_ago']}
                                    </div>
                                    <div style="color: #6b7280; font-size: 0.85em; font-style: italic; margin-bottom: 8px;">
                                        💬 {row['message']}
                                    </div>
                                    {ticket_section}
                                </div>
                                """, unsafe_allow_html=True)
        
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(f"<p style='text-align: center; color: #6b7280;'>Dashboard last updated: {get_local_now().strftime('%Y-%m-%d %H:%M:%S')} WIB</p>", unsafe_allow_html=True)
    
    # ========== PAGE: ACTIVE TICKETS ==========
    elif st.session_state.page == "Active Tickets":
        st.title("🎫 Active Support Tickets")
        
        if not tickets_df.empty:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    label="📋 Total Active Tickets",
                    value=len(tickets_df)
                )
            
            with col2:
                error_tickets = len(tickets_df[tickets_df['issue_type'] == 'ERROR'])
                st.metric(
                    label="⚠️ Error Tickets",
                    value=error_tickets
                )
            
            with col3:
                offline_tickets = len(tickets_df[tickets_df['issue_type'] == 'OFFLINE'])
                st.metric(
                    label="🔌 Offline Tickets",
                    value=offline_tickets
                )
            
            st.markdown("---")
            
            # Tampilkan tabel tickets dengan timezone lokal
            display_df = tickets_df.copy()
            display_df['created_at_dt'] = pd.to_datetime(display_df['created_at'], unit='s', utc=True).dt.tz_convert(LOCAL_TZ).dt.strftime('%Y-%m-%d %H:%M:%S')
            display_df['updated_at_dt'] = pd.to_datetime(display_df['updated_at'], unit='s', utc=True).dt.tz_convert(LOCAL_TZ).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            table_df = display_df[['ticket_id', 'device_id', 'issue_type', 'message', 'assigned_to', 'created_at_dt', 'updated_at_dt']].copy()
            table_df.columns = ['Ticket ID', 'Device ID', 'Issue Type', 'Message', 'Assigned To', 'Created At', 'Updated At']
            
            st.dataframe(
                table_df,
                use_container_width=True,
                hide_index=True
            )
            
            st.markdown("---")
            st.subheader("🔍 Ticket Details")
            
            for _, ticket in tickets_df.iterrows():
                with st.expander(f"🎫 {ticket['ticket_id']} - {ticket['device_id']}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**Device ID:** {ticket['device_id']}")
                        st.markdown(f"**Issue Type:** {ticket['issue_type']}")
                        st.markdown(f"**Status:** {ticket['status']}")
                    
                    with col2:
                        # Konversi timestamp ke timezone lokal tanpa offset
                        created_dt = datetime.fromtimestamp(ticket['created_at'], tz=LOCAL_TZ)
                        updated_dt = datetime.fromtimestamp(ticket['updated_at'], tz=LOCAL_TZ)
                        st.markdown(f"**Created:** {created_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                        st.markdown(f"**Updated:** {updated_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                        st.markdown(f"**Assigned To:** {ticket['assigned_to'] if ticket['assigned_to'] else 'Unassigned'}")
                    
                    st.markdown(f"**Issue Description:** {ticket['message']}")
                    
                    if ticket['notes']:
                        st.markdown("**Notes:**")
                        st.text_area("", value=ticket['notes'], height=100, key=f"notes_view_{ticket['ticket_id']}", disabled=True)
                    
                    st.markdown("---")
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        with st.form(key=f"assign_{ticket['ticket_id']}"):
                            technician_name = st.text_input("Technician Name", key=f"tech_{ticket['ticket_id']}")
                            if st.form_submit_button("🔧 Assign Technician"):
                                if technician_name:
                                    if update_ticket(ticket['ticket_id'], 'assigned_to', technician_name):
                                        st.success(f"Assigned to {technician_name}")
                                        st.cache_data.clear()
                                        time.sleep(1)
                                        st.rerun()
                                else:
                                    st.warning("Please enter a name")
                    
                    with col_btn2:
                        with st.form(key=f"note_{ticket['ticket_id']}"):
                            note_text = st.text_input("Add Note", key=f"note_input_{ticket['ticket_id']}")
                            if st.form_submit_button("📝 Add Note"):
                                if note_text:
                                    if update_ticket(ticket['ticket_id'], 'notes', note_text):
                                        st.success("Note added")
                                        st.cache_data.clear()
                                        time.sleep(1)
                                        st.rerun()
                                else:
                                    st.warning("Please enter a note")
        else:
            st.success("✅ No active tickets. All devices are operating normally.")
            st.balloons()
    
    # ========== PAGE: TICKET HISTORY ==========
    elif st.session_state.page == "Ticket History":
        st.title("📜 Ticket History")
        
        all_tickets_df = get_tickets_from_db(active_only=False)
        
        if not all_tickets_df.empty:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("📊 Total Tickets", len(all_tickets_df))
            
            with col2:
                active_count = len(all_tickets_df[all_tickets_df['is_active'] == True])
                st.metric("🔴 Active", active_count)
            
            with col3:
                resolved_count = len(all_tickets_df[all_tickets_df['is_active'] == False])
                st.metric("✅ Resolved", resolved_count)
            
            st.markdown("---")
            
            # Filter
            col_filter1, col_filter2 = st.columns(2)
            with col_filter1:
                filter_status = st.selectbox(
                    "Filter by Status",
                    ["All", "Active", "Resolved"]
                )
            
            with col_filter2:
                filter_type = st.selectbox(
                    "Filter by Issue Type",
                    ["All", "ERROR", "OFFLINE"]
                )
            
            # Apply filters
            filtered_df = all_tickets_df.copy()
            if filter_status == "Active":
                filtered_df = filtered_df[filtered_df['is_active'] == True]
            elif filter_status == "Resolved":
                filtered_df = filtered_df[filtered_df['is_active'] == False]
            
            if filter_type != "All":
                filtered_df = filtered_df[filtered_df['issue_type'] == filter_type]
            
            # Prepare display dataframe dengan timezone lokal
            display_df = filtered_df.copy()
            display_df['created_at_dt'] = pd.to_datetime(display_df['created_at'], unit='s', utc=True).dt.tz_convert(LOCAL_TZ).dt.strftime('%Y-%m-%d %H:%M:%S')
            display_df['status_display'] = display_df['is_active'].apply(lambda x: 'Active' if x else 'Resolved')
            
            table_df = display_df[['ticket_id', 'device_id', 'issue_type', 'status_display', 'message', 'assigned_to', 'created_at_dt']].copy()
            table_df.columns = ['Ticket ID', 'Device ID', 'Issue Type', 'Status', 'Message', 'Assigned To', 'Created At']
            
            st.dataframe(
                table_df,
                use_container_width=True,
                hide_index=True
            )
            
            # Statistik tambahan
            st.markdown("---")
    
    
    # ========== PAGE: DEVICE HISTORY ==========
    elif st.session_state.page == "Device History":
        st.title("📈 Device History")
        
        # Device selector
        device_list = sorted(df['device_id'].unique())
        selected_device = st.selectbox("Select Device", device_list)
        
        if selected_device:
            # Get device history
            history_df = get_device_history(selected_device, limit=200)
            
            if not history_df.empty:
                # Current status
                current_status = df[df['device_id'] == selected_device].iloc[0]
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Current Status", current_status['status'].upper())
                
                with col2:
                    st.metric("Last Seen", current_status['time_ago'])
                
                with col3:
                    st.metric("Total Records", len(history_df))
                
                with col4:
                    # Calculate uptime percentage
                    online_records = len(history_df[history_df['status'] == 'online'])
                    uptime_pct = (online_records / len(history_df) * 100) if len(history_df) > 0 else 0
                    st.metric("Uptime %", f"{uptime_pct:.1f}%")
                
                st.markdown("---")
                
                # Timeline chart dengan timezone lokal
                st.subheader("📊 Status Timeline")
                
                # Data sudah dalam timezone lokal dari get_device_history
                history_df['status_numeric'] = history_df['status'].map({
                    'online': 2,
                    'error': 1,
                    'offline': 0
                })
                
                fig_timeline = px.line(
                    history_df,
                    x='timestamp_dt',
                    y='status_numeric',
                    title=f'Status Timeline for {selected_device}',
                    labels={'timestamp_dt': 'Time (WIB)', 'status_numeric': 'Status'},
                    markers=True
                )
                
                fig_timeline.update_yaxes(
                    tickmode='array',
                    tickvals=[0, 1, 2],
                    ticktext=['Offline', 'Error', 'Online']
                )
                
                fig_timeline.update_traces(
                    line=dict(color='#2563eb', width=2),
                    marker=dict(size=6)
                )
                
                st.plotly_chart(fig_timeline, use_container_width=True)
                
                st.markdown("---")
                
                # Status distribution
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📊 Status Distribution")
                    status_counts = history_df['status'].value_counts()
                    
                    fig_dist = go.Figure(data=[go.Pie(
                        labels=status_counts.index,
                        values=status_counts.values,
                        hole=0.5,
                        marker=dict(colors=['#10b981', '#ef4444', '#6b7280']),
                        textinfo='value',
                        textfont=dict(size=16, color='white', family='Arial Black')
                    )])
                    
                    fig_dist.update_layout(
                        showlegend=True,
                        height=370,
                        margin=dict(t=10, b=80, l=10, r=10),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.2,
                            xanchor="center",
                            x=0.5,
                            font=dict(size=15)
                        )
                    )
                    
                    st.plotly_chart(fig_dist, use_container_width=True)
                
                with col2:
                
                    # Detailed history table dengan timezone lokal
                    st.subheader("📜 Detailed History")
                    
                    # Format timestamp tanpa timezone offset
                    table_df = history_df.copy()
                    table_df['timestamp_formatted'] = table_df['timestamp_dt'].dt.strftime('%Y-%m-%d %H:%M:%S')
                    table_df = table_df[['timestamp_formatted', 'status', 'message']]
                    table_df.columns = ['Timestamp', 'Status', 'Message']
                    
                    st.dataframe(
                        table_df,
                        use_container_width=True,
                        hide_index=True,
                        height=400
                    )
                    
                    # Export option
                    csv = table_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download History as CSV",
                        data=csv,
                        file_name=f"{selected_device}_history_{get_local_now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            else:
                st.info("No history available for this device yet.")

# Auto-refresh
if auto_refresh:
    time.sleep(delay)
    st.rerun()