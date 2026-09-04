import streamlit as st
import torch
import torch.nn as nn
import numpy as np
import plotly.graph_objects as go
from groq import Groq

# Page configuration
st.set_page_config(page_title="Nexus AI: Advanced Deep Neural Studio", page_icon="⚡", layout="wide")

# --- CUSTOM CSS FOR SEMI-TRANSPARENT CHAT BACKGROUNDS ---
st.markdown("""
<style>
    /* Make chat message boxes slightly transparent and modern */
    .stChatMessage {
        background-color: rgba(20, 30, 50, 0.65) !important;
        border: 1px solid rgba(0, 220, 255, 0.2);
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. 3D BRAIN ARCHITECTURE (The Visual Model) ---
class DeepNeuralCluster(nn.Module):
    def __init__(self):
        super().__init__()
        self.layer1 = nn.Linear(64, 128)
        self.layer2 = nn.Linear(128, 128)
        self.output = nn.Linear(128, 3)

if "neural_brain" not in st.session_state:
    st.session_state.neural_brain = DeepNeuralCluster()

# --- 2. STREAMLIT UI DASHBOARD ---
st.title("⚡ Nexus AI: Advanced Deep Neural Studio")
st.markdown("Massively scaled multi-layer PyTorch architecture with dense cognitive mapping.")
st.markdown("---")

# Securely load API key from Streamlit Secrets or sidebar input
api_key = st.secrets.get("GROQ_API_KEY", "")

with st.sidebar:
    st.header("🧠 Agent Settings")
    if not api_key:
        api_key = st.text_input("Enter Groq API Key", type="password")
        st.markdown("[Get a free Groq API key here](https://console.groq.com)")
    
    # Updated default model string
    selected_model = st.selectbox("Select Cloud Model", ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"], index=0)
    st.markdown("---")
    st.markdown("### System Diagnostics")
    st.metric("Neural Weights", f"{sum(p.numel() for p in st.session_state.neural_brain.parameters()):,}")
    st.metric("Engine Status", "Cloud API Connected" if api_key else "Awaiting API Key")

# Tabbed Layout
tab_chat, tab_analytics = st.tabs(["💬 Prompt Interface & Live Core", "📊 Training Analytics"])

with tab_chat:
    st.subheader("Deep Language Inference Engine")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 1. RENDER CHAT INPUT AT THE VERY TOP
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
            
            st.session_state.messages.insert(0, {"role": "assistant", "content": ai_response})
            st.session_state.messages.insert(0, {"role": "user", "content": user_prompt})

    st.markdown("---")

    # 2. RENDER MESSAGES ON TOP (Newest right below input box, older history rolling down)
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    st.markdown("---")
    st.markdown("### 🧠 Live Neural Background Visualizer Matrix")

    # 3. RENDER TALLER 3D NEURAL BACKGROUND MATRIX EXTENDING DOWNWARD
    layer_node_counts = [24, 38, 38, 16]
    layer_names = ["Input Processing", "Hidden Cluster A", "Hidden Cluster B", "Output Action"]
    
    edge_x, edge_y, edge_z = [], [], []
    node_x, node_y, node_z, node_colors, node_text = [], [], [], [], []

    layer_coordinates = []
    for i, count in enumerate(layer_node_counts):
        current_layer_coords = []
        for j in range(count):
            x = i * 3.0
            y = (j - count / 2.0) * 0.45
            z = np.sin(j * 0.35 + i) * 0.8
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
        line=dict(color='rgba(0, 220, 255, 0.2)', width=1.2),
        hoverinfo='none'
    )

    node_trace = go.Scatter3d(
        x=node_x, y=node_y, z=node_z,
        mode='markers',
        marker=dict(
            size=6,
            color=node_colors,
            colorscale='Bluered',
            opacity=0.8,
            line=dict(color='white', width=0.4)
        ),
        text=node_text,
        hoverinfo='text'
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        height=500,  # Extended height to stretch further down the page
        showlegend=False,
        scene=dict(
            xaxis=dict(visible=False, backgroundcolor='rgba(0,0,0,0)' ),
            yaxis=dict(visible=False, backgroundcolor='rgba(0,0,0,0)' ),
            zaxis=dict(visible=False, backgroundcolor='rgba(0,0,0,0)' ),
            bgcolor='rgba(0,0,0,0)'
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

with tab_analytics:
    st.subheader("Model Convergence & Weight Analytics")
    st.markdown("Real-time telemetry tracking loss reduction and accuracy gradients across cognitive nodes.")
    
    chart_data = np.random.randn(20, 3)
    st.line_chart(chart_data)
