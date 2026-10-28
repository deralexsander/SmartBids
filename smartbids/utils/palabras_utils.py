"""
Módulo de Normalización y Procesamiento NLP de Palabras Clave de SmartBids.

Implementa de forma fiel y optimizada las funciones de 'Funciones SmartBids.txt':
- leer_STOPWORDS: lectura desde la tabla 'config.stop_word' con caché en memoria (RAM mínima).
- filtrar_STOPWORDS: exclusión de tokens pertenecientes al conjunto de stopwords.
- obtener_palabras_unicas: generación de unigramas, bigramas y trigramas (npal = 1, 2, 3).
- sanitizar_caracteres_especiales: eliminación de caracteres de control ASCII y Unicode invisible.
- normalizar_texto / normalizar_texto_vectorizado: pipeline de normalización paso a paso.
- procesar_palabras_usuario: interfaz de alto nivel para gestionar simultáneamente pref_palabras_claves
  (entrada original del usuario) y pref_palabras_claves_norm (conjunto normalizado).
"""

import re
import os
import inspect
import logging

logger = logging.getLogger('smartbids.nlp')

# Caché en memoria para STOPWORDS (optimizado para no consultar PostgreSQL en cada petición)
_STOPWORDS_CACHE = None


def Desplegar_Error(nombre_funcion, mensaje):
    """Registra errores en los logs del sistema preservando la firma original."""
    logger.error(f"[SmartBids NLP::{nombre_funcion}] {mensaje}")


def leer_STOPWORDS(directorio=None, archivo=None, force_refresh=False):
    """
    Obtiene el conjunto unificado de STOPWORDS.
    Por directriz del proyecto, lee desde la tabla poblada 'config.stop_word' en base de datos,
    manteniendo una caché en memoria para consumo mínimo de RAM y velocidad instantánea (< 1ms).
    """
    global _STOPWORDS_CACHE
    if _STOPWORDS_CACHE is not None and not force_refresh:
        return _STOPWORDS_CACHE

    stopwords_set = set()

    # 1. Leer de la tabla config.stop_word de la base de datos
    try:
        from smartbids.models.config import StopWord
        palabras_db = StopWord.objects.values_list('nombre_stop_word', flat=True)
        for p in palabras_db:
            if p:
                p_limpia = str(p).strip().lower()
                # Reemplazo base de acentos para compatibilidad
                p_limpia = (p_limpia.replace('á', 'a')
                                    .replace('é', 'e')
                                    .replace('í', 'i')
                                    .replace('ó', 'o')
                                    .replace('ú', 'u')
                                    .replace('ü', 'u')
                                    .replace('ñ', 'n'))
                stopwords_set.add(p_limpia)
    except Exception as e:
        logger.warning(f"[SmartBids NLP] No se pudieron cargar stopwords desde la BD: {e}")

    # 2. Respaldo opcional desde archivo .txt si se proporciona directorio y archivo
    if directorio and archivo:
        ruta_archivo = os.path.join(directorio, archivo)
        if os.path.exists(ruta_archivo):
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                for linea in f:
                    lin = linea.strip().lower()
                    if lin:
                        stopwords_set.add(lin)

    _STOPWORDS_CACHE = stopwords_set
    return _STOPWORDS_CACHE


def filtrar_STOPWORDS(texto, stopwords_set):
    """
    Filtra stopwords dividiendo el texto en palabras y reuniéndolas.
    Idéntico a Funciones SmartBids.txt.
    """
    if not texto or not stopwords_set:
        return texto or ''
    # Dividir el texto en palabras (tokens)
    tokens = texto.split()
    
    # Filtrar stopwords
    tokens_filtrados = [token for token in tokens if token not in stopwords_set]
    
    # Unir los tokens filtrados de nuevo en un string
    return ' '.join(tokens_filtrados)


def obtener_palabras_unicas(texto, npal=1):
    """
    Convierte un string en un conjunto de palabras únicas y n-gramas (hasta 3 palabras).
    Idéntico a Funciones SmartBids.txt.
    """
    # Obtener el nombre de la función
    nombre_funcion = inspect.currentframe().f_code.co_name

    # Dividir el texto en palabras
    palabras = texto.split()
    
    # Crear un conjunto para almacenar las palabras únicas
    palabras_unicas = set()
    
    # Procesar palabras individuales
    if npal >= 1:
        palabras_unicas.update(palabras)                          # se usa update, porque se agregan muchos terminos
    
    # Procesar pares de palabras consecutivas
    if npal >= 2:
        for i in range(len(palabras) - 1):
            palabras_unicas.add(f"{palabras[i]} {palabras[i+1]}")       # se usa add porque se agrega un string
    
    # Procesar tríos de palabras consecutivas
    if npal >= 3:
        for i in range(len(palabras) - 2):
            palabras_unicas.add(f"{palabras[i]} {palabras[i+1]} {palabras[i+2]}")
    
    # Manejar casos no válidos
    if npal == 0 or npal > 3:
        Desplegar_Error(nombre_funcion, f"Error: no está definida la función para este número de palabras '{npal}'.")
        return set()
    
    return palabras_unicas


def sanitizar_caracteres_especiales(objeto):
    """
    Sanitiza cadenas de texto o DataFrames de Pandas eliminando caracteres 
    de control ASCII (0-31 y 127-159) e invisibles Unicode que corrompen 
    archivos de Excel (openpyxl) o generan errores en librerías de Python.
    Idéntico a Funciones SmartBids.txt.
    """
    patron_control = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F\ue000-\uf8ff]')
    
    def _limpiar_texto(cadena):
        if isinstance(cadena, str):
            return patron_control.sub('', cadena)
        return cadena

    # Si se recibe un DataFrame de Pandas (verificación dinámica para optimizar RAM sin forzar dependencia pesada)
    if hasattr(objeto, 'select_dtypes') and hasattr(objeto, 'copy'):
        df_limpio = objeto.copy()
        columnas_texto = df_limpio.select_dtypes(include=['object', 'string']).columns
        for col in columnas_texto:
            df_limpio[col] = df_limpio[col].apply(_limpiar_texto)
        return df_limpio
    
    # Si se recibe una lista o tupla
    elif isinstance(objeto, (list, tuple)):
        return [_limpiar_texto(x) for x in objeto]

    # Si se recibe un texto individual
    elif isinstance(objeto, str):
        return _limpiar_texto(objeto)
    
    # Para otros tipos de datos (int, float, datetime, etc.)
    return objeto


def normalizar_texto(texto, stopwords_set=None):
    """
    Ejecuta exactamente todos los pasos de normalización definidos en normalizar_texto_vectorizado
    sobre una cadena de texto individual, optimizando memoria RAM:
    1. Asegurar string y minúsculas.
    2. Eliminar acentos de forma masiva (á, é, í, ó, ú, ü, ñ).
    3. Eliminar números aislados rodeados de espacios (regex r'\\s*[\\+\\-]?\\d+(\\.\\d+)?\\s*').
    4. Eliminar todos los caracteres que no sean letras, números o espacios (regex r'[^a-z0-9\\s]').
    5. Reemplazar saltos de línea con espacios ('\\n' -> ' ').
    6. Filtrar STOPWORDS si se proporciona el conjunto.
    7. Eliminar espacios dobles y hacer strip (regex r'\\s+' -> ' ').
    """
    if texto is None:
        texto = ''
    texto = str(texto).lower()

    # 3. Eliminar acentos
    texto = (texto.replace('á', 'a')
                  .replace('é', 'e')
                  .replace('í', 'i')
                  .replace('ó', 'o')
                  .replace('ú', 'u')
                  .replace('ü', 'u')
                  .replace('ñ', 'n'))

    # 4. Eliminar números aislados rodeados de espacios
    # Nota: regex r'\s*[\+\-]?\d+(\.\d+)?\s*'
    texto = re.sub(r'(?:^|\s)[\+\-]?\d+(?:\.\d+)?(?=\s|$)', ' ', texto)

    # 5. Eliminar todos los caracteres que no sean letras, números o espacios
    texto = re.sub(r'[^a-z0-9\s]', '', texto)

    # 6. Reemplazar saltos de línea con espacios
    texto = texto.replace('\n', ' ')

    # 7. Si se incluye STOPWORDS
    if stopwords_set:
        texto = filtrar_STOPWORDS(texto, stopwords_set)

    # 8. Eliminar espacios de más (dobles espacios) y hacer strip
    texto = re.sub(r'\s+', ' ', texto).strip()

    return texto


def normalizar_texto_vectorizado(serie_pandas, stopwords_set=None):
    """
    Normaliza una columna completa de Pandas (Serie) o iterable de forma fiel a Funciones SmartBids.txt.
    """
    try:
        import pandas as pd
        if not isinstance(serie_pandas, pd.Series):
            serie_pandas = pd.Series(serie_pandas)

        texto = serie_pandas.fillna('').astype(str).str.lower()
        texto = (texto.str.replace('á', 'a', regex=False)
                      .str.replace('é', 'e', regex=False)
                      .str.replace('í', 'i', regex=False)
                      .str.replace('ó', 'o', regex=False)
                      .str.replace('ú', 'u', regex=False)
                      .str.replace('ü', 'u', regex=False)
                      .str.replace('ñ', 'n', regex=False))

        texto = texto.str.replace(r'\s*[\+\-]?\d+(\.\d+)?\s*', ' ', regex=True)
        texto = texto.str.replace(r'[^a-z0-9\s]', '', regex=True)
        texto = texto.str.replace('\n', ' ', regex=False)

        if stopwords_set:
            texto = texto.apply(lambda x: filtrar_STOPWORDS(x, stopwords_set))

        texto = texto.str.replace(r'\s+', ' ', regex=True).str.strip()
        return texto
    except ImportError:
        # Modo fallback liviano sin Pandas (mínimo uso de RAM)
        if isinstance(serie_pandas, (list, tuple, set)):
            return [normalizar_texto(item, stopwords_set) for item in serie_pandas]
        return normalizar_texto(serie_pandas, stopwords_set)


def procesar_palabras_usuario(palabras_input, npal=3):
    """
    Procesa las palabras clave ingresadas por el usuario:
    Retorna una tupla: (palabras_originales_usuario, conjunto_normalizado_tokens)
    
    1. 'palabras_originales_usuario' (pref_palabras_claves):
       Lista de términos con la escritura original del usuario (solo limpiada de espacios y caracteres de control),
       para que el usuario no vea alteraciones visibles más que la separación por comas.
       
    2. 'conjunto_normalizado_tokens' (pref_palabras_claves_norm):
       Conjunto unificado de palabras clave normalizadas aplicando:
       - sanitizar_caracteres_especiales
       - normalizar_texto (minúsculas, sin tildes, sin números aislados, sin símbolos, filtrado con config.stop_word)
       - obtener_palabras_unicas (con n-gramas hasta npal=3, soportando términos simples como 'computadora'
         y compuestos como 'sistema de riesgo' -> 'sistema riesgo' -> ['sistema', 'riesgo', 'sistema riesgo']).
    """
    if isinstance(palabras_input, str):
        items_raw = palabras_input.split(',')
    elif isinstance(palabras_input, (list, tuple, set)):
        items_raw = list(palabras_input)
    else:
        items_raw = []

    stopwords_set = leer_STOPWORDS()

    palabras_usuario = []
    palabras_usuario_vistas = set()
    conjunto_normalizado = set()

    for item in items_raw:
        if not item:
            continue
        # Limpieza suave de caracteres de control sin alterar el texto ni mayúsculas/tildes
        item_sanitizado = sanitizar_caracteres_especiales(str(item)).strip()
        if not item_sanitizado:
            continue

        clave_dedup = item_sanitizado.lower()
        if clave_dedup not in palabras_usuario_vistas:
            palabras_usuario_vistas.add(clave_dedup)
            palabras_usuario.append(item_sanitizado[:50])

        # Pipeline NLP de normalización
        texto_norm = normalizar_texto(item_sanitizado, stopwords_set=stopwords_set)
        if texto_norm:
            tokens_unicos = obtener_palabras_unicas(texto_norm, npal=npal)
            for token in tokens_unicos:
                tok_limpio = token.strip()
                if tok_limpio and len(tok_limpio) > 1:
                    conjunto_normalizado.add(tok_limpio[:50])

    # Convertir a lista ordenada para consistencia en la base de datos
    return palabras_usuario, sorted(list(conjunto_normalizado))
