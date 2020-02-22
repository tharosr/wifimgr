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
    """ Esta funcion verifica que estén todos los programas. Son programas estándar, por lo que no deberían no estar.
    
    """
    global AUTOCONECTAR
    global supplicant_conf
    print("Verificando aplicaciones necesarias...", end="")
    sys.stdout.flush()
    sleep (1)
    cant_ausentes = 0
    for item in lista_apps:
        try:
            tmp = sp.run(['which', item], stdout = sp.PIPE, stderr = sp.PIPE)
        except:
            print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
            return -1
        if (tmp.returncode != 0): 
            cant_ausentes += 1
            
    if (cant_ausentes != 0):
        print(Fore.RED + " error" + Fore.WHITE)
        return -2
    print(Fore.GREEN + " ok" + Fore.WHITE)    
    return 0

def cargar_configuracion(argv):
    """ Carga la configuración de config.ini y lee los parámetros de la línea de comandos.
    Luego actualiza las variables leídas del config en función de los parámetros pasados por línea de comandos, que tienen prioridad.
    
    Básicamente, en este momento, el único modificador válido es -a (o --autoconectar), que puede ser true o false.
    """
    global AUTOCONECTAR
    global AUTOCONECTAR_PRIORIDAD
    
    print("Cargando configuración...", end="")
    sys.stdout.flush()
    sleep(1)
    
    try: 
        opts, args = getopt.getopt(argv,"ha:",["help", "autoconectar="])
        
        for opt, arg in opts:
            if opt == '-h':
                print ('Modo de uso:\n\n\twifimgr.py [-a (true/false)]\n\nOpciones:\n\n-a, --autoconectar\tIndica si usar o no la función de autoconectar omitiendo la configuración.\n\t\t\tSi es true, se usará la autoconexión para cualquier red ya configurada dentro del\n\t\t\talcance. Si es false, no se usará la autoconexión.')
                salir()
            elif opt == '-a':
                if (arg.capitalize() != "True") and (arg.capitalize() != "False"):
                     print(Fore.RED + " error" + Fore.WHITE)
                     print ('Modo de uso:\n\n\twifimgr.py [-a (true/false)]\n\nOpciones:\n\n-a, --autoconectar\tIndica si usar o no la función de autoconectar omitiendo la configuración.\n\t\t\tSi es true, se usará la autoconexión para cualquier red ya configurada dentro del\n\t\t\talcance. Si es false, no se usará la autoconexión.')
                     salir()
                AUTOCONECTAR_PRIORIDAD = arg.capitalize()
    except getopt.GetoptError:
        print(Fore.RED + " error" + Fore.WHITE)
        print ('wifimgr.py [-a (true/false)]')
        salir()
    
    
    
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
                elif (parametro == "supplicant_conf"):
                    supplicant_conf = valor.strip()
    fp.close()
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


def buscar_tarjetas_red():
    """ Busca las tarjetas de red inalámbricas en el sistema
    """
    global tarjetas_disponibles
    global indice_tarjetas
    global info_red
    
    try: tmp = sp.run(['iwconfig'], stdout = sp.PIPE, stderr = sp.PIPE)
    except: return -1
    
    if (tmp.returncode != 0): return -2
    
    salida = tmp.stdout.decode().split("\n")
 
    for linea in salida:
        if ("ESSID" in linea):
            tarjeta = linea.split()[0]
            if (tarjeta not in tarjetas_disponibles):
                tarjetas_disponibles.append(tarjeta)
            
    if (len(tarjetas_disponibles) > 1):
        indice_tarjetas = []
        contador = 1
        for tarjeta in tarjetas_disponibles:
            indice_tarjetas.append(contador)
            contador += 1
    elif (len(tarjetas_disponibles) == 1): info_red['tarjeta'] = tarjetas_disponibles[0]
    else: return -3
    return 0

def mostrar_tarjetas_red():
    """ Muestra las tarjetas de red disponibles, en caso de que haya mas de una
    """
    if (len(tarjetas_disponibles) > 1):
        contador = 1
        for tarjeta in tarjetas_disponibles:
            print("\t" + str(contador) + ". " + tarjeta)
            contador += 1
        print()

        que_tarjeta_usar = 0
        while (que_tarjeta_usar not in indice_tarjetas):
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
    
    sleep (1)
    global info_red
    salida = ""
    tmp = ""

    if (__name__ == "__main__"):
        estado_funcion = -1000
        estado_funcion = buscar_tarjetas_red()
        if (estado_funcion != 0):
            print(Fore.RED + "Error buscando las tarjetas de red (" + str(estado_funcion) + ")" + Fore.WHITE)
            salir()

        mostrar_tarjetas_red()
        
    try: tmp = sp.run(['iwconfig', info_red['tarjeta']], stdout = sp.PIPE, stderr = sp.PIPE)
    except:
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        return -1

    if (tmp.returncode != 0):
        print(Fore.RED + " error" + Fore.WHITE)
        return -2

    # solo son utiles las dos primeras lineas
    salida = tmp.stdout.decode().split("\n")

    linea1 = salida[0].split()
    linea2 = salida[1]

    mac_reg = re.compile('(?:[0-9a-fA-F]:?){12}')
    essid = "-"
    ap = "-"
    frecuencia = 0
    canal = 0
    ipv4 = "-"
    ipv6 = "-"
    subred = "-"
    broadcast = "-"
    mac = "-"

    for item in linea1:
        if ("ESSID" in item):
            essid = salida[0].split(":")[1].replace("\"", "")
            if (len(essid) == 0) or (essid == "off/any"): essid = "-"


    if (essid != "-"):
        if ("Frequency" in linea2):
            frecuencia = float(linea2.split("Frequency:")[1].split()[0])
            if (banda24_inv.get(frecuencia*1000, 0) == 0): canal = int(banda5_inv[frecuencia*1000])
            else: canal = int(banda24_inv[frecuencia*1000])

        if ("Not-Associated" in linea2): ap = "-"
        else:

            ap = re.findall(mac_reg, linea2)
            ap = ap[0]

    try: tmp = sp.run(['ifconfig', info_red['tarjeta']], stdout = sp.PIPE, stderr = sp.PIPE)
    except:
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        return -3

    if (tmp.returncode != 0):
        print(Fore.RED + " error" + Fore.WHITE)
        return -4

    salida = tmp.stdout.decode().split("\n")

    for item in salida:
        if ("inet" in item) and ("netmask" in item):
            linea = item.split()
            ipv4 = linea[1]
            subred = linea[3]
            broadcast = linea[5]
        if ("inet6" in item):
            linea = item.split()
            ipv6 = linea[1]
        if ("ether" in item):
            linea = item.split()
            mac = linea[1]

    info_red['ap'] = ap
    info_red['essid'] = essid
    info_red['frecuencia'] = frecuencia
    info_red['canal'] = canal
    info_red['ipv4'] = ipv4
    info_red['ipv6'] = ipv6
    info_red['subred'] = subred
    info_red['broadcast'] = broadcast
    info_red['mac'] = mac

    print(Fore.GREEN + " ok" + Fore.WHITE)
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
    sleep (1)

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
    
def activar_tarjeta():
    """ activa la tarjeta de red 
    """
    
    print("Activando la tarjeta de red...", end="")
    sys.stdout.flush()
    sleep (1)
    
    desconectar()
    desasociar()
    
    try: tmp = sp.run(['ifconfig', info_red['tarjeta'], 'down'], stdout = sp.PIPE, stderr = sp.PIPE)
    except:
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        return -1
    
    if (tmp.returncode != 0):
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        return -2
    
    try: tmp = sp.run(['ifconfig', info_red['tarjeta'], 'up'], stdout = sp.PIPE, stderr = sp.PIPE)
    except:
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        return -3

    if (tmp.returncode != 0):
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        return -4
    
    print(Fore.GREEN + " ok" + Fore.WHITE)
    return 0

def escanear_redes():
    """ escanea las redes inalámbricas dentro del alcance
    
    """

    print(Fore.WHITE + "Escaneando las redes...", end="")
    sys.stdout.flush()
    
    sleep (1)
    global lista_redes

    try: tmp = sp.run(['ifconfig', info_red['tarjeta'], 'down'], stdout = sp.PIPE, stderr = sp.PIPE)
    except: print(str(tmp.returncode) + ": " + tmp.stderr.decode())
    
    try: tmp = sp.run(['ifconfig', info_red['tarjeta'], 'up'], stdout = sp.PIPE, stderr = sp.PIPE)
    except: print(str(tmp.returncode) + ": " + tmp.stderr.decode())

    try: tmp = sp.run(['iwlist', info_red['tarjeta'], 'scan'], stdout = sp.PIPE, stderr = sp.PIPE)
    except:
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        return -1

    if (tmp.returncode != 0):
        print(Fore.RED + " error (" + str(tmp.returncode) + ")" + Fore.WHITE)
        print(str(tmp.returncode) + ": " + tmp.stderr.decode())
        return -2
    resultado = tmp.stdout.decode().split("Cell")

    campos_a_buscar = ("Address", "Channel:", "Frequency", "Encryption", "ESSID", "WPA2", "WPA", "WEP")

    mac = ""
    canal = 0
    frecuencia = 0
    cifrado = "no"
    essid = ""
    wpa2 = 0
    wpa = 0
    wep = 0
    indice = 1
    
    for elemento in resultado:
        lineas = elemento.split("\n")
        for item in lineas:
            if (item.find("Address") != -1): mac = item.split()[3]
            if (item.find("Channel:") != -1): canal = item.split(":")[1]
            if (item.find("Frequency:") != -1): frecuencia = item.split(":")[1].split()[0]
            if (item.find("Encryption") != -1): cifrado = item.split(":")[1]
            if (item.find("ESSID") != -1): essid = item.split("\"")[1]
            if (cifrado == "on"):
                if (item.find("WPA2") != -1): wpa2 = 1
                if (item.find("WPA") != -1): wpa = 1
                if (item.find("WEP") != -1): wep = 1

        if (canal != 0):
            lista_redes[indice] = {"essid":essid, "mac":mac, "frecuencia":frecuencia, "canal":canal, "cifrado":cifrado, "wpa2":wpa2, "wpa":wpa, "wep":wep, "existe":0}            
            indice += 1
        mac = ""
        canal = 0
        frecuencia = 0
        cifrado = "no"
        essid = ""
        wpa2 = 0
        wpa = 0
        wep = 0

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
            if (lista_redes[item]['cifrado'] == "on"):
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
    
def verificar_asociacion(conectar_a, psk=""):
    """ Verifica la asociación al AP sin realizar cambios en archivos de configuración
    conectar_a es el id del diccionario lista_redes
    psk es la clave o contraseña.
    
    Devuelve cero si la asociación fue correcta, un número negativo si no.
    """
    
    comando = ""
    archivo_tmp = os.getcwd() + "/" + "wpa_supp_tmp.conf"
    salida_psk = ""
    es_nueva_red = True
    hay_que_actualizar = False

    # la red existe y es el primer intento de asociación
    if (lista_redes[conectar_a]['existe'] == 1) and (psk == ""):
        es_nueva_red = False
        hay_que_actualizar = False
    # la red existe y se cambio la contraseña
    if (lista_redes[conectar_a]['existe'] == 1) and (psk != ""):
        es_nueva_red = False
        hay_que_actualizar = True

    if (not es_nueva_red):
        
        if (not hay_que_actualizar):
            indice = -1
            for indice in range(len(AUTOCONECTAR_redes_dc)):
                if (AUTOCONECTAR_redes_dc[indice]['essid'] == lista_redes[conectar_a]['essid']):
                    psk = AUTOCONECTAR_redes_dc[indice]['clave']
                    indice = conectar_a
                    break
    
            if (indice == -1):
                print(Fore.RED + "No se ha podido verificar la red existente" + Fore.WHITE)
                return -4
        elif (hay_que_actualizar):
            for indice in range(len(AUTOCONECTAR_redes_dc)):
                if (AUTOCONECTAR_redes_dc[indice]['essid'] == lista_redes[conectar_a]['essid']):
                    AUTOCONECTAR_redes_dc[indice]['clave'] = str(psk)
                    AUTOCONECTAR_redes_dc[indice]['psk'] = ""
                    break
        
    salida_psk = wpa_string(conectar_a, psk)

    try: fp = open(archivo_tmp, "w")
    except: return -5

    try: fp.write(salida_psk)
    except:
        fp.close()
        return -6
    fp.close()

    desconectar()
    desasociar()
    
    # intentar asociación
    # en este caso se usa Popen para poder leer la salida del comando en tiempo real
    try: comando = sp.Popen('wpa_supplicant -i ' + info_red['tarjeta'] + ' -D nl80211,wext,roboswitch,bsd,ndis -c' + archivo_tmp, stderr = sp.PIPE, stdout = sp.PIPE, shell = True)
    except:return -7
    
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

def selector_red():
    """ Muestra el selector de red
    
    No recibe ningún parámetro.
    Devuelve un entero mayor a cero si es correcta la selección, o -1 si se canceló
    """
    conectar_a = ""
    while (conectar_a not in lista_redes):
        conectar_a = input("A qué red te queres conectar? [c para cancelar]: ")
        if (conectar_a.isnumeric()): conectar_a = int(conectar_a)
        else:
            if (conectar_a.upper() == "C"): return -1
            else: conectar_a = 0
    return conectar_a

def conectar():
    
    conectar_a = 0
    password = ""
    hay_que_actualizar = False
    
    
    hay_disponibles_redes_existentes = False
    for red in lista_redes:
        if (lista_redes[red]['existe'] == 1):
            hay_disponibles_redes_existentes = True
            break
    
    estado_funcion = -1000
    contador_error = 0
    while True:

        conectar_a = selector_red()
        if (conectar_a == -1): return -1
        
        # si la red no existe, o estado_funcion != -1000 (error en el password probablemente)
        if (lista_redes[conectar_a]['existe'] == 0) or (estado_funcion != -1000):
            password = pedir_password()
            hay_que_actualizar = True
            # si la red ya fue configurada pero no se asocia con los datos guardados, actualizar conf de supplicant
            if (lista_redes[conectar_a]['existe'] == 1) and (estado_funcion != -1000): hay_que_actualizar = True
            
        # si la red existe y todavía no se intentó asociar, buscar info en conf de supplicant (AUTOCONECTAR_redes_dc)
        elif (lista_redes[conectar_a]['existe'] == 1) and (estado_funcion == -1000):
            for red in AUTOCONECTAR_redes_dc:
                if (red['essid'] == lista_redes[conectar_a]['essid']): password = red['clave']

        # intentar conexion para verificar la clave
        print("Intentando asociar a " + str(lista_redes[conectar_a]['essid']) + "...", end="")
        sys.stdout.flush()
        sleep(1)
            
        estado_funcion = -1000
        estado_funcion = verificar_asociacion(conectar_a, password)
        
        # conexión correcta
        if (estado_funcion == 0): 
            print(Fore.GREEN + " ok" + Fore.WHITE)
            break
        
        # contraseña incorrecta (supplicant lo intenta 3 veces.
        # aca lo intentamos otras 4, por lo que son 12 intentos
        elif (estado_funcion == -8):
            print(Fore.YELLOW + " Contraseña incorrecta (" + str(password) + ")" + Fore.WHITE)
            contador_error += 1
        elif (estado_funcion == -9):
            print(Fore.YELLOW + " Contraseña incorrecta (" + str(password) + ")" + Fore.WHITE)
            contador = 4
        # otro error que no es contraseña incorrecta
        else:
            print(Fore.YELLOW + " Error " + str(estado_funcion) + Fore.WHITE)
            contador_error += 1

        if (contador_error == 4): break


    # si el intento de asociación fue exitoso:
    #    - si es una nueva red, agregarla a conf de supplicant
    #    - si es una red existente sin cambio de contraseña, no hacer nada y mantener la conexión actual
    #    - si es una red existente con cambio de contraseña, actualizar conf de supplicant
    # Si no fue exitoso, salir
    if (estado_funcion == 0) and (hay_que_actualizar):
        estado_funcion = -1000
        estado_funcion = configurar_supplicant(conectar_a, password)
        if (estado_funcion == 0):
            print(Fore.GREEN + " ok" + Fore.WHITE)
            return 0
        else:
            print(Fore.RED + "No se pudo configurar WPA Supplicant (" + str(estado_funcion) + ")" + Fore.WHITE)
            salir()
    elif (estado_funcion == 0) and (not hay_que_actualizar):
        print(Fore.GREEN + " ok" + Fore.WHITE)
        return 0
    else:
        print(Fore.RED + " error: " + str(estado_funcion) + Fore.WHITE)
        return -2
   

    return 0

def wpa_string(conectar_a, password):
    """ Ejecuta la funcion wpa_passphrase y devuelve el string generado, o un entero negativo en caso de error
    En caso de que no se use WPA/2, y sea WEP, abierta u oculta, devuelve el string correspondiente
    """
    salida = ""
    
    # wpa/wpa2
    if (lista_redes[conectar_a]['wpa'] == 1) or (lista_redes[conectar_a]['wpa2'] == 1):
    
        try: tmp = sp.run(['wpa_passphrase', str(lista_redes[conectar_a]['essid']), str(password)], stdout = sp.PIPE, stderr = sp.PIPE)
        except: return -1
        
        if (tmp.returncode != 0): return -tmp.returncode
        
        salida = tmp.stdout.decode()
    
    # wep
    elif (lista_redes[conectar_a]['wpa'] == 0) and (lista_redes[conectar_a]['wpa2'] == 0) and (lista_redes[conectar_a]['wep'] == 1):
        
        salida = "network={\n\t"
        salida += "ssid=\"" + lista_redes[conectar_a]['essid'] + "\"\n\t"
        salida += "key_mgmt=NONE\n\t"
        salida += "wep_key0=\"" + str(password) + "\"\n\t"
        salida += "#wep_key0=\"" + str(password) + "\"\n\t"
        salida += "wep_tx_keyidx=0\n"
        salida += "}"
    
    # abierta
    elif (lista_redes[conectar_a]['wpa'] == 0) and (lista_redes[conectar_a]['wpa2'] == 0) and (lista_redes[conectar_a]['wep'] == 0):
        
        salida = "network={\n\t"
        salida += "ssid=\"" + lista_redes[conectar_a]['essid'] + "\"\n\t"
        salida += "key_mgmt=NONE\n\t"
        salida += "priority=100\n"
        salida += "}"
        
    # oculta
    elif (lista_redes[conectar_a]['essid'] == "*oculta"):
        
        salida = "network={\n\t"
        salida += "ssid=\"" + lista_redes[conectar_a]['essid'] + "\"\n\t"
        salida += "scan_ssid=1\n\t"
        salida += "psk=\"" + str(password) + "\"\n\t"
        salida += "#psk=\"" + str(password) + "\"\n"
        salida += "}"
        
    if (len(salida) == 0): return -3
    return salida + "\n"

def configurar_supplicant(conectar_a=0, password=""):
    """ Configura el archivo wpa_supplicant.conf para agregar la red
    
    Si password es una cadena de longitud 0, no hay que hacer nada porque es una red ya configurada y operativa
    Si password no es una cadena de longitud 0, hay que ver si hay que actualizar una red existente o crear una nueva
    """
    print("Configurando WPA Supplicant...", end="")
    sys.stdout.flush()
    sleep(1)
    
    if (conectar_a == 0):
        print(Fore.RED + " error: no seas trolo man, decime a qué red te queres conectar")
        return -1
    
    actualizar = False
    for red in AUTOCONECTAR_redes_dc:
        if (red['essid'] == lista_redes[conectar_a]['essid']): actualizar = True
        
    
    
    salida = wpa_string(conectar_a, password)
    if (not isinstance(salida, str)):
        print(Fore.RED + " error: " + str(salida) + Fore.WHITE)
        return -2


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
    sleep(1)
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
    sleep(1)
    # parsear wpa_supplicant.conf
    try:
        fp = open(supplicant_conf, "r")
    except:
        print(Fore.YELLOW + " se omite" + Fore.WHITE)
    else:
        
        contador = 0
        contador_items = 0
        essid = ""
        clave = ""
        psk = ""
        aux = {'essid':essid, 'clave':clave, 'psk':psk}
        while True:
            linea = fp.readline()
            
            if (not linea): break
            else:
                
                linea = linea.strip()
                if ("ssid" in linea) and (contador == 0): 
                    essid = linea.strip().split("\"")[1]
                    aux['essid'] = essid
                    AUTOCONECTAR_redes.append(essid)
                    contador += 1
                    
                if ("#psk" in linea) and (contador == 1): 
                    clave = linea.strip().split("\"")[1]
                    aux['clave'] = clave
                    contador += 1
                    
                if ("psk" in linea) and ("#" not in linea) and (contador == 2):
                    psk = linea.strip().split("=")[1]
                    aux['psk'] = psk
                    AUTOCONECTAR_redes_dc.append(aux)
                    contador = 0
                    essid = ""
                    clave = ""
                    psk = ""
                    aux = {'essid':essid, 'clave':clave, 'psk':psk}

        fp.close()
        
        if (len(AUTOCONECTAR_redes) == 0):
            print(Fore.GREEN + " 0 encontradas" + Fore.WHITE)
            AUTOCONECTAR = False
        else: print(Fore.GREEN + " " + str(len(AUTOCONECTAR_redes)) + " encontradas" + Fore.WHITE)

    return 0
    
    

def autoconectar():
    """ Esta función intenta autoconectarse a alguna red disponible dentro del alcance y la cual ya se encuentre configurada
    Esta función hay que afinarla para que, en caso de no poder conectarse a una red ya configurada, intente con las siguientes
    
    Si no se han encontrado redes ya configuradas, AUTOCONECTAR = False y pasa a conexión manual
    """
    global AUTOCONECTAR
    
    print("Intentando autoconexión...", end="")
    sys.stdout.flush()
    sleep(1)
    
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
        print(Fore.RED + " error lanzando supplicant" + Fore.WHITE)
        return -6
    
    if (tmp.returncode != 0):
        print(Fore.RED + " Error iniciando supplicant (error: " + str(tmp.returncode) + ")" + Fore.WHITE)
        return -7
    
    obtener_ip()
    
    informacion_tarjeta_red()
    
    mostrar_info_tarjeta_red()
    
    verificar_conexion()
    return 0
#    salir()
    
def verificar_conexion():
    """ Verifica que la conexión a la red es correcta.
    Ejecuta el comando ping al router.
    No garantiza la conexión a internet, ya que depende de otros factores que están fuera del alcance.
    """
    print("Verificando la conexión...", end="")
    sys.stdout.flush()
    sleep(1)

    
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
            retun -5
        else: 
            print(Fore.RED + " error" + Fore.WHITE) 
            retun -5
    

def salir():
    print(Style.RESET_ALL + Back.RESET + Fore.RESET)
    print()
    quit()
    



def main(argv):
    
    encabezado.setTituloAplicacion("WiFi Manager 0.21b por @juliorollan")
    encabezado.mostrarTitulo()
    
    # código de salida de la función llamada
    estado_funcion = -1000
    
    # obtener y mostrar la info del usuario
    estado_funcion = informacion_usuario()
    if (estado_funcion != 0):
        print(Fore.RED + "No se ha podido obtener la información del usuario" + Fore.WHITE)
        salir()
    mostrar_info_usuario()
    print()
    
    # verificar que los comandos necesarios están disponibles
    estado_funcion = -1000
    estado_funcion = verificacion()
    if (estado_funcion != 0):
        if (estado_funcion == -1):
            print(Fore.RED + "Ocurrió un error inesperado realizando las verificaciones de programas necesarios: " + str(estado_funcion) + Fore.WHITE)
            salir()
        elif (estado_funcion == -2):
            print(Fore.YELLOW + "No se han encontrado algunos programas necesarios: " + str(estado_funcion) + Fore.WHITE)
            if (info_usuario['id'] != 0):
                print("Parece que tu usuario no tiene privilegios de root. Este programa necesita privilegios de root para poder funcionar.\nHabla con el administrador del sistema")
            print()
            print("Estos son los programas necesarios:")    
            print()
            salida = ""
            for app in lista_apps: salida += app + ", "
            print("\t" + salida[0:len(salida)-2])
            salir()
    
    # cargar la configuracion y leer los parámetros de línea de comandos
    estado_funcion = -1000
    estado_funcion = cargar_configuracion(argv)
    if (estado_funcion != 0):
        print(Fore.RED + "No se pudo cargar la configuración. Error " + str(estado_funcion) + "." + Fore.WHITE)
        salir()
        
    # obtener la información de la tarjeta de red y de la conexión
    estado_funcion = -1000
    estado_funcion = informacion_tarjeta_red()
    if (estado_funcion != 0):
        print(Fore.RED + "Ha ocurrido un error (" + str(estado_funcion) + ") obteniendo la información de la tarjeta de red." + Fore.WHITE)
        print()
        if (estado_funcion == -3): print("Asegurate que existe una tarjeta de red inalámbrica, que está instalada y funciona.")
        salir()
    mostrar_info_tarjeta_red()

    # cargar las redes previamente configuradas
    # en caso de que devuelva un error, ignorarlo
    estado_funcion = -1000
    estado_funcion = autoconectar_redes()

    
    estado_funcion = -1000
    estado_funcion = autoconectar()
    if (estado_funcion == 0):
        print()
        salir()
        
    
    # activar la tarjeta de red
    estado_funcion = -1000
    estado_funcion = activar_tarjeta()
    if (estado_funcion != 0):
        print(Fore.RED + "No se ha podido activar la tarjeta '" + info_red['tarjeta'] + "' (" + str(estado_funcion) + ")" + Fore.WHITE)
        salir()
    
    
    # escanear redes
    estado_funcion = -1000
    estado_funcion = escanear_redes()
    if (estado_funcion != 0):
        print()
        print(Fore.RED + "No se ha podido escanear las redes: " + str(estado_funcion) + Fore.WHITE)
        print()
        print()
        salir()

    # mostrar redes
    estado_funcion = -1000
    estado_funcion = mostrar_redes()
    if (estado_funcion != 0):
        print()
        print(Fore.RED + "No se pueden mostrar las redes (" + str(estado_funcion) + ")" + Fore.WHITE)
        print() 
        print()
        salir()
    
    # conectar a la red
    estado_funcion = -1000
    estado_funcion = conectar()
    if (estado_funcion != 0):
        print()
        if (estado_funcion == -1): print(Fore.YELLOW + "Proceso cancelado por el usuario" + Fore.WHITE)
    #    elif (estado_funcion == -2): print(Fore.YELLOW + "La opción de conectarse a una red sin cifrar no está disponible aún" + Fore.WHITE)
    #    elif (estado_funcion == -3): print(Fore.YELLOW + "La opción de conectarse a una red con cifrado WEP no está disponible aún" + Fore.WHITE)
        else: print(Fore.RED + "No se ha podido conectar a la red (" + str(estado_funcion) + ")" + Fore.WHITE)
        salir()
    
    # obtener ip
    estado_funcion = -1000
    estado_funcion = obtener_ip()
    if (estado_funcion != 0):
        print()
        print(Fore.RED + "No se ha podido obtener una dirección IP dinámica (" + str(estado_funcion) + ")" + Fore.WHITE)
        salir()
    
    # mostrar info actualizada de la tarjeta de red
    estado_funcion = -1000
    estado_funcion = informacion_tarjeta_red()
    if (estado_funcion != 0):
        print(Fore.RED + "Ha ocurrido un error (" + str(estado_funcion) + ") obteniendo la información de la tarjeta de red." + Fore.WHITE)
        print()
        if (estado_funcion == -3): print("Asegurate que existe una tarjeta de red inalámbrica, que está instalada y funciona.")
        salir()
    mostrar_info_tarjeta_red()
        
    # verificar la conexion
    estado_funcion = -1000
    estado_funcion = verificar_conexion()
    if (estado_funcion < 0) and (estado_funcion < -4):
        print(Fore.RED + "No se ha podido verificar la conexión." + Fore.YELLOW + " Eso no significa que no esté operativa." + Fore.WHITE)
    else:
        print(Fore.GREEN + "Se ha conectado correctamente a la red" + Fore.WHITE)
    
    
    
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
lista_apps = ['ifconfig', 'iwconfig', 'iwlist', 'dhclient', 'wpa_supplicant', 'rfkill', 'systemctl', 'ip', 'ping', 'killall']
# contiene la información del usuario
info_usuario = {}

# tarjetas de red disponibles en el sistema
tarjetas_disponibles = []
indice_tarjetas = []

# contiene la información actual de la red
info_red = {}
info_red = {"ap":"-", "mac":"-", "ipv4":"-", "ipv6":"-", "tarjeta":"-", "red":"-", "essid":"-", "canal":0, "subred":"-", "broadcast":"-", "frecuencia":0}
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

if (__name__ == "__main__"): main(sys.argv[1:])
