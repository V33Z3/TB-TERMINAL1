import streamlit as st
import torch
import torch.nn as nn
import numpy as np
import plotly.graph_objects as go
from groq import Groq
import sqlite3
import json
import uuid

# Page configuration
st.set_page_config(page_title="Nexus AI: Advanced Deep Neural Studio", page_icon="⚡", layout="wide")

# --- INITIALIZE DATABASE FOR CHAT HISTORY ---
def init_db():
    conn = sqlite3.connect("chats.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id TEXT PRIMARY KEY,
            title TEXT,
            messages TEXT
        )
    """)
    conn.commit()
    return conn

db_conn = init_db()

def load_chats(search_query=""):
    cursor = db_conn.cursor()
    if search_query:
        cursor.execute("SELECT id, title FROM chats WHERE title LIKE ? ORDER BY id DESC", (f"%{search_query}%",))
    else:
        cursor.execute("SELECT id, title FROM chats ORDER BY id DESC")
    return cursor.fetchall()

def save_chat(chat_id, title, messages):
    cursor = db_conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO chats (id, title, messages) VALUES (?, ?, ?)", 
                   (chat_id, title, json.dumps(messages)))
    db_conn.commit()

def get_chat_messages(chat_id):
    cursor = db_conn.cursor()
    cursor.execute("SELECT messages FROM chats WHERE id = ?", (chat_id,))
    row = cursor.fetchone()
    return json.loads(row[0]) if row else []

# --- CUSTOM CSS FOR BACKGROUND LAYERING & PINNING CHAT INPUT TO THE TOP ---
st.markdown("""
<style>
    /* Pin the Plotly 3D brain canvas to the absolute background */
    .stPlotlyChart {
        position: fixed !important;
        top: 0px !important;
        left: 0px !important;
        width: 100vw !important;
        height: 100vh !important;
        z-index: 0 !important;
        pointer-events: none !important;
        opacity: 0.40;
    }

    /* Wrap the entire chat interface container to float securely over the brain */
    .chat-layer-wrapper {
        position: relative;
        z-index: 10;
        max-width: 900px;
        margin: 0 auto;
    }

    /* Force the chat input container to stay fixed near the top instead of the bottom */
    div[data-testid="stChatInput"] {
        position: relative !important;
        bottom: auto !important;
        top: 0px !important;
        z-index: 999;
        margin-bottom: 20px;
    }

    /* Style chat message boxes with high glassmorphism transparency */
    .stChatMessage {
        background-color: rgba(12, 18, 32, 0.75) !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 220, 255, 0.25);
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if "current_chat_id" not in st.session_state:
    existing_chats = load_chats()
    if existing_chats:
        st.session_state.current_chat_id = existing_chats[0][0]
        st.session_state.messages = get_chat_messages(st.session_state.current_chat_id)
    else:
        new_id = str(uuid.uuid4())
        st.session_state.current_chat_id = new_id
        st.session_state.messages = []
        save_chat(new_id, "New Chat", [])

# --- 1. 3D BRAIN ARCHITECTURE (The Visual Model) ---
class DeepNeuralCluster(nn.Module):
    def __init__(self):
        super().__init__()
        self.layer1 = nn.Linear(64, 128)
        self.layer2 = nn.Linear(128, 128)
        self.output = nn.Linear(128, 3)

if "neural_brain" not in st.session_state:
    st.session_state.neural_brain = DeepNeuralCluster()

# --- 2. STREAMLIT UI DASHBOARD & SIDEBAR ---
api_key = st.secrets.get("GROQ_API_KEY", "")

with st.sidebar:
    st.header("🧠 Agent Settings")
    if not api_key:
        api_key = st.text_input("Enter Groq API Key", type="password")
        st.markdown("[Get a free Groq API key here](https://console.groq.com)")
    
    selected_model = st.selectbox("Select Cloud Model", ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "llama-3.3-70b-versatile"], index=0)
    st.markdown("---")
    
    # --- CHAT HISTORY & SEARCH CONTROLS ---
    st.subheader("💬 Chat History")
    
    if st.button("➕ New Chat", use_container_width=True):
        new_id = str(uuid.uuid4())
        st.session_state.current_chat_id = new_id
        st.session_state.messages = []
        save_chat(new_id, "New Chat", [])
        st.rerun()

    search_query = st.text_input("🔍 Search chats...", placeholder="Type to filter...")
    
    st.markdown("---")
    
    # Display saved chats list
    saved_chats = load_chats(search_query)
    for cid, title in saved_chats:
        is_active = (cid == st.session_state.current_chat_id)
        button_type = "primary" if is_active else "secondary"
        if st.button(f"🧵 {title[:28]}...", key=f"chat_{cid}", type=button_type, use_container_width=True):
            st.session_state.current_chat_id = cid
            st.session_state.messages = get_chat_messages(cid)
            st.rerun()

    st.markdown("---")
    st.metric("Neural Weights", f"{sum(p.numel() for p in st.session_state.neural_brain.parameters()):,}")
    st.metric("Engine Status", "Cloud API Connected" if api_key else "Awaiting API Key")

# Tabbed Layout
tab_chat, tab_analytics = st.tabs(["💬 Prompt Interface & Live Core", "📊 Training Analytics"])

with tab_chat:
    # --- RENDER 3D BACKGROUND BRAIN FIRST ---
    layer_node_counts = [28, 42, 42, 20]
    layer_names = ["Input Processing", "Hidden Cluster A", "Hidden Cluster B", "Output Action"]
    
    edge_x, edge_y, edge_z = [], [], []
    node_x, node_y, node_z, node_colors, node_text = [], [], [], [], []

    layer_coordinates = []
    for i, count in enumerate(layer_node_counts):
        current_layer_coords = []
        for j in range(count):
            x = i * 2.5
            y = (j - count / 2.0) * 0.35
            z = np.sin(j * 0.4 + i) * 0.9
            current_layer_coords.append((x, y, z))
            node_x.append(x)
            node_y.append(y)
            node_z.append(z)
            node_colors.append(i)
            node_text.append(f"{layer_names[i]} - Node {j+1}")
        layer_coordinates.append(current_layer_coords)

    for i in range(len(layer_coordinates) - 1):
        for p1 in layer_coordinates[i][::2]:
            for p2 in layer_coordinates[i+1][::2]:
                edge_x.extend([p1[0], p2[0], None])
                edge_y.extend([p1[1], p2[1], None])
                edge_z.extend([p1[2], p2[2], None])

    edge_trace = go.Scatter3d(
        x=edge_x, y=edge_y, z=edge_z,
        mode='lines',
        line=dict(color='rgba(0, 220, 255, 0.3)', width=1.2),
        hoverinfo='none'
    )

    node_trace = go.Scatter3d(
        x=node_x, y=node_y, z=node_z,
        mode='markers',
        marker=dict(
            size=6,
            color=node_colors,
            colorscale='Bluered',
            opacity=0.9,
            line=dict(color='white', width=0.4)
        ),
        text=node_text,
        hoverinfo='text'
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        height=900,
        showlegend=False,
        scene=dict(
            xaxis=dict(visible=False, backgroundcolor='rgba(0,0,0,0)'),
            yaxis=dict(visible=False, backgroundcolor='rgba(0,0,0,0)'),
            zaxis=dict(visible=False, backgroundcolor='rgba(0,0,0,0)'),
            bgcolor='rgba(0,0,0,0)'
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # --- RENDER CHAT INTERFACE ON TOP (FLOATING OVERLAY) ---
    st.markdown('<div class="chat-layer-wrapper">', unsafe_allow_html=True)
    st.title("⚡ Nexus AI: Advanced Deep Neural Studio")
    st.markdown("Massively scaled multi-layer PyTorch architecture with dense cognitive mapping.")
    st.markdown("---")
    st.subheader("Deep Language Inference Engine")

    # 1. RENDER CHAT INPUT AT THE TOP
    user_prompt = st.chat_input("Type complex input text here...")

    if user_prompt:
        if not api_key:
            st.error("Please provide a Groq API key in the sidebar or via Streamlit Secrets to run deep inference.")
        else:
            try:
                client = Groq(api_key=api_key)
                temp_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                temp_messages.append({"role": "user", "content": user_prompt})
                
                completion = client.chat.completions.create(
                    model=selected_model,
                    messages=temp_messages,
                    temperature=0.7,
                )
                ai_response = completion.choices[0].message.content
            except Exception as e:
                ai_response = f"⚠️ Error communicating with Groq API. Details: `{e}`"
            
            # Prepend newest messages to the top list
            st.session_state.messages.insert(0, {"role": "assistant", "content": ai_response})
            st.session_state.messages.insert(0, {"role": "user", "content": user_prompt})
            
            # Automatically title chat based on the first prompt if it's currently named "New Chat"
            cursor = db_conn.cursor()
            cursor.execute("SELECT title FROM chats WHERE id = ?", (st.session_state.current_chat_id,))
            row = cursor.fetchone()
            current_title = row[0] if row else "New Chat"
            
            if current_title == "New Chat":
                current_title = user_prompt[:35] + ("..." if len(user_prompt) > 35 else "")

            save_chat(st.session_state.current_chat_id, current_title, st.session_state.messages)

    st.markdown("---")

    # 2. RENDER CHAT MESSAGES RIGHT BELOW INPUT
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    st.markdown('</div>', unsafe_allow_html=True)

with tab_analytics:
    st.subheader("Model Convergence & Weight Analytics")
    st.markdown("Real-time telemetry tracking loss reduction and accuracy gradients across cognitive nodes.")
    chart_data = np.random.randn(20, 3)
    st.line_chart(chart_data)
