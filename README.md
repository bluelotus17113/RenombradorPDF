# RenombradorPDF

Aplicación de escritorio (Python + Tkinter) que renombra PDFs en lote a partir de un **informe en PDF**.

Lee el informe, extrae los pares **Acta + Identificación**, los empareja en orden con los PDFs
seleccionados y los renombra siguiendo una plantilla configurable
(`{DocType}_{Identificacion}_{Acta}.pdf`), marcando con sufijo `_CO` los registros del régimen
**Contributivo**. Al terminar genera un reporte en Excel con los renombrados exitosos y fallidos.

## Flujo de trabajo

1. **Cargar Informe** — se extrae el texto del PDF con PyMuPDF; si la capa de texto de una página
   es insuficiente (menos de 5 palabras), esa página se procesa con OCR (Tesseract, idioma `spa`).
2. **Extracción de registros** — dos modos:
   - `por_filas` (recomendado): cada línea que empieza con una fecha se toma como un registro, con
     su acta e identificación vinculadas. Detecta los encabezados de sección para marcar
     `EsContributivo`.
   - `dos_listas` (fallback): recolecta actas e identificaciones por separado y las une por posición.
   Los números de la lista de excluidos (años, NIT, teléfonos) se ignoran.
3. **Cargar PDFs** — los archivos se vinculan en orden con las filas del informe.
4. **Revisión** — tabla editable (Acta / Identificación / Tipo / Nuevo nombre propuesto) con vista
   previa del PDF (zoom con la rueda, desplazamiento arrastrando), reordenar filas, intercambiar,
   desplazar archivos, editar celdas, añadir filas manuales y cambiar tipo de documento o sufijo `_CO`.
5. **Ejecutar** — renombra hacia la carpeta destino y genera `reporte_renombrado_<fecha>.xlsx`.

## Estructura

```
src/
  gui.py                 Interfaz Tkinter (RenamerApp) y diálogo de configuración por perfiles
  logica_renombrado.py   Extracción de registros, generación de nombres y ejecución del renombrado
  procesamiento_pdf.py   Lectura de PDFs con PyMuPDF, OCR con Tesseract y vista previa
  config.py              Carga de perfiles y rutas de trabajo
  config.json            Perfiles guardados (regex, plantilla, números excluidos)
```

Carpetas de trabajo que crea la app junto al proyecto (o junto al `.exe`):
`archivos_entrada/`, `archivos_salida/renombrados/`, `logs/`.

## Requisitos

- Python 3.11+
- Dependencias: `pip install -r requirements.txt` (pandas, openpyxl, PyMuPDF, pytesseract, Pillow)
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) con el paquete de idioma español
  (`spa`), solo necesario si los PDFs son escaneados. Fuera del ejecutable, la ruta se indica con
  la clave `tesseract_cmd` en `src/config.json`.

## Uso

```bash
pip install -r requirements.txt
python src/gui.py
```

## Compilar el ejecutable

```bash
pyinstaller RenombradorPDF-Experimental.spec
```

El build queda en `dist/`. Para que el OCR funcione en el ejecutable, copiar Tesseract dentro de
`dist/RenombradorPDF-Experimental/tesseract/` (con su carpeta `tessdata`).

## Configuración por perfiles

Desde el botón **Configuración** se editan perfiles con: regex de acta, identificación y fecha,
plantilla del nombre, modo de extracción, preferencia de capa de texto, DPI del OCR y la lista de
números excluidos. Los perfiles se guardan en `src/config.json`.
