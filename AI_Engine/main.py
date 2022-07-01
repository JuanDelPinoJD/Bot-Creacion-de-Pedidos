# -*- coding: utf-8 -*-
"""
Created on Mon Apr 04 13:51:56 2022

@author: W8DE5P2 
"""

import cv2 as cv
import os
import pandas as pd
import numpy as np
import json
from AI_Engine.sample import modulo_general as modg
from AI_Engine.sample import modulo_basic_functions as mod_basic
from AI_Engine.sample import doc_layout_analysis
from AI_Engine.sample import table_detection
from AI_Engine.sample import dataframe_handling as df_handling
from AI_Engine.format_table import FormatTable
from AI_Engine.lines import search_horiz_lines
from Packages.constants import poppler_online_path, tesseract_exe_online_path, ai_online_path


def main(proveedor: str, pedidos_path: str,
         is_img_shown: bool = False,
         ai_path: str = None, poppler_path: str = None, tesseract_exe_path: str = None) -> pd.DataFrame:
    """
    Metodo principal de extraccion de datos de proveedores
    Parameters:
        proveedor: Nombre del proveedor del cual se extraera la informacion
        pedidos_path: Ruta de la carpeta donde se encuentran los archivos o ruta del propio archivo a extraer
         la informacion
        is_img_shown: (Opcional) Variable para visualizar la extraccion de datos. Por defecto, esta a false
        ai_path: (Opcional) Ruta donde se encuentran las carpetas que vaya a usar la apliacacion (Config, Resultados,
         etc.). Por defecto, coge la ruta en linea
        poppler_path: (Opcional) Ruta donde se encuentran los binarios de Poppler. Por defecto, coge la ruta en linea
        tesseract_exe_path: (Opcional) Ruta donde se encuentra el ejecutable de Tesseract. Por defecto, coge la ruta en linea

    Returns:
        Dataframe de los datos extraidos. None si ha habido algun error
    """

    # region Adaptacion de parametros
    pedidos_path = os.path.normpath(pedidos_path)
    if ai_path is None:
        ai_path = ai_online_path
    ai_path = os.path.normpath(ai_path)
    if poppler_path is None:
        poppler_path = poppler_online_path
    poppler_path = os.path.normpath(poppler_path)
    if tesseract_exe_path is None:
        tesseract_exe_path = tesseract_exe_online_path
    tesseract_exe_path = os.path.normpath(tesseract_exe_path)
    # endregion

    # region Constantes
    # General constants
    PEDIDOS_WINDOW = 'PDF pedidos'
    COLUMNAS = ("order_number", "client", "reference", "quantity", "ship_out_date", "arrival_date", "confidence")
    # COLUMNAS = ("archivo",) + COLUMNAS
    CAMPOS = ("order_number", "reference", "quantity", "ship_out_date", "arrival_date")
    HEIGHT_TO_SHOW = 800
    CONF_ROW_INVALID = -200
    CONF_ROW_WRONG_FIELD = -100
    # Paths
    PATH_CONFIG = os.path.join(ai_path, 'Config')
    PATH_RESULTADOS = os.path.join(ai_path, 'Resultados')
    # Filepaths
    FILEPATH_PROVEEDORES_DATA = os.path.join(PATH_CONFIG, r"proveedores_data.json")
    FILEPATH_FORMATO_CAMPOS = os.path.join(PATH_CONFIG, r"default_formats.json")
    FILEPATH_PATH_FORMATS = os.path.join(PATH_CONFIG, "formats.xlsx")
    # File names
    FILE_TABLE_HEADER = r"header"
    FILE_TABLE_END = r"end"
    # endregion

    # region Variables
    # Dataframe
    df_total = pd.DataFrame(columns=COLUMNAS)
    # endregion

    # region Main
    print("-------------- " + proveedor + " --------------")

    # region Listado archivos de proveedores
    files = []
    if os.path.isdir(pedidos_path):
        files = os.listdir(pedidos_path)
        files = list(map(lambda name: os.path.join(pedidos_path, name), files))
    else:
        files.append(pedidos_path)
    # endregion

    # region Lectura de configuracion

    # region Informacion del proveedor
    proveedores_data = {}
    # Leo archivo JSON
    if os.path.exists(FILEPATH_PROVEEDORES_DATA):
        with open(FILEPATH_PROVEEDORES_DATA, 'r') as openfile:
            proveedores_data = json.load(openfile)
    else:
        mod_basic.close_windows("Configuracion de proveedores no encontrada")
        return
    # Compruebo que existe el proveedor
    if proveedor not in proveedores_data:
        mod_basic.close_windows("Configuracion de proveedores no contiene información del proveedor")
        return
    else:
        # Compruebo que sea un diccionario
        if not type(proveedores_data[proveedor]) is dict:
            mod_basic.close_windows("El formato de la Configuracion de proveedores no es correcta")
            return
    # endregion

    # region Formato campos
    default_formats = {}
    # Leo archivo JSON
    if os.path.exists(FILEPATH_FORMATO_CAMPOS):
        with open(FILEPATH_FORMATO_CAMPOS, 'r') as openfile:
            default_formats = json.load(openfile)
    else:
        mod_basic.close_windows("Configuracion de formato no encontrado")
        return
    # Formateo el diccionario
    for campo in default_formats:
        default_formats[campo] = "|".join(default_formats[campo])
    # endregion

    # region Formatos
    # Leo archivo JSON
    if os.path.exists(FILEPATH_PATH_FORMATS):
        data = pd.read_excel(FILEPATH_PATH_FORMATS, sheet_name="order_number_format", dtype=str)
        order_number_formats = pd.DataFrame(data, dtype=str)
        data = pd.read_excel(FILEPATH_PATH_FORMATS, sheet_name="reference_format", dtype=str)
        reference_formats = pd.DataFrame(data, dtype=str)
        data = pd.read_excel(FILEPATH_PATH_FORMATS, sheet_name="number_format", dtype=str)
        number_formats = pd.DataFrame(data, dtype=str)
        data = pd.read_excel(FILEPATH_PATH_FORMATS, sheet_name="date_format", dtype=str)
        date_formats = pd.DataFrame(data, dtype=str)
    else:
        mod_basic.close_windows("Formatos no encontrados")
        return
    # endregion

    # Creo variables de acceso directo
    proveedor_data = proveedores_data[proveedor]
    proveedor_campos = proveedor_data["fields"]
    proveedor_tabla = proveedor_data["table"]

    # region Creacion tuplas campos hoja y campos tabla
    # Creo tuplas de los campos dentro y fuera de tabla
    campos_tabla, campos_hoja = [], []
    for campo in CAMPOS:
        # Compruebo que la configuracion no es nula
        if proveedor_campos[campo] is not None:
            if proveedor_campos[campo]['in_table']:
                campos_tabla.append(campo)
            else:
                campos_hoja.append(campo)
    campos_tabla, campos_hoja = tuple(campos_tabla), tuple(campos_hoja)
    campos_validos = campos_hoja + campos_tabla
    # endregion

    # Extraemos las expresiones regulares de cada campo que se utilizaran para la validacion
    decimal_separator = None
    date_format_regex = pd.DataFrame(columns=("regex", "format_code"), dtype=str)
    for campo in proveedor_campos:
        if proveedor_campos[campo] is not None:
            # order_number
            if campo == "order_number":
                # Si no se ha establecido ningun regex de validacion, establecemos el de por defecto
                if proveedor_campos["order_number"].get("regex_validation") is None:
                    proveedor_campos["order_number"]["regex_validation"] = order_number_formats["regex"].iloc[0]
            # reference
            elif campo == "reference":
                # Si no se ha establecido ningun regex de validacion, establecemos el de por defecto
                if proveedor_campos["reference"].get("regex_validation") is None:
                    proveedor_campos["reference"]["regex_validation"] = reference_formats["regex"].iloc[0]
            # quantity
            elif campo == "quantity":
                # Si se ha establecido separador decimal, le asignamos el regex correspondiente
                if proveedor_campos["quantity"].get("decimal_separator") in number_formats[
                    "decimal_separator"].unique():
                    # Obtenemos el separador decimal
                    decimal_separator = proveedor_campos["quantity"]["decimal_separator"]
                # Si no se ha establecido ningun regex de validacion, establecemos uno
                if proveedor_campos["quantity"].get("regex_validation") is None:
                    # Si no se ha establecido separador decimal, le asignamos la combinacion de los regex posibles
                    if decimal_separator is None:
                        proveedor_campos["quantity"]["regex_validation"] = "|".join(
                            number_formats["regex"].unique().tolist())
                    else:
                        proveedor_campos["quantity"]["regex_validation"] = number_formats[
                            number_formats["decimal_separator"] == decimal_separator]["regex"].iloc[0]
            # ship_out_date y arrival_date
            elif campo == "ship_out_date" or campo == "arrival_date":
                # Se ha establecido formato de fecha
                if proveedor_campos[campo].get("date_format") is not None:
                    # Si el valor no es una lista, la meto en una para poder hacer el bucle
                    if type(proveedor_campos[campo].get("date_format")) != list:
                        proveedor_campos[campo]["date_format"] = [proveedor_campos[campo].get("date_format")]
                    # Obtengo el dataframe de los formatos de fecha junto a los regex
                    date_format_regex = date_formats[
                        date_formats["date_format"].isin(proveedor_campos[campo]["date_format"])][
                        ["regex", "format_code"]]
                # No se ha establecido formato de fecha
                else:
                    # Obtengo el dataframe entero de los formatos de fecha junto a los regex
                    date_format_regex = date_formats[["regex", "format_code"]]
                # Si no se ha establecido ningun regex de validacion, establecemos uno
                if proveedor_campos[campo].get("regex_validation") is None:
                    # Le asignamos el regex correspondiente
                    proveedor_campos[campo]["regex_validation"] = "|".join(date_format_regex["regex"].tolist())

    # Leo las imagenes de los headers y final de la tabla
    pathfile_table_header_list = [os.path.join(PATH_CONFIG, proveedor, filename) for filename in
                                  os.listdir(os.path.join(PATH_CONFIG, proveedor)) if
                                  filename.startswith(FILE_TABLE_HEADER)]
    pathfile_table_end_list = [os.path.join(PATH_CONFIG, proveedor, filename) for filename in
                               os.listdir(os.path.join(PATH_CONFIG, proveedor)) if
                               filename.startswith(FILE_TABLE_END)]
    img_table_header_list = [cv.imread(pathfile) for pathfile in pathfile_table_header_list]
    img_table_end_list = [cv.imread(pathfile) for pathfile in pathfile_table_end_list]
    # endregion

    # region Lectura del proveedor
    # Recorro todos los archivos del directorio
    n_files = 0
    for filename in files:

        # region Filtrado de archivo
        # Compruebo que el archivo sea PDF
        if not os.path.splitext(filename)[1].lower() == ".pdf":
            continue
        # if n_files > 4:
        #     break
        # endregion

        # Imprimo nombre del archivo
        print(filename + ":")

        # region Conversion PDF a imagen
        img_list = mod_basic.pdf_to_img(os.path.join(filename), poppler_path=poppler_path)
        # endregion

        # region Visualizacion pedido
        if is_img_shown:
            # Calculo las dimensiones de la primera hoja
            shape_original = img_list[0].shape[:2]  # height, width
            shape_resized = (HEIGHT_TO_SHOW, round((shape_original[1] / shape_original[0]) * HEIGHT_TO_SHOW))
            # Muestro el PDF
            cv.imshow(PEDIDOS_WINDOW,
                      cv.resize(img_list[0], (shape_resized[1], shape_resized[0]), interpolation=cv.INTER_AREA))
            cv.waitKey(1)
        # endregion

        # region Creacion sets de informacion
        # Recorro la configuracion para crear los sets de informacion
        # Estos set contendran los campos presentes y el numero de pagina donde se encuentran
        sets_info = []
        # Recorremos cada pagina
        for n_pag in range(len(img_list)):
            set_info = {}
            # Recorro campos fijos para crear el set de info
            for campo in campos_hoja:
                if proveedor_campos[campo]["pag"] == "all" or proveedor_campos[campo]["pag"] == n_pag + 1:
                    set_info[campo] = n_pag
            # Si hay campos hoja en la pagina, creamos nuevo set
            if set_info != {}:
                set_info["table"] = [n_pag]
                sets_info.append(set_info)
            # Si no hay campos hoja, actualizamos el campo tabla del ultimo set
            else:
                sets_info[-1]["table"].append(n_pag)
        print("sets_info:")
        print(sets_info)
        print()
        # endregion

        # region Creacion lista imagenes de tabla
        # Creo la lista de imagenes donde se encontrara la tabla
        img_table_info_list = []
        if proveedor_tabla["coordinates"] is not None:
            img_table_info_list = modg.create_table_info_list(img_list,
                                                              img_table_header_list,
                                                              img_table_end_list,
                                                              proveedor_tabla["coordinates"])

            # region Visualizacion lista imagenes de tabla
            if is_img_shown and False:
                for img_table_info in img_table_info_list:
                    cv.imshow("img_table",
                              cv.resize(img_table_info["roi"], None, fx=0.5, fy=0.5, interpolation=cv.INTER_AREA))
                    cv.waitKey(0)
                cv.destroyWindow("img_table")
            # endregion

        # endregion

        # region Creacion dataframe
        df = pd.DataFrame(columns=COLUMNAS)
        # Recorremos cada set de informacion
        for set_info in sets_info:
            set_data = {}
            df_set = pd.DataFrame(dtype=object)

            # region Lectura campos tabla
            # Inicializo campos tabla
            for campo in campos_tabla:
                set_data[campo] = []
            # Leo campos tabla
            if len(campos_tabla) > 0:

                # region Tabla "lines"
                if proveedor_tabla["type"] == "lines":

                    # region Creacion tabla combinada
                    table_img = modg.create_combined_table_img(set_info["table"], img_table_info_list)
                    # endregion

                    if table_img is not None:

                        # region Conversion tabla a escala de grises
                        table_img_gray = modg.convert_rgb_to_grayscale(table_img)
                        # endregion

                        # region Visualizacion tabla del set
                        if is_img_shown:
                            cv.imshow("img_table",
                                      cv.resize(table_img, None, fx=0.5, fy=0.5, interpolation=cv.INTER_AREA))
                            cv.waitKey(0)
                            cv.destroyWindow("img_table")
                        # endregion

                        # region Busqueda de lineas horizontales
                        lines = search_horiz_lines(table_img_gray, 3)
                        # endregion

                        # region Eliminacion de lineas horizontales
                        thresh = cv.threshold(table_img_gray, 0, 255, cv.THRESH_BINARY_INV + cv.THRESH_OTSU)[1]
                        horizontal_kernel = cv.getStructuringElement(cv.MORPH_RECT, (40, 1))
                        remove_horizontal = cv.morphologyEx(thresh, cv.MORPH_OPEN, horizontal_kernel, iterations=1)
                        cnts = cv.findContours(remove_horizontal, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
                        cnts = cnts[0] if len(cnts) == 2 else cnts[1]
                        tabla_procesada = table_img_gray.copy()
                        for c in cnts:
                            cv.drawContours(tabla_procesada, [c], -1, (255, 255, 255), 5)

                        # region Visualizacion tabla sin lineas
                        if is_img_shown:
                            cv.imshow("tabla_procesada",
                                      cv.resize(tabla_procesada, None, fx=0.5, fy=0.5, interpolation=cv.INTER_AREA))
                            cv.waitKey(0)
                            cv.destroyWindow("tabla_procesada")
                        # endregion

                        # endregion

                        # region Creacion de lista de imagenes por fila de tabla
                        filas_img = []
                        y1, y_end = 0, tabla_procesada.shape[0]
                        for line in lines:
                            y2 = line[0][1]
                            filas_img.append(tabla_procesada[y1:y2])
                            y1 = y2
                        filas_img.append(tabla_procesada[y1:y_end])
                        # endregion

                        # region Lectura de campos
                        # Recorro las imagenes de las filas
                        for fila_img in filas_img:

                            # region Visualizacion fila
                            if is_img_shown:
                                cv.imshow("fila",
                                          cv.resize(fila_img, None, fx=0.5, fy=0.5, interpolation=cv.INTER_AREA))
                                cv.waitKey(0)
                                cv.destroyWindow("fila")
                            # endregion

                            # region Lectura de campo por fila
                            for campo in campos_tabla:
                                # Leo la region
                                list_lecture = modg.lectura_campo(fila_img,
                                                                  proveedor_campos[campo]["coordinates"],
                                                                  tesseract_exe_path,
                                                                  proveedor_campos[campo]["method_ocr"],
                                                                  is_img_shown)
                                # Manejo la lista de resultados
                                set_data[campo].append(modg.handle_lecture_ocr(list_lecture,
                                                                               proveedor_campos[campo][
                                                                                   'regex_validation'],
                                                                               proveedor_campos[campo].get(
                                                                                   'regex_filter')))
                            # endregion

                        # Relleno el dataset
                        df_set = pd.DataFrame(set_data)
                        # endregion

                # endregion

                # region Tabla "no_lines"
                elif proveedor_tabla["type"] == "no_lines":

                    # region Creacion tabla combinada
                    table_img = modg.create_combined_table_img(set_info["table"], img_table_info_list)
                    # endregion

                    if table_img is not None:

                        # region Conversion tabla a escala de grises
                        table_img_gray = modg.convert_rgb_to_grayscale(table_img)
                        # endregion

                        for campo in campos_tabla:
                            # Creo el ROI que contiene la columna
                            ix, iy, fx, fy = proveedor_campos[campo]["coordinates"]
                            column_img = table_img_gray[iy:fy, ix:fx]
                            # Detecto los contornos de las lineas del texto
                            column_img_to_show = column_img.copy() if is_img_shown else None
                            boxes, column_img_to_show = doc_layout_analysis.process_line(column_img, column_img_to_show,
                                                                                         True)
                            if is_img_shown:
                                cv.imshow("column_img",
                                          cv.resize(column_img_to_show, None, fx=0.5, fy=0.5,
                                                    interpolation=cv.INTER_AREA))
                            # Por cada contorno leo el campo
                            for box in reversed(boxes):
                                # Leo la region
                                list_lecture = modg.lectura_campo(column_img, box, tesseract_exe_path,
                                                                  proveedor_campos[campo]["method_ocr"],
                                                                  is_img_shown)
                                # Manejo la lista de resultados
                                set_data[campo].append(modg.handle_lecture_ocr(list_lecture,
                                                                               proveedor_campos[campo][
                                                                                   'regex_validation'],
                                                                               proveedor_campos[campo].get(
                                                                                   'regex_filter')))
                    # Relleno el dataset
                    df_set = pd.DataFrame(set_data)
                # endregion

                # region Tabla "table"
                elif proveedor_tabla["type"] == "table":
                    # Creacion lista dataframes
                    df_list = []
                    for table_pag in set_info["table"]:

                        # region Deteccion header
                        header_center = (None, None)
                        header_coordinates = img_table_info_list[table_pag]["header_coordinates"]
                        if header_coordinates != ((None, None), (None, None)):
                            header_center = (int((header_coordinates[0][0] + header_coordinates[0][1]) / 2),
                                             int((header_coordinates[1][0] + header_coordinates[1][1]) / 2))
                        # endregion

                        # region Deteccion tabla
                        # Detectamos las tablas
                        size_factor = proveedor_tabla["detection_parameters"]["size_factor"]
                        scale_x = proveedor_tabla["detection_parameters"]["scale_x"]
                        scale_y = proveedor_tabla["detection_parameters"]["scale_y"]
                        tables_data, src_no_lines = table_detection.table_detector(img_list[table_pag], size_factor,
                                                                                   scale_x, scale_y, is_img_shown)
                        # Si no se ha enocntrado ninguna tabla saltamos a la siguiente pagina
                        if tables_data is None or len(tables_data) < 1:
                            continue
                        # Escogemos la tabla
                        table_data = None
                        # Elegimos la tabla que contiene al header
                        if header_center != (None, None):
                            for item in tables_data:
                                if mod_basic.is_point_en_rect(header_center, item["table_coordinates"]):
                                    table_data = item
                                    break
                        # Elegimos la tabla mas grande (donde estaran los datos)
                        else:
                            table_data = max(tables_data,
                                             key=lambda item: mod_basic.area_rect(item["table_coordinates"][0],
                                                                                  item["table_coordinates"][1]))
                        # Si no se ha encontrado la tabla, saltamos a la siguiente pagina
                        if table_data is None:
                            continue
                        # endregion

                        # region Visualizacion detecciones
                        # Dibujamos las detecciones y las mostramos
                        table_img_to_show = img_list[table_pag].copy()
                        table_img_to_show = table_img_to_show[
                                            table_data["table_coordinates"][0][1]:table_data["table_coordinates"][1][1],
                                            table_data["table_coordinates"][0][0]:table_data["table_coordinates"][1][0]]
                        # Dibujo tabla
                        cv.rectangle(table_img_to_show, table_data["table_coordinates"][0],
                                     table_data["table_coordinates"][1], (0, 255, 0), 5)
                        # Dibujo celdas
                        for cell_data in table_data["cells"]:
                            cv.rectangle(table_img_to_show,
                                         (cell_data["lines_coordinates"][0][0],
                                          cell_data["lines_coordinates"][0][1]),
                                         (cell_data["lines_coordinates"][1][0],
                                          cell_data["lines_coordinates"][1][1]),
                                         (0, 0, 255), 2)
                            cv.circle(table_img_to_show,
                                      (int((cell_data["lines_coordinates"][0][0] +
                                            cell_data["lines_coordinates"][1][0]) / 2),
                                       int((cell_data["lines_coordinates"][0][1] +
                                            cell_data["lines_coordinates"][1][1]) / 2)),
                                      5, (255, 255, 0), cv.FILLED)
                        # Dibujo joints
                        for joint_points in table_data["joints_coordinates"]:
                            cv.circle(table_img_to_show, (joint_points[0], joint_points[1]), 7, (255, 0, 0), -1)
                        # endregion

                        # region Creacion matriz raw de tabla
                        # Extraigo las posiciones de lineas horizontales y verticales de la tabla
                        horizontal_lines_y_pos = table_data["horizontal_lines_y_pos"]
                        vertical_lines_x_pos = table_data["vertical_lines_x_pos"]
                        # Filtro las lineas horizontales que estan por encima de la tabla
                        # horizontal_lines_y_pos = filter(lambda y: y >= header_pt2[1], horizontal_lines_y_pos)
                        # Creo la matriz que contendra la tabla
                        matrix_table = np.empty((len(horizontal_lines_y_pos), len(vertical_lines_x_pos)),
                                                dtype=object)
                        matrix_table[:] = None
                        # endregion

                        # region Relleno matriz tabla
                        # Busco las coordenadas del header dentro de la tabla
                        header_pt1, header_pt2 = mod_basic.get_closest_lines(table_data["vertical_lines_x_pos"],
                                                                             table_data["horizontal_lines_y_pos"],
                                                                             mod_basic.subs_points(
                                                                                 header_coordinates[0],
                                                                                 table_data["table_coordinates"][
                                                                                     0]),
                                                                             mod_basic.subs_points(
                                                                                 header_coordinates[1],
                                                                                 table_data["table_coordinates"][
                                                                                     0]))
                        # Creo ROI de la tabla
                        table_img = img_list[table_pag][
                                    table_data["table_coordinates"][0][1]:table_data["table_coordinates"][1][1],
                                    table_data["table_coordinates"][0][0]:table_data["table_coordinates"][1][0]]
                        # Creo lista de columnas con contenido
                        column_list = []
                        for campo in campos_tabla:
                            if "column_pos" in proveedor_campos[campo]:
                                column_list.append(proveedor_campos[campo]["column_pos"])
                        # Recorro las celdas para eliminar las que no esten en la tabla (debajo de header)
                        for cell in table_data["cells"]:
                            # Si esta por encima del header no indizo la celda
                            if cell["lines_coordinates"][0][1] < header_pt1[1]:
                                continue
                            # Visualizacion celda
                            # cv.imshow("cell", table_img_to_show[cell["lines_coordinates"][0][1]:cell["lines_coordinates"][1][1],
                            #           cell["lines_coordinates"][0][0]:cell["lines_coordinates"][1][0]])
                            # cv.waitKey(0)
                            # Busco coordenadas top izq de la celda
                            vertical_index = vertical_lines_x_pos.index(cell["lines_coordinates"][0][0])
                            horizontal_index = horizontal_lines_y_pos.index(cell["lines_coordinates"][0][1])
                            # Si la celda esta en la tabla, se inserta la informacion de la celda
                            matrix_table[horizontal_index][vertical_index] = cell
                        # endregion

                        print()

                        # region Transformacion matriz a dataframe
                        df_table = pd.DataFrame(matrix_table, dtype="object")
                        # Borro filas y columnas None
                        df_table = df_handling.remove_null_rows_cols(df_table)
                        # endregion

                        # region Lectura de celdas
                        # Recorro las columnas
                        for (col_index, col_name) in enumerate(df_table):
                            # Recorro las filas
                            for i in df_table.index:
                                # Leo las celdas
                                if df_table[col_name][i] is not None and \
                                        (proveedor_tabla["read_all_cells"] or \
                                         (not proveedor_tabla["read_all_cells"] and col_index + 1 in column_list)):
                                    df_table[col_name][i] = modg.lectura_campo(table_img,
                                                                               df_table[col_name][i][
                                                                                   "content_coordinates"],
                                                                               tesseract_exe_path, None, False)
                                # La celda se pone vacia
                                else:
                                    df_table[col_name][i] = [("", -100)]
                        # endregion

                        # Añado dataframe a la lista
                        df_list.append(df_table)

                    # Relleno el dataset
                    df_set = df_handling.handler(df_list, campos_tabla, proveedor, proveedor_data)
                    print("------------------")
                    print(df_set.to_string())
                    # Aplico regex a los resultados
                    for campo in campos_tabla:
                        df_set[campo] = df_set[campo].map(
                            lambda x: modg.handle_lecture_ocr(x, proveedor_campos[campo]['regex_validation'],
                                                              proveedor_campos[campo].get('regex_filter')))
                    print("------- ######## ---------")
                    print(df_set.to_string())
                    print("------------------")

                # endregion

            # Compruebo que el dataframe con los valores de los campos en tabla no este vacio
            if df_set.empty:
                # Si alguna lista de tabla no tiene valores, saltamos al siguiente set
                continue
            # endregion

            # region Lectura campos hoja
            for campo in campos_hoja:
                if set_info[campo] is not None:
                    img_read = img_list[set_info[campo]]
                    # Leo la region
                    list_lecture = modg.lectura_campo(img_read,
                                                      proveedor_campos[campo]["coordinates"],
                                                      tesseract_exe_path,
                                                      proveedor_campos[campo]["method_ocr"],
                                                      is_img_shown)
                    # Manejo la lista de resultados
                    lecture = modg.handle_lecture_ocr(list_lecture, proveedor_campos[campo]['regex_validation'],
                                                      proveedor_campos[campo].get('regex_filter'))
                    # Inserto el resultado en el dataframe
                    df_set[campo] = None
                    df_set[campo] = df_set[campo].apply(lambda x: lecture)
            # endregion
            # Concateno el nuevo dataframe
            df = pd.concat([df, df_set], ignore_index=True)
        # endregion

        # region Manejo dataframe

        # region Relleno columnas de campos de hoja
        for campo in campos_hoja:
            df[campo] = df[campo].ffill(axis=0)
        # endregion

        # region Calculo de confianza por fila
        list_conf = []
        # Recorro las filas del dataframe
        for i in df.index:
            # Calculo el valor minimo de confianza de las columnas
            list_conf_row = []
            for campo in campos_validos:
                list_conf_row.append(df[campo][i][1])
            list_conf.append(min(list_conf_row))
        # Relleno columna de confianza
        df["confidence"] = list_conf
        print(df.to_string())
        # endregion

        # region Transformacion de tuplas a texto
        for campo in campos_validos:
            df[campo] = df[campo].map(lambda x: x[0] if type(x) is tuple and len(x) > 0 and x[0].strip() else "")
        # endregion

        # region Columnas extra
        # Relleno el valor de las columnas extra
        if "archivo" in COLUMNAS:
            df["archivo"] = filename
        df["client"] = proveedor
        # endregion

        # region Validacion dataframe
        # Recorro todas las filas del dataframe para comprobar si el formato de los campos son correcto
        for i in range(len(df)):
            # Creo variables auxiliares
            campo_tabla_is_valid, campo_hoja_is_valid = {}, {}
            for campo in campos_tabla:
                campo_tabla_is_valid[campo] = True
            for campo in campos_hoja:
                campo_hoja_is_valid[campo] = True
            # Recorro los campos para validarlos
            for campo in campos_validos:
                # Aplico regex para comprobar el formato
                reg_res = modg.regex_group(proveedor_campos[campo]["regex_validation"], df.loc[i, campo], True)
                # Si el formato no es correcto, lo guardo en la variable auxiliar
                if reg_res is None or df.loc[i, campo] is None or len(reg_res) != len(df.loc[i, campo]):
                    if campo in campos_tabla:
                        campo_tabla_is_valid[campo] = False
                    else:
                        campo_hoja_is_valid[campo] = False
                    print("(" + str(i) + ", " + campo + ") " + df.loc[i, campo] + " no hace match con " +
                          proveedor_campos[campo]["regex_validation"])
            # Modifico el valor de confianza
            # Todos los campos tabla son invalidos
            if all(not campo for campo in campo_tabla_is_valid.values()):
                df.loc[i, "confidence"] = CONF_ROW_INVALID
            # Al menos un campo tabla es invalido
            elif False in campo_tabla_is_valid.values():
                df.loc[i, "confidence"] = CONF_ROW_WRONG_FIELD
            # Un campo hoja es invalido
            elif False in campo_hoja_is_valid.values():
                df.loc[i, "confidence"] = CONF_ROW_WRONG_FIELD
        # endregion

        # endregion

        # endregion

        # region Eliminacion visualizacion pedido
        if is_img_shown:
            cv.destroyWindow(PEDIDOS_WINDOW)
        # endregion

        # region Visualizacion dataframe
        print("· Dataframe archivo: ")
        print(df.to_string())
        # endregion

        # Concateno el dataframe del archivo al dataframe total
        df_total = pd.concat([df_total, df], ignore_index=True)
        n_files = n_files + 1
    # endregion

    # region Formateo dataframe
    # Visulaizacion pre formateo
    print()
    print("· Dataframe total (sin formateo):")
    print(df_total.to_string())

    # Guardo el dataframe en un EXCEL para su visualizacion
    path_dataframe = os.path.join(PATH_RESULTADOS, proveedor)
    if not os.path.exists(path_dataframe):
        os.makedirs(path_dataframe)
    df_total.to_excel(os.path.join(path_dataframe, "dataFrame.xlsx"))

    # Borro las filas invalidas
    df_total.drop(df_total[df_total['confidence'] == CONF_ROW_INVALID].index, inplace=True)

    # Sacar un promedio de la columna de confianza
    # confidences = df_total['confidence'].to_list()
    # if len(confidences) > 1:
    #     total_confidence = (sum(confidences) / len(
    #         confidences)) / 100  # Dividirlo por 100 para tener valores entre [0-1]
    #     total_confidence = round(total_confidence, 2)  # Redondear a 2 decimales
    #     df_total['confidence'] = [total_confidence] * len(confidences)

    # Formatear las columnas de la tabla
    try:
        df_total = FormatTable(orders=df_total, decimal_separator=decimal_separator,
                               date_format_regex=date_format_regex).format()
    except Exception as e:
        import traceback
        traceback.print_exc()
        # return empty df en caso de error
        df_total = pd.DataFrame()
    # endregion

    # region Visualizacion y guardado de dataframe
    # Imprimo el dataframe
    print()
    print("· Dataframe total:")
    print(df_total.to_string())
    # endregion

    # Borro ventanas
    mod_basic.close_windows("Aplicacion terminada")
    # endregion

    return df_total


if __name__ == '__main__':
    proveedor = "70012672"  # EMP
    proveedor = "99999TSE01 (lines)"  # JD REMAN (lines)
    proveedor = "70017703"  # Engine Power Components
    proveedor = "test"  # test
    proveedor = "99999TSE01"  # JD REMAN
    proveedor = "99999TCD00"  # JD SARAN
    proveedor = "70017048"  # Thyssenkrupp Crankshaft
    proveedor = "70017869"  # TIG
    proveedor = "70017078"  # Thyssenkrupp Campo Limpo
    proveedor = "70001256"  # ESP
    proveedor = "70001353"  # Skyway
    proveedor = "70018938"  # WorldClass Industries

    pedidos_path_root = r"C:\Users\W8DE5P2\OneDrive-Deere&Co\OneDrive - Deere & Co\Desktop\Proveedores"
    pedidos_path = r"extra\Thyssenkrupp Campo Limpo\20-04-2022_09h-22m.pdf"
    pedidos_path = r"orders_history\ESP INTERNATIONAL_1223728_R116529"
    pedidos_path = r"extra\Thyssenkrupp Campo Limpo"
    pedidos_path = r"test"
    pedidos_path = r"orders_history\Thyssen Krupp Cranks_5500044982_DZ104463\10-02-2022_11h-06m.pdf"
    pedidos_path = r"CLIIENTES JOHN DEERE\Engine Power Components\t42.pdf"
    pedidos_path = r"CLIIENTES JOHN DEERE\TIG\john deere iberica po 0016415 r1.pdf"
    pedidos_path = r"CLIIENTES JOHN DEERE\Thyssenkrupp Campo Limpo"
    pedidos_path = r"orders_history\ESP INTERNATIONAL_1223728_R116529"
    pedidos_path = r"CLIIENTES JOHN DEERE\ESP"
    pedidos_path = r"CLIIENTES JOHN DEERE\Skyway txt\John Deere Iberica SPW Open Order Report.pdf"
    pedidos_path = r"CLIIENTES JOHN DEERE\WorldClass Industries"
    pedidos_path = os.path.join(pedidos_path_root, pedidos_path)

    main(proveedor, pedidos_path, is_img_shown=False, ai_path=".",
         poppler_path=r"C:\Program Files (x86)\poppler-22.01.0\Library\bin",
         tesseract_exe_path=r"C:\Program Files\Tesseract-OCR\tesseract.exe")

    #############################################

    list_pro = (
        ("99999TCD00", "JD SARAN"),
        ("99999TSE01", "JD REMAN"),
        ("70001256", "ESP"),
        ("70012672", "EMP"),
        ("70017048", "Thyssenkrupp Crankshaft"),
        ("70017078", "Thyssenkrupp Campo Limpo"),
        ("70017703", "Engine Power Components"),
        ("70017869", "TIG"),
        ("70018938", "WorldClass Industries"),
        ("70001353", "Skyway txt"),
        ("99999TSE01 (lines)", "JD REMAN (lines)")
    )

    list_ex = []
    for item in list_pro:
        try:
            main(item[0], os.path.join(pedidos_path_root, "CLIIENTES JOHN DEERE\\", item[1]),
                 is_img_shown=False, ai_path=".",
                 poppler_path=r"C:\Program Files (x86)\poppler-22.01.0\Library\bin",
                 tesseract_exe_path=r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        except Exception as e:
            list_ex.append((item[0], e))

    print("Exception:")
    print(str(list_ex))
