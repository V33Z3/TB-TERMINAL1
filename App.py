import streamlit as st
import torch
import torch.nn as nn
import numpy as np
import plotly.graph_objects as go
import ollama

# Page configuration
st.set_page_config(page_title="Nexus AI: Local Agent Studio", page_icon="🧠", layout="wide")

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
st.title("⚡ Nexus AI: Agent & Neural Core")
st.markdown("A dual-engine setup: An interactive 3D neural map paired with a local LLM agent capable of chatting, coding, and reasoning.")
st.markdown("---")

# Sidebar Configuration
with st.sidebar:
    st.header("🧠 Agent Settings")
    selected_model = st.selectbox("Select Local Model", ["llama3", "deepseek-coder", "mistral"], index=0)
    st.markdown("---")
    st.markdown("### System Diagnostics")
    st.metric("Neural Weights", f"{sum(p.numel() for p in st.session_state.neural_brain.parameters()):,}")
    st.metric("Engine Status", "Ollama Bridge Active")

# Tabbed Layout
tab_chat, tab_brain = st.tabs(["💬 Agent Chat & Code Studio", "🧠 AI's 3D Brain (Visualizer)"])

with tab_chat:
    st.subheader("Conversational Agent & Code Generator")
    st.markdown("Talk to your AI, ask it to look up information, or have it write and explain code blocks.")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Handle user prompt input
    if user_prompt := st.chat_input("Ask your agent to write code, solve a problem, or chat..."):
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("Thinking...")
            
            try:
                # Call local Ollama model
                response = ollama.chat(
                    model=selected_model,
                    messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                )
                ai_response = response['message']['content']
            except Exception as e:
                ai_response = f"⚠️ Error connecting to Ollama. Make sure Ollama is running on your machine. Details: `{e}`"
            
            message_placeholder.markdown(ai_response)
            st.session_state.messages.append({"role": "assistant", "content": ai_response})

with tab_brain:
    st.subheader("Interactive 3D Neural Architecture Matrix")
    st.markdown("This 3D web models the structural layers powering the interface framework.")

    layer_node_counts = [24, 40, 40, 16]
    layer_names = ["Input Processing", "Hidden Cluster A", "Hidden Cluster B", "Output Action"]
    
    edge_x, edge_y, edge_z = [], [], []
    node_x, node_y, node_z, node_colors, node_text = [], [], [], [], []

    layer_coordinates = []
    for i, count in enumerate(layer_node_counts):
        current_layer_coords = []
        for j in range(count):
            x = i * 3.0
            y = (j - count / 2.0) * 0.4
            z = np.sin(j * 0.4 + i) * 0.7
            
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
        line=dict(color='rgba(0, 220, 255, 0.25)', width=1.5),
        hoverinfo='none'
    )

    node_trace = go.Scatter3d(
        x=node_x, y=node_y, z=node_z,
        mode='markers',
        marker=dict(
            size=7,
            color=node_colors,
            colorscale='Bluered',
            opacity=0.9,
            line=dict(color='white', width=0.5)
        ),
        text=node_text,
        hoverinfo='text'
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title="Live Neural Network Topology",
        showlegend=False,
        scene=dict(
            xaxis=dict(title='Depth', backgroundcolor='rgba(10, 15, 30, 1)', gridcolor='rgba(40,40,40,0.5)' ),
            yaxis=dict(title='Spread Y', backgroundcolor='rgba(10, 15, 30, 1)', gridcolor='rgba(40,40,40,0.5)' ),
            zaxis=dict(title='Elevation Z', backgroundcolor='rgba(10, 15, 30, 1)', gridcolor='rgba(40,40,40,0.5)' ),
            bgcolor='rgba(10, 15, 30, 1)'
        ),
        margin=dict(l=0, r=0, b=0, t=30),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    st.plotly_chart(fig, use_container_width=True)
