
#-------------------------------------------------------------------------------
# Name:         constants
# Purpose:      Constantes del script
#
# Author:       Fredys Barrera Artiaga <fbarrera@esri.cl>
# Created:      12-04-2020
# Copyright:    (c) fbarrera 2020
# Licence:      <your licence>
#-------------------------------------------------------------------------------

from decouple import config

# **********************************************************************************************
# Workspace
WORKSPACE = config('FOLDER_WORKSPACE')

# **********************************************************************************************
# Credenciales para obtener token
USERNAME = config('TOKEN_USERNAME')
PASSWORD = config('TOKEN_PASSWORD')
REFERER = config('TOKEN_REFERER')
URL = config('TOKEN_URL')
# **********************************************************************************************

URL_REST_MEDIDORES = config('URL_REST_MEDIDORES')
URL_CAMBIOS = URL_REST_MEDIDORES + '/0/query'
URL_VISITAS = URL_REST_MEDIDORES + '/1/query'
URL_ATTACHMENT_CAMBIOS = URL_REST_MEDIDORES + '/0/queryAttachments'
URL_ATTACHMENT_VISITAS = URL_REST_MEDIDORES + '/1/queryAttachments'
