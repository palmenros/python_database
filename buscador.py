import sys
import os
import unicodedata
import pickle
import math

# -----------------------------------
# Indices
# -----------------------------------

# Estructura:
# string: List[int]
# clave: [i1, i2, ..., in] donde cada i es un indice para la lista de tuplas entradas
indice_titulos = {}
indice_directores = {}

# Misma estructura que los otros indices, pero la clave es unicamente una palabra de la descripcion
# Hay una entrada por cada palabra de la descripcion de la pelicula
indice_descripciones = {}

# -----------------------------------
# Entradas
# -----------------------------------

# Estructura:
# Cada elemento de la lista es de la forma
# (id_unico, nombre, anyo_publicacion, director, tipo, ruta_bbdd)
# Todos los elementos de la tupla son strings
entradas = []

# -----------------------------------
# Funciones de indexado
# -----------------------------------

def generar_indices(ruta):
    encontrada_base_datos = False

    for subdir, dirs, files in os.walk(ruta):
        for file in files:
            if file.endswith('.tsv'):
                indexar_fichero(subdir + '/' + file, indice_titulos, indice_directores, indice_descripciones, entradas)
                encontrada_base_datos = True

    if not encontrada_base_datos:
        print("Error: no se ha encontrado ninguna base de datos")
        exit(1)
    else:
        guardar_indices(ruta)


def indexar_directorio(ruta):
    if not os.path.isdir(ruta):
        print("Error: la ruta introducida no es valida")
        exit(1)

    if existen_indices_precomputados(ruta):
        cargar_indices(ruta)
    else:
        generar_indices(ruta)
        guardar_indices(ruta)


def guardar_indices(ruta):
    ruta_indices = ruta + '/' + '__index'

    # Si la carpeta de indices no existe, la generamos
    if not os.path.isdir(ruta_indices):
        try:
            os.mkdir(ruta_indices)
        except OSError as error:
            print('Error, no se pudieron guardar los indices: {}'.format(error))

    with open(ruta_indices + '/indice_titulos.bin', 'wb') as archivo:
        pickle.dump(indice_titulos, archivo)

    with open(ruta_indices + '/indice_directores.bin', 'wb') as archivo:
        pickle.dump(indice_directores, archivo)

    with open(ruta_indices + '/indice_descripciones.bin', 'wb') as archivo:
        pickle.dump(indice_descripciones, archivo)

    with open(ruta_indices + '/entradas.bin', 'wb') as archivo:
        pickle.dump(entradas, archivo)


def cargar_indices(ruta):
    global indice_titulos
    global indice_directores
    global indice_descripciones
    global entradas

    print('Cargando los índices desde disco.')

    ruta_indices = ruta + '/' + '__index'

    with open(ruta_indices + '/indice_titulos.bin', 'rb') as archivo:
        indice_titulos = pickle.load(archivo)

    with open(ruta_indices + '/indice_directores.bin', 'rb') as archivo:
        indice_directores = pickle.load(archivo)

    with open(ruta_indices + '/indice_descripciones.bin', 'rb') as archivo:
        indice_descripciones = pickle.load(archivo)

    with open(ruta_indices + '/entradas.bin', 'rb') as archivo:
        entradas = pickle.load(archivo)


def existen_indices_precomputados(ruta):
    if not os.path.isdir(ruta + '/' + '__index'):
        return False

    carpeta_indices = os.scandir(ruta + '/' + '__index')
    file_names = set()

    for e in carpeta_indices:
        if e.is_file():
            file_names.add(e.name)

    archivos_necesarios = [
        'indice_titulos.bin',
        'indice_directores.bin',
        'indice_descripciones.bin',
        'entradas.bin'
    ]

    for archivo in archivos_necesarios:
        if archivo not in file_names:
            return False

    return True


def indexar_fichero(ruta_fichero, ind_titulos, ind_directores, ind_descripciones, entradasbd):
    with open(ruta_fichero, 'r') as f:
        for linea in f:
            linea = linea.rstrip('\n')

            # Extraer datos de la linea
            id,titulo,anyo,director,tipo,descripcion = linea.split('\t')

            # Agregar datos a la lista de tuplas
            posicion = len(entradas)
            entradasbd.append((id, titulo, anyo, director, tipo, ruta_fichero))

            # Actualizar indices
            anyadir_basico(titulo, ind_titulos, posicion)
            anyadir_basico(director, ind_directores, posicion)
            anyadir_descripcion(descripcion, ind_descripciones, posicion)


def anyadir_basico(clave, indice, posicion):
    preproc = preprocesar(clave)
    if preproc not in indice:
        indice[preproc] = []
    indice[preproc].append(posicion)


def anyadir_descripcion(desc, indice, posicion):
    # Diccionario que guarda las palabras de la descripcion
    # ya agregadas al indice
    anyadidas = {}

    # Iteramos sobre las palabras de la descripcion
    for palabra in extrae_palabras(desc):
        preproc = preprocesar(palabra)

        # Si no se ha agregado al indice la palabra:
        if preproc not in anyadidas:
            # Se marca como agregada al indice
            anyadidas[preproc] = True

            # Si el indice no contiene la palabra porque no se ha
            # indexado ninguna descripcion que la contenga:
            # Agregamos una entrada al indice cuya clave es una lista vacia
            if preproc not in indice:
                indice[preproc] = []

            # Agregamos la posicion al final de la entrada
            indice[preproc].append(posicion)


# -----------------------------------
# Funciones de tratamiento de cadenas
# -----------------------------------

def preprocesar(cadena):
    # Quitamos acentos y convertimos a minusculas
    return quitar_acentos(cadena).lower()


def extrae_palabras(cadena):
    puntuacion = r"""¡!"#$%&'()*+,-./:;<=>¿?@[\]^_`{|}~"""
    for caracter in puntuacion:
        cadena = cadena.replace(caracter, ' ')

    cadena = cadena.replace('\t', ' ')
    lista = cadena.split(' ')
    return [e for e in lista if e != '']


def quitar_acentos(cadena):
    return unicodedata.normalize("NFKD", cadena).encode("ascii", "ignore").decode("ascii")


# -----------------------------------
# Funciones de busqueda
# -----------------------------------

def buscador(busqueda, indice, entradasbd):
    preproc =preprocesar(busqueda)
    result = []
    if preproc in indice:
        for posicion in indice[preproc]:
            result.append(entradasbd[posicion])
    return result


def buscador_descripcion(busqueda, indice, entradasbd):
    result = set()
    palabras = extrae_palabras(busqueda)

    # Decidir si utilizar AND / OR

    # Por defecto utilizaremos la politica OR, como dice el enunciado original,
    # para activar la politica AND palabras debe consistir en una lista del estilo:
    # termino1 AND termino2 AND termino3
    utilizar_estilo_AND = False

    if len(palabras) > 1:
        utilizar_estilo_AND = True
        for i in range(1, len(palabras), 2):
            if palabras[i] != 'AND':
                utilizar_estilo_AND = False
                break

    # Es posible que utilicemos el estilo OR explicito, aunque no sea necesario, en ese caso debemos saltar los casos de OR
    estilo_OR_explicito = False
    if len(palabras) > 1:
        estilo_OR_explicito = True
        for i in range(1, len(palabras), 2):
            if palabras[i] != 'OR':
                estilo_OR_explicito = False
                break

    if estilo_OR_explicito:
        # Estilo OR explicito, omitimos las palabras en posiciones impares (que son OR)
        for i in range(0, len(palabras), 2):
            palabra = palabras[i]
            preproc = preprocesar(palabra)
            if preproc in indice:
                for posicion in indice[preproc]:
                    result.add(entradasbd[posicion])

    elif utilizar_estilo_AND:
        # Anyadimos todas los posibles resultados (los que contienen el primer termino) a la lista
        palabra = palabras[0]
        preproc = preprocesar(palabra)

        indices_resultados = set()

        if preproc in indice:
            for posicion in indice[preproc]:
                indices_resultados.add(posicion)
        else:
            # No hay ninguna entrada con este termino
            return []

        # Estilo AND explicito, omitimos las palabras en posiciones impares (que son AND)
        # Eliminamos las tuplas del resultado cuya descripcion no contenga el termino i
        for i in range(2, len(palabras), 2):
            palabra = palabras[i]
            preproc = preprocesar(palabra)
            if preproc in indice:
                # Eliminamos los antiguos resultados cuya descripcion no contenga preproc
                nuevos_resultados = set()

                for antiguo_resultado in indices_resultados:
                    if antiguo_resultado in indice[preproc]:
                        nuevos_resultados.add(antiguo_resultado)

                indices_resultados = nuevos_resultados
            else:
                # No hay ninguna entrada con este termino
                return []

        for i in indices_resultados:
            result.add(entradasbd[i])

    else:
        # Estilo OR implicito, como el enunciado original
        for palabra in palabras:
            preproc = preprocesar(palabra)
            if preproc in indice:
                for posicion in indice[preproc]:
                    result.add(entradasbd[posicion])

    return list(result)


# -----------------------------------
# Funciones de entrada / salida
# -----------------------------------

# Pide un numero al usuario entre inferior y superior (incluidos)
def pedir_numero_entre(texto, inferior, superior):
    while True:
        res = input(texto)
        try:
            numero = int(res)
            if numero < inferior or numero > superior:
                print('Error: Debe introducir un numero entre {} y {}'.format(inferior, superior))
            else:
                return numero
        except ValueError:
            print("Error: Debe introducir un numero")


def visualizar_descripcion(resultados, pagina):
    num_elementos_por_pagina = 20

    nueva_pagina = pagina

    # No results to show
    if len(resultados) == 0:
        return

    texto = 'Introduce el número de resultado para el que quieres visualizar la descripción, 0 para volver al menú principal, S para pasar a la página siguiente o A para pasar a la página anterior: '

    while True:
        res = input(texto)

        if res == 'S' or res == 'A':
            break

        try:
            num = int(res)

            inferior = 1 + (pagina - 1) * num_elementos_por_pagina
            superior = inferior + 20 - 1

            if (num < inferior and num != 0) or num > superior:
                print('Error: Debe introducir un numero entre {} y {} o 0 o A o S'.format(inferior, superior))
            else:
                break
        except ValueError:
            print("Error: Debe introducir un numero o A o S")

    if res == 'S':
        num_paginas = math.ceil(len(resultados) / num_elementos_por_pagina)
        if pagina != num_paginas:
            nueva_pagina = pagina + 1
    elif res == 'A':
        if pagina != 1:
            nueva_pagina = pagina - 1
    else:
        if num == 0:
            return

        # Mostrar descripcion del resultado num
        id, titulo, anyo, director, tipo, ruta_fichero = resultados[num-1]

        with open(ruta_fichero, 'r') as f:
            for linea in f:
                linea = linea.rstrip('\n')

                # Extraer datos de la linea
                id_archivo,titulo_archivo,anyo_archivo,director_archivo,tipo_archivo,descripcion_archivo = linea.split('\t')
                if id == id_archivo:
                    print()
                    print(descripcion_archivo)
                    break

    mostrar_resultados(resultados, nueva_pagina)


def mostrar_resultados(resultados, pagina=1):
    num_elementos_por_pagina = 20

    num_paginas = math.ceil(len(resultados) / num_elementos_por_pagina)

    if len(resultados) != 1:
        print("\n{} elementos encontrados. Página {} de {}.".format(len(resultados), pagina, num_paginas))
    else:
        print("\n1 elemento encontrado. Página 1 de 1.")

    primer_elemento_resultados = (pagina - 1) * num_elementos_por_pagina
    ultimo_elemento_resultados = pagina * num_elementos_por_pagina

    comienzo_indice = 1 + (pagina - 1) * num_elementos_por_pagina

    for i, tupla in enumerate(resultados[primer_elemento_resultados:ultimo_elemento_resultados], start=comienzo_indice):
        id, titulo, anyo, director, tipo, ruta_fichero = tupla
        print("{}.\t{} ({}).\t{}.\t {} [{}]".format(i, titulo, anyo, director, tipo, ruta_fichero))
    print()

    visualizar_descripcion(resultados, pagina)


def listar_directores():
    directores = []
    for lista in indice_directores.values():
        directores.append(entradas[lista[0]][3])

    ordenado = sorted(directores)
    print()
    for dir in ordenado:
        print(dir)
    print()


def mostrar_menu():
    while True:
        cadena_menu = '1) Buscar por título \n2) Listar directores \n3) Buscar por director \n4) Buscar por ' \
                      'descripción \n5) Salir \nIntroduce una opción: '

        num = pedir_numero_entre(cadena_menu, 1, 5)

        if num == 1:
            titulo = input('Introduce el título: ')
            mostrar_resultados(buscador(titulo, indice_titulos, entradas))
        elif num == 2:
            listar_directores()
        elif num == 3:
            director = input('Introduce el director: ')
            mostrar_resultados(buscador(director, indice_directores, entradas))
        elif num == 4:
            descripcion = input('Introduce la descripción: ')
            mostrar_resultados(buscador_descripcion(descripcion, indice_descripciones, entradas))
        elif num == 5:
            return

# -----------------------------------
# Programa principal
# -----------------------------------


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Error: numero invalido de argumentos")
        print("Uso: python buscador.py [ruta]")
        exit(1)

    indexar_directorio(sys.argv[1])
    mostrar_menu()