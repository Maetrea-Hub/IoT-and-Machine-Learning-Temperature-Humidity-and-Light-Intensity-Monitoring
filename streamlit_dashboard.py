"""
Streamlit Dashboard for IoT ML Monitoring System
Real-time monitoring of Temperature, Humidity, and Light Intensity
with Machine Learning Classification

Requirements:
"""
pip install streamlit paho-mqtt pandas plotly

import streamlit as st
import paho.mqtt.client as mqtt
import json
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from io import StringIO

# ===== Page Configuration =====
st.set_page_config(
    page_title="IoT ML Monitor Dashboard",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== Custom CSS =====
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stMetric {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 10px 0;
    }
    .status-dingin {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }
    .status-normal {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
    }
    .status-panas {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
    }
    .status-terang {
        background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
    }
    .status-gelap {
        background: linear-gradient(135deg, #434343 0%, #000000 100%);
    }
    </style>
""", unsafe_allow_html=True)

# ===== MQTT Configuration =====
# ===== MQTT Configuration (HiveMQ Cloud) =====
MQTT_BROKER = "c0ba63802d884690a923b132979daad3.s1.eu.hivemq.cloud"  # Ganti dengan host Anda
MQTT_PORT = 8883                           # Port TLS/SSL
MQTT_USERNAME = "esp32_client"             # Username Anda
MQTT_PASSWORD = "KensellMHA245n10"         # Password Anda
MQTT_TOPIC = "iot/ml/monitor/data"
MQTT_CLIENT_ID = "Streamlit_Dashboard_001"

# ===== Initialize Session State =====
if 'data' not in st.session_state:
    st.session_state.data = []
if 'mqtt_connected' not in st.session_state:
    st.session_state.mqtt_connected = False
if 'latest_data' not in st.session_state:
    st.session_state.latest_data = {
        'temperature': 0,
        'humidity': 0,
        'lightIntensity': 0,
        'lightCondition': 'Terang',
        'mlClassification': 'normal',
        'timestamp': datetime.now()
    }

# ===== MQTT Callbacks =====
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        st.session_state.mqtt_connected = True
        client.subscribe(MQTT_TOPIC)
        print(f"Connected to MQTT Broker! Subscribed to {MQTT_TOPIC}")
    else:
        st.session_state.mqtt_connected = False
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        payload['timestamp'] = datetime.now()
        
        # Update latest data
        st.session_state.latest_data = payload
        
        # Append to historical data
        st.session_state.data.append(payload)
        
        # Keep only last 100 readings
        if len(st.session_state.data) > 100:
            st.session_state.data.pop(0)
        
        print(f"Received: {payload}")
    except Exception as e:
        print(f"Error processing message: {e}")

def on_disconnect(client, userdata, flags, rc, properties=None):
    st.session_state.mqtt_connected = False
    print("Disconnected from MQTT Broker")

# ===== Initialize MQTT Client =====
@st.cache_resource
def init_mqtt():
    client = mqtt.Client(
        client_id=MQTT_CLIENT_ID,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    
    # Set username dan password
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    
    # Enable TLS/SSL
    client.tls_set()
    
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        return client
    except Exception as e:
        print(f"MQTT Connection Error: {e}")
        return None

# ===== Main Dashboard =====
def main():
    # Initialize MQTT
    mqtt_client = init_mqtt()
    
    # Header
    st.title("🌡️ IoT ML Monitoring Dashboard")
    st.markdown("Real-time Temperature, Humidity & Light Monitoring with ML Classification")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        st.info(f"**MQTT Broker:** {MQTT_BROKER}")
        st.info(f"**Topic:** {MQTT_TOPIC}")
        
        if st.session_state.mqtt_connected:
            st.success("✅ MQTT Connected")
        else:
            st.error("❌ MQTT Disconnected")
        
        st.markdown("---")
        st.header("📊 Data Statistics")
        if len(st.session_state.data) > 0:
            st.metric("Total Readings", len(st.session_state.data))
        else:
            st.warning("No data received yet")
        
        st.markdown("---")
        auto_refresh = st.checkbox("Auto Refresh", value=True)
        if auto_refresh:
            refresh_interval = st.slider("Refresh Interval (seconds)", 1, 10, 2)
        
        st.markdown("---")
        if st.button("🗑️ Clear Data"):
            st.session_state.data = []
            st.rerun()
    
    # Main Content
    latest = st.session_state.latest_data
    
    # Current Status Cards
    st.subheader("📈 Current Status")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🌡️ Temperature",
            value=f"{latest['temperature']:.1f}°C",
            delta=None
        )
    
    with col2:
        st.metric(
            label="💧 Humidity",
            value=f"{latest['humidity']:.1f}%",
            delta=None
        )
    
    with col3:
        st.metric(
            label="💡 Light Intensity",
            value=f"{latest['lightIntensity']}",
            delta=None
        )
    
    with col4:
        # ML Classification with color coding
        classification = latest['mlClassification']
        if classification == "dingin":
            st.markdown(f"""
                <div class="metric-card status-dingin">
                    <h3>❄️ ML Status</h3>
                    <h2>{classification.upper()}</h2>
                </div>
            """, unsafe_allow_html=True)
        elif classification == "panas":
            st.markdown(f"""
                <div class="metric-card status-panas">
                    <h3>🔥 ML Status</h3>
                    <h2>{classification.upper()}</h2>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="metric-card status-normal">
                    <h3>✅ ML Status</h3>
                    <h2>{classification.upper()}</h2>
                </div>
            """, unsafe_allow_html=True)
    
    # Light Condition
    col5, col6 = st.columns([1, 3])
    with col5:
        light_cond = latest['lightCondition']
        if light_cond == "Gelap":
            st.markdown(f"""
                <div class="metric-card status-gelap">
                    <h3>🌙 Light Condition</h3>
                    <h2>{light_cond.upper()}</h2>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="metric-card status-terang">
                    <h3>☀️ Light Condition</h3>
                    <h2>{light_cond.upper()}</h2>
                </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Historical Data Charts
    if len(st.session_state.data) > 0:
        st.subheader("📊 Historical Data")
        
        df = pd.DataFrame(st.session_state.data)
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Temperature Over Time', 'Humidity Over Time', 
                          'Light Intensity Over Time', 'ML Classification Distribution'),
            specs=[[{"type": "scatter"}, {"type": "scatter"}],
                   [{"type": "scatter"}, {"type": "pie"}]]
        )
        
        # Temperature trace
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['temperature'], 
                      mode='lines+markers', name='Temperature',
                      line=dict(color='#ff6b6b', width=2)),
            row=1, col=1
        )
        
        # Humidity trace
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['humidity'], 
                      mode='lines+markers', name='Humidity',
                      line=dict(color='#4ecdc4', width=2)),
            row=1, col=2
        )
        
        # Light intensity trace
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['lightIntensity'], 
                      mode='lines+markers', name='Light Intensity',
                      line=dict(color='#ffe66d', width=2)),
            row=2, col=1
        )
        
        # ML Classification distribution
        classification_counts = df['mlClassification'].value_counts()
        fig.add_trace(
            go.Pie(labels=classification_counts.index, 
                  values=classification_counts.values,
                  marker=dict(colors=['#4ecdc4', '#95e1d3', '#ff6b6b'])),
            row=2, col=2
        )
        
        # Update layout
        fig.update_xaxes(title_text="Time", row=1, col=1)
        fig.update_yaxes(title_text="Temperature (°C)", row=1, col=1)
        fig.update_xaxes(title_text="Time", row=1, col=2)
        fig.update_yaxes(title_text="Humidity (%)", row=1, col=2)
        fig.update_xaxes(title_text="Time", row=2, col=1)
        fig.update_yaxes(title_text="Light Intensity", row=2, col=1)
        
        fig.update_layout(
            height=700,
            showlegend=True,
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Data Table
        st.subheader("📋 Recent Data Table")
        display_df = df[['timestamp', 'temperature', 'humidity', 
                        'lightIntensity', 'lightCondition', 'mlClassification']].tail(20)
        display_df = display_df.sort_values('timestamp', ascending=False)
        st.dataframe(display_df, use_container_width=True)
        
        # Download CSV
        st.subheader("💾 Download Data")
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"iot_ml_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("⏳ Waiting for data from ESP32...")
        st.info("Make sure your ESP32 is connected and publishing to the MQTT topic.")
    
    # Auto refresh
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()

if __name__ == "__main__":
    main()
