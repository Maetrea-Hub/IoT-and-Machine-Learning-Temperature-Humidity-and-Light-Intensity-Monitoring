# streamlit_dashboard.py (stable for Streamlit Cloud)
import streamlit as st
import paho.mqtt.client as mqtt
import ssl
import json
import pandas as pd
from datetime import datetime, timezone, timedelta
import plotly.graph_objects as go
import threading
import time
import tempfile
import random
import queue

# ---------------------------
# Config (edit as needed)
# ---------------------------
MQTT_BROKER = "ac2c24cb9a454ce58c90f3f25913b733.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USERNAME = "esp32_client"
MQTT_PASSWORD = "KensellMHA245n10"
MQTT_TOPIC = "iot/ml/monitor/data"
CLIENT_ID = f"Streamlit_Dashboard_{random.randint(1000,9999)}"

# TLS root cert (optional if broker uses public CA; provided here for HiveMQ Cloud)
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

# timezone helper
TZ = timezone(timedelta(hours=7))

# ---------------------------
# Global queue & flags
# ---------------------------
GLOBAL_MQ = queue.Queue()
mqtt_thread_started_flag = "_mqtt_thread_started"

# ---------------------------
# Streamlit setup & session_state init (must be before starting worker)
# ---------------------------
st.set_page_config(page_title="IoT Monitoring Dashboard", page_icon="🌡️", layout="wide")
st.markdown("<h2>Temperature, Humidity, and Light Intensity Monitoring</h2>", unsafe_allow_html=True)

# session state initial values (do this before worker starts)
if "data" not in st.session_state:
    st.session_state.data = []
if "latest_data" not in st.session_state:
    st.session_state.latest_data = {
        "temperature": 0.0, "humidity": 0.0, "lightIntensity": 0, "lightCondition": "Terang",
        "mlClassification": "normal", "timestamp": datetime.now(tz=TZ)
    }
if "last_status" not in st.session_state:
    st.session_state.last_status = False
if mqtt_thread_started_flag not in st.session_state:
    st.session_state[mqtt_thread_started_flag] = False

# ---------------------------
# MQTT callbacks (must NOT touch st.session_state here)
# ---------------------------
def _on_connect(client, userdata, flags, rc, properties=None):
    try:
        client.subscribe(MQTT_TOPIC, qos=1)
    except Exception:
        pass
    # push connection status into queue
    GLOBAL_MQ.put({"_type": "status", "connected": (rc == 0), "ts": time.time()})

def _on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode(errors="ignore")
        data = json.loads(payload)
        # attach timestamp
        data["timestamp"] = datetime.now(tz=TZ)
        GLOBAL_MQ.put({"_type": "sensor", "data": data, "ts": time.time(), "topic": msg.topic})
        print(f"📨 Received: T={data.get('temperature')}°C, H={data.get('humidity')}%")
    except Exception as e:
        # if not JSON, push raw
        GLOBAL_MQ.put({"_type": "raw", "payload": payload, "ts": time.time()})
        print(f"❌ MQTT on_message parse error: {e}")

def _on_disconnect(client, userdata, rc, properties=None):
    GLOBAL_MQ.put({"_type": "status", "connected": False, "ts": time.time()})
    if rc != 0:
        print(f"⚠️ Unexpected disconnect (rc={rc})")

# ---------------------------
# MQTT worker (runs in daemon thread exactly once)
# ---------------------------
def mqtt_worker():
    # create client with optional websocket transport
    transport = "websockets" if USE_WEBSOCKETS else "tcp"
    client = mqtt.Client(client_id=CLIENT_ID, transport=transport, protocol=mqtt.MQTTv5)

    client.on_connect = _on_connect
    client.on_message = _on_message
    client.on_disconnect = _on_disconnect

    # credentials
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    # TLS (if using TLS)
    try:
        cert_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem')
        cert_file.write(ROOT_CA_CERT)
        cert_file.close()
        client.tls_set(ca_certs=cert_file.name, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
    except Exception as e:
        print(f"⚠️ TLS setup warning: {e}")

    # connect loop with simple backoff
    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            client.loop_forever()  # blocks until disconnect or error
        except Exception as e:
            GLOBAL_MQ.put({"_type": "error", "msg": f"MQTT worker error: {e}", "ts": time.time()})
            time.sleep(5)

def start_mqtt_thread_once():
    if not st.session_state.get(mqtt_thread_started_flag, False):
        t = threading.Thread(target=mqtt_worker, daemon=True, name="mqtt_worker")
        t.start()
        st.session_state[mqtt_thread_started_flag] = True
        time.sleep(0.05)

# ---------------------------
# Queue processing (drain GLOBAL_MQ into st.session_state safely)
# ---------------------------
def process_queue_once():
    updated = False
    q = GLOBAL_MQ
    while not q.empty():
        item = q.get()
        ttype = item.get("_type")
        if ttype == "status":
            st.session_state.last_status = item.get("connected", False)
            updated = True
        elif ttype == "error":
            # log or display once
            st.error(item.get("msg"))
            updated = True
        elif ttype == "raw":
            row = {"timestamp": datetime.now(tz=TZ), "raw": item.get("payload")}
            st.session_state.data.append(row)
            st.session_state.latest_data = row
            updated = True
        elif ttype == "sensor":
            d = item.get("data", {})
            # normalize keys used in your dashboard
            row = {
                "timestamp": d.get("timestamp", datetime.now(tz=TZ)),
                "temperature": float(d.get("temperature", 0.0)),
                "humidity": float(d.get("humidity", 0.0)),
                "lightIntensity": int(d.get("lightIntensity", 0)),
                "lightCondition": d.get("lightCondition", "Terang"),
                "mlClassification": d.get("mlClassification", "normal")
            }
            st.session_state.latest_data = row
            st.session_state.data.append(row)
            # bound the stored data
            if len(st.session_state.data) > 1000:
                st.session_state.data = st.session_state.data[-1000:]
            updated = True
    return updated

# ---------------------------
# Start the MQTT thread AFTER session_state has been initialized
# ---------------------------
start_mqtt_thread_once()

# ---------------------------
# UI: process queue, then render
# ---------------------------
_ = process_queue_once()

# Optional auto-refresh: use streamlit_autorefresh if installed, otherwise rely on manual refresh
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=3000, key="autorefresh")  # every 3s
except Exception:
    pass

# Header & status
col1, col2, col3 = st.columns(3)
with col1:
    st.write("Broker:", f"{MQTT_BROKER}:{MQTT_PORT} (ws)" if USE_WEBSOCKETS else "")
    st.metric("MQTT Connected", "Yes" if st.session_state.last_status else "No")
with col2:
    st.metric("Data Points", len(st.session_state.data))
with col3:
    if st.session_state.data:
        last_ts = st.session_state.latest_data.get("timestamp", datetime.now(tz=TZ))
        elapsed = int((datetime.now(tz=TZ) - last_ts).total_seconds())
        st.metric("Last update", f"{elapsed}s ago")
    else:
        st.info("Waiting for data...")

st.markdown("---")

# Charts
left, right = st.columns(2)
latest = st.session_state.latest_data

with left:
    st.subheader("Temperature")
    if st.session_state.data:
        df = pd.DataFrame(st.session_state.data)
        fig_temp = go.Figure()
        fig_temp.add_trace(go.Scatter(x=df['timestamp'], y=df['temperature'], mode='lines+markers', name='Temperature'))
        fig_temp.update_layout(height=350, template='plotly_dark')
        st.plotly_chart(fig_temp, use_container_width=True)
        st.metric("Current Temperature", f"{latest['temperature']:.1f}°C")
    else:
        st.info("Waiting for temperature data...")
        st.metric("Current Temperature", "0.0°C")

with right:
    st.subheader("Humidity")
    if st.session_state.data:
        df = pd.DataFrame(st.session_state.data)
        fig_hum = go.Figure()
        fig_hum.add_trace(go.Scatter(x=df['timestamp'], y=df['humidity'], mode='lines+markers', name='Humidity'))
        fig_hum.update_layout(height=350, template='plotly_dark')
        st.plotly_chart(fig_hum, use_container_width=True)
        st.metric("Current Humidity", f"{latest['humidity']:.1f}%")
    else:
        st.info("Waiting for humidity data...")
        st.metric("Current Humidity", "0.0%")

st.markdown("---")
st.subheader("Light")
if latest:
    if latest.get("lightCondition", "Terang") == "Gelap":
        st.write("Kondisi: GELAP")
    else:
        st.write("Kondisi: TERANG")
    st.write("Intensity:", latest.get("lightIntensity", 0))

st.markdown("---")
st.subheader("Download data")
if st.session_state.data:
    df_dl = pd.DataFrame(st.session_state.data)
    df_dl['timestamp'] = pd.to_datetime(df_dl['timestamp']).dt.strftime("%Y-%m-%d %H:%M:%S")
    csv = df_dl.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv, file_name=f"iot_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
else:
    st.info("No data to download")

# drain queue again at end of render to pick up any messages arrived during render
process_queue_once()
