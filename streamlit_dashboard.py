"""
Temperature, Humidity, and Light Intensity Monitoring Dashboard
Working version based on successful app.py pattern
"""

import streamlit as st
import paho.mqtt.client as mqtt
import ssl
import json
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import time
import tempfile
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
    </style>
""", unsafe_allow_html=True)

# ===== MQTT Configuration =====
MQTT_BROKER = "ac2c24cb9a454ce58c90f3f25913b733.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USERNAME = "esp32_client"
MQTT_PASSWORD = "KensellMHA245n10"
MQTT_TOPIC = "iot/ml/monitor/data"
MQTT_CLIENT_ID = "Streamlit_IoT_Dashboard"

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

# ===== Global Queue (Module Level - NOT session_state) =====
GLOBAL_QUEUE = queue.Queue()

# ===== MQTT Callbacks (Use GLOBAL_QUEUE, NOT st.session_state) =====
def on_connect(client, userdata, flags, rc, properties=None):
    """Called when connected to MQTT broker"""
    try:
        client.subscribe(MQTT_TOPIC, qos=1)
    except Exception:
        pass
    # Push connection status to queue
    GLOBAL_QUEUE.put({
        "_type": "status",
        "connected": (rc == 0),
        "ts": time.time()
    })
    
    if rc == 0:
        print(f"✅ Connected to MQTT - Subscribed to {MQTT_TOPIC}")
    else:
        print(f"❌ Connection failed (rc={rc})")

def on_message(client, userdata, msg):
    """Called when message received - put in GLOBAL_QUEUE"""
    payload = msg.payload.decode(errors="ignore")
    try:
        data = json.loads(payload)
    except Exception:
        # Push raw payload if JSON parse fails
        GLOBAL_QUEUE.put({
            "_type": "raw",
            "payload": payload,
            "ts": time.time()
        })
        return
    
    # Push structured sensor message to queue
    GLOBAL_QUEUE.put({
        "_type": "sensor",
        "data": data,
        "ts": time.time(),
        "topic": msg.topic
    })
    
    print(f"📨 Queued: Temp={data.get('temperature')}°C, Hum={data.get('humidity')}%")

# ===== Start MQTT Thread (Worker) =====
def start_mqtt_thread_once():
    """Start MQTT client in background thread"""
    def worker():
        # Write certificate to temp file
        cert_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem')
        cert_file.write(ROOT_CA_CERT)
        cert_file.close()
        
        client = mqtt.Client(
            client_id=MQTT_CLIENT_ID,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            protocol=mqtt.MQTTv5
        )
        client.on_connect = on_connect
        client.on_message = on_message
        
        # Set credentials
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        
        # Configure TLS
        client.tls_set(
            ca_certs=cert_file.name,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLSv1_2
        )
        
        while True:
            try:
                print(f"🔌 Connecting to {MQTT_BROKER}:{MQTT_PORT}")
                client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
                client.loop_forever()
            except Exception as e:
                # Push error to queue
                GLOBAL_QUEUE.put({
                    "_type": "error",
                    "msg": f"MQTT error: {e}",
                    "ts": time.time()
                })
                print(f"❌ MQTT error: {e}")
                time.sleep(5)  # Backoff then retry
    
    if not st.session_state.mqtt_thread_started:
        t = threading.Thread(target=worker, daemon=True, name="mqtt_worker")
        t.start()
        st.session_state.mqtt_thread_started = True
        time.sleep(0.1)  # Give thread time to start

# ===== Session State Init =====
if "msg_queue" not in st.session_state:
    st.session_state.msg_queue = GLOBAL_QUEUE

if "logs" not in st.session_state:
    st.session_state.logs = []

if "last" not in st.session_state:
    st.session_state.last = None

if "last_status" not in st.session_state:
    st.session_state.last_status = False

if "mqtt_thread_started" not in st.session_state:
    st.session_state.mqtt_thread_started = False

# ===== Process Queue (Drain messages) =====
def process_queue():
    """Process all messages in queue and update session_state"""
    updated = False
    q = st.session_state.msg_queue
    
    while not q.empty():
        try:
            item = q.get_nowait()
            ttype = item.get("_type")
            
            if ttype == "status":
                # Connection status
                st.session_state.last_status = item.get("connected", False)
                updated = True
                
            elif ttype == "error":
                # Error message
                print(f"⚠️ {item.get('msg')}")
                updated = True
                
            elif ttype == "raw":
                # Raw payload
                row = {
                    "ts": datetime.fromtimestamp(item.get("ts", time.time())).strftime("%Y-%m-%d %H:%M:%S"),
                    "raw": item.get("payload")
                }
                st.session_state.logs.append(row)
                st.session_state.last = row
                updated = True
                
            elif ttype == "sensor":
                # Sensor data
                d = item.get("data", {})
                
                row = {
                    "ts": datetime.fromtimestamp(item.get("ts", time.time())).strftime("%Y-%m-%d %H:%M:%S"),
                    "temperature": d.get("temperature"),
                    "humidity": d.get("humidity"),
                    "lightIntensity": d.get("lightIntensity"),
                    "lightCondition": d.get("lightCondition"),
                    "mlClassification": d.get("mlClassification")
                }
                
                st.session_state.last = row
                st.session_state.logs.append(row)
                
                # Keep bounded (last 500 entries)
                if len(st.session_state.logs) > 500:
                    st.session_state.logs = st.session_state.logs[-500:]
                
                updated = True
                print(f"✅ Processed: Temp={row['temperature']}°C")
                
        except queue.Empty:
            break
        except Exception as e:
            print(f"❌ Process error: {e}")
            break
    
    return updated

# ===== Main Dashboard =====
def main():
    # Start MQTT thread once
    start_mqtt_thread_once()
    
    # Process incoming messages
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
        if st.session_state.last_status:
            st.success("✅ MQTT Connected")
        else:
            st.error("❌ MQTT Disconnected")
    
    with col_status2:
        st.info(f"📊 Data Points: {len(st.session_state.logs)}")
    
    with col_status3:
        if st.session_state.last:
            st.info(f"⏱️ Last: {st.session_state.last.get('ts', 'N/A')}")
        else:
            st.info("⏱️ Waiting...")
    
    st.markdown("---")
    
    # Get latest data
    if st.session_state.last:
        latest = st.session_state.last
    else:
        latest = {
            'temperature': 0.0,
            'humidity': 0.0,
            'lightIntensity': 0,
            'lightCondition': 'Terang',
            'mlClassification': 'normal'
        }
    
    # ===== Temperature and Humidity Charts =====
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🌡️ Temperature")
        
        if len(st.session_state.logs) > 0:
            df = pd.DataFrame(st.session_state.logs)
            
            # Filter valid temperature data
            df_temp = df[df['temperature'].notna()]
            
            if len(df_temp) > 0:
                fig_temp = go.Figure()
                fig_temp.add_trace(go.Scatter(
                    x=list(range(len(df_temp))),
                    y=df_temp['temperature'],
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
                    xaxis_title="Reading #",
                    yaxis_title="Temperature (°C)",
                    showlegend=False,
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                
                st.plotly_chart(fig_temp, use_container_width=True)
                st.metric("Current", f"{latest.get('temperature', 0):.1f}°C")
            else:
                st.info("⏳ No temperature data yet")
        else:
            st.info("⏳ Waiting for data...")
    
    with col2:
        st.subheader("💧 Humidity")
        
        if len(st.session_state.logs) > 0:
            df = pd.DataFrame(st.session_state.logs)
            
            # Filter valid humidity data
            df_hum = df[df['humidity'].notna()]
            
            if len(df_hum) > 0:
                fig_hum = go.Figure()
                fig_hum.add_trace(go.Scatter(
                    x=list(range(len(df_hum))),
                    y=df_hum['humidity'],
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
                    xaxis_title="Reading #",
                    yaxis_title="Humidity (%)",
                    showlegend=False,
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                
                st.plotly_chart(fig_hum, use_container_width=True)
                st.metric("Current", f"{latest.get('humidity', 0):.1f}%")
            else:
                st.info("⏳ No humidity data yet")
        else:
            st.info("⏳ Waiting for data...")
    
    st.markdown("---")
    
    # ===== Light Intensity =====
    st.subheader("💡 Light Intensity")
    
    light_condition = latest.get('lightCondition', 'Terang')
    light_intensity = latest.get('lightIntensity', 0)
    
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
    
    ml_class = latest.get('mlClassification', 'normal')
    
    col_ml1, col_ml2, col_ml3 = st.columns(3)
    
    with col_ml1:
        if ml_class == "dingin":
            st.info("❄️ **DINGIN**")
        else:
            st.text("❄️ dingin")
    
    with col_ml2:
        if ml_class == "normal":
            st.success("✅ **NORMAL**")
        else:
            st.text("✅ normal")
    
    with col_ml3:
        if ml_class == "panas":
            st.error("🔥 **PANAS**")
        else:
            st.text("🔥 panas")
    
    st.markdown("---")
    
    # ===== Download CSV =====
    st.subheader("💾 Download Data")
    
    if len(st.session_state.logs) > 0:
        df = pd.DataFrame(st.session_state.logs)
        
        # Prepare CSV
        csv_data = df[['ts', 'temperature', 'humidity', 'lightCondition']].copy()
        csv_data.columns = ['timestamp', 'temperature', 'humidity', 'lightCondition']
        csv_string = csv_data.to_csv(index=False)
        
        col_dl1, col_dl2, col_dl3 = st.columns(3)
        
        with col_dl1:
            st.download_button(
                label="📥 Essential Data",
                data=csv_string,
                file_name=f"iot_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col_dl2:
            full_csv = df[['ts', 'temperature', 'humidity', 'lightCondition', 'mlClassification']].copy()
            full_csv.columns = ['timestamp', 'temperature', 'humidity', 'lightCondition', 'mlClassification']
            full_csv_string = full_csv.to_csv(index=False)
            
            st.download_button(
                label="📥 With ML Data",
                data=full_csv_string,
                file_name=f"iot_ml_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col_dl3:
            complete_csv = df.to_csv(index=False)
            
            st.download_button(
                label="📥 Complete Data",
                data=complete_csv,
                file_name=f"iot_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        # Preview
        st.markdown("#### 📋 Recent Data (Last 10)")
        preview = csv_data.tail(10).iloc[::-1]  # Reverse to show latest first
        st.dataframe(preview, use_container_width=True, hide_index=True)
        
        # Statistics
        st.markdown("#### 📊 Statistics")
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        
        with col_s1:
            avg_temp = df['temperature'].dropna().mean()
            st.metric("Avg Temp", f"{avg_temp:.1f}°C" if not np.isnan(avg_temp) else "N/A")
        
        with col_s2:
            avg_hum = df['humidity'].dropna().mean()
            st.metric("Avg Humidity", f"{avg_hum:.1f}%" if not np.isnan(avg_hum) else "N/A")
        
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
        - ✅ Publishing to `iot/ml/monitor/data`
        """)
    
    # Process queue again at end of render
    process_queue()
    
    # Auto-refresh every 2 seconds
    time.sleep(2)
    st.rerun()

if __name__ == "__main__":
    main()
