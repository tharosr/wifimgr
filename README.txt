Wifi Manager 0.22rc

Este programa es un gestor de redes inalámbricas para consola.
El objetivo del programa es gestionar de forma rápida y simple la conexión inalámbrica desde la consola, a la vez que es mi primer programa en Python,
y se me ocurrió automatizar ese "tedioso" proceso y darlo a conocer para que otros lo puedan usar si quieren, o puedan aprender las cosas mas básicas
de Python con un programa operativo y real y darse cuenta que Python no son todo clases.

Tiene soporte para múltiples tarjetas de red inalámbricas y función de autoconexión.

El soporte para IPv4 es completo. Para IPv6, no está completo el soporte.

Tiene cosas que cambiar y mejorar, sin embargo, cumple su función. Estoy trabajando en una GUI muy simple con TKinter para poder realizar las mismas
gestiones desde el entorno gráfico.

Sugerencias sobre mejoras, nuevas funciones, bugs y comentarios, buscarme en tuiter como @juliorollan. Agradecería que no se modifique el programa para
distribuir.

Y si, lo hice todo en español. Si alguien quiere pasar traducciones, no sea trolo y póngase en contacto. Yo paso de ponerme a traducir.

Podes decargarlo desde: https://github.com/tharosr/wifimgr


REQUERIMIENTOS

    Python >= 3.5.3
    Módulos de Python (no incluidos):
    	colorama
    	subprocess
    	getpass
    	re
    	time
    	sys
    	getopt
    Otros módulos (incluidos):
    	titulo_aplicacion
    	formatear_salida

    Software del sistema:
    	iwconfig (wireless-tools)
    	iwlist (wireless-tools)
    	ifconfig (net-tools)
    	dhclient
    	wpa_supplicant
    	rfkill
    	systemctl (para sistemas debian)
    	ip (iproute2)
    	ping (iputils-161105)
    	killall (psmisc)

    Y obvio que un adaptador inalámbrico.

    Nota: no se adjuntan posibles dependencias del software del sistema, pero te imaginarás que un compilador de C y algunas librerías necesitarás.

INSTALACIÓN

    No requiere instalación.
    Si no tenés los paquetes instalados, te avisará la aplicación. Los programas van adjuntos porque se supone que tal vez no tengas conexión.
    Igual se pueden descargar desde los repositorios de tu distribución o desde la página del desarrollador

USO

    Para ejecutar esta aplicación son necesarios permisos de root. Si tu usuario no es root, habla con el administrador. Si vos sos el administrador,
    podes usar el archivo sudoers para darle al usuario permisos de root para wifimgr.py. Indirectamente, los programas como ifconfig y demás
    heredarán esos permisos.

    Para ejecutarlo: ./wifimgr.py

    Hay una forma mas práctica y es creando un enlace blanco. Hay un archivo que se llama wifimgr.sh y es un simple lanzador. Ese archivo, tiene una
    variable llamada ruta. Esa variable debe contener la ruta completa al archivo wifimgr.py, por ejemplo:

    	ruta="/home/<usuario>/Documentos/apps/"

    Después:

    	ln -s /home/<usuario>/Documentos/apps/wifimgr.sh /usr/bin/wifimgr

    Con esto, podrás ejecutar el programa desde cualquier directorio, como un comando, vamos.

OPCIONES

    -a, --autoconectar
    	Sirve para establecer si la autoconexión se activa o no. Por defecto, viene activada y se puede modificar en config.ini.
    	Sus valores pueden ser true o false.
    -h
    	Muestra una brevísima ayuda.

NOTAS

    Se han detectado incompatibilidades y comportamientos extraños cuando network-manager está instalado. Si no se desea desinstalar, se puede
    deshabilitar network-manager y evitar que sea cargado al inicio.

    Es posible que en determinadas circunstancias la aplicación salga inesperadamente. A veces puede pasar que la tipografía de la aplicación no
    sea reseteada. Para corregir eso:

    	./colorama_reset_emergencia.py

    No modifica ningún archivo del sistema. El único archivo que modifica es /etc/wpa_supplicant/wpa_supplicant.conf para actualizar las  redes.

    Si en tu distribución recibis un mensaje de error que dice que falta algún programa, agradecería mucho que te pongas en contacto.
    Siguientes pasos: el primer paso es pulir esta aplicación y el segundo paso es terminar la GUI.

    Si queres contribuir económicamente, contactame para detalles.

MAS INFORMACIÓN

    archivo: config.ini

AUTOR

    Julio Rollan - en tuiter: @juliorollan



