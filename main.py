#-------------------------------------------------------------------------------
# Name:         main
# Purpose:      Script que permite respaldar el contenido de una capa de arcgis online dentro de una GDB.
#               
# Author:       Fredys Barrera Artiaga <fbarrera@esri.cl>
# Created:      14-10-2020
# Copyright:    (c) fbarrera 2020
# Licence:      <your licence>
#-------------------------------------------------------------------------------

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


def main():
    """Main function."""

    timeStart = time.time()
    arcpy.AddMessage("Proceso iniciado... " + str(datetime.now()))
    utils.log("Proceso iniciado")

    print("Obteniendo token... ")
    token = utils.get_token()

    print('token: ', token)
    print('URL_CAMBIOS: ', const.URL_CAMBIOS)
    print('URL_VISITAS: ', const.URL_VISITAS)

    get_data_agol(token)

    end_process(timeStart)


def get_data_agol(token):
    """Obtiene la data de la capa desde Arcgis Online."""

    try:
        response = requests.get(
            const.URL_CAMBIOS, params=utils.get_params_count(token), headers=utils.get_headers())
        response_json = json.loads(response.text)
        cantidad_registros = response_json['count']
        print('cantidad_registros: ', cantidad_registros)
        record_count = 2000

        if cantidad_registros > 0:
            cantidad_paginas = get_cantidad_por_pagina(cantidad_registros, record_count)
            offset = 0
            print('cantidad_paginas: ', cantidad_paginas)
            for num in range(0, cantidad_paginas):
                print('num: ', num)
                print('offset: ', offset)
                offset += record_count
                response = requests.get(
                    const.URL_CAMBIOS, params=utils.get_params_query(token, offset, record_count), headers=utils.get_headers())
                response_json = json.loads(response.text)
                print('response_json: ', response_json)

                # Aca debería hacer el insert
                # envio el lote de 2000 registros a la funcion y los recorro uno por uno para obtener las visitas




    except:
        print("Failed get_data_agol (%s)" %
              traceback.format_exc())
        utils.error_log("Failed get_data_agol (%s)" %
                        traceback.format_exc())


def get_cantidad_por_pagina(cantidad, datos_pagina):
    try:
        page = divmod(cantidad, datos_pagina)
        cantidad_paginas = page[0]
        if page[0] == 0:
            cantidad_paginas = 1
        if page[1] != 0:
            cantidad_paginas = cantidad_paginas + 1
        return cantidad_paginas

    except:
        print("Failed get_cantidad_por_pagina (%s)" %
            traceback.format_exc())
        utils.error_log("Failed get_cantidad_por_pagina (%s)" %
            traceback.format_exc())


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
