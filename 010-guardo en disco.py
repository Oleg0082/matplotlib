import sqlite3
import matplotlib.pyplot as plt



conexion = sqlite3.connect('graficaspersonales.sqlite3')
cursor = conexion.cursor()
cursor.execute('SELECT * FROM peso')
filas = cursor.fetchall()

etiquetas = []
valores = []

for fila in filas:
    etiquetas.append(fila[0])
    valores.append(float(fila[1]))

plt.bar(etiquetas, valores)
plt.savefig("peso.png")
