"""
Temperature, Humidity, and Light Intensity Monitoring Dashboard
"""

import streamlit as st
import paho.mqtt.client as mqtt
import ssl
import json
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import time
import tempfile
import random

# ===== Page Configuration =====
st.set_page_config(
    page_title="IoT Monitoring Dashboard",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ===== Custom CSS =====
st.markdown("""
    <style>
    body, .main {
        background-color: #10182b !important;
    }
    .title-center {
        text-align: center;
        color: #4fc3f7;
        font-family: 'Segoe UI', 'Roboto', 'Arial', sans-serif;
        font-size: 2.8rem;
        font-weight: 700;
        margin-bottom: 2.2rem;
        padding: 1.2rem;
        background: linear-gradient(135deg, #232b43 0%, #0f2027 100%);
        border-radius: 18px;
        box-shadow: 0 4px 32px 0 rgba(80,180,255,0.10);
        letter-spacing: 1px;
    }
    .status-box {
        padding: 22px 10px 18px 10px;
        border-radius: 14px;
        text-align: center;
        font-size: 1.45rem;
        font-weight: 600;
        margin: 12px 0;
        box-shadow: 0 2px 16px 0 rgba(80,180,255,0.08);
        transition: box-shadow 0.2s;
    }
    .status-box:hover {
        box-shadow: 0 4px 32px 0 rgba(80,180,255,0.18);
    }
    .status-terang {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: #e3f2fd;
        border: 1.5px solid #4fc3f7;
    }
    .status-gelap {
        background: linear-gradient(135deg, #232b43 0%, #0f2027 100%);
        color: #b3e5fc;
        border: 1.5px solid #1976d2;
    }
    .stMetric {
        background: #162447;
        padding: 18px 10px;
        border-radius: 12px;
        color: #b3e5fc !important;
        font-weight: 600;
        border: 1.5px solid #283e6d;
        box-shadow: 0 2px 12px 0 rgba(80,180,255,0.07);
    }
    .stButton>button {
        background: linear-gradient(90deg, #1976d2 0%, #4fc3f7 100%);
        color: #fff;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        font-size: 1.1rem;
        padding: 0.6rem 1.2rem;
        box-shadow: 0 2px 8px 0 rgba(80,180,255,0.10);
        transition: background 0.2s, box-shadow 0.2s;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #1565c0 0%, #29b6f6 100%);
        box-shadow: 0 4px 16px 0 rgba(80,180,255,0.18);
    }
    .stDataFrame {
        background: #10182b !important;
        color: #b3e5fc !important;
        border-radius: 10px;
        font-size: 1.05rem;
    }
    .stSubheader, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
        color: #4fc3f7 !important;
        font-family: 'Segoe UI', 'Roboto', 'Arial', sans-serif;
    }
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# ===== MQTT Configuration =====
MQTT_BROKER = "ac2c24cb9a454ce58c90f3f25913b733.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USERNAME = "esp32_client"
MQTT_PASSWORD = "KensellMHA245n10"
MQTT_TOPIC = "iot/ml/monitor/data"

# ISRG Root X1 Certificate
ROOT_CA_CERT = """-----BEGIN CERTIFICATE-----
MIIFazCCA1OgAwIBAgIRAIIQz7DSQONZRGPgu2OCiwAwDQYJKoZIhvcNAQELBQAw
TzELMAkGA1UEBhMCVVMxKTAnBgNVBAoTIEludGVybmV0IFNlY3VyaXR5IFJlc2Vh
cmNoIEdyb3VwMRUwEwYDVQQDEwxJU1JHIFJvb3QgWDEwHhcNMTUwNjA0MTEwNDM4
WhcNMzUwNjA0MTEwNDM4WjBPMQswCQYDVQQGEwJVUzEpMCcGA1UEChMgSW50ZXJu
ZXQgU2VjdXJpdHkgUmVzZWFyY2ggR3JvdXAxFTATBgNVBAMTDElTUkcgUm9vdCBY
MTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAK3oJHP0FDfzm54rVygc
h77ct984kIxuPOZXoHj3dcKi/vVqbvYATyjb3miGbESTtrFj/RQSa78f0uoxmyF+
0TM8ukj13Xnfs7j/EvEhmkvBioZxaUpmZmyPfjxwv60pIgbz5MDmgK7iS4+3mX6U
A5/TR5d8mUgjU+g4rk8Kb4Mu0UlXjIB0ttov0DiNewNwIRt18jA8+o+u3dpjq+sW
T8KOEUt+zwvo/7V3LvSye0rgTBIlDHCNAymg4VMk7BPZ7hm/ELNKjD+Jo2FR3qyH
B5T0Y3HsLuJvW5iB4YlcNHlsdu87kGJ55tukmi8mxdAQ4Q7e2RCOFvu396j3x+UC
B5iPNgiV5+I3lg02dZ77DnKxHZu8A/lJBdiB3QW0KtZB6awBdpUKD9jf1b0SHzUv
KBds0pjBqAlkd25HN7rOrFleaJ1/ctaJxQZBKT5ZPt0m9STJEadao0xAH0ahmbWn
OlFuhjuefXKnEgV4We0+UXgVCwOPjdAvBbI+e0ocS3MFEvzG6uBQE3xDk3SzynTn
jh8BCNAw1FtxNrQHusEwMFxIt4I7mKZ9YIqioymCzLq9gwQbooMDQaHWBfEbwrbw
qHyGO0aoSCqI3Haadr8faqU9GY/rOPNk3sgrDQoo//fb4hVC1CLQJ13hef4Y53CI
rU7m2Ys6xt0nUW7/vGT1M0NPAgMBAAGjQjBAMA4GA1UdDwEB/wQEAwIBBjAPBgNV
HRMBAf8EBTADAQH/MB0GA1UdDgQWBBR5tFnme7bl5AFzgAiIyBpY9umbbjANBgkq
hkiG9w0BAQsFAAOCAgEAVR9YqbyyqFDQDLHYGmkgJykIrGF1XIpu+ILlaS/V9lZL
ubhzEFnTIZd+50xx+7LSYK05qAvqFyFWhfFQDlnrzuBZ6brJFe+GnY+EgPbk6ZGQ
3BebYhtF8GaV0nxvwuo77x/Py9auJ/GpsMiu/X1+mvoiBOv/2X/qkSsisRcOj/KK
NFtY2PwByVS5uCbMiogziUwthDyC3+6WVwW6LLv3xLfHTjuCvjHIInNzktHCgKQ5
ORAzI4JMPJ+GslWYHb4phowim57iaztXOoJwTdwJx4nLCgdNbOhdjsnvzqvHu7Ur
TkXWStAmzOVyyghqpZXjFaH3pO3JLF+l+/+sKAIuvtd7u+Nxe5AW0wdeRlN8NwdC
jNPElpzVmbUq4JUagEiuTDkHzsxHpFKVK7q4+63SM1N95R1NbdWhscdCb+ZAJzVc
oyi3B43njTOQ5yOf+1CceWxG1bQVs5ZufpsMljq4Ui0/1lvh+wjChP4kqKOJ2qxq
4RgqsahDYVvTH9w7jXbyLeiNdd8XM2w9U/t7y0Ff/9yi0GE44Za4rF2LN9d11TPA
mRGunUHBcnWEvgJBQl9nJEiU0Zsnvgc/ubhPgXRR4Xq37Z0j4r7g1SgEEzwxA57d
emyPxgcYxn/eR44/KJ4EBs+lVDR3veyJm+kXQ99b21/+jh5Xos1AnX5iItreGCc=
-----END CERTIFICATE-----"""

# ===== Persistent Storage =====
@st.cache_resource
def get_data_store():
    """Persisted storage for data (kept across reruns)."""
    return {
        "data": [],
        "latest_data": {
            'temperature': 29.0,
            'humidity': 60.0,
            'lightIntensity': 800,
            'lightCondition': 'Terang',
            'mlClassification': 'normal',
            'timestamp': datetime.now()
        }
    }

# ===== Initialize Simulator (replaces real MQTT init) =====
@st.cache_resource
def init_simulator():
    """Return a dummy client-like object that reports connected always."""
    class DummyClient:
        def is_connected(self):
            return True
    return DummyClient()

# ===== Main Dashboard =====
def main():
    # Initialize simulator (always connected)
    mqtt_client = init_simulator()
    
    # Get persisted storage (not session_state)
    store = get_data_store()

    # Ambil data sebelumnya untuk perubahan perlahan
    prev = store['latest_data']
    prev_temp = prev.get('temperature', 29.0)
    prev_hum = prev.get('humidity', 60.0)

    # Simulasi perubahan perlahan
    temp_min, temp_max = 28.7, 31.9
    hum_min, hum_max = 55.0, 85.0

    # Perubahan kecil per refresh
    temp_delta = random.uniform(-0.07, 0.09)
    hum_delta = random.uniform(-0.15, 0.18)

    # Update temperature
    new_temp = prev_temp + temp_delta
    new_temp = max(temp_min, min(temp_max, new_temp))
    new_temp = round(new_temp, 1)

    # Update humidity
    new_hum = prev_hum + hum_delta
    new_hum = max(hum_min, min(hum_max, new_hum))
    new_hum = round(new_hum, 1)

    # Kondisi terang/gelap berganti setiap 5 detik
    now = datetime.now()
    terang = (now.second // 5) % 2 == 0
    light_condition = 'Terang' if terang else 'Gelap'
    light_intensity = random.randint(700, 1023) if terang else random.randint(0, 300)

    # ML classification
    if new_temp < 29.5:
        ml_class = 'dingin'
    elif new_temp > 31.0:
        ml_class = 'panas'
    else:
        ml_class = 'normal'

    payload = {
        'temperature': new_temp,
        'humidity': new_hum,
        'lightIntensity': light_intensity,
        'lightCondition': light_condition,
        'mlClassification': ml_class,
        'timestamp': now
    }

    store['latest_data'] = payload
    store['data'].append(payload)
    if len(store['data']) > 300:
        store['data'].pop(0)
    
    # (Optional) debug
    print(f"🔁 payload: {payload}")
    
    # Title
    st.markdown("""
        <div class="title-center">
            🌡️ Temperature, Humidity, and Light Intensity Monitoring Dashboard
        </div>
    """, unsafe_allow_html=True)
    
    # Connection Status
    col_status1, col_status2, col_status3 = st.columns(3)

    with col_status1:
        if mqtt_client and getattr(mqtt_client, "is_connected", lambda: False)():
            st.success("✅ MQTT Connected")
        else:
            st.error("❌ MQTT Disconnected")
    
    with col_status2:
        st.info(f"📊 Data Points: {len(store['data'])}")
    
    with col_status3:
        if len(store['data']) > 0:
            last_time = store['latest_data']['timestamp']
            elapsed = (datetime.now() - last_time).seconds
            st.info(f"⏱️ Last update: {elapsed}s ago")
        else:
            st.info("⏱️ Waiting for data...")
    
    latest = store['latest_data']
    
    st.markdown("---")
    
    # ===== Temperature and Humidity Charts =====
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🌡️ Temperature")
        
        if len(store['data']) > 0:
            df = pd.DataFrame(store['data'])
            
            fig_temp = go.Figure()
            fig_temp.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['temperature'],
                mode='lines+markers',
                name='Temperature',
                line=dict(color='#ff6b6b', width=3),
                marker=dict(size=6),
                fill='tozeroy',
                fillcolor='rgba(255, 107, 107, 0.2)'
            ))
            
            fig_temp.update_layout(
                height=400,
                template='plotly_dark',
                xaxis_title="Time",
                yaxis_title="Temperature (°C)",
                hovermode='x unified',
                showlegend=False,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            
            st.plotly_chart(fig_temp, use_container_width=True)
            st.metric("Current Temperature", f"{latest['temperature']:.1f}°C")
        else:
            st.info("⏳ Waiting for temperature data...")
            st.metric("Current Temperature", "0.0°C")
    
    with col2:
        st.subheader("💧 Humidity")
        
        if len(store['data']) > 0:
            df = pd.DataFrame(store['data'])
            
            fig_hum = go.Figure()
            fig_hum.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['humidity'],
                mode='lines+markers',
                name='Humidity',
                line=dict(color='#4ecdc4', width=3),
                marker=dict(size=6),
                fill='tozeroy',
                fillcolor='rgba(78, 205, 196, 0.2)'
            ))
            
            fig_hum.update_layout(
                height=400,
                template='plotly_dark',
                xaxis_title="Time",
                yaxis_title="Humidity (%)",
                hovermode='x unified',
                showlegend=False,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            
            st.plotly_chart(fig_hum, use_container_width=True)
            st.metric("Current Humidity", f"{latest['humidity']:.1f}%")
        else:
            st.info("⏳ Waiting for humidity data...")
            st.metric("Current Humidity", "0.0%")
    
    st.markdown("---")
    
    # ===== Light Intensity =====
    st.subheader("💡 Light Intensity")
    
    light_condition = latest['lightCondition']
    light_intensity = latest['lightIntensity']
    
    if light_condition == "Gelap":
        st.markdown(f"""
            <div class="status-box status-gelap">
                🌙 Kondisi: <span style="font-weight:700;">GELAP</span>
                <br>
                <small>Light Intensity: <b>{light_intensity}</b></small>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div class="status-box status-terang">
                ☀️ Kondisi: <span style="font-weight:700;">TERANG</span>
                <br>
                <small>Light Intensity: <b>{light_intensity}</b></small>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ===== ML Classification =====
    st.subheader("🤖 Machine Learning Classification")
    
    ml_class = latest['mlClassification']
    
    col_ml1, col_ml2, col_ml3 = st.columns(3)
    
    with col_ml1:
        if ml_class == "dingin":
            st.info("❄️ **Status: DINGIN**")
        else:
            st.text("❄️ dingin")
    
    with col_ml2:
        if ml_class == "normal":
            st.success("✅ **Status: NORMAL**")
        else:
            st.text("✅ normal")
    
    with col_ml3:
        if ml_class == "panas":
            st.error("🔥 **Status: PANAS**")
        else:
            st.text("🔥 panas")
    
    st.markdown("---")
    
    # ===== Download CSV =====
    st.subheader("💾 Download Data")
    
    if len(store['data']) > 0:
        df = pd.DataFrame(store['data'])
        
        # Prepare CSV (ensure timestamp dtype)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        csv_data = df[['timestamp', 'temperature', 'humidity', 'lightCondition']].copy()
        csv_data['timestamp'] = csv_data['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        csv_string = csv_data.to_csv(index=False)
        
        col_dl1, col_dl2, col_dl3 = st.columns(3)
        
        with col_dl1:
            st.download_button(
                label="📥 Download Essential Data",
                data=csv_string,
                file_name=f"iot_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col_dl2:
            full_csv = df[['timestamp', 'temperature', 'humidity', 'lightCondition', 'mlClassification']].copy()
            full_csv['timestamp'] = pd.to_datetime(full_csv['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            full_csv_string = full_csv.to_csv(index=False)
            
            st.download_button(
                label="📥 Download with ML Data",
                data=full_csv_string,
                file_name=f"iot_ml_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col_dl3:
            complete_csv = df.copy()
            complete_csv['timestamp'] = pd.to_datetime(complete_csv['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            complete_csv_string = complete_csv.to_csv(index=False)
            
            st.download_button(
                label="📥 Download Complete",
                data=complete_csv_string,
                file_name=f"iot_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        # Preview
        st.markdown("#### 📋 Data Preview (Last 10)")
        preview = csv_data.tail(10).sort_values('timestamp', ascending=False)
        st.dataframe(preview, use_container_width=True, hide_index=True)
        
        # Statistics
        st.markdown("#### 📊 Statistics")
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        
        with col_s1:
            st.metric("Avg Temp", f"{df['temperature'].mean():.1f}°C")
        with col_s2:
            st.metric("Avg Humidity", f"{df['humidity'].mean():.1f}%")
        with col_s3:
            terang = (df['lightCondition'] == 'Terang').sum()
            st.metric("Terang", terang)
        with col_s4:
            gelap = (df['lightCondition'] == 'Gelap').sum()
            st.metric("Gelap", gelap)
    else:
        st.warning("⚠️ No data available")
        st.info("""
        Data is generated locally each refresh.
        """)
    
    # Auto-refresh every 5 seconds (simulate realtime)
    time.sleep(5)
    st.rerun()

if __name__ == "__main__":
    main()
