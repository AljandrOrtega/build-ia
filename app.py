from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import cv2
import base64
import threading
import json
import os
import time
import io
import PIL.Image
import google.generativeai as genai
import numpy as np

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Configure Gemini AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY", "AIzaSyCArkYnVjbECSeBEhzoJPGps4Jn84it6EI"))
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

# Camera control
camera_active = False
camera_thread = None
face_classifier = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Emotion to HR recommendation mapping (fallback)
EMOTION_RECOMMENDATIONS = {
    "stress": "Recomendación: Considera ofrecer recursos para manejar el estrés o opciones de trabajo flexibles",
    "stressed": "Recomendación: Programa una reunión de bienestar con el empleado",
    "anxious": "Recomendación: Proporciona acceso a recursos de atención plena o servicios de apoyo al empleado (EAP)",
    "tired": "Recomendación: Habla sobre el equilibrio de la carga laboral y considera opciones de descanso",
    "fatigue": "Recomendación: Evalúa las horas de trabajo y fomenta pausas regulares",
    "sad": "Recomendación: Ofrece recursos de apoyo para la salud mental",
    "depressed": "Recomendación: Contacta con el equipo de salud mental para una intervención temprana",
    "angry": "Recomendación: Podría ser útil una capacitación en resolución de conflictos",
    "frustrated": "Recomendación: Programa una reunión 1:1 para discutir los puntos problemáticos",
    "bored": "Recomendación: Revisa las asignaciones y ofrece desafíos nuevos o proyectos más interesantes",
    "neutral": "Recomendación: Mantén reuniones regulares para asegurar el compromiso",
    "happy": "¡Genial! Continúa con las estrategias actuales de compromiso",
    "excited": "¡Señal positiva! Reconoce y recompensa este entusiasmo",
    "engaged": "Recomendación: Ofrece oportunidades de crecimiento para mantener la motivación",
    "motivated": "Recomendación: Refuerza este estado con nuevos retos u oportunidades de liderazgo",
    "confused": "Recomendación: Proporciona aclaraciones y apoyo adicional sobre las tareas",
    "disappointed": "Recomendación: Aborda las expectativas no cumplidas en una conversación abierta",
    "proud": "Recomendación: Reconoce públicamente el logro o esfuerzo del empleado",
    "surprised": "Recomendación: Verifica si la sorpresa fue positiva o negativa y actúa en consecuencia",
    "overwhelmed": "Recomendación: Revisa la carga de trabajo y establece prioridades claras",
    "lonely": "Recomendación: Fomenta el trabajo en equipo y actividades de integración"
}


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/get_employees')
def get_employees():
    json_path = os.path.join(app.root_path, "data/employees.json")
    try:
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                return jsonify(json.load(f))
        return jsonify([])
    except Exception as e:
        print(f"Error loading employee data: {str(e)}")
        return jsonify([])

def enhance_image(frame):
    """Improve image quality for better detection"""
    # Convert to LAB color space for better lighting adjustment
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # Apply CLAHE to L channel
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    
    # Merge channels and convert back to BGR
    limg = cv2.merge((cl, a, b))
    enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    
    # Slight sharpening
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    return cv2.filter2D(enhanced, -1, kernel)

def camera_stream():
    global camera_active
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    if not cap.isOpened():
        socketio.emit('camera_error', {'message': 'Could not access camera'})
        camera_active = False
        return
    
    last_analysis_time = 0
    analysis_cooldown = 3  # seconds between AI analyses
    
    while camera_active:
        ret, frame = cap.read()
        if not ret:
            continue

        # Enhance image quality
        enhanced_frame = enhance_image(frame)
        gray = cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces with optimized parameters
        faces = face_classifier.detectMultiScale(
            gray, 
            scaleFactor=1.05, 
            minNeighbors=6, 
            minSize=(100, 100),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        emotion = "No face detected"
        recommendation = "Position face in camera view"
        
        if len(faces) > 0:
            x, y, w, h = faces[0]
            # Draw rectangle on face
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Only analyze once per cooldown period
            current_time = time.time()
            if current_time - last_analysis_time > analysis_cooldown:
                last_analysis_time = current_time
                
                face_img = frame[y:y+h, x:x+w]
                _, buffer = cv2.imencode('.jpg', face_img)
                
                try:
                    pil_image = PIL.Image.open(io.BytesIO(buffer.tobytes()))
                    response = model.generate_content([
                        "You are an HR specialist. Analyze this employee's face and: "
                        "1. Identify the dominant emotion in one word (e.g., happy, stressed, tired). "
                        "2. Provide one HR recommendation based on the emotion. "
                        "Format: Emotion: [emotion] | Recommendation: [recommendation]",
                        pil_image
                    ])
                    
                    # Parse AI response
                    if response.text:
                        parts = response.text.split("|")
                        if len(parts) >= 2:
                            emotion = parts[0].replace("Emotion:", "").strip()
                            recommendation = parts[1].replace("Recommendation:", "").strip()
                        else:
                            # Fallback to keyword matching
                            emotion = "unknown"
                            for key in EMOTION_RECOMMENDATIONS:
                                if key in response.text.lower():
                                    emotion = key
                                    recommendation = EMOTION_RECOMMENDATIONS[key]
                                    break
                            else:
                                recommendation = "Analysis complete. Consider follow-up conversation."
                except Exception as e:
                    emotion = f"Error: {str(e)}"
                    recommendation = "Technical issue - try again"

        # Convert full frame to base64
        _, frame_buffer = cv2.imencode('.jpg', frame)
        frame_b64 = base64.b64encode(frame_buffer).decode('utf-8')

        socketio.emit('camera_update', {
            'image': frame_b64,
            'faces': len(faces),
            'emotion': emotion,
            'recommendation': recommendation
        })

        time.sleep(0.1)

    cap.release()
    print("Camera released")

@socketio.on('control_camera')
def handle_camera_control(data):
    global camera_active, camera_thread
    
    if data['action'] == 'start' and not camera_active:
        camera_active = True
        camera_thread = threading.Thread(target=camera_stream)
        camera_thread.daemon = True
        camera_thread.start()
        emit('camera_status', {'status': 'active'})
        
    elif data['action'] == 'stop' and camera_active:
        camera_active = False
        if camera_thread:
            camera_thread.join(timeout=2.0)
        emit('camera_status', {'status': 'inactive'})
        
@socketio.on('analyze_frame')
def handle_analyze_frame(data):
    image_b64 = data.get("image")
    if not image_b64:
        emit('camera_error', {'message': 'No image data received'})
        return

    try:
        # Decodificar imagen base64
        image_bytes = base64.b64decode(image_b64)
        pil_image = PIL.Image.open(io.BytesIO(image_bytes))

        # Enviar imagen a Gemini
        response = model.generate_content([
            "You are an HR specialist. Analyze this employee's face and: "
            "1. Identify the dominant emotion in one word (e.g., happy, stressed, tired). "
            "2. Provide one HR recommendation based on the emotion. "
            "Format: Emotion: [emotion] | Recommendation: [recommendation]",
            pil_image
        ])

        # Analizar respuesta
        emotion = "unknown"
        recommendation = "Analysis incomplete"

        if response.text:
            parts = response.text.split("|")
            if len(parts) >= 2:
                emotion = parts[0].replace("Emotion:", "").strip()
                recommendation = parts[1].replace("Recommendation:", "").strip()
            else:
                # Fallback si no cumple el formato
                for key in EMOTION_RECOMMENDATIONS:
                    if key in response.text.lower():
                        emotion = key
                        recommendation = EMOTION_RECOMMENDATIONS[key]
                        break

        emit('camera_update', {
            'image': '',  # No reenviamos imagen, ya se ve localmente
            'faces': 1,   # Asumimos al menos una cara
            'emotion': emotion,
            'recommendation': recommendation
        })

    except Exception as e:
        print(f"[Error en análisis]: {str(e)}")
        emit('camera_error', {'message': 'Error processing the image'})


if __name__ == "__main__":
    socketio.run(app, debug=True, host='0.0.0.0')