import os
import json
import threading
import time
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS  # Importación necesaria

app = Flask(__name__)
CORS(app)  # Inicialización necesaria para permitir conexiones externas

# Configuración
API_TOKEN_SECRETO = "MiClaveSecretaSuperSegura2026"
DATABASE_FILE = "datos_empleos.json"

def inicializar_db():
    if not os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

inicializar_db()

# Esta función busca trabajos
def buscar_empleos():
    print("🚀 Iniciando búsqueda automática de empleos...")
    # Aquí iría tu lógica de scraping
    print("✅ Búsqueda finalizada y datos guardados.")

def bucle_automatico():
    while True:
        buscar_empleos()
        time.sleep(21600)  # Espera 6 horas

# Iniciar el hilo de búsqueda en segundo plano
threading.Thread(target=bucle_automatico, daemon=True).start()

@app.route('/', methods=['GET'])
def home():
    return jsonify({"api": "Remote Jobs API", "status": "online"})

@app.route('/jobs', methods=['GET'])
def obtener_empleos():
    with open(DATABASE_FILE, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
