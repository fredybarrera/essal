#-------------------------------------------------------------------------------
# Name:         main
# Purpose:      Script que permite respaldar el contenido de una capa de arcgis online dentro de una GDB.
#               
# Author:       Fredys Barrera Artiaga <fbarrera@esri.cl>
# Created:      14-10-2020
# Copyright:    (c) fbarrera 2020
# Licence:      <your licence>
#-------------------------------------------------------------------------------

import arceditor
import arcinfo
import arcpy
import utils
import constants as const
import requests
import xml.etree.ElementTree as et
import urllib.request as ur
import traceback
import os
import time
import json
from datetime import datetime, timedelta

# Workspace
arcpy.env.workspace = const.WORKSPACE
# Sobreescribo la misma capa de salida
arcpy.env.overwriteOutput = True
# Set the preserveGlobalIds environment to True
arcpy.env.preserveGlobalIds = True
# Ruta absoluta del script
script_dir = os.path.dirname(__file__)
# Dataset
dataset = const.DATASET
# Tablas cambios
cambios = const.CAMBIOS
cambios_attach = const.CAMBIOS_ATTACH
# Tablas visitas
visitas = const.VISITAS
visitas_attach = const.VISITAS_ATTACH
# Flag para truncar o no la data
truncar = const.TRUNCAR


def main():
    """Main function."""

    timeStart = time.time()
    arcpy.AddMessage("Proceso iniciado... " + str(datetime.now()))
    utils.log("Proceso iniciado")

    print("Obteniendo token ")
    utils.log("Obteniendo token AGOL")
    token = utils.get_token()

    if truncar == 'true':
        truncate_tables()
        
    get_data_agol(token)

    end_process(timeStart)


def get_data_agol(token):
    """Obtiene la data de la capa desde Arcgis Online."""

    try:
        # Obtengo la cantidad total de registros de la capa.
        response = requests.get(
            const.URL_CAMBIOS, params=utils.get_params_count(token), headers=utils.get_headers())
        response_json = json.loads(response.text)
        cantidad_registros = response_json['count']
        print('Se descargarán un total de {} registros'.format(cantidad_registros))
        utils.log('Se descargarán un total de {} registros'.format(cantidad_registros))

        record_count = 2000
        print('Consultando lotes de {} registros'.format(record_count))
        utils.log('Consultando lotes de {} registros'.format(record_count))
        lote = 1
        flag = True

        if cantidad_registros > 0:
            # Divido el total de registros de la capa por 2000
            cantidad_paginas = get_cantidad_por_pagina(cantidad_registros, record_count)
            offset = 0
            print('Cantidad total de lotes: ', cantidad_paginas)
            utils.log('Cantidad total de lotes {}'.format(cantidad_paginas))

            for num in range(0, cantidad_paginas):
                if flag:
                    print('num: ', num)
                    print('offset: ', offset)
                    offset += record_count
                    response = requests.get(
                        const.URL_CAMBIOS, params=utils.get_params_query(token, offset, record_count), headers=utils.get_headers())
                    response = json.loads(response.text)
                    # Proceso el lote de cambios obtenidos desde la encuesta de AGOL
                    process_data(token, response, lote)
                    lote += 1
                    flag = False
    except:
        print("Failed get_data_agol (%s)" % traceback.format_exc())
        utils.error_log("Failed get_data_agol (%s)" % traceback.format_exc())


def process_data(token, response, lote):
    """
    Permite guardar los cambios en la GDB.
    Por cada cambio, obtiene y almacena los attachment, las visitas y los attachment de visitas
    """
    try:

        fc = os.path.join(arcpy.env.workspace, dataset, cambios)
        fields = []

        # Start an edit session. Must provide the workspace.
        edit = arcpy.da.Editor(arcpy.env.workspace)

        # Conservar Id. globales
        arcpy.env.preserveGlobalIds = True

        # Edit session is started without an undo/redo stack for versioned data
        #  (for second argument, use False for unversioned data)
        edit.startEditing(False, True)

        # Start an edit operation
        edit.startOperation()

        # Conservar Id. globales
        arcpy.env.preserveGlobalIds = True

        for field in response['fields']:
            fields.append(field['name'])
        fields.append('PreserveGlobalID')
        fields.append('SHAPE@XY')
        print('Descargando cambios, visitas y adjuntos del lote {0}'.format(str(lote)))
        utils.log('Descargando cambios, visitas y adjuntos del lote {0}'.format(str(lote)))
        with arcpy.da.InsertCursor(fc, fields) as cursor:
            for feature in response['features']:
                values = []
                global_id = ''
                for key, val in feature['attributes'].items():
                    if key == 'created_date' and val != None:
                        s = val/ 1000.0
                        date = datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S')
                        val = date
                    if key == 'last_edited_date' and val != None:
                        s = val/ 1000.0
                        date = datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S')
                        val = date
                    if key == 'FECHA_CAMBIO' and val != None:
                        s = float(val)/ 1000.0
                        date = datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S')
                        val = date
                    if key == 'CreationDate' and val != None:
                        s = val/ 1000.0
                        date = datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S')
                        val = date
                    if key == 'EditDate' and val != None:
                        s = val/ 1000.0
                        date = datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S')
                        val = date
                    if key == 'FECHA_EJECUCION' and val != None:
                        s = val/ 1000.0
                        date = datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S')
                        val = date
                    if key == 'GlobalID':
                        global_id = val
                    values.append(val)

                # geom = tuple(feature['geometry'].values())
                # print('geom: ', geom)
                # point = arcpy.Point(geom[1], geom[0])
                # geometry = arcpy.PointGeometry(point, out_sr)
                geometry = tuple(feature['geometry'].values())
                values.append(global_id)
                values.append(geometry)
                cursor.insertRow(tuple(values))

                # Proceso el lote de cambios, por cada uno, obtengo y almaceno los adjuntos, visitas y adjuntos de visitas.
                get_attachment_cambios(token, global_id)
                process_visitas(token, global_id)
        
        # Stop the edit operation.
        edit.stopOperation()

        # Stop the edit session and save the changes
        edit.stopEditing(True)


    except:
        print("Failed process_data (%s)" % traceback.format_exc())
        utils.error_log("Failed process_data (%s)" % traceback.format_exc())


def get_attachment_cambios(token, global_id):
    """Permite obtener los adjuntos de los cambios (medidores)."""

    try:
        url = const.URL_ATTACHMENT_CAMBIOS
        response = requests.get(
                    url, params=utils.get_params_attachments(token, global_id), headers=utils.get_headers())
        response_json = json.loads(response.text)
        save_attachment('cambios', response_json)

    except:
        print("Failed get_attachment_cambios (%s)" % traceback.format_exc())
        utils.error_log("Failed get_attachment_cambios (%s)" % traceback.format_exc())


def save_attachment(table, data):
    """Permite almacenar los adjuntos."""

    try:
        fields = ['GLOBALID', 'PreserveGlobalID', 'ATT_NAME', 'CONTENT_TYPE', 'DATA_SIZE', 'url', 'ParentGlobalID']
        values = []

        if len(data['attachmentGroups']) > 0:
            attach = data['attachmentGroups'][0]
            ParentGlobalID = attach['parentGlobalId']
            values = []
            if table == 'cambios':
                fc = os.path.join(arcpy.env.workspace, dataset, cambios_attach)
                for attachment in attach['attachmentInfos']:
                    # Guardo en la gdb de attachment de cambios
                    with arcpy.da.InsertCursor(fc, fields) as cursor:
                        values = []
                        for key, val in attachment.items():
                            # if key == 'url':
                                # url = val
                                # val = ur.urlopen(url)
                            if key != 'keywords' and key != 'exifInfo':
                                values.append(val)
                        
                        values.append(ParentGlobalID)
                        cursor.insertRow(tuple(values))
            else:
                fc = os.path.join(arcpy.env.workspace, dataset, visitas_attach)
                for attachment in attach['attachmentInfos']:
                    # Guardo en la gdb de attachment de cambios
                    with arcpy.da.InsertCursor(fc, fields) as cursor:
                        values = []
                        for key, val in attachment.items():
                            # if key == 'url':
                            #     url = val
                            #     val = ur.urlopen(url)
                            if key != 'keywords' and key != 'exifInfo':
                                values.append(val)
                        
                        values.append(ParentGlobalID)
                        cursor.insertRow(tuple(values))

    except:
        print("Failed save_attachment (%s)" % traceback.format_exc())
        utils.error_log("Failed save_attachment (%s)" % traceback.format_exc())


def process_visitas(token, global_id):
    """Permite obtener las visitas realizadas a un cambio de medidor."""

    try:
        url = const.URL_VISITAS
        response = requests.get(url, params=utils.get_params_visitas(token, global_id), headers=utils.get_headers())
        response_json = json.loads(response.text)
        fc = os.path.join(arcpy.env.workspace, dataset, visitas)
        fields = ["OBJECTID", "ParentGlobalID", "FECHA_EJECUCION", "RUT_TECNICO", "FIRMA_ORDEN", "OBSERVACIÓN_FIRMA", "DIFICULTAD_TECNICA", "OBSERVACIONES", "ESTADO_EJECUCION", "GlobalID", "created_user", "created_date", "last_edited_user", "last_edited_date", "CreationDate", "Creator", "EditDate", "Editor", "PreserveGlobalId"]
        if len(response_json['features']) > 0:
            with arcpy.da.InsertCursor(fc, fields) as cursor:
                for feature in response_json['features']:
                    values = []
                    global_id = ''
                    for key, val in feature['attributes'].items():
                        if key == 'created_date' and val != None:
                            s = val/ 1000.0
                            date = datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S')
                            val = date
                        if key == 'last_edited_date' and val != None:
                            s = val/ 1000.0
                            date = datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S')
                            val = date
                        if key == 'CreationDate' and val != None:
                            s = val/ 1000.0
                            date = datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S')
                            val = date
                        if key == 'EditDate' and val != None:
                            s = val/ 1000.0
                            date = datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S')
                            val = date
                        if key == 'FECHA_EJECUCION' and val != None:
                            s = val/ 1000.0
                            date = datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S')
                            val = date
                        if key == 'GlobalID':
                            global_id = val
                        values.append(val)
                    
                    values.append(global_id)
                    cursor.insertRow(tuple(values))
                    get_attachment_visitas(token, global_id)
    
    except:
        print("Failed process_visitas (%s)" % traceback.format_exc())
        utils.error_log("Failed process_visitas (%s)" % traceback.format_exc())


def get_attachment_visitas(token, global_id):
    """Permite obtener los adjuntos de las visitas."""
    
    try:
        url = const.URL_ATTACHMENT_VISITAS
        response = requests.get(url, params=utils.get_params_attachments(token, global_id), headers=utils.get_headers())
        response_json = json.loads(response.text)

        save_attachment('visitas', response_json)

    except:
        print("Failed get_attachment_visitas (%s)" % traceback.format_exc())
        utils.error_log("Failed get_attachment_visitas (%s)" % traceback.format_exc())


def get_cantidad_por_pagina(cantidad, datos_pagina):
    """Permite obtener la cantidad de registros por página."""

    try:
        page = divmod(cantidad, datos_pagina)
        cantidad_paginas = page[0]
        if page[0] == 0:
            cantidad_paginas = 1
        if page[1] != 0:
            cantidad_paginas = cantidad_paginas + 1
        return cantidad_paginas

    except:
        print("Failed get_cantidad_por_pagina (%s)" % traceback.format_exc())
        utils.error_log("Failed get_cantidad_por_pagina (%s)" % traceback.format_exc())

def truncate_tables():
    """Pemrite truncar las tablas del script."""
    
    try:
        print('Limpiando registros anteriores')
        utils.log('Limpiando registros anteriores')
        utils.truncate_table(cambios)
        utils.truncate_table(cambios_attach)
        utils.truncate_table(visitas)
        utils.truncate_table(visitas_attach)
        
    except:
        print("Failed truncate_tables (%s)" % traceback.format_exc())
        utils.error_log("Failed truncate_tables (%s)" % traceback.format_exc())

def end_process(timeStart):
    """Muestra y registra informacion sobre la ejecución del proceso."""

    timeEnd = time.time()
    timeElapsed = timeEnd - timeStart
    arcpy.AddMessage("Proceso finalizado... " + str(datetime.now()))
    arcpy.AddMessage("Tiempo de ejecución: " +
                     str(utils.convert_seconds(timeElapsed)))
    utils.log("Tiempo de ejecución: " +
              str(utils.convert_seconds(timeElapsed)))
    utils.log("Proceso finalizado \n")



if __name__ == '__main__':
    main()
