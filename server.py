import os
import json
import threading
import time
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuración de Seguridad
API_TOKEN_SECRETO = "MiClaveSecretaSuperSegura2026"
DATABASE_FILE = "datos_empleos.json"

# Función para asegurar que el archivo de base de datos exista
def inicializar_db():
    if not os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

inicializar_db()

def guardar_empleo_local(nuevo_empleo):
    try:
        with open(DATABASE_FILE, "r+", encoding="utf-8") as f:
            datos = json.load(f)
            datos.append(nuevo_empleo)
            f.seek(0)
            json.dump(datos, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error guardando: {e}")

@app.route('/', methods=['GET'])
def home():
    return jsonify({"api": "Remote Jobs API", "status": "online", "message": "Servidor seguro operativo"})

@app.route('/jobs', methods=['POST'])
def guardar_empleo():
    token_recibido = request.headers.get("Authorization")
    if not token_recibido or token_recibido != f"Bearer {API_TOKEN_SECRETO}":
        return jsonify({"status": "error", "message": "No autorizado"}), 401
    
    datos = request.get_json()
    if not datos:
        return jsonify({"status": "error", "message": "Sin datos"}), 400
        
    guardar_empleo_local(datos)
    return jsonify({"status": "success", "message": "Guardado correctamente"})

# Esto es lo que permite que Render corra el servidor de forma profesional
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
