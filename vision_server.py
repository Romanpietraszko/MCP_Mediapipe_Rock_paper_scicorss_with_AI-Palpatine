import cv2
import mediapipe as mp
import numpy as np
import threading
import time
from collections import Counter
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mcp.server.fastmcp import FastMCP

# 1. DEFINICJA SERWERA MCP
# FastMCP automatycznie tworzy infrastrukturę, która pozwala modelom AI 
# na "odpytywanie" tego skryptu o dane z kamery.
mcp = FastMCP("VisionServer")

current_gesture = "BRAK DLONI"
gesture_buffer = [] 
BUFFER_SIZE = 5 # Stabilizacja (Histereza) - eliminuje migotanie gestów

# 2. LOGIKA RYSOWANIA EFEKTÓW (Augmented Reality)
def draw_power_fx(frame, gesture, lm):
    h, w, _ = frame.shape
    # Punkt 9 (środek dłoni) służy jako kotwica dla efektów wizualnych
    cx, cy = int(lm[9].x * w), int(lm[9].y * h)
    
    if gesture == "ROCK": # Efekt gruzu (Kamień)
        for _ in range(12):
            ox, oy = np.random.randint(-50, 50), np.random.randint(-50, 50)
            cv2.circle(frame, (cx+ox, cy+oy), np.random.randint(5, 12), (60, 60, 65), -1)
    elif gesture == "PAPER": # Pioruny (Papier)
        for tip in [8, 12, 16, 20]:
            tx, ty = int(lm[tip].x * w), int(lm[tip].y * h)
            cv2.line(frame, (cx, cy), (tx, ty), (255, 255, 0), 2)
    elif gesture == "SCISSORS": # Wir (Nożyczki)
        t = time.time() * 20
        for r in range(1, 4):
            cv2.ellipse(frame, (cx, cy), (r*18, r*9), int(t), 0, 360, (220, 220, 220), 2)

# 3. PĘTLA PRZETWARZANIA OBRAZU (Computer Vision Pipeline)
def run_vision():
    global current_gesture, gesture_buffer
    # Konfiguracja MediaPipe Hand Landmarker
    detector = vision.HandLandmarker.create_from_options(
        vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path='hand_landmarker.task'),
            num_hands=1, 
            min_hand_detection_confidence=0.8, # Wyższa pewność = lepsze ROCK
            min_hand_presence_confidence=0.8
        )
    )
    cap = cv2.VideoCapture(0)
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        frame = cv2.flip(frame, 1) # Lustrzane odbicie dla intuicyjnego UI
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame))

        raw_g = "BRAK DLONI"
        if result.hand_landmarks:
            lm = result.hand_landmarks[0]
            
            # --- POPRAWIONA LOGIKA GESTÓW ---
            # Sprawdzamy, czy końcówki palców są powyżej stawów (Y maleje w górę)
            # Dla ROCK wszystkie muszą być "zaciśnięte"
            fingers = [lm[t].y < lm[j].y for t, j in zip([8, 12, 16, 20], [6, 10, 14, 18])]
            thumb_open = lm[4].x > lm[3].x if lm[4].x > lm[0].x else lm[4].x < lm[3].x
            
            up_count = sum(fingers)
            
            if up_count == 0 and not thumb_open: raw_g = "ROCK"
            elif up_count >= 3: raw_g = "PAPER"
            elif up_count == 2 and fingers[0] and fingers[1]: raw_g = "SCISSORS"
            
            draw_power_fx(frame, raw_g, lm)

        # Stabilizacja: zapobiega gwałtownym zmianom gestu przy szumie obrazu
        gesture_buffer.append(raw_g)
        if len(gesture_buffer) > BUFFER_SIZE: gesture_buffer.pop(0)
        current_gesture = Counter(gesture_buffer).most_common(1)[0][0]

        cv2.putText(frame, f"POZIOM MOCY: {current_gesture}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.imshow("SITH_VISION_MONITOR", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

# Uruchomienie wizji w osobnym wątku, aby serwer MCP mógł odpowiadać na zapytania
threading.Thread(target=run_vision, daemon=True).start()

# 4. EXPOSING THE TOOL
# To jest serce MCP. Narzędzie 'get_gesture' staje się dostępne dla LLM.
@mcp.tool()
def get_gesture():
    """Zwraca aktualnie wykryty gest dłoni gracza (ROCK, PAPER, SCISSORS lub BRAK DLONI)."""
    return current_gesture

if __name__ == "__main__":
    mcp.run(transport='stdio') # To sprawia, że serwer słucha przez standardowe wejście/wyjście
