import sqlite3


conexion = sqlite3.connect('graficaspersonales.sqlite3')
cursor = conexion.cursor()
cursor.execute('SELECT * FROM peso')
filas = cursor.fetchall()

print(filas)
