# Geocodificación Inversa Masiva para ArcGIS Pro
Script de Python para ArcGIS Pro 3.x que automatiza la asignación de direcciones postales a elementos de una capa de puntos, utilizando la Google Maps Geocoding API.
Desarrollado en el contexto de un proyecto de gestión de infraestructura eléctrica de baja tensión.

# 📋 Descripción
El flujo manual que automatiza este script es el siguiente:

Abrir tabla de atributos → seleccionar un poste → buscar sus coordenadas → consultar Google Maps → copiar la dirección → pegar en el campo LOCATION_ADDRESS

Con el script, ese proceso se ejecuta de forma masiva sobre todos los elementos que fueron modificados en una fecha específica y que aún no tienen dirección asignada.

# ✨ Características

Filtro por fecha de modificación — procesa únicamente los elementos editados en el día indicado, usando el campo de Editor Tracking de ArcGIS.
Filtro por dirección vacía — omite registros que ya tienen dirección calculada, evitando duplicados si el script se ejecuta varias veces en el mismo día.
Reproyección automática — convierte coordenadas de MAGNA-SIRGAS Colombia Bogotá (EPSG:3116) a WGS84 (EPSG:4326) antes de consultar la API.
Compatible con File GDB y Enterprise GDB (SDE/Oracle) — detecta el tipo de workspace automáticamente y abre sesión de edición cuando es necesario.
Formato de dirección simplificado — retorna únicamente calle y municipio: Cra. 4a # 1B-77, Municipio X.


# 🛠️ Requisitos
Requisito Versión / DetalleArcGIS Pro3.0.3 o superiorPython3.x (incluido en ArcGIS Pro)requests Incluida en el entorno de ArcGIS Pro Google Maps API Key Geocoding API habilitada

# 🔑 Configuración de la API Key

Ir a Google Cloud Console
Crear un proyecto nuevo
Habilitar Geocoding API en APIs y servicios → Biblioteca
Crear una API Key en APIs y servicios → Credenciales
Pegar la key en el parámetro GOOGLE_API_KEY del script


Costo estimado: USD $0.005 por consulta. Google otorga USD $200 de crédito gratuito mensual (~40.000 consultas). Para proyectos de infraestructura eléctrica municipal el costo es prácticamente cero.


# ⚙️ Configuración del script
Ajusta los siguientes parámetros al inicio del archivo reverse_geocode_arcgis.py:

```python
NOMBRE_CAPA     = "Estructura"              # Nombre exacto de la capa en el panel de contenidos 
NOMBRE_MAPA     = "Map"                     # Nombre exacto del mapa en ArcGIS Pro
CAMPO_DIRECCION = "LOCATION_ADDRESS"        # Campo donde se escribe la dirección
CAMPO_FECHA_MOD = "EDITION_DATE"            # Campo de fecha de modificación (Editor Tracking)
FECHA_FILTRO    = "2026-05-06"              # Día a procesar (formato YYYY-MM-DD)
GOOGLE_API_KEY  = "TU_API_KEY_AQUI"         # API Key de Google Maps Platform
```


# 🚀 Uso

Abre tu proyecto .aprx en ArcGIS Pro.
Asegúrate de que la capa de puntos esté cargada en el mapa.
Ve a Analysis → Python Window.
Abre el archivo reverse_geocode_arcgis.py o pega su contenido en la ventana.
Ajusta los parámetros según tu proyecto.
Ejecuta el script.

Ejemplo de salida esperada
```python
[INFO] Capa encontrada: 'Estructura' en mapa 'Map'
[INFO] Workspace : C:\Proyectos\Proyecto.gdb
[INFO] Tipo      : LocalDatabase
[INFO] Filtro    : EDITION_DATE >= timestamp '2026-05-06 00:00:00' AND ...
[INFO] Registros a procesar: 39
[INFO] Abriendo sesión de edición...
  [1/39] Cra. 4a # 1B-77, Pradera
  [2/39] Cl. 7 # 3-12, Pradera
  ...
  [39/39] Cra. 2 # 5-40, Pradera

[RESUMEN] 39 actualizados, 0 errores.
```
