import os
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# Esta es la contraseña secreta para que nadie te hackee la API.
# Podés cambiar lo que está entre comillas por el texto que quieras.
API_TOKEN_SECRETO = "MiClaveSecretaSuperSegura2026"

DATABASE_FILE = "datos_empleos.json"

def cargar_empleos_locales():
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def guardar_empleo_local(nuevo_empleo):
    empleos = cargar_empleos_locales()
    empleos.append(nuevo_empleo)
    with open(DATABASE_FILE, "w", encoding="utf-8") as f:
        json.dump(empleos, f, indent=4, ensure_ascii=False)

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "api": "Remote Jobs API",
        "message": "Bienvenido a la API de Empleos Remotos",
        "status": "online"
    })

@app.route('/jobs', methods=['POST'])
def guardar_empleo():
    # 1. Leemos la contraseña que viaja en los headers
    token_recibido = request.headers.get("Authorization")
    
    # 2. Si no coincide, rebota al intruso con un error 401
    if not token_recibido or token_recibido != f"Bearer {API_TOKEN_SECRETO}":
        return jsonify({
            "status": "error", 
            "message": "No autorizado. Token inválido o ausente."
        }), 401
    
    # 3. Si está todo OK, guarda los datos del bot
    datos = request.get_json()
    if not datos:
        return jsonify({"status": "error", "message": "No se enviaron datos"}), 400
        
    guardar_empleo_local(datos)
    return jsonify({
        "status": "success", 
        "message": "Empleo guardado correctamente de forma segura."
    })
