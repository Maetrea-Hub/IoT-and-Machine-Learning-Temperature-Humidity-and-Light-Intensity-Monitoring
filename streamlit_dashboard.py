"""
Streamlit MQTT Realtime Dashboard
Displays Temperature, Humidity, and Light Intensity from topic: iot/ml/monitor/data

How to use:
1. Install dependencies:
   pip install streamlit paho-mqtt
2. Fill in your HiveMQ Cloud credentials below or set environment variables.
3. Run:
   streamlit run streamlit_mqtt_dashboard.py

Assumptions:
- MQTT payload is JSON, e.g. {"temperature":25.3, "humidity":60.1, "light":320, "timestamp":"2025-12-08T10:00:00Z"}
- If payload is plain CSV or three values, the code will attempt to parse robustly.

This single-file app starts an MQTT client in a background thread and pushes incoming sensor values
into Streamlit's session_state for real-time display and simple charts.

Update: Added support for custom TLS authentication (CA cert and optional client cert/key).
"""

import streamlit as st
import paho.mqtt.client as mqtt
import threading
import time
import json
from collections import deque
from queue import Queue, Empty
import os
import ssl

MQTT_BROKER = os.environ.get("HIVEMQ_HOST", "ac2c24cb9a454ce58c90f3f25913b733.s1.eu.hivemq.cloud")
MQTT_PORT = int(os.environ.get("HIVEMQ_PORT", "8883"))  # default secure MQTT port
MQTT_USERNAME = os.environ.get("HIVEMQ_USER", "streamlit_client")
MQTT_PASSWORD = os.environ.get("HIVEMQ_PASS", "KensellMHA245n10")
MQTT_TOPIC = os.environ.get("MQTT_TOPIC", "iot/ml/monitor/data")
USE_TLS = os.environ.get("USE_TLS", "1") not in ("0", "false", "False")

# TLS-specific environment variables (optional)
# Path to CA certificate file (PEM). If not provided, system CA store will be used via client.tls_set()
TLS_CA_CERT = os.environ.get("HIVEMQ_CA_CERT", "")
# Optional client certificate and key for mutual TLS
TLS_CLIENT_CERT = os.environ.get("HIVEMQ_CLIENT_CERT", "")
TLS_CLIENT_KEY = os.environ.get("HIVEMQ_CLIENT_KEY", "")
# Whether to disable hostname/certificate verification (not recommended in production)
TLS_INSECURE = os.environ.get("HIVEMQ_TLS_INSECURE", "0") in ("1", "true", "True")
# TLS version to use. Default to TLSv1.2
TLS_VERSION = ssl.PROTOCOL_TLSv1_2
# ---------------------------------------------------------------------------

# Shared queue for incoming messages from MQTT thread
incoming_q = Queue()

# MQTT callbacks

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(MQTT_TOPIC)
        print(f"Connected and subscribed to {MQTT_TOPIC}")
    else:
        print(f"Failed to connect, rc={rc}")


def on_message(client, userdata, msg):
    payload = msg.payload.decode(errors='ignore')
    # Push raw payload and topic to queue for Streamlit to consume
    incoming_q.put((time.time(), payload))


# Start MQTT client in background
def start_mqtt():
    client = mqtt.Client()

    # Set username/password if provided
    if MQTT_USERNAME and MQTT_USERNAME != "YOUR_USERNAME":
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    # Configure TLS if requested
    if USE_TLS:
        try:
            # If CA cert path is provided, pass it; else allow paho to use system defaults by calling tls_set() with no args
            if TLS_CA_CERT:
                # If client cert/key provided, include them (mutual TLS)
                if TLS_CLIENT_CERT and TLS_CLIENT_KEY:
                    client.tls_set(ca_certs=TLS_CA_CERT,
                                   certfile=TLS_CLIENT_CERT,
                                   keyfile=TLS_CLIENT_KEY,
                                   tls_version=TLS_VERSION)
                else:
                    client.tls_set(ca_certs=TLS_CA_CERT, tls_version=TLS_VERSION)
            else:
                # Use system CA store / default settings
                client.tls_set(tls_version=TLS_VERSION)

            # Optionally skip hostname / cert verification (insecure)
            if TLS_INSECURE:
                client.tls_insecure_set(True)

        except Exception as e:
            print(f"TLS configuration error: {e}")
            # proceed without TLS if configuration fails (will likely fail to connect)

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    except Exception as e:
        print(f"MQTT connect error: {e}")
        return

    # Blocking loop will run in its own thread
    client.loop_forever()


# Helper to parse payload into dict with keys temperature, humidity, light, timestamp
def parse_payload(payload):
    # Try JSON first
    try:
        data = json.loads(payload)
        # Normalize keys
        result = {}
        if isinstance(data, dict):
            # accept multiple possible key names
            for k, v in data.items():
                lk = k.lower()
                if 'temp' in lk:
                    result['temperature'] = float(v)
                elif 'hum' in lk:
                    result['humidity'] = float(v)
                elif 'light' in lk or 'lux' in lk:
                    result['light'] = float(v)
                elif 'time' in lk or 'timestamp' in lk:
                    result['timestamp'] = str(v)
        return result
    except Exception:
        pass

    # Fallback: try comma/space-separated values (safe version)
    try:
        cleaned = payload.replace('\n', '').replace('\r', '')
        parts = [p.strip() for p in cleaned.split(',') if p.strip()]
        if len(parts) >= 3:
            return {
                'temperature': float(parts[0]),
                'humidity': float(parts[1]),
                'light': float(parts[2]),
                'timestamp': parts[3] if len(parts) > 3 else None
            }
    except Exception:
        pass

    # If all fails, return raw
    return {'raw': payload}


# Initialize session state
if 'history_len' not in st.session_state:
    st.session_state.history_len = 200

if 'temperature' not in st.session_state:
    st.session_state.temperature = deque(maxlen=st.session_state.history_len)
if 'humidity' not in st.session_state:
    st.session_state.humidity = deque(maxlen=st.session_state.history_len)
if 'light' not in st.session_state:
    st.session_state.light = deque(maxlen=st.session_state.history_len)
if 'timestamps' not in st.session_state:
    st.session_state.timestamps = deque(maxlen=st.session_state.history_len)
if 'last_raw' not in st.session_state:
    st.session_state.last_raw = ''
if 'connected' not in st.session_state:
    st.session_state.connected = False

# Start MQTT thread once
if 'mqtt_thread' not in st.session_state:
    t = threading.Thread(target=start_mqtt, daemon=True)
    t.start()
    st.session_state.mqtt_thread = t

# UI layout
st.set_page_config(page_title="IoT Realtime Dashboard", layout="wide")
st.title("Realtime IoT Dashboard — Temperature / Humidity / Light")

col1, col2, col3 = st.columns(3)
with col1:
    temp_metric = st.metric("Temperature (°C)", value="—")
with col2:
    hum_metric = st.metric("Humidity (%)", value="—")
with col3:
    light_metric = st.metric("Light (lux)", value="—")

# Place for charts
chart_col1, chart_col2 = st.columns([2,1])
with chart_col1:
    st.subheader("Trends")
    st.line_chart({
        'Temperature (°C)': list(st.session_state.temperature),
        'Humidity (%)': list(st.session_state.humidity)
    })
with chart_col2:
    st.subheader("Light Intensity")
    st.line_chart({'Light (lux)': list(st.session_state.light)})

st.subheader("Raw / Recent Message")
st.text_area("Last message (raw)", value=st.session_state.last_raw, height=120)

# Process incoming messages (non-blocking)
processed = 0
while True:
    try:
        ts, payload = incoming_q.get(block=False)
    except Empty:
        break
    processed += 1
    parsed = parse_payload(payload)
    st.session_state.last_raw = payload
    # Update session state if parsed values exist
    if 'temperature' in parsed:
        st.session_state.temperature.append(parsed['temperature'])
        st.session_state.timestamps.append(parsed.get('timestamp', ts))
    if 'humidity' in parsed:
        st.session_state.humidity.append(parsed['humidity'])
    if 'light' in parsed:
        st.session_state.light.append(parsed['light'])

# Update metric displays with latest values
if len(st.session_state.temperature) > 0:
    st.metric("Temperature (°C)", f"{st.session_state.temperature[-1]:.2f}")
if len(st.session_state.humidity) > 0:
    st.metric("Humidity (%)", f"{st.session_state.humidity[-1]:.2f}")
if len(st.session_state.light) > 0:
    st.metric("Light (lux)", f"{st.session_state.light[-1]:.2f}")

# Footer: connection info and tips
st.markdown("---")
st.write("Broker:", MQTT_BROKER, "; Topic:", MQTT_TOPIC)
st.info("TLS config:
- Set HIVEMQ_CA_CERT to path of CA PEM file to verify broker certificate (optional).
- For mutual TLS set HIVEMQ_CLIENT_CERT and HIVEMQ_CLIENT_KEY.
- To disable cert verification (insecure) set HIVEMQ_TLS_INSECURE=1.
Set these env vars before running the app. Example:
HIVEMQ_HOST=your-host hiveMQ, HIVEMQ_CA_CERT=/path/ca.pem streamlit run streamlit_mqtt_dashboard.py")

# Auto-refresh small amount so UI updates frequently (adjust as needed)
# Realtime dashboard update loop
import time
placeholder = st.empty()

while True:
    with placeholder.container():
        # Update latest metrics safely
        if len(st.session_state.temperature) > 0:
            st.metric("Temperature (°C)", f"{st.session_state.temperature[-1]:.2f}")
        if len(st.session_state.humidity) > 0:
            st.metric("Humidity (%)", f"{st.session_state.humidity[-1]:.2f}")
        if len(st.session_state.light) > 0:
            st.metric("Light (lux)", f"{st.session_state.light[-1]:.2f}")
    time.sleep(1)
