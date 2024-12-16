import sqlite3


conexion = sqlite3.connect('graficaspersonales.sqlite3')
cursor = conexion.cursor()
cursor.execute('SELECT * FROM peso')
filas = cursor.fetchall()

etiquetas = []
valores = []

for fila in filas:
    etiquetas.append(fila[0])
    valores.append(fila[1])

