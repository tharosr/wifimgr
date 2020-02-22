#!/usr/bin/python3
"""
Usar este archivo en caso de salida inesperada de un programa.
Lo que hace es resetear los estilos de la fuente de la consola.
"""
import colorama
print(colorama.Style.RESET_ALL + colorama.Back.RESET + colorama.Fore.RESET)
