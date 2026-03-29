import streamlit as st
import ollama
import random
import time
import os
import base64
from vision_server import get_gesture # Importujemy z serwera MCP

# --- KONFIGURACJA ARCHITEKTURY MCP ---
# Host: Streamlit (Zarządza logiką i interfejsem)
# Server: vision_server.py (Dostarcza narzędzia wizyjne)
st.set_page_config(page_title="Sith Arena Final", layout="wide")

def set_bg(file):
    """Wstrzyknięcie tła z efektem przejścia (Transition)."""
    if os.path.exists(file):
        with open(file, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()
        st.markdown(f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background-image: url("data:image/jpeg;base64,{b64}");
            background-size: cover; 
            background-position: center;
            transition: background-image 0.8s ease-in-out; /* Płynne przenikanie tła */
        }}
        .main {{ background: rgba(0,0,0,0.4); }}
        .sith-bubble {{
            background: #000; border: 2px solid #f00; border-radius: 12px;
            padding: 10px; color: #f44; text-align: center; font-weight: bold;
            box-shadow: 0 0 15px rgba(255, 0, 0, 0.5); font-family: 'Courier New';
        }}
        .hud-card {{
            background: rgba(0, 15, 25, 0.95); border: 1px solid cyan;
            padding: 15px; border-radius: 10px; margin-top: 50px; color: cyan;
            font-family: 'Courier New', monospace; box-shadow: 0 0 15px cyan;
        }}
        .mcp-log {{
            font-size: 0.7rem; color: #00ff00; font-family: 'Courier New';
            background: rgba(0,0,0,0.8); padding: 5px; border-radius: 5px;
        }}
        </style>
        """, unsafe_allow_html=True)

# Inicjalizacja stanów (Zarządzanie sesją inżynierską)
if "state" not in st.session_state:
    st.session_state.state = {"p": 0, "s": 0, "msg": "", "res": "", "a": "---"}
if "last_processed" not in st.session_state:
    st.session_state.last_processed = "BRAK DLONI"
if "mcp_logs" not in st.session_state:
    st.session_state.mcp_logs = []

def add_mcp_log(text):
    """Funkcja symulująca logowanie zdarzeń protokołu MCP."""
    st.session_state.mcp_logs.append(f"[{time.strftime('%H:%M:%S')}] {text}")
    if len(st.session_state.mcp_logs) > 3: st.session_state.mcp_logs.pop(0)

# --- LOGIKA GŁÓWNA ---

# 1. WYWOŁANIE NARZĘDZIA (MCP Tool Call)
curr = get_gesture().strip()

# 2. DYNAMICZNE TŁO (Wybór pliku zależnie od wykrycia dłoni)
if curr != "BRAK DLONI":
    set_bg("sith_battle.jpeg") # Tryb walki
else:
    set_bg("sith_room.jpeg")   # Tryb spoczynku

# 3. LOGIKA POJEDYNKU (Orchestracja)
if curr in ["ROCK", "PAPER", "SCISSORS"] and curr != st.session_state.last_processed:
    add_mcp_log(f"Executing tool: get_gesture -> Result: {curr}")
    
    ai_choice = random.choice(["ROCK", "PAPER", "SCISSORS"])
    add_mcp_log(f"Ollama sub-process: Analyzing game state...")
    
    # Obliczenie wyniku (Python Logic)
    if curr == ai_choice: 
        r = "REMIS"
    elif (curr == "ROCK" and ai_choice == "SCISSORS") or \
         (curr == "PAPER" and ai_choice == "ROCK") or \
         (curr == "SCISSORS" and ai_choice == "PAPER"):
        r = "WYGRANA"
        st.session_state.state["p"] += 1
    else:
        r = "PORAŻKA"
        st.session_state.state["s"] += 1

    # 4. INTERAKCJA Z MODELEM (Generative Layer)
    try:
        add_mcp_log(f"Sending context to qwen2.5:3b...")
        resp = ollama.generate(
            model='qwen2.5:3b', 
            system="Jesteś mrocznym Sithem. Mów mrocznie, max 3-4 słowa.", 
            prompt=f"Wynik: {r}. Ty:{ai_choice}, Gracz:{curr}."
        )
        st.session_state.state.update({"res": r, "msg": resp['response'], "a": ai_choice})
    except:
        st.session_state.state.update({"res": r, "msg": "Moc słabnie...", "a": ai_choice})
    
    st.session_state.last_processed = curr

# --- RENDEROWANIE UI ---
col_hud, col_space, col_sith = st.columns([0.8, 1.1, 1.1])

with col_hud:
    st.markdown(f"""<div class="hud-card">
        <center>📡 <b>BATTLE STATUS (MCP)</b></center>
        <hr style="border-color:cyan;">
        👤 TY: <b>{curr}</b><br>
        💀 AI: <b>{st.session_state.state["a"] if curr != "BRAK DLONI" else "---"}</b><br>
        ---<br>
        WYNIK: <span style="color:#ff4444;">{st.session_state.state["res"] if curr != "BRAK DLONI" else "---"}</span><br>
        PUNKTY: {st.session_state.state["p"]} : {st.session_state.state["s"]}
        <hr style="border-color:cyan;">
        <div class="mcp-log">
            <b>MCP SYSTEM LOG:</b><br>
            {"<br>".join(st.session_state.mcp_logs) if st.session_state.mcp_logs else "Waiting for Tool-Call..."}
        </div>
    </div>""", unsafe_allow_html=True)

with col_space:
    # Obszar na Twoje okno OpenCV
    st.markdown('<div style="height:350px; margin-top:50px; border:1px dashed rgba(0,255,255,0.2); border-radius:15px;"></div>', unsafe_allow_html=True)

with col_sith:
    sith_view = st.empty()
    if curr != "BRAK DLONI" and st.session_state.state["msg"]:
        with sith_view.container():
            st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)
            st.markdown(f'<div class="sith-bubble">{st.session_state.state["msg"]}</div>', unsafe_allow_html=True)
            
            res_val = st.session_state.state["res"]
            img = "palaptine_lighting.jpg" if res_val == "WYGRANA" else \
                  "palpatine_remis.jpeg" if res_val == "REMIS" else "palpatine_attack.jpeg"
            
            if os.path.exists(img):
                st.image(img, use_container_width=True)
    else:
        sith_view.empty()

# Odświeżanie pętli głównej
time.sleep(0.05)
st.rerun()
