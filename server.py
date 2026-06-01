import os
import json
from flask import Flask, jsonify

app = Flask(__name__)
DB_FILE = "datos_empleos.json"

def db_leer():
    if not os.path.exists(DB_FILE):
        # Si no encuentra el archivo en la nube, arma una lista inicial para que no falle
        return [
            {"id": 1, "titulo": "Senior Python Developer", "empresa": "TechFin Solutions", "ubicacion": "Remoto (EE.UU.)", "salario": "$6,500 - $8,000 USD", "fecha": "Hace 2 horas"},
            {"id": 2, "titulo": "Data Analyst Bilingüe", "empresa": "MktGlobal Agency", "ubicacion": "Remoto (Latam)", "salario": "$1,800 - $2,500 USD", "fecha": "Hace 4 horas"}
        ]
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

@app.route('/')
def home():
    return jsonify({"api": "Remote Jobs API", "status": "online", "message": "Bienvenido a la API de Empleos Remotos"})

@app.route('/jobs', methods=['GET'])
def get_jobs():
    return jsonify(db_leer())

@app.route('/stats', methods=['GET'])
def get_stats():
    return jsonify({"total_registros": len(db_leer()), "status": "online"})

if __name__ == '__main__':
    # El servidor en internet usa el puerto automático que le asigne la nube
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)