"""
Temperature, Humidity, and Light Intensity Monitoring Dashboard
WORKING VERSION - Real-time data updates with proper queue processing
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
import queue
import threading

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
    .main {
        background-color: #0e1117;
    }
    .title-center {
        text-align: center;
        color: #00d9ff;
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 2rem;
        padding: 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
    }
    .status-box {
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
        margin: 10px 0;
    }
    .status-terang {
        background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
        color: #000;
    }
    .status-gelap {
        background: linear-gradient(135deg, #434343 0%, #000000 100%);
        color: #fff;
    }
    .stMetric {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 10px;
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

# ===== Global Queue (Module-level, thread-safe) =====
GLOBAL_QUEUE = queue.Queue()
MQTT_CONNECTED = False
MQTT_CLIENT_ID = f"Streamlit_Dashboard_{random.randint(1000, 9999)}"

# ===== MQTT Callbacks (Use GLOBAL_QUEUE, NOT session_state) =====
def on_connect(client, userdata, flags, rc, properties=None):
    """Called when connected"""
    global MQTT_CONNECTED
    
    if rc == 0:
        MQTT_CONNECTED = True
        client.subscribe(MQTT_TOPIC, qos=1)
        GLOBAL_QUEUE.put({"_type": "status", "connected": True})
        print(f"✅ Connected to MQTT (Client: {MQTT_CLIENT_ID})")
        print(f"📥 Subscribed to: {MQTT_TOPIC}")
    else:
        MQTT_CONNECTED = False
        GLOBAL_QUEUE.put({"_type": "status", "connected": False})
        errors = {1: "Protocol", 2: "Client ID", 3: "Unavailable", 4: "Bad credentials", 5: "Unauthorized"}
        print(f"❌ Connection failed: {errors.get(rc, f'Error {rc}')}")

def on_message(client, userdata, msg):
    """Called when message received - put in GLOBAL_QUEUE"""
    try:
        payload = json.loads(msg.payload.decode())
        # Add timestamp and put in queue
        GLOBAL_QUEUE.put({"_type": "sensor", "data": payload, "ts": time.time()})
        print(f"📨 Received: T={payload.get('temperature')}°C, H={payload.get('humidity')}%")
    except Exception as e:
        print(f"❌ Parse error: {e}")

def on_disconnect(client, userdata, flags, rc, properties=None):
    """Called when disconnected"""
    global MQTT_CONNECTED
    MQTT_CONNECTED = False
    GLOBAL_QUEUE.put({"_type": "status", "connected": False})
    if rc != 0:
        print(f"⚠️ Unexpected disconnect (rc={rc})")

# ===== MQTT Worker Thread =====
def mqtt_worker():
    """Worker thread that runs MQTT client loop"""
    while True:
        try:
            # Create client
            client = mqtt.Client(
                client_id=MQTT_CLIENT_ID,
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                protocol=mqtt.MQTTv5
            )
            
            # Set callbacks
            client.on_connect = on_connect
            client.on_message = on_message
            client.on_disconnect = on_disconnect
            
            # Set credentials
            client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
            
            # Configure TLS
            cert_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem')
            cert_file.write(ROOT_CA_CERT)
            cert_file.close()
            
            client.tls_set(
                ca_certs=cert_file.name,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLSv1_2
            )
            
            print(f"🔌 Connecting to {MQTT_BROKER}:{MQTT_PORT}")
            
            # Connect and loop forever
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            client.loop_forever()
            
        except Exception as e:
            print(f"❌ MQTT worker error: {e}")
            time.sleep(5)  # Backoff before retry

# ===== Start MQTT Thread Once =====
if "mqtt_thread_started" not in st.session_state:
    st.session_state.mqtt_thread_started = False

if not st.session_state.mqtt_thread_started:
    thread = threading.Thread(target=mqtt_worker, daemon=True, name="mqtt_worker")
    thread.start()
    st.session_state.mqtt_thread_started = True
    print("🚀 MQTT worker thread started")
    time.sleep(0.1)  # Give thread time to start

# ===== Session State Init =====
if 'data' not in st.session_state:
    st.session_state.data = []
if 'latest_data' not in st.session_state:
    st.session_state.latest_data = {
        'temperature': 0.0,
        'humidity': 0.0,
        'lightIntensity': 0,
        'lightCondition': 'Terang',
        'mlClassification': 'normal',
        'timestamp': datetime.now()
    }
if 'mqtt_status' not in st.session_state:
    st.session_state.mqtt_status = False
if 'message_count' not in st.session_state:
    st.session_state.message_count = 0

# ===== Process Queue Function =====
def process_queue():
    """Drain queue and update session_state (safe in main thread)"""
    updated = False
    
    while not GLOBAL_QUEUE.empty():
        try:
            item = GLOBAL_QUEUE.get_nowait()
            item_type = item.get("_type")
            
            if item_type == "status":
                st.session_state.mqtt_status = item.get("connected", False)
                updated = True
                
            elif item_type == "sensor":
                data = item.get("data", {})
                
                # Create data row with timestamp
                row = {
                    'temperature': float(data.get('temperature', 0)),
                    'humidity': float(data.get('humidity', 0)),
                    'lightIntensity': int(data.get('lightIntensity', 0)),
                    'lightCondition': data.get('lightCondition', 'Terang'),
                    'mlClassification': data.get('mlClassification', 'normal'),
                    'timestamp': datetime.fromtimestamp(item.get('ts', time.time()))
                }
                
                # Update latest and append to history
                st.session_state.latest_data = row
                st.session_state.data.append(row)
                st.session_state.message_count += 1
                
                # Keep last 500 readings
                if len(st.session_state.data) > 500:
                    st.session_state.data = st.session_state.data[-500:]
                
                updated = True
                
        except queue.Empty:
            break
        except Exception as e:
            print(f"❌ Queue processing error: {e}")
            break
    
    return updated

# ===== Main Dashboard =====
def main():
    # Process queue FIRST (before rendering UI)
    process_queue()
    
    # Title
    st.markdown("""
        <div class="title-center">
            🌡️ Temperature, Humidity, and Light Intensity Monitoring Dashboard
        </div>
    """, unsafe_allow_html=True)
    
    # Connection Status
    col_status1, col_status2, col_status3 = st.columns(3)
    
    with col_status1:
        if st.session_state.mqtt_status:
            st.success("✅ MQTT Connected")
        else:
            st.error("❌ MQTT Disconnected")
    
    with col_status2:
        st.info(f"📊 Messages: {st.session_state.message_count}")
    
    with col_status3:
        if len(st.session_state.data) > 0:
            last_time = st.session_state.latest_data['timestamp']
            elapsed = (datetime.now() - last_time).seconds
            st.info(f"⏱️ Last: {elapsed}s ago")
        else:
            st.info("⏱️ Waiting...")
    
    latest = st.session_state.latest_data
    
    st.markdown("---")
    
    # ===== Temperature and Humidity Charts =====
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🌡️ Temperature")
        
        if len(st.session_state.data) > 0:
            df = pd.DataFrame(st.session_state.data)
            
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
        
        if len(st.session_state.data) > 0:
            df = pd.DataFrame(st.session_state.data)
            
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
                🌙 Kondisi Sedang: GELAP
                <br>
                <small>Light Intensity: {light_intensity}</small>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div class="status-box status-terang">
                ☀️ Kondisi Sedang: TERANG
                <br>
                <small>Light Intensity: {light_intensity}</small>
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
    
    if len(st.session_state.data) > 0:
        df = pd.DataFrame(st.session_state.data)
        
        # Prepare CSV
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
            full_csv['timestamp'] = full_csv['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
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
            complete_csv['timestamp'] = complete_csv['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
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
        st.markdown("#### 📊 Statistics Summary")
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
        **Ensure ESP32 is:**
        - ✅ Powered on
        - ✅ Connected to WiFi  
        - ✅ Connected to MQTT
        - ✅ Publishing to `iot/ml/monitor/data`
        
        **Check Serial Monitor for:**
        ```
        ✅ Data published to MQTT
        ```
        """)
    
    # Process queue again at end (catch any messages that arrived during render)
    process_queue()
    
    # Auto-refresh every 3 seconds
    time.sleep(3)
    st.rerun()

if __name__ == "__main__":
    main()
