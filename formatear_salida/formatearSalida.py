def formatearSalida(texto="", largoCampo=35):
    "formatea el texto"
    espacios = 0
    salida = ""
    texto = str(texto)
    if (len(texto) < largoCampo): espacios = largoCampo - len(texto)
    salida = texto + (espacios*" ")
    return salida
