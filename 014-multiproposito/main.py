import re
import sqlite3
import matplotlib.pyplot as plt
from matplotlib import use
from flask import Flask, request, render_template, jsonify
from flask_cors import CORS

# Use a non-interactive backend for Matplotlib
use('Agg')

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

def is_valid_stat_name(name):
    # Allow only letters, digits, and underscores to prevent SQL injection
    return bool(re.match(r'^[A-Za-z0-9_]+$', name))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/envia', methods=['GET'])
def envia():
    stat_name = request.args.get('stat_name', '').strip()
    etiqueta = request.args.get('etiqueta', '').strip()
    valor = request.args.get('valor', '').strip()

    if not stat_name or not is_valid_stat_name(stat_name):
        return jsonify({'error': 'Invalid statistic name.'}), 400

    if not etiqueta:
        return jsonify({'error': 'Etiqueta (label) cannot be empty.'}), 400

    try:
        valor = float(valor)  # Ensure that the value is a number
    except (ValueError, TypeError):
        return jsonify({'error': 'El valor debe ser un número válido'}), 400

    # Connect to database and insert data into the corresponding statistic table
    conexion = sqlite3.connect('graficaspersonales.sqlite3')
    cursor = conexion.cursor()

    # Create the table if it doesn't exist
    cursor.execute(f'CREATE TABLE IF NOT EXISTS "{stat_name}" (etiqueta TEXT, valor REAL)')

    # Insert the new record
    cursor.execute(f'INSERT INTO "{stat_name}" VALUES (?, ?)', (etiqueta, valor))
    conexion.commit()

    # Retrieve all data for this stat
    cursor.execute(f'SELECT * FROM "{stat_name}"')
    filas = cursor.fetchall()
    conexion.close()

    # Filter valid values
    etiquetas = [fila[0] for fila in filas if fila[1] is not None]
    valores = [float(fila[1]) for fila in filas if fila[1] is not None]

    # Generate the plot for this statistic
    plt.figure(figsize=(8, 4))
    plt.bar(etiquetas, valores, color='#4CAF50')
    plt.title(f'Estadística: {stat_name}', fontsize=14, fontweight='bold')
    plt.xlabel('Etiqueta', fontsize=12)
    plt.ylabel('Valor', fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(f"static/{stat_name}.png")
    plt.close()

    return jsonify({'resultado': 'ok'})


if __name__ == '__main__':
    app.run(debug=True, host='192.168.1.215', port=3000)
