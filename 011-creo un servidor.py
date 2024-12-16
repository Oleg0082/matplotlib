import sqlite3
import matplotlib.pyplot as plt
from flask import Flask, request, render_template, jsonify
from flask_cors import CORS

aplicacion = Flask(__name__)
CORS(aplicacion, resources={r"/*": {"origins": "*"}})


@aplicacion.route('/')
def inicio():
    return render_template('index.html')

@aplicacion.route('/envia')
def envia():
    etiqueta = request.args.get('etiqueta')
    valor = request.args.get('valor')
    conexion = sqlite3.connect('graficaspersonales.sqlite3')
    cursor = conexion.cursor()
    cursor.execute(f'INSERT INTO peso VALUES ("{etiqueta}","{valor}")')
    conexion.commit()
    return "{'resultado':'ok'}"

if __name__ == '__main__':
    aplicacion.run(debug=True, host='192.168.1.215', port=3000)
    """
    cursor.execute('SELECT * FROM peso')
filas = cursor.fetchall()

etiquetas = []
valores = []

for fila in filas:
    etiquetas.append(fila[0])
    valores.append(float(fila[1]))

plt.bar(etiquetas, valores)
plt.savefig("peso.png")

"""




