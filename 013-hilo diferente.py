import sqlite3
import matplotlib.pyplot as plt
from matplotlib import use
from flask import Flask, request, render_template, jsonify
from flask_cors import CORS

# Configurar el backend de Matplotlib
use('Agg')

aplicacion = Flask(__name__)
CORS(aplicacion, resources={r"/*": {"origins": "*"}})

@aplicacion.route('/')
def inicio():
    return render_template('index.html')

@aplicacion.route('/envia')
def envia():
    etiqueta = request.args.get('etiqueta')
    valor = request.args.get('valor')
    
    try:
        valor = float(valor)  # Validar que valor sea un número
    except (ValueError, TypeError):
        return jsonify({'error': 'El valor debe ser un número válido'}), 400

    conexion = sqlite3.connect('graficaspersonales.sqlite3')
    cursor = conexion.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS peso (etiqueta TEXT, valor REAL)')
    cursor.execute('INSERT INTO peso VALUES (?, ?)', (etiqueta, valor))
    conexion.commit()
    cursor.execute('SELECT * FROM peso')
    filas = cursor.fetchall()
    conexion.close()

    # Filtrar valores válidos
    etiquetas = [fila[0] for fila in filas if fila[1] is not None]
    valores = [float(fila[1]) for fila in filas if fila[1] is not None]

    # Generar gráfico
    plt.bar(etiquetas, valores)
    plt.savefig("static/peso.png")
    plt.close()  # Cerrar el gráfico para liberar memoria
    
    return jsonify({'resultado': 'ok'})

if __name__ == '__main__':
    aplicacion.run(debug=True, host='192.168.1.215', port=3000)
