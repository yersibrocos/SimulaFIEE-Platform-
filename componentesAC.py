import pygame
import os
import random


class Componente:
    def __init__(self, nombre, ruta_imagen, descripcion=""):
        self.nombre = nombre
        self.ruta_imagen = ruta_imagen
        self.descripcion = descripcion
        self.imagen = self.cargar_imagen()

    def cargar_imagen(self):
        imagen = pygame.image.load(self.ruta_imagen).convert_alpha()
        imagen = pygame.transform.scale(imagen, (250, 250))
        return imagen

    def get_nombre(self):
        return self.nombre

    def get_imagen(self):
        return self.imagen

    def get_descripcion(self):
        return self.descripcion


class Resistor(Componente):
    def __init__(self, ruta_imagen):
        super().__init__("Resistor", ruta_imagen, "Hace limitar el paso de corriente.")

class Condensador(Componente):
    def __init__(self, ruta_imagen):
        super().__init__("Condensador", ruta_imagen, "Se encarga de almacenar carga eléctrica.")

class Diodo(Componente):
    def __init__(self, ruta_imagen):
        super().__init__("Diodo", ruta_imagen, "Permite el paso de corriente en un solo sentido.")

class Transistor(Componente):
    def __init__(self, ruta_imagen):
        super().__init__("Transistor", ruta_imagen, "Amplifica o conmuta señales.")

class Conmutador(Componente):
    def __init__(self, ruta_imagen):
        super().__init__("Conmutador", ruta_imagen, "Permite conectar o desconectar un circuito.")

class Interruptor(Componente):
    def __init__(self, ruta_imagen):
        super().__init__("Interruptor", ruta_imagen, "Puede abrir o cerrar un circuito manualmente.")

class LED(Componente):
    def __init__(self, ruta_imagen):
        super().__init__("LED", ruta_imagen, "Puede emitir luz al recibir corriente.")

class Microcontrolador(Componente):
    def __init__(self, ruta_imagen):
        super().__init__("Microcontrolador", ruta_imagen, "Es un pequeño cerebro programable de un circuito.")

class Pila(Componente):
    def __init__(self, ruta_imagen):
        super().__init__("Pila", ruta_imagen, "Es la fuente de energía eléctrica portátil.")

class Pulsador(Componente):
    def __init__(self, ruta_imagen):
        super().__init__("Pulsador", ruta_imagen, "Es un interruptor momentáneo al presionarlo.")


class GestorComponentes:
    def __init__(self):
        self.carpeta = "componentes"
        self.componentes = []
        self.indice_actual = 0
        self.cargar_componentes()
        random.shuffle(self.componentes)

    def cargar_componentes(self):
        archivos = os.listdir(self.carpeta)
        for archivo in archivos:
            if archivo.endswith(".png"):
                nombre_base = archivo.replace(".png", "").lower()
                ruta = os.path.join(self.carpeta, archivo)
                componente = self.crear_componente(nombre_base, ruta)
                if componente:
                    self.componentes.append(componente)

    def crear_componente(self, nombre, ruta):
        if nombre == "resistor":
            return Resistor(ruta)
        elif nombre == "condensador":
            return Condensador(ruta)
        elif nombre == "diodo":
            return Diodo(ruta)
        elif nombre == "transistor":
            return Transistor(ruta)
        elif nombre == "conmutador":
            return Conmutador(ruta)
        elif nombre == "interruptor":
            return Interruptor(ruta)
        elif nombre == "led":
            return LED(ruta)
        elif nombre == "microcontrolador":
            return Microcontrolador(ruta)
        elif nombre == "pila":
            return Pila(ruta)
        elif nombre == "pulsador":
            return Pulsador(ruta)
        else:
            return Componente(nombre.capitalize(), ruta)

    def obtener_siguiente(self):
        if self.indice_actual < len(self.componentes):
            componente = self.componentes[self.indice_actual]
            self.indice_actual += 1
            return componente
        else:
            return None

    def generar_opciones(self, componente_correcto):
        nombres = [comp.get_nombre() for comp in self.componentes]
        opciones = [componente_correcto.get_nombre()]
        nombres.remove(componente_correcto.get_nombre())

        while len(opciones) < 4 and nombres:
            opcion = random.choice(nombres)
            opciones.append(opcion)
            nombres.remove(opcion)

        random.shuffle(opciones)
        return opciones