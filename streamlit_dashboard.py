"""
Streamlit Dashboard for IoT ML Monitoring System - FIXED VERSION
Real-time monitoring with HiveMQ Cloud support
Enhanced with additional charts and CSV download features
"""

import streamlit as st
import paho.mqtt.client as mqtt
import ssl
import json
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import threading

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
    .connection-status {
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
        font-weight: bold;
    }
    .status-connected {
        background-color: #28a745;
        color: white;
    }
    .status-disconnected {
        background-color: #dc3545;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# ===== MQTT Configuration =====
MQTT_BROKER = "ac2c24cb9a454ce58c90f3f25913b733.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USERNAME = "esp32_client"
MQTT_PASSWORD = "KensellMHA245n10"
MQTT_TOPIC = "iot/ml/monitor/#"
MQTT_CLIENT_ID = "Streamlit_Dashboard_001"

# ===== Initialize Session State =====
if 'data' not in st.session_state:
    st.session_state.data = []
if 'mqtt_connected' not in st.session_state:
    st.session_state.mqtt_connected = False
if 'connection_status' not in st.session_state:
    st.session_state.connection_status = "Connecting..."
if 'latest_data' not in st.session_state:
    st.session_state.latest_data = {
        'temperature': 0,
        'humidity': 0,
        'lightIntensity': 0,
        'lightCondition': 'Terang',
        'mlClassification': 'normal',
        'timestamp': datetime.now()
    }
if 'message_count' not in st.session_state:
    st.session_state.message_count = 0
if 'last_message_time' not in st.session_state:
    st.session_state.last_message_time = None

# ===== MQTT Callbacks =====
def on_connect(client, userdata, flags, rc, properties=None):
    """Callback when connected to MQTT broker"""
    print(f"\n{'='*60}")
    print(f"MQTT Connection Callback - RC: {rc}")
    print(f"{'='*60}")
    
    if rc == 0:
        st.session_state.mqtt_connected = True
        st.session_state.connection_status = "Connected"
        result, mid = client.subscribe(MQTT_TOPIC, qos=1)
        print(f"✅ Connected successfully!")
        print(f"📥 Subscribed to: {MQTT_TOPIC}")
        print(f"   Result: {result}, Message ID: {mid}")
    else:
        st.session_state.mqtt_connected = False
        error_messages = {
            1: "Incorrect protocol version",
            2: "Invalid client identifier",
            3: "Server unavailable",
            4: "Bad username or password",
            5: "Not authorized"
        }
        status = error_messages.get(rc, f"Unknown error ({rc})")
        st.session_state.connection_status = f"Failed: {status}"
        print(f"❌ Connection failed: {status}")

def on_subscribe(client, userdata, mid, granted_qos, properties=None):
    """Callback when subscribed to topic"""
    print(f"✅ Subscription confirmed - Message ID: {mid}, QoS: {granted_qos}")

def on_message(client, userdata, msg):
    """Callback when message received"""
    try:
        payload = json.loads(msg.payload.decode())
        payload['timestamp'] = datetime.now()
        
        # Update latest data
        st.session_state.latest_data = payload
        st.session_state.message_count += 1
        st.session_state.last_message_time = datetime.now()
        
        # Append to historical data
        st.session_state.data.append(payload)
        
        # Keep only last 200 readings
        if len(st.session_state.data) > 200:
            st.session_state.data.pop(0)
        
        print(f"📨 Message #{st.session_state.message_count}: Temp={payload.get('temperature')}°C")
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
    except Exception as e:
        print(f"❌ Error processing message: {e}")

def on_disconnect(client, userdata, flags, rc, properties=None):
    """Callback when disconnected"""
    st.session_state.mqtt_connected = False
    if rc != 0:
        st.session_state.connection_status = f"Disconnected (code: {rc})"
        print(f"⚠️ Unexpected disconnection - RC: {rc}")
    else:
        st.session_state.connection_status = "Disconnected"
        print(f"👋 Disconnected from broker")

def on_log(client, userdata, level, buf):
    """Debug logging"""
    print(f"[MQTT LOG] {buf}")

# ===== Initialize MQTT Client =====
@st.cache_resource
def init_mqtt():
    """Initialize MQTT client with proper TLS configuration"""
    print("\n" + "="*60)
    print("🔌 Initializing MQTT Client")
    print("="*60)
    print(f"Broker: {MQTT_BROKER}")
    print(f"Port: {MQTT_PORT}")
    print(f"Username: {MQTT_USERNAME}")
    print(f"Topic: {MQTT_TOPIC}")
    print("="*60)
    
    try:
        # Create client
        client = mqtt.Client(
            client_id=MQTT_CLIENT_ID,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            protocol=mqtt.MQTTv5
        )
        
        # Set callbacks
        client.on_connect = on_connect
        client.on_subscribe = on_subscribe
        client.on_message = on_message
        client.on_disconnect = on_disconnect
        # client.on_log = on_log  # Uncomment for debug
        
        # Set username and password
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        
        # Configure TLS/SSL
        client.tls_set(
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLSv1_2
        )
        
        # Disable hostname verification (for cloud deployments)
        client.tls_insecure_set(False)
        
        print("✅ MQTT client configured")
        print("🔌 Attempting connection...")
        
        # Connect to broker
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        # Start network loop in background thread
        client.loop_start()
        
        print("✅ Connection initiated")
        
        return client
        
    except Exception as e:
        print(f"❌ Error initializing MQTT: {type(e).__name__}")
        print(f"   {str(e)}")
        st.session_state.connection_status = f"Error: {str(e)}"
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
        st.header("⚙️ Connection Settings")
        
        # Connection status with color coding
        if st.session_state.mqtt_connected:
            st.markdown("""
                <div class="connection-status status-connected">
                    ✅ MQTT Connected
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="connection-status status-disconnected">
                    ❌ {st.session_state.connection_status}
                </div>
            """, unsafe_allow_html=True)
        
        st.info(f"**Broker:** {MQTT_BROKER}")
        st.info(f"**Topic:** {MQTT_TOPIC}")
        
        st.markdown("---")
        st.header("📊 Statistics")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Messages", st.session_state.message_count)
        with col2:
            st.metric("Stored", len(st.session_state.data))
        
        if st.session_state.last_message_time:
            elapsed = (datetime.now() - st.session_state.last_message_time).seconds
            st.caption(f"Last message: {elapsed}s ago")
        
        st.markdown("---")
        st.header("🔄 Refresh Settings")
        auto_refresh = st.checkbox("Auto Refresh", value=True)
        if auto_refresh:
            refresh_interval = st.slider("Interval (seconds)", 1, 10, 2)
        
        st.markdown("---")
        
        # Actions
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Reconnect", use_container_width=True):
                st.cache_resource.clear()
                st.rerun()
        
        with col2:
            if st.button("🗑️ Clear Data", use_container_width=True):
                st.session_state.data = []
                st.session_state.message_count = 0
                st.rerun()
        
        # Troubleshooting
        with st.expander("🔧 Troubleshooting"):
            st.markdown("""
            **If not connecting:**
            1. Check HiveMQ cluster is running
            2. Verify credentials in console
            3. Check topic permissions: `#`
            4. ESP32 must be publishing data
            5. Try reconnect button
            """)
    
    # Main Content
    latest = st.session_state.latest_data
    
    # Current Status Cards
    st.subheader("📈 Current Status")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🌡️ Temperature",
            value=f"{latest['temperature']:.1f}°C"
        )
    
    with col2:
        st.metric(
            label="💧 Humidity",
            value=f"{latest['humidity']:.1f}%"
        )
    
    with col3:
        st.metric(
            label="💡 Light Intensity",
            value=f"{latest['lightIntensity']}"
        )
    
    with col4:
        classification = latest['mlClassification']
        if classification == "dingin":
            st.markdown("""
                <div class="metric-card status-dingin">
                    <h3>❄️ ML Status</h3>
                    <h2>DINGIN</h2>
                </div>
            """, unsafe_allow_html=True)
        elif classification == "panas":
            st.markdown("""
                <div class="metric-card status-panas">
                    <h3>🔥 ML Status</h3>
                    <h2>PANAS</h2>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div class="metric-card status-normal">
                    <h3>✅ ML Status</h3>
                    <h2>NORMAL</h2>
                </div>
            """, unsafe_allow_html=True)
    
    # Light Condition
    col5, col6 = st.columns([1, 3])
    with col5:
        light_cond = latest['lightCondition']
        if light_cond == "Gelap":
            st.markdown("""
                <div class="metric-card status-gelap">
                    <h3>🌙 Light</h3>
                    <h2>GELAP</h2>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div class="metric-card status-terang">
                    <h3>☀️ Light</h3>
                    <h2>TERANG</h2>
                </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Historical Data Charts
    if len(st.session_state.data) > 0:
        st.subheader("📊 Historical Data Analysis")
        
        df = pd.DataFrame(st.session_state.data)
        
        # === Chart 1: Temperature & Humidity Over Time ===
        st.markdown("#### 🌡️ Temperature & Humidity Trends")
        
        fig1 = make_subplots(
            rows=1, cols=2,
            subplot_titles=('Temperature Over Time', 'Humidity Over Time')
        )
        
        fig1.add_trace(
            go.Scatter(
                x=df['timestamp'], 
                y=df['temperature'],
                mode='lines+markers',
                name='Temperature',
                line=dict(color='#ff6b6b', width=2),
                marker=dict(size=4)
            ),
            row=1, col=1
        )
        
        fig1.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['humidity'],
                mode='lines+markers',
                name='Humidity',
                line=dict(color='#4ecdc4', width=2),
                marker=dict(size=4)
            ),
            row=1, col=2
        )
        
        fig1.update_xaxes(title_text="Time", row=1, col=1)
        fig1.update_yaxes(title_text="Temperature (°C)", row=1, col=1)
        fig1.update_xaxes(title_text="Time", row=1, col=2)
        fig1.update_yaxes(title_text="Humidity (%)", row=1, col=2)
        
        fig1.update_layout(
            height=400,
            showlegend=True,
            template="plotly_dark",
            hovermode='x unified'
        )
        
        st.plotly_chart(fig1, use_container_width=True)
        
        # === Chart 2: Light Intensity & Classification ===
        st.markdown("#### 💡 Light Intensity & ML Classification")
        
        fig2 = make_subplots(
            rows=1, cols=2,
            subplot_titles=('Light Intensity Over Time', 'ML Classification Distribution'),
            specs=[[{"type": "scatter"}, {"type": "pie"}]]
        )
        
        fig2.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['lightIntensity'],
                mode='lines+markers',
                name='Light Intensity',
                line=dict(color='#ffe66d', width=2),
                marker=dict(size=4),
                fill='tozeroy',
                fillcolor='rgba(255, 230, 109, 0.1)'
            ),
            row=1, col=1
        )
        
        # ML Classification pie chart
        classification_counts = df['mlClassification'].value_counts()
        colors = {
            'dingin': '#4facfe',
            'normal': '#43e97b',
            'panas': '#ff6b6b'
        }
        pie_colors = [colors.get(label, '#95e1d3') for label in classification_counts.index]
        
        fig2.add_trace(
            go.Pie(
                labels=classification_counts.index,
                values=classification_counts.values,
                marker=dict(colors=pie_colors),
                textinfo='label+percent',
                hoverinfo='label+value+percent'
            ),
            row=1, col=2
        )
        
        fig2.update_xaxes(title_text="Time", row=1, col=1)
        fig2.update_yaxes(title_text="Light Intensity", row=1, col=1)
        
        fig2.update_layout(
            height=400,
            showlegend=True,
            template="plotly_dark"
        )
        
        st.plotly_chart(fig2, use_container_width=True)
        
        # === Chart 3: Light Condition Distribution ===
        st.markdown("#### 🌓 Light Condition Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            light_counts = df['lightCondition'].value_counts()
            
            fig3 = go.Figure(data=[
                go.Pie(
                    labels=light_counts.index,
                    values=light_counts.values,
                    marker=dict(colors=['#434343', '#ffecd2']),
                    hole=0.4,
                    textinfo='label+percent'
                )
            ])
            
            fig3.update_layout(
                title="Light Condition Distribution",
                template="plotly_dark",
                height=350
            )
            
            st.plotly_chart(fig3, use_container_width=True)
        
        with col2:
            # Statistics summary
            st.markdown("##### 📈 Summary Statistics")
            
            stats_data = {
                'Metric': ['Temperature', 'Humidity', 'Light Intensity'],
                'Min': [
                    f"{df['temperature'].min():.1f}°C",
                    f"{df['humidity'].min():.1f}%",
                    f"{df['lightIntensity'].min()}"
                ],
                'Max': [
                    f"{df['temperature'].max():.1f}°C",
                    f"{df['humidity'].max():.1f}%",
                    f"{df['lightIntensity'].max()}"
                ],
                'Average': [
                    f"{df['temperature'].mean():.1f}°C",
                    f"{df['humidity'].mean():.1f}%",
                    f"{df['lightIntensity'].mean():.0f}"
                ]
            }
            
            stats_df = pd.DataFrame(stats_data)
            st.dataframe(stats_df, use_container_width=True, hide_index=True)
            
            st.markdown("##### 🎯 ML Classification Count")
            for label, count in classification_counts.items():
                percentage = (count / len(df)) * 100
                st.metric(label.capitalize(), f"{count} ({percentage:.1f}%)")
        
        st.markdown("---")
        
        # === Data Table ===
        st.subheader("📋 Recent Data Table")
        
        display_df = df[[
            'timestamp', 'temperature', 'humidity',
            'lightIntensity', 'lightCondition', 'mlClassification'
        ]].tail(30).copy()
        
        display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        display_df = display_df.sort_values('timestamp', ascending=False)
        display_df = display_df.reset_index(drop=True)
        
        st.dataframe(display_df, use_container_width=True, height=400)
        
        # === Download Section ===
        st.markdown("---")
        st.subheader("💾 Download Data")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Full dataset
            csv_full = df.to_csv(index=False)
            st.download_button(
                label="📥 Download All Data (CSV)",
                data=csv_full,
                file_name=f"iot_ml_full_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            # Essential columns only
            csv_essential = df[[
                'timestamp', 'temperature', 'humidity', 'lightCondition'
            ]].to_csv(index=False)
            
            st.download_button(
                label="📥 Download Essential Data (CSV)",
                data=csv_essential,
                file_name=f"iot_ml_essential_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col3:
            # ML classification data
            csv_ml = df[[
                'timestamp', 'temperature', 'humidity', 'mlClassification'
            ]].to_csv(index=False)
            
            st.download_button(
                label="📥 Download ML Data (CSV)",
                data=csv_ml,
                file_name=f"iot_ml_classification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
    else:
        st.info("⏳ Waiting for data from ESP32...")
        st.markdown("""
        ### 📡 Connection Checklist:
        
        1. ✅ ESP32 is powered on and connected to WiFi
        2. ✅ ESP32 connected to HiveMQ Cloud (check Serial Monitor)
        3. ✅ ESP32 publishing to topic: `iot/ml/monitor/data`
        4. ✅ Dashboard subscribed to same topic
        5. ✅ HiveMQ cluster status is **Running**
        
        **Tip:** Check Serial Monitor on ESP32 for "Data published to MQTT" message.
        """)
    
    # Auto refresh
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()

if __name__ == "__main__":
    main()
