# -*- coding: utf-8 -*-
"""
================================================================================
reverse_geocode_arcgis.py
================================================================================

Descripción:
    Script de geocodificación inversa masiva para ArcGIS Pro 3.x.
    Lee los puntos de una capa de tipo Point almacenada en una File Geodatabase,
    reprojecta las coordenadas de MAGNA-SIRGAS Colombia Bogotá (EPSG:3116) a
    WGS84 (EPSG:4326), consulta la Google Maps Geocoding API y escribe la
    dirección resultante en un campo de texto de la misma capa.

Características principales:
    - Filtro por fecha de modificación: solo procesa elementos editados en un
      día específico, evitando recalcular registros innecesarios.
    - Filtro por dirección vacía: excluye registros que ya tienen dirección
      calculada, previniendo duplicados si el script se ejecuta varias veces.
    - Compatible con File GDB y Enterprise GDB (SDE/Oracle), detectando
      automáticamente el tipo de workspace y abriendo sesión de edición cuando
      es necesario.
    - Formato de dirección simplificado: retorna únicamente calle y municipio
      (ej. "Cra. 4a # 1B-77, Pradera"), descartando departamento y país.

Requisitos:
    - ArcGIS Pro 3.x con licencia activa
    - Librería `requests` (incluida en el entorno de Python de ArcGIS Pro)
    - API Key de Google Maps Platform con la Geocoding API habilitada
      → https://console.cloud.google.com

Configuración de la API Key:
    1. Ir a https://console.cloud.google.com
    2. Crear un proyecto nuevo
    3. Habilitar "Geocoding API" en APIs y servicios → Biblioteca
    4. Crear una API Key en APIs y servicios → Credenciales
    5. Pegar la key en el parámetro GOOGLE_API_KEY de este script

Costo estimado (Google Maps Platform):
    - Costo por consulta : USD $0.005
    - Crédito gratuito   : USD $200 / mes (~40.000 consultas gratuitas)
    - Referencia         : https://mapsplatform.google.com/pricing/

Uso:
    1. Abrir el proyecto .aprx en ArcGIS Pro
    2. Ir a Analysis → Python Window
    3. Ajustar los parámetros de la sección PARÁMETROS
    4. Ejecutar el script

Autor       : Dillan Díaz
Fecha       : 2026-05-08
Versión     : 1.0
ArcGIS Pro  : 3.0.3
================================================================================
"""

import arcpy
import requests
import time

# ─── PARÁMETROS ───────────────────────────────────────────────────────────────
NOMBRE_CAPA     = "Estructura"              # Nombre exacto de la capa en el panel de contenidos
NOMBRE_MAPA     = "Map"                     # Nombre exacto del mapa donde está la capa
CAMPO_DIRECCION = "LOCATION_ADDRESS"        # Campo de texto donde se escribe la dirección
CAMPO_FECHA_MOD = "EDITION_DATE"            # Campo de fecha de modificación (Editor Tracking)
FECHA_FILTRO    = "2026-05-06"              # Día a procesar (formato YYYY-MM-DD)
GOOGLE_API_KEY  = "TU_API_KEY_AQUI"         # API Key de Google Maps Platform
PAUSA_SEGUNDOS  = 0.05                      # Pausa entre consultas (Google permite ~50 req/seg)
# ──────────────────────────────────────────────────────────────────────────────

# Sistemas de referencia
sr_wgs84 = arcpy.SpatialReference(4326)     # WGS84 — requerido por Google Maps API


def reverse_geocode(lat: float, lon: float) -> str:
    """
    Realiza geocodificación inversa usando Google Maps Geocoding API.

    Parámetros:
        lat (float): Latitud en grados decimales (WGS84).
        lon (float): Longitud en grados decimales (WGS84).

    Retorna:
        str: Dirección formateada como "Calle, Municipio".
             Ejemplo: "Cra. 4a # 1B-77, Pradera"

    Excepciones:
        Exception: Si la API retorna un estado diferente a OK o ZERO_RESULTS.
    """
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "latlng": f"{lat},{lon}",
        "key": GOOGLE_API_KEY,
        "language": "es"
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    status = data.get("status")
    if status == "ZERO_RESULTS":
        return "Sin resultado"
    if status != "OK":
        raise Exception(f"Google API error: {status}")

    # Google retorna: "Cra. 4a # 1B-77, Pradera, Valle del Cauca, Colombia"
    # Se recortan los dos primeros componentes: "Cra. 4a # 1B-77, Pradera"
    direccion_completa = data["results"][0].get("formatted_address", "Sin resultado")
    partes = [p.strip() for p in direccion_completa.split(",")]
    return ", ".join(partes[:2]) if len(partes) >= 2 else direccion_completa


def obtener_workspace(capa) -> tuple:
    """
    Determina la ruta raíz del workspace de una capa, subiendo un nivel
    si la feature class está dentro de un Feature Dataset.

    Parámetros:
        capa: Objeto Layer de arcpy.mp.

    Retorna:
        tuple: (workspace_path, workspace_type)
               workspace_type puede ser 'LocalDatabase' o 'RemoteDatabase'.
    """
    desc_capa = arcpy.Describe(capa)
    desc_contenedor = arcpy.Describe(desc_capa.path)

    if desc_contenedor.dataType == "FeatureDataset":
        workspace = desc_contenedor.path
    else:
        workspace = desc_capa.path

    workspace_type = arcpy.Describe(workspace).workspaceType
    return workspace, workspace_type


def construir_where_clause(workspace_type: str) -> str:
    """
    Construye la cláusula WHERE para filtrar por fecha y dirección vacía,
    usando la sintaxis SQL correcta según el tipo de base de datos.

    Parámetros:
        workspace_type (str): 'LocalDatabase' para File GDB,
                              'RemoteDatabase' para SDE/Oracle/PostgreSQL.

    Retorna:
        str: Cláusula WHERE lista para usar en MakeFeatureLayer.
    """
    if workspace_type == "RemoteDatabase":
        # Sintaxis Oracle / SQL Server
        fecha_ini = f"TO_DATE('{FECHA_FILTRO} 00:00:00', 'YYYY-MM-DD HH24:MI:SS')"
        fecha_fin = f"TO_DATE('{FECHA_FILTRO} 23:59:59', 'YYYY-MM-DD HH24:MI:SS')"
    else:
        # Sintaxis File GDB
        fecha_ini = f"timestamp '{FECHA_FILTRO} 00:00:00'"
        fecha_fin = f"timestamp '{FECHA_FILTRO} 23:59:59'"

    return (
        f"{CAMPO_FECHA_MOD} >= {fecha_ini} AND "
        f"{CAMPO_FECHA_MOD} <= {fecha_fin} AND "
        f"({CAMPO_DIRECCION} IS NULL OR {CAMPO_DIRECCION} = '')"
    )


def main():
    """
    Función principal. Orquesta la búsqueda de la capa, el filtrado por fecha,
    la geocodificación inversa y la escritura de resultados en la GDB.
    """
    aprx = arcpy.mp.ArcGISProject("CURRENT")

    # ── Buscar el mapa ────────────────────────────────────────────────────────
    mapas = aprx.listMaps(NOMBRE_MAPA)
    if not mapas:
        disponibles = [m.name for m in aprx.listMaps()]
        print(f"[ERROR] No se encontró el mapa '{NOMBRE_MAPA}'.")
        print(f"[INFO]  Mapas disponibles: {disponibles}")
        return
    mapa = mapas[0]

    # ── Buscar la capa ────────────────────────────────────────────────────────
    capas = mapa.listLayers(NOMBRE_CAPA)
    if not capas:
        disponibles = [l.name for l in mapa.listLayers()]
        print(f"[ERROR] No se encontró la capa '{NOMBRE_CAPA}' en '{NOMBRE_MAPA}'.")
        print(f"[INFO]  Capas disponibles: {disponibles}")
        return
    capa = capas[0]
    print(f"[INFO] Capa encontrada: '{capa.name}' en mapa '{mapa.name}'")

    # ── Detectar workspace ────────────────────────────────────────────────────
    workspace, workspace_type = obtener_workspace(capa)
    print(f"[INFO] Workspace : {workspace}")
    print(f"[INFO] Tipo      : {workspace_type}")

    # ── Construir filtro ──────────────────────────────────────────────────────
    where_clause = construir_where_clause(workspace_type)
    print(f"[INFO] Filtro    : {where_clause}")

    # ── Crear capa temporal filtrada ──────────────────────────────────────────
    if arcpy.Exists("capa_filtrada_temp"):
        arcpy.management.Delete("capa_filtrada_temp")

    capa_filtrada = arcpy.management.MakeFeatureLayer(
        capa, "capa_filtrada_temp", where_clause
    )
    total = int(arcpy.management.GetCount(capa_filtrada).getOutput(0))
    print(f"[INFO] Registros a procesar: {total}")

    if total == 0:
        print("[INFO] No hay registros para procesar. Verifica la fecha o el campo de dirección.")
        return

    # ── Abrir sesión de edición ───────────────────────────────────────────────
    print(f"[INFO] Abriendo sesión de edición...")
    editor = arcpy.da.Editor(workspace)
    editor.startEditing(False, False)
    editor.startOperation()

    procesados = 0
    errores    = 0

    try:
        with arcpy.da.UpdateCursor(capa_filtrada, [CAMPO_DIRECCION, "SHAPE@"]) as cursor:
            for row in cursor:
                geom = row[1]
                if geom is None:
                    print(f"  [OMITIDO] Geometría nula en registro {procesados + errores + 1}")
                    errores += 1
                    continue

                # Reproyectar MAGNA-SIRGAS Bogotá (EPSG:3116) → WGS84 (EPSG:4326)
                try:
                    punto_wgs84 = geom.projectAs(sr_wgs84, "BOGOTA_To_WGS_1984")
                except Exception:
                    punto_wgs84 = geom.projectAs(sr_wgs84)

                lon = punto_wgs84.firstPoint.X
                lat = punto_wgs84.firstPoint.Y

                try:
                    direccion = reverse_geocode(lat, lon)
                    row[0] = direccion
                    cursor.updateRow(row)
                    procesados += 1
                    print(f"  [{procesados}/{total}] {direccion}")
                except Exception as e:
                    errores += 1
                    print(f"  [ERROR] ({lat:.5f}, {lon:.5f}) → {e}")

                time.sleep(PAUSA_SEGUNDOS)

        editor.stopOperation()
        editor.stopEditing(True)
        print(f"\n[RESUMEN] {procesados} actualizados, {errores} errores.")

    except Exception as e:
        editor.stopOperation()
        editor.stopEditing(False)
        print(f"\n[ERROR CRÍTICO] Se revirtieron los cambios: {e}")


# ── Punto de entrada ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
