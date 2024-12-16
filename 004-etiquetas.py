import matplotlib.pyplot as plt

datos = [1,2,3,4,5,6]
etiquetas = ['pais1','pais2','pais3','pais4','pais5','pais6']

plt.pie(datos,labels=etiquetas)
plt.savefig("grafica.png")
plt.show()
