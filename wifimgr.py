#!/usr/bin/env python3
"""
Este es un pequeño gestor de redes inalámbricas para línea de comandos

En ocasiones, es necesario reiniciar el servicio networking.
Para evitar incompatibilidades y comportamientos extraños, network-manager debería ser desinstalado, o al menos, no cargarlo al inicio

En ocasiones, es necesario editar el archivo /etc/default/avahi-daemon y establecer
AVAHI_DAEMON_DETECT_LOCAL = 0        
"""

import os
import subprocess as sp
import getpass
import re
import time
from time import sleep
import sys
import getopt
import colorama
from colorama import Fore, Back, Style

from titulo_aplicacion import vista
encabezado = vista.Vista()

from formatear_salida import formatearSalida

def verificacion():
    """ Esta funcion verifica que estén todos los programas. 
    También busca y carga las tarjetas de red inalámbricas.
    En caso de encontrar mas de uno, muestra una selección
    """
    
    print("Verificando aplicaciones necesarias...", end="")
    sys.stdout.flush()
    
    faltantes = []
    for item in lista_apps:
        try:
            tmp = sp.run(['which', item], stdout = sp.PIPE, stderr = sp.PIPE)
        except:
            print(Fore.RED + " error verificando las aplicaciones necesarias" + Fore.WHITE)
            if (debug):
                print("No se ha encontrado el programa: " + str(item))
                print("Lista de programas: " + str(lista_apps))
                print("Código de error del comando 'which': " + str(tmp.returncode))
                print("Mensaje de error: " + str(tmp.stderr.decode()))
            salir()
            
        if (tmp.returncode != 0): faltantes.append(item)
            
    if (len(faltantes) != 0):
        print(Fore.RED + " error: " + Fore.YELLOW + "faltan estos programas: ", end="")
        print(', '.join(faltantes))
        salir()
    print(Fore.GREEN + " ok" + Fore.WHITE)
    
    return 0

def cargar_configuracion(argv):
    """ Carga la configuración de config.ini y lee los parámetros de la línea de comandos.
    Luego actualiza las variables leídas del config en función de los parámetros pasados por línea de comandos, que tienen prioridad.
    """
    global AUTOCONECTAR
    global AUTOCONECTAR_PRIORIDAD
    global supplicant_conf
    global default_nic
    global verif_conexion
    # si hubo error en los argumentos de CLI
    error = False
    
    print("Cargando configuración...", end="")
    sys.stdout.flush()
    
    # leer y cargar el archivo de configuración
    # esta es una forma poco ortodoxa de hacerlo
    # hay un módulo dedicado a esto pero eso requiere que el archivo ini tenga un formato determinado
    # Ya que se trata también de un programa "educativo", lo hice esta manera para simplificar 
    try: fp = open("config.ini", "r")
    except:
        print(Fore.RED + " error" + Fore.WHITE)
        AUTOCONECTAR = False
    
    while True:
        linea = fp.readline()

        if (not linea): break
        if (linea[0:1] != "#") and (linea[0:1] != ""):
            aux = linea.strip("\n")
            if (len(aux) != 0):
                aux = linea.split("=")
                parametro = aux[0].strip()
                valor = aux[1].strip()
                if (parametro == "autoconectar"):
                    if (valor.capitalize() == "True"): AUTOCONECTAR = True
                    else: AUTOCONECTAR = False
                elif (parametro == "supplicant_conf"): supplicant_conf = valor.strip()
                elif (parametro == "default_nic"): default_nic = valor.strip()
                elif (parametro == "verificar_conexion"):
                    if (valor.capitalize() == "True"): verif_conexion = True
                    else: verif_conexion = False
                    
    fp.close()
    
    # leer los modificadores de línea de comandos
    try: 
        opts, args = getopt.getopt(argv,"ha:n:t:",[])
    except getopt.GetoptError:
        print(Fore.RED + " error" + Fore.WHITE)
        print ('wifimgr.py [-a (true/false)]')
        salir()
            
    for opt, arg in opts:
        # ayuda
        if (opt == '-h'): error = True
        # autoconectar
        elif (opt == '-a'):
            if (arg.capitalize() != "True") and (arg.capitalize() != "False"): error = True
            else: AUTOCONECTAR_PRIORIDAD = arg.capitalize()
        # verificar conexion
        elif (opt == "-n"):
            if (arg.capitalize() != "True") and (arg.capitalize() != "False"): error = True
            else: verif_conexion = arg.capitalize()
        # NIC 
        elif (opt == "-t"): default_nic = arg
        
        if (error):
            print(Fore.RED + " error" + Fore.WHITE)
            print ('Ver el archivo README.txt')
            salir()

    print(Fore.GREEN + " ok" + Fore.WHITE)
    if (AUTOCONECTAR_PRIORIDAD != -1): AUTOCONECTAR = AUTOCONECTAR_PRIORIDAD
    
    return 0

def informacion_usuario():
    global info_usuario
    try:
        usuario = getpass.getuser()
        idusuario = os.geteuid()
        idgrupo = os.getegid()
        otrosgrupos = os.getgroups()
        grupos = ""
        for item in otrosgrupos: grupos += str(item) + ", "
        
        info_usuario = {"usuario": usuario, "id": idusuario, "grupo":idgrupo, "grupos":grupos}
    except: return -1
    return 0
    
def mostrar_info_usuario():
    print(Fore.WHITE + "Usuario: " + Fore.YELLOW, end="")
    print(info_usuario['usuario'] + " (" + str(info_usuario['id']) + ")  |  ", end="")
    print(Fore.WHITE + "Grupo: " + Fore.YELLOW + str(info_usuario['grupo']) + Fore.WHITE)
    print()

def buscar_tarjetas_red():
    """ Busca las tarjetas de red inalámbricas en el sistema
    """
    global tarjetas_disponibles
    
    print("Buscando adaptadores inalámbricos...", end="")
    sys.stdout.flush()
    
    
    dir_class_net = "/sys/class/net"
    try: tmp = sp.run(['ls', dir_class_net], stdout = sp.PIPE, stderr = sp.PIPE)
    except:
        print(Fore.RED + " error: " + str(tmp.returncode) + Fore.WHITE)
        if (debug):
            print("No se pudo obtener el listado de las tarjetas de red")
            print("Directorio: " + dir_class_net)
            print("Código de error del comando 'ls " + dir_class_net + "': " + str(tmp.returncode))
            print("Mensaje de error: " + str(tmp.stderr.decode()))
        salir()
        
    tarjetas_aux = tmp.stdout.decode().split()
    if (len(tarjetas_aux) == 0):
        print(Fore.YELLOW + "No hay adaptadores de red disponibles en el sistema" + Fore.WHITE)
        if (debug): print(tarjetas_aux)
        salir()
    
    for tarjeta in tarjetas_aux:
        try: tmp = sp.run(['iw', 'dev', tarjeta, 'info'], stdout = sp.PIPE, stderr = sp.PIPE)
        except:
            print(Fore.RED + " error: " + str(tmp.returncode) + Fore.WHITE)
            if (debug):
                print("No se pudo obtener la información de '" + str(tarjeta) + "'")
                print("Código de error del comando 'iw dev " + str(tarjeta) + " info': " + str(tmp.returncode))
                print("Mensaje de error: " + str(tmp.stderr.decode()))
            salir()
        
        if (tmp.returncode == 0): tarjetas_disponibles.append(tarjeta)

    if (len(tarjetas_disponibles) < 1):
        print(Fore.RED + " error: " + str(tmp.returncode) + Fore.WHITE)
        if (debug):
            print("No se han encontrado tarjetas de red inalámbricas")
            print("Mensaje de error: " + str(tmp.stderr.decode()))
        salir()
    
    print(Fore.GREEN + " ok" + Fore.WHITE)
    if (debug): print("Tarjetas disponibles: " + str(tarjetas_disponibles))
    
def mostrar_tarjetas_red():
    """ Asigna la tarjeta a utilizar. Si hay una, es automático.
    Si hay mas de una, muestra un selector
    """
    global info_red
    
    if (default_nic != 0):
        info_red['tarjeta'] = default_nic
        return 0
    
    if (len(tarjetas_disponibles) == 1): info_red['tarjeta'] = tarjetas_disponibles[0]
    elif (len(tarjetas_disponibles) > 1):
        contador = 1
        print()
        print("Tarjetas de red inalámbricas disponibles: \n")
        for tarjeta in tarjetas_disponibles:
            print("\t" + str(contador) + ". " + tarjeta)
            contador += 1
        print()

        que_tarjeta_usar = 1000
        while (que_tarjeta_usar not in range(contador)):
            que_tarjeta_usar = input("Qué tarjeta usar? [c para cancelar]: ")

            if (que_tarjeta_usar.isnumeric()): que_tarjeta_usar = int(que_tarjeta_usar)
            else:
                if (que_tarjeta_usar.upper() == "C"): salir()
                else: que_tarjeta_usar = 0
        info_red['tarjeta'] = tarjetas_disponibles[que_tarjeta_usar - 1]

    return 0

def informacion_tarjeta_red():

    print("Obteniendo información de la tarjeta de red...", end="")
    sys.stdout.flush()
    
    
    global info_red
    salida = ""
    tmp = ""

    try: tmp = sp.run(['iw', 'dev', info_red['tarjeta'], 'link'], stdout = sp.PIPE, stderr = sp.PIPE)
    except:
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        if (debug):
            print("No se pudo ejecutar: 'iw dev " + str(info_red['tarjeta']) + " link'")
            print("Código de error: " + str(tmp.returncode))
            print("Mensaje de error: " + str(tmp.stderr.decode()))
        return -1

    if (tmp.returncode != 0):
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        if (debug):
            print("Error en la ejecución de: 'iw dev " + str(info_red['tarjeta']) + " link'")
            print("Código de error: " + str(tmp.returncode))
            print("Mensaje de error: " + str(tmp.stderr.decode()))
        return -2

    salida = tmp.stdout.decode().split("\n")

    
    essid = "-"
    ap = "-"
    frecuencia = 0
    canal = 0
    ipv4 = "-"
    ipv6 = "-"
    mac = "-"

    # hay alguna asociación activa
    if ("Connected to" in salida[0]):
        ap = re.findall(mac_reg, salida[0])
        ap = ap[0].upper()
        essid = salida[1].split(": ")[1]
        frecuencia = int(salida[2].split(": ")[1])
        if (frecuencia in banda24_inv): canal = banda24_inv[frecuencia]
        elif (frecuencia in banda5_inv): canal = banda5_inv[frecuencia]
        else: canal = -1
        frecuencia = frecuencia / 1000

#    try: tmp = sp.run(['ifconfig', info_red['tarjeta']], stdout = sp.PIPE, stderr = sp.PIPE)
    try: tmp = sp.run(['ip', 'address', 'show', info_red['tarjeta']], stdout = sp.PIPE, stderr = sp.PIPE)
    except:
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        if (debug):
            print("No se pudo ejecutar: 'ip address show " + str(info_red['tarjeta']) + "'")
            print("Código de error: " + str(tmp.returncode))
            print("Mensaje de error: " + str(tmp.stderr.decode()))
        return -3

    if (tmp.returncode != 0):
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        if (debug):
            print("Error en la ejecución de: 'ip address show " + str(info_red['tarjeta']) + "'")
            print("Código de error: " + str(tmp.returncode))
            print("Mensaje de error: " + str(tmp.stderr.decode()))
        return -4

    salida = tmp.stdout.decode().split("\n")
    
    for linea in salida:
        # mac
        if ("link/ether" in linea): mac = linea.lstrip().split(" ")[1].upper()
        # ipv6
        elif ("inet6" in linea): ipv6 = linea.lstrip().split(" ")[1].split("/")[0].upper()
        # ipv4
        elif ("inet" in linea): ipv4 = linea.lstrip().split(" ")[1].split("/")[0]

            
    if (debug):
        print(salida)
        print("AP: " + str(ap))
        print("ESSID: " + str(essid))
        print("Canal: " + str(canal))
        print("Frecuencia: " + str(frecuencia))
        print("IPv4: " + str(ipv4))
        print("MAC: " + str(mac))
        print("IPv6: " + str(ipv6))

    info_red['ap'] = ap
    info_red['essid'] = essid
    info_red['frecuencia'] = frecuencia
    info_red['canal'] = canal
    info_red['ipv4'] = ipv4
    info_red['ipv6'] = ipv6
    info_red['mac'] = mac

    print(Fore.GREEN + " ok" + Fore.WHITE)
    if (debug): print("info_red: " + str(info_red))
    return 0

def mostrar_info_tarjeta_red():
    # mostrar la información de la tarjeta de red y de la conexión
    print("\nTarjeta: " + Fore.YELLOW + info_red['tarjeta'] + Fore.WHITE + "\t\tEstado: " + Fore.YELLOW, end="")

    if (len(info_red['ipv4']) == 1): print(Fore.RED + "no conectado" + Fore.WHITE, end="")
    else: print(Fore.GREEN + "conectado" + Fore.WHITE, end="")
    print(" / ", end="")
    if (info_red['ap'] == "-"): print(Fore.RED + "no asociado" + Fore.WHITE)
    else: print(Fore.GREEN + "asociado" + Fore.WHITE)

    if (info_red['essid'] != "-"):
        print(Fore.WHITE + "Red: " + Fore.YELLOW + info_red['essid'] + Fore.WHITE, end="")
        print("\tAP: " + Fore.YELLOW + info_red['ap'] + Fore.WHITE, end="")
        print("\t\tBanda: " + Fore.YELLOW + str(info_red['frecuencia']) + " Ghz (Canal " + str(info_red['canal']) + ")" + Fore.WHITE)
        print("IPv4: " + Fore.YELLOW + str(info_red['ipv4']) + Fore.WHITE + "\tMAC: " + Fore.YELLOW + str(info_red['mac']))
        print(Fore.WHITE + "IPv6: " + Fore.YELLOW + str(info_red['ipv6']))
    print(Fore.WHITE + "\n")

def reiniciar_servicios_red():
    """ reinicia el servicio de networking. mata dhclient y wpa_supplicant
    """
        
    print("Reiniciando los servicios de red...", end="")
    sys.stdout.flush()
    

    desconectar()
    desasociar()
    
    try: tmp = sp.run(['ifconfig', info_red['tarjeta'], "down"], stdout = sp.PIPE, stderr = sp.PIPE)
    except:
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        return -1
    if (tmp.returncode != 0):
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        return -2
    
    try: tmp = sp.run(["systemctl", "stop", "networking"], stdout = sp.PIPE, stderr = sp.PIPE)
    except:
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        return -3
    if (tmp.returncode != 0):
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        return -4

    try: tmp = sp.run(["systemctl", "start", "networking"], stdout = sp.PIPE, stderr = sp.PIPE)
    except:
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        return -5
    if (tmp.returncode != 0):
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        return -6
    
    try: tmp = sp.run(['ifconfig', info_red['tarjeta'], "up"], stdout = sp.PIPE, stderr = sp.PIPE)
    except:
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        return -7
    if (tmp.returncode != 0):
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        return -8
    
    print(Fore.GREEN + " ok" + Fore.WHITE)
    return 0
        
def desasociar():
    """ Desasocia la conexión inalámbrica.
    No necesariamente libera la dirección IP
    """
    try: tmp = sp.run(['killall', 'wpa_supplicant'], stdout = sp.PIPE, stderr = sp.PIPE)
    except: return -1
    if (tmp.returncode != 0): return -2
    return 0

def desconectar():
    """ Libera la dirección IP
    """
    try: tmp = sp.run(['dhclient', '-r', info_red['tarjeta']], stdout = sp.PIPE, stderr = sp.PIPE)
    except: return -1
    if (tmp.returncode != 0): return -2
    return 0

def estado_tarjeta_red():
    """ Devuelve el estado de la tarjeta de red
    Si el valor devuelto es 0 (cero), la tarjeta está desactivada
    Si el valor devuelto es 1 (uno), la tarjeta está activada
    """
    try: tmp = sp.run(['ip', 'link', 'show', info_red['tarjeta']], stdout = sp.PIPE, stderr = sp.PIPE)
    except:
        if (debug): print(Fore.RED + " Error ejecutando 'ip link show " + info_red['tarjeta'] + "': " + str(tmp.returncode) + Fore.WHITE)
        return -1
    
    if (tmp.returncode != 0):
        if (debug):
            print(Fore.RED + "Error en la ejecución de 'ip link show " + info_red['tarjeta'] + "': " + str(tmp.returncode) + Fore.WHITE)
            print("Mensaje de error: " + str(tmp.stderr.decode()))
        return -2
    
    if ("DOWN" in tmp.stdout.decode()): return 0
    elif ("UP" in tmp.stdout.decode()): return 1
    else:
        if (debug):
            print(Fore.RED + "Error obteniendo el estado de la tarjeta '" + str(info_red['tarjta']) + "'" + Fore.WHITE)
            print("Mensaje: " + str(tmp.stdout.decode()))
        return -3
    
def activar_tarjeta():
    """ (des)activa la tarjeta de red
    comando previsto para futuras versiones: ip a s wlx00c0ca972549 |grep state 
    """
    
    print("Activando la tarjeta de red...", end="")
    sys.stdout.flush()
    
    
    desconectar()
    desasociar()
    
    try: tmp = sp.run(['ip', 'link', 'set', info_red['tarjeta'], 'down'], stdout = sp.PIPE, stderr = sp.PIPE)
    except:
        if (debug):
            print(Fore.RED + " No se ha podido ejecutar 'ip link set " + info_red['tarjeta'] + " down': " + str(tmp.returncode) + Fore.WHITE)
            print("Mensaje: " + str(tmp.stderr.decode()))
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        return -1
    
    if (tmp.returncode != 0):
        if (debug):
            print(Fore.RED + " Error ejecutando 'ip link set " + info_red['tarjeta'] + " down': " + str(tmp.returncode) + Fore.WHITE)
            print("Mensaje: " + str(tmp.stdput.decode()))
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        return -2
    
    try: tmp = sp.run(['ip', 'link', 'set', info_red['tarjeta'], 'up'], stdout = sp.PIPE, stderr = sp.PIPE)
    except:
        if (debug):
            print(Fore.RED + " No se ha podido ejecutar 'ip link set " + info_red['tarjeta'] + " up': " + str(tmp.returncode) + Fore.WHITE)
            print("Mensaje: " + str(tmp.stderr.decode()))
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        return -3
    
    if (tmp.returncode != 0):
        if (debug):
            print(Fore.RED + " Error ejecutando 'ip link set " + info_red['tarjeta'] + " up': " + str(tmp.returncode) + Fore.WHITE)
            print("Mensaje: " + str(tmp.stdput.decode()))
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        return -4
    
    print(Fore.GREEN + " ok" + Fore.WHITE)
    return 0

def escanear_redes():
    """ escanea las redes inalámbricas dentro del alcance
    Esta función "parsea" los resultados de iw. Se podrían usar comandos como sed y awk.
    Sin embargo, la idea es "mantenerlo en python". Además, la salida de iw no se 
    puede considerar estable.
    """

    print(Fore.WHITE + "Escaneando las redes...", end="")
    sys.stdout.flush()
    
    
    global lista_redes

    try: tmp = sp.run(['iw', info_red['tarjeta'], 'scan'], stdout = sp.PIPE, stderr = sp.PIPE)
    except:
        print(Fore.RED + " error escaneando las redes inalámbricas disponibles: (" + str(tmp.returncode) + ")" + Fore.WHITE)
        salir()
    
    if (tmp.returncode != 0):
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        print(str(tmp.returncode) + ": " + tmp.stderr.decode())
        salir()
    
    
    mac = ""
    canal = 0
    frecuencia = 0
    cifrado = "no"
    essid = ""
    wpa2 = 0
    wpa = 0
    wep = 0
    indice = 1
    
    def reset_variables():
        mac = ""
        canal = 0
        frecuencia = 0
        cifrado = 0
        essid = ""
        wpa2 = 0
        wpa = 0
        wep = 0
    
    resultado = tmp.stdout.decode().split("\nBSS")
    for red in resultado:
        red = red.split("\n")
        reset_variables()
        for linea in red:
            if ("on " + info_red['tarjeta'] in linea): mac = re.findall(mac_reg, linea)[0]
            if (linea[1:6] == "freq:"):
                frecuencia = int(linea.split(": ")[1])
                if (frecuencia not in banda24_inv): canal = banda5_inv[frecuencia]
                else: canal = banda24_inv[frecuencia]
            if (linea[1:6] == "SSID:"): essid = linea.split(": ")[1]
            if ("capability: ESS Privacy" in linea): cifrado = 1
            if ("RSN:" in linea): wpa2 = 1
            if ("WPA:" in linea): wpa = 1
            
            
        if (cifrado == 1) and (wpa2 == 0) and (wpa == 0): wep = 1
        lista_redes[indice] = {"essid":essid, "mac":mac.upper(), "frecuencia":frecuencia/1000, "canal":canal, "cifrado":cifrado, "wpa2":wpa2, "wpa":wpa, "wep":wep, "existe":0}
        indice += 1
        
        

    if (debug): print(lista_redes)

    if (len(lista_redes) == 0):
        print(Fore.YELLOW + "No se han encontrado redes dentro del alcance" + Fore.WHITE)
        salir()
    
    # actualizar el diccionario verificando si entre las redes detectadas alguna ya fue configurada con anterioridad
    for item in lista_redes:
        for existente in AUTOCONECTAR_redes:
            if (existente == lista_redes[item]['essid']): lista_redes[item]['existe'] = 1

    return 0

def mostrar_redes():

    print()
    print()
    print("Las redes en verde son redes previamente configuradas")
    print()
    print("\t" + formatearSalida.formatearSalida("Nro.", 7), end="")
    print(formatearSalida.formatearSalida("Red", 30), end="")
    print(formatearSalida.formatearSalida("Cif.", 6), end="")
    print(formatearSalida.formatearSalida("Tipo Cif.", 15), end="")
    print(formatearSalida.formatearSalida("Canal", 20), end="")
    print(formatearSalida.formatearSalida("MAC", 22))
    print("\t" + "-"*95)

    for item in lista_redes:
        if (lista_redes[item]['canal'] != 0):
            aux_cifrado = ""
            essid = ""
            print("\t" + formatearSalida.formatearSalida(str(item), 7), end="")
           
            if (len(lista_redes[item]['essid']) == 0): essid = "*oculta"
            else: essid = lista_redes[item]['essid']
            if (lista_redes[item]['existe'] == 1): print(Fore.GREEN, end="")
            else: print(Fore.YELLOW, end="")
            print(formatearSalida.formatearSalida(essid, 30) + Fore.WHITE, end="")
            print(formatearSalida.formatearSalida(lista_redes[item]['cifrado'], 6), end="")
            if (lista_redes[item]['cifrado'] == 1):
                if (lista_redes[item]['wpa2'] == 1): aux_cifrado += "WPA2/"
                else: aux_cifrado += "-/"
                if (lista_redes[item]['wpa'] == 1): aux_cifrado += "WPA/"
                else: aux_cifrado += "-/"
                if (lista_redes[item]['wep'] == 1): aux_cifrado += "WEP"
                else: aux_cifrado += "-"
            else: aux_cifrado = "-/-/-"
            print(formatearSalida.formatearSalida(aux_cifrado, 15), end="")
            print(formatearSalida.formatearSalida(str(lista_redes[item]['canal']) + " (" + str(lista_redes[item]['frecuencia']) + " Ghz)", 20), end="")
            print(formatearSalida.formatearSalida(lista_redes[item]['mac'], 22))

    print()
    return 0
    
def verificar_asociacion(conectar_a, essid, psk):
    """ Verifica la asociación al AP sin realizar cambios en archivos de configuración
    conectar_a es el id del diccionario lista_redes
    essid es el nombre de la red (útil particularmente para redes ocultas)
    psk es la clave o contraseña.
    
    Devuelve cero si la asociación fue correcta, un número negativo si no.
    """
    
    if (conectar_a not in lista_redes): return -1
    if (len(str(essid)) == 0): return -2
    if (len(str(psk)) == 0): return -3
    
    
    comando = ""
    archivo_tmp = os.getcwd() + "/" + "wpa_supp_tmp.conf"
    # hash
    salida_psk = ""
    es_nueva_red = True
    hay_que_actualizar = False
    
    salida_psk = wpa_string(conectar_a, essid, psk)
    
    try: fp = open(archivo_tmp, "w")
    except: return -4

    try: fp.write(salida_psk)
    except:
        fp.close()
        return -5
    fp.close()
    
    desconectar()
    desasociar()
    
    try: comando = sp.Popen('wpa_supplicant -i ' + info_red['tarjeta'] + ' -D nl80211,wext,roboswitch,bsd,ndis -c' + archivo_tmp, stderr = sp.PIPE, stdout = sp.PIPE, shell = True)
    except:return -6
    
    # verificar salida del intento de asociación
    conexion = 0
    estado = 0
    anterior = ""
    salida = ""
    while True:
        anterior = salida
        salida = comando.stdout.readline()
        if (salida == "") and (comando.poll() is not None): break
        if (salida):
#            descomentar la siguiente linea para ver la salida en tiempo real del comando wpa_supplicant
#            print(salida.decode().split("\n"))

            if ("CTRL-EVENT-CONNECTED" in salida.decode().split("\n")[0]): 
                if ("Key negotiation completed" in anterior.decode().split("\n")[0]):
                    estado = 0
                    break

            if ("auth_failures" in salida.decode().split("\n")[0]):
                if ("WRONG_KEY" in salida.decode().split("\n")[0]):
                    estado = -8
                    break
                auth_failures = int(salida.decode().split("\n")[0].split("auth_failures=")[1].split(" ")[0])
                if (auth_failures >= 4):
                    estado = -9
                    break
            
        rc = comando.poll()
#    try: comando = sp.run(['rm', archivo_tmp], stdout = sp.PIPE, stderr = sp.PIPE)
#    except: pass
    return estado

def pedir_password():
    """ Pide la contraseña de la red
    """
    while True:
        password = input("Cuál es la contraseña? [c para cancelar]: ")
        if (not password.isnumeric()) and (password.upper() == "C"): salir()
        if (len(password) != 0) and (len(password) >= wep_min_long) and (len(password) <= wep_max_long): return password

def pedir_essid():
    """ Pide el nombre de la red (para conexión a redes ocultas)
    """
    essid = ""
    while True:
        essid = input("Cuál es el nombre de la red? [c para cancelar]: ")
        if (essid.upper() == "C"): salir()
        if (len(essid) != 0): return essid

def selector_red():
    """ Muestra el selector de red
    
    No recibe ningún parámetro.
    Devuelve un entero mayor a cero si es correcta la selección, o -1 si se canceló
    """
    conectar_a = ""
    ssid = ""
    
    while (conectar_a not in lista_redes):
        conectar_a = input("A qué red te queres conectar? [c para cancelar]: ")
        if (conectar_a.isnumeric()): conectar_a = int(conectar_a)
        else:
            if (conectar_a.upper() == "C"): salir()
            else: conectar_a = 0
    return conectar_a

def conectar():
    """ 
    1. Mostrar las redes
    2. Elegir red
    3. Si la red es oculta, pedir nombre de red
    4. Si la red no está configurada, pedir password
    5. Si todo ok, verificar
    6. Si no se conecta, pedir nuevo password (y red si es oculta)
    """

    conectar_a = 0
    password = ""
    essid = ""
    cifrado = ""
    hay_que_actualizar = False
    es_nueva_red = True

    hay_disponibles_redes_existentes = False
    for red in lista_redes:
        if (lista_redes[red]['existe'] == 1):
            hay_disponibles_redes_existentes = True
            break
    
    estado_funcion = -1000
    contador_error = 0
    while True:

        conectar_a = selector_red()

        if (lista_redes[conectar_a]['essid'] == ""): essid = pedir_essid()
        else: essid = lista_redes[conectar_a]['essid']

        # primer paso del bucle. Si la red no fue configurada previamente, pedir password
        # si ya fue configurada, recuperar el password 
        if (estado_funcion == -1000):
            if (lista_redes[conectar_a]['existe'] == 0):
                password = pedir_password()
                es_nueva_red = True
            else:
                for red in AUTOCONECTAR_redes_dc:
                    if (red['essid'] == essid):
                        password = red['clave']
                        break
        else:
            password = pedir_password()
            if (lista_redes[conectar_a]['existe'] == 1): hay_que_actualizar = True
            


        # intentar conexion para verificar la clave
        print("Intentando asociar a " + str(essid) + "...", end="")
        sys.stdout.flush()
        
        
        estado_funcion = verificar_asociacion(conectar_a, essid, password)
        
        # conexión correcta
        if (estado_funcion == 0): 
            print(Fore.GREEN + " ok" + Fore.WHITE)
            break
       
       # contraseña incorrecta
        elif (estado_funcion == -8):
            print(Fore.YELLOW + " Contraseña incorrecta (" + str(password) + ")" + Fore.WHITE)
            contador_error += 1
            
        # el límite máximo de contraseñas incorrectas fue alcanzado 
        elif (estado_funcion == -9):
            print(Fore.YELLOW + " Contraseña incorrecta (" + str(password) + ")" + Fore.WHITE)
            contador = 4

        # otro error que no es contraseña incorrecta
        else:
            print(Fore.YELLOW + " Error " + str(estado_funcion) + Fore.WHITE)
            contador_error += 1

        if (contador_error == 4): salir()



    # si el intento de asociación fue exitoso:
    #    - si es una nueva red, agregarla a conf de supplicant
    #    - si es una red existente sin cambio de contraseña, no hacer nada y mantener la conexión actual
    #    - si es una red existente con cambio de contraseña, actualizar conf de supplicant
    # Si no fue exitoso, salir
    if (estado_funcion == 0) and ((hay_que_actualizar) or (es_nueva_red)):
        estado_funcion = -1000
        estado_funcion = configurar_supplicant(conectar_a, essid, password)
        if (estado_funcion == 0):
            print(Fore.GREEN + " ok" + Fore.WHITE)
            return 0
        else:
            print(Fore.RED + "No se pudo configurar WPA Supplicant (" + str(estado_funcion) + ")" + Fore.WHITE)
            salir()
    elif (estado_funcion == 0) and (not hay_que_actualizar) and (not es_nueva_red):
        print(Fore.GREEN + " ok" + Fore.WHITE)
        return 0
    else:
        print(Fore.RED + " error: " + str(estado_funcion) + Fore.WHITE)
        return -2


    
    return 0

def wpa_string(conectar_a, essid, password):
    """ Ejecuta la funcion wpa_passphrase y devuelve el string generado, o un entero negativo en caso de error
    En caso de que no se use WPA/2, y sea WEP, abierta u oculta, devuelve el string correspondiente
    """
    salida = ""
    
    # wpa/wpa2
    if (lista_redes[conectar_a]['wpa'] == 1) or (lista_redes[conectar_a]['wpa2'] == 1):
    
        try: tmp = sp.run(['wpa_passphrase', str(essid), str(password)], stdout = sp.PIPE, stderr = sp.PIPE)
        except: return -1
        
        if (tmp.returncode != 0): return -tmp.returncode
        
        salida = tmp.stdout.decode()
        
        if (lista_redes[conectar_a]['essid'] == ""): salida = salida.replace("}", "\tscan_ssid=1\n}")
    
    # wep
    elif (lista_redes[conectar_a]['wpa'] == 0) and (lista_redes[conectar_a]['wpa2'] == 0) and (lista_redes[conectar_a]['wep'] == 1):
        
        salida = "network={\n\t"
        salida += "ssid=\"" + str(essid) + "\"\n\t"
        salida += "key_mgmt=NONE\n\t"
        salida += "wep_key0=\"" + str(password) + "\"\n\t"
        salida += "#wep_key0=\"" + str(password) + "\"\n\t"
        salida += "wep_tx_keyidx=0\n"
        if (lista_redes[conectar_a]['essid'] == ""): salida += "\tscan_ssid=1\n"
        salida += "}"
    
    # abierta
    elif (lista_redes[conectar_a]['wpa'] == 0) and (lista_redes[conectar_a]['wpa2'] == 0) and (lista_redes[conectar_a]['wep'] == 0):
        
        salida = "network={\n\t"
        salida += "ssid=\"" + str(essid) + "\"\n\t"
        salida += "key_mgmt=NONE\n\t"
        salida += "priority=100\n"
        if (lista_redes[conectar_a]['essid'] == ""): salida += "\tscan_ssid=1\n"
        salida += "}"
        
        
    if (len(salida) == 0): return -2
    return salida + "\n"

def configurar_supplicant(conectar_a, essid, password):
    """ Configura el archivo wpa_supplicant.conf para agregar/actualizar la red
    Esta función solo es llamada si hay que agregar o actualizar una red
    """
    print("Configurando WPA Supplicant...", end="")
    sys.stdout.flush()
    

    if (conectar_a == 0):
        print(Fore.RED + " error: no seas trolo man, decime a qué red te queres conectar")
        return -1

    actualizar = False
    for red in AUTOCONECTAR_redes_dc:
        if (red['essid'] == essid): actualizar = True

    salida = wpa_string(conectar_a, essid, password)
    if (not isinstance(salida, str)):
        print(Fore.RED + " error: " + str(salida) + Fore.WHITE)
        return -2

    # nueva red
    if (actualizar == False):

        try: fp = open(supplicant_conf, "a+")
        except:
            print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
            return -3
        
        try: fp.write(salida)
        except:
            print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
            fp.flush()
            fp.close()
            return -4
        
        fp.close()
        print(Fore.GREEN + " ok" + Fore.WHITE)
        return 0
    
    elif (actualizar == True):

        contador = 0
        actualizacion = ""    
        salida_aux = salida.replace("\t", "")
        salida_aux = salida_aux.split("\n")

        essid = salida_aux[1].split("\"")[1]
        psk = salida_aux[3].split("=")[1]
        
        for item in range(len(AUTOCONECTAR_redes_dc)):
            aux = ""
            if (AUTOCONECTAR_redes_dc[item]['essid'] == essid):
                AUTOCONECTAR_redes_dc[item]['clave'] = password
                AUTOCONECTAR_redes_dc[item]['psk'] = psk

        try: fp = open(supplicant_conf, "r")
        except:
            print(Fore.RED + " error" + Fore.WHITE)
            return -12
        
        supplicant_lineas = ""
        supplicant_lineas = fp.readlines()
        
        try: fp.close()
        except:
            fp.flush()
            fp.close()
            return -14
        
        anterior = -1
        actual = 0
        contador = 0
        for item in supplicant_lineas:
            if (lista_redes[conectar_a]['essid'] in item): anterior = contador - 1
            if ("}" in item) and (anterior != -1):
                actual = contador
                break
            contador += 1

        contador = 0
        for linea in supplicant_lineas:
            if (contador < anterior) or (contador > actual): salida += linea
            contador += 1
        
        try: fp = open(supplicant_conf, "w")
        except:
            print(Fore.RED + " error" + Fore.WHITE)
            return -12
        
        try: fp.write(salida)
        except:
            fp.flush()
            fp.close()
            return -13
        
        fp.close()
        
        print(Fore.GREEN + " ok" + Fore.WHITE)
        return 0
        

def obtener_ip():
    print("Obteniendo dirección IP...", end="")
    sys.stdout.flush()
    
    try:
        tmp = sp.run(['dhclient', '-4', info_red['tarjeta']], stdout = sp.PIPE, stderr = sp.PIPE)
    except:
        print(Fore.RED + " error" + Fore.WHITE)
        return -1
    
    if (tmp.returncode != 0):
        print(Fore.RED + " error" + Fore.WHITE)
        return -2
    
    print(Fore.GREEN + " ok" + Fore.WHITE)
    return 0


def autoconectar_redes():
    """ Esta función obtiene las redes previamente configuradas
    
    Ya sea que AUTOCONECTAR sea True o False, si la red fue previamente configurada
    se obtienen los datos para reducir 1 paso (o más si hay error) la intervención del usuario
    
    """

    global AUTOCONECTAR_redes
    global AUTOCONECTAR_redes_dc    
    
    print("Buscando redes ya configuradas...", end="")
    sys.stdout.flush()
    
    
    # parsear wpa_supplicant.conf
    try: fp = open(supplicant_conf, "r")
    except: print(Fore.YELLOW + " error, se omite" + Fore.WHITE)
    else:

        contador_items = 0
        essid = ""
        clave = ""
        psk = ""
        oculta = 0
        ap = 0
        aux = {'essid':essid, 'clave':clave, 'psk':psk, 'oculta':oculta, "ap":ap}
        
        lineas = ""
        while True:
            linea = fp.readline()
            if (not linea): break
            lineas += linea
        fp.close()
        
        lineas = lineas.split("network=")
        for linea in lineas:
            if (linea != ""):
                # linea_aux es una red
                linea_aux = linea.split()
                if (debug): print(Fore.MAGENTA + str(linea_aux) + Fore.WHITE)
                for linea_red in linea_aux:
                    if ("scan_ssid" in linea_red): oculta = linea_red.split("=")[1]
                    elif ("ssid" in linea_red): essid = linea_red.split("\"")[1]
                    elif ("#psk" in linea_red): clave = linea_red.split("\"")[1]
                    elif ("psk" in linea_red): psk = linea_red.split("=")[1]
    
                    elif ("}" in linea_red):
                        AUTOCONECTAR_redes.append(essid)
                        aux = {'essid':essid, 'clave':clave, 'psk':psk, 'oculta':oculta, "ap":ap}
                        AUTOCONECTAR_redes_dc.append(aux)
                        contador_items += 1
                        if (debug): print("aux: " + str(aux))
                        essid = ""
                        clave = ""
                        psk = ""
                        oculta = 0
                        ap = 0
                        aux = {'essid':essid, 'clave':clave, 'psk':psk, 'oculta':oculta, "ap":ap}
        fp.close()
        
        print(Fore.GREEN + " " + str(len(AUTOCONECTAR_redes)) + " encontradas" + Fore.WHITE)
        if (len(AUTOCONECTAR_redes_dc) == 0): AUTOCONECTAR = False

    if (debug):
        print("AUTOCONECTAR_redes: " + str(AUTOCONECTAR_redes))
        print("AUTOCONECTAR_redes_dc: " + str(AUTOCONECTAR_redes_dc))

    return 0
    
    

def autoconectar():
    """ Esta función intenta autoconectarse a alguna red disponible dentro del alcance y la cual ya se encuentre configurada
    Esta función hay que afinarla para que, en caso de no poder conectarse a una red ya configurada, intente con las siguientes
    
    Si no se han encontrado redes ya configuradas, AUTOCONECTAR = False y pasa a conexión manual
    """
    global AUTOCONECTAR
    
    print("Intentando autoconexión...", end="")
    sys.stdout.flush()
    
    
#    AUTOCONECTAR = False
    if (AUTOCONECTAR != True):
        print(Fore.RED + " desactivada" + Fore.WHITE)
        return -1
    
    if (len(AUTOCONECTAR_redes) == 0):
        print(Fore.YELLOW + " no se han encontrado redes" + Fore.WHITE)
        AUTOCONECTAR = False
        return -2
    
    estado_funcion = 0
    desconectar()
    desasociar()
#    estado_funcion = reiniciar_servicios_red()
    if (estado_funcion != 0):
        print(Fore.RED + " error (" + str(estado_funcion) + ")" + Fore.WHITE)
        return -3
    
    estado_funcion = activar_tarjeta()
    if (estado_funcion != 0):
        print(Fore.RED + " error (" + str(estado_funcion) + ")" + Fore.WHITE)
        return -4
    

    try: tmp = sp.run(['wpa_supplicant', '-B', '-i', info_red['tarjeta'], '-D', 'nl80211,wext', '-c', supplicant_conf], stdout = sp.PIPE, stderr = sp.PIPE)
    except:
        print(Fore.RED + " error " + str(tmp.returncode) + " ejecutando supplicant" + Fore.WHITE)
        return -6
    
    if (tmp.returncode != 0):
        print(Fore.RED + " Error iniciando supplicant (error: " + str(tmp.returncode) + ")" + Fore.WHITE)
        return -7
    
    obtener_ip()
    
    informacion_tarjeta_red()
    
    mostrar_info_tarjeta_red()
    
    verificar_conexion()
    return 0
    
def verificar_conexion():
    """ Verifica que la conexión a la red es correcta.
    Ejecuta el comando ping al router.
    No garantiza la conexión a internet, ya que depende de otros factores que están fuera del alcance.
    """
    print("Verificando la conexión...", end="")
    sys.stdout.flush()

    if (not verif_conexion):
        print(Fore.YELLOW + " omitido por usuario" + Fore.WHITE)
        return 0

    enviar = 20
    enviados = 0
    recibidos = 0
    tolerancia = 0.25
    destino = "google.com"

    tmp = sp.run(['ping', '-c', str(enviar), destino], stdout = sp.PIPE, stderr = sp.PIPE)
    for item in tmp.stdout.decode().split("\n"):
        if ("transmitted" in item) and ("received" in item):
            enviados = int(item.split()[0])
            recibidos = int(item.split()[3])
            break
    
    if (enviados == enviar):
        if (round(enviados / enviar) >= (1 - tolerancia)): 
            print(Fore.GREEN + " ok" + Fore.WHITE)
            return 0
        elif (round(enviados / enviar) >= (1 - (tolerancia * 2))): 
            print(Fore.YELLOW + " lento" + Fore.WHITE) 
            return -1
        else: 
            print(Fore.RED + " error" + Fore.WHITE) 
            return -2
    else: 
        print(Fore.RED + " error" + Fore.WHITE) 
        return -3
    

def salir():
    print(Style.RESET_ALL + Back.RESET + Fore.RESET)
    print()
    quit()
    



def main(argv):
    
#    if (debug):
    t0 = time.time()
    
    encabezado.setTituloAplicacion("WiFi Manager 0.3rc por @juliorollan")
    encabezado.mostrarTitulo()
    
    informacion_usuario()
    mostrar_info_usuario()
    verificacion()
    cargar_configuracion(argv)
    buscar_tarjetas_red()
    mostrar_tarjetas_red()
    informacion_tarjeta_red()
    mostrar_info_tarjeta_red()
    autoconectar_redes()
#    autoconectar()
    activar_tarjeta()
    escanear_redes()
    mostrar_redes()
    conectar()
    obtener_ip()
    informacion_tarjeta_red()
    mostrar_info_tarjeta_red()
    verificar_conexion()
    
#    if (debug):
    t1 = time.time()
    tt = t1 - t0
    print("Tiempo total de ejecución: ", tt, " segs")
    
    salir()


# determina si se intenta la autoconexion, basado en config.ini
# en caso de error en la lectura de config.ini o una configuración
# incorrecta, AUTOCONECTAR=False
AUTOCONECTAR = False
AUTOCONECTAR_PRIORIDAD = -1
# contiene las redes previamente configuradas en wpa_supplicant.conf
# estos valores son usados tanto por la función autoconectar, como para la conexión manual
AUTOCONECTAR_redes = []
# este diccionario contiene la misma info que la lista de arriba pero con claves y psk.
# es una transición a la versión 0.3. Sin esto, habría que revisar todo el código y ahora no me pinta
AUTOCONECTAR_redes_dc = []
# archivo de configuración de wpa_supplicant
supplicant_conf = "/etc/wpa_supplicant/wpa_supplicant.conf"
# lista de aplicaciones necesarias
lista_apps = ['iw', 'dhclient', 'wpa_supplicant', 'ip', 'ping', 'killall']
# contiene la información del usuario
info_usuario = {}
# tarjetas de red disponibles en el sistema
tarjetas_disponibles = []
# si en el archivo de configuración se estableció una tarjeta inalámbrica 
# por defecto, se carga en esta variable. d
default_nic = 0
# verificar o no la conexión mediante el comando ping
verif_conexion = True
# contiene la información actual de la red
info_red = {}
info_red = {"ap":"-", "mac":"-", "ipv4":"-", "ipv6":"-", "tarjeta":"-", "essid":"-", "canal":0, "frecuencia":0, "existe":0}
# diccionarios de relación frecuencias-canales
banda24 = {1:2412, 2:2417, 3:2422, 4:2427, 5:2432, 6:2437, 7:2442, 8:2447, 9:2452, 10:2457, 11:2462, 12:2467, 13:2472, 14:2484}
banda24_inv = {2412:1, 2417:2, 2422:3, 2427:4, 2432:5, 2437:6, 2442:7, 2447:8, 2452:9, 2457:10, 2462:11, 2467:12, 2472:13, 2484:14}
banda5 = {34:5170, 36:5180, 38:5190, 40:5200, 42:5210, 44:5220, 46:5230, 48:5240, 52:5260, 56:5280, 60:5300, 64:5320, 149:5745, 153:5765, 157:5785, 161:5805}
banda5_inv= {5170:34, 5180:36, 5190:38, 5200:40, 5210:42, 5220:44, 5230:46, 5240:48, 5260:52, 5280:56, 5300:60, 5320:64, 5745:149, 5765:153, 5785:157, 5805:161}
# longitudes maximas y minimas de contraseñas
wpa_max_long = 63
wpa_min_long = 8
wpa2_max_long = 63
wpa2_min_long = 8
wep_max_long = 58
wep_min_long = 4
# contiene el listado de redes dentro del alcance
lista_redes = {}
# expresion regular para obtener la MAC
mac_reg = re.compile('(?:[0-9a-fA-F]:?){12}')
# si debug=True, se muestran mensajes de error extendidos.
# este valor es modificado por los parámentos de CLI
debug = False

if (__name__ == "__main__"): main(sys.argv[1:])
