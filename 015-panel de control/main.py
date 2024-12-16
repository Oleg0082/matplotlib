import re
import os
import sqlite3
import matplotlib.pyplot as plt
from matplotlib import use
from flask import Flask, request, render_template, jsonify, send_from_directory
from flask_cors import CORS

use('Agg')

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

DB_NAME = 'graficaspersonales.sqlite3'
STATIC_DIR = 'static'

def is_valid_stat_name(name):
    return bool(re.match(r'^[A-Za-z0-9_]+$', name))

def get_datasets():
    """Retrieve the list of tables (datasets) from the SQLite database."""
    if not os.path.exists(DB_NAME):
        return []
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Query SQLite system tables to get user-defined tables
    c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    datasets = [row[0] for row in c.fetchall()]
    conn.close()
    return datasets

def generate_charts():
    """Generate charts for all datasets and save them as PNG in static dir."""
    datasets = get_datasets()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    for ds in datasets:
        c.execute(f'SELECT etiqueta, valor FROM "{ds}"')
        rows = c.fetchall()
        etiquetas = [r[0] for r in rows if r[1] is not None]
        valores = [float(r[1]) for r in rows if r[1] is not None]

        # Generate chart if there's data
        if len(etiquetas) > 0 and len(valores) > 0:
            plt.figure(figsize=(4,3))
            plt.bar(etiquetas, valores, color='#4CAF50')
            plt.title(f'{ds}', fontsize=12, fontweight='bold')
            plt.tight_layout()
            plt.savefig(f"{STATIC_DIR}/{ds}.png")
            plt.close()
        else:
            # If no data, maybe create a placeholder chart or skip
            # To keep it simple, just skip creating a chart if no data
            pass
    conn.close()

@app.route('/')
def index():
    # Generate all charts before rendering
    generate_charts()
    datasets = get_datasets()
    return render_template('index.html', datasets=datasets)

@app.route('/datasets', methods=['GET'])
def list_datasets():
    datasets = get_datasets()
    return jsonify(datasets)

@app.route('/create_dataset', methods=['POST'])
def create_dataset():
    stat_name = request.form.get('stat_name', '').strip()
    if not stat_name:
        return jsonify({'error': 'Dataset name cannot be empty'}), 400
    if not is_valid_stat_name(stat_name):
        return jsonify({'error': 'Invalid dataset name. Use letters, digits, underscores.'}), 400

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(f'CREATE TABLE IF NOT EXISTS "{stat_name}" (etiqueta TEXT, valor REAL)')
    conn.commit()
    conn.close()

    return jsonify({'result': 'ok', 'dataset': stat_name})

@app.route('/envia', methods=['POST'])
def envia():
    stat_name = request.form.get('stat_name', '').strip()
    etiqueta = request.form.get('etiqueta', '').strip()
    valor = request.form.get('valor', '').strip()

    if not stat_name or not is_valid_stat_name(stat_name):
        return jsonify({'error': 'Invalid statistic name.'}), 400
    if not etiqueta:
        return jsonify({'error': 'Etiqueta cannot be empty.'}), 400
    try:
        valor = float(valor)
    except (ValueError, TypeError):
        return jsonify({'error': 'El valor debe ser un número válido'}), 400

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(f'INSERT INTO "{stat_name}" (etiqueta, valor) VALUES (?,?)', (etiqueta, valor))
    conn.commit()
    conn.close()

    return jsonify({'resultado': 'ok'})

if __name__ == '__main__':
    app.run(debug=True, host='192.168.1.215', port=3000)
