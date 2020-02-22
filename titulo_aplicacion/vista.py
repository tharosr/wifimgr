#!/usr/bin/python3

import os
import shutil
import colorama
from colorama import Fore, Back, Style

print(Style.BRIGHT)
resetFondo = Back.RESET
resetTipografia = Fore.RESET
resetEstilo = Style.RESET_ALL

class Vista:

    anchoMax = shutil.get_terminal_size().columns
    tituloAplicacion = "título de la aplicación"
    caracterRelleno = "*"
    colorFondoTitulo = Back.GREEN
    colorTipografiaTitulo = Fore.WHITE
    
    def __init__(self):
        if (self.anchoMax % 2 != 0): self.anchoMax = self.anchoMax - 1
        
    def setTituloAplicacion(self, titulo=""):
        if (titulo != ""):
            self.tituloAplicacion = titulo
        
    def getTituloAplicacion(self):
        return self.tituloAplicacion
        
    def setCaracterRelleno(self, caracter=caracterRelleno):
        self.caracterRelleno = caracter
        
    def setColorFondoTitulo(self, color=colorFondoTitulo):
        self.colorFondoTitulo = color
    
    def setColorTipografiaTitulo(self, color=colorTipografiaTitulo):
        self.colorTipografíaTitulo = color

    def mostrarTitulo(self):
        os.system("clear")
        # cabecera
        caracteres = int((self.anchoMax - len(self.tituloAplicacion) - 2) / 2)
        cabecera = self.colorFondoTitulo + self.colorTipografiaTitulo + self.caracterRelleno*self.anchoMax + "\n"

        diferencia = 0
        aux = self.caracterRelleno*caracteres + " " + self.tituloAplicacion + " " + self.caracterRelleno*caracteres
        if (len(aux) < self.anchoMax): diferencia = self.anchoMax - len(aux)
        cabecera += aux + self.caracterRelleno*diferencia + "\n"
        
        cabecera += self.caracterRelleno*self.anchoMax + resetFondo + resetTipografia + "\n"
        print(cabecera)
