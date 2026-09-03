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
5. **Ejecutar** — muestra un resumen (listos, sin archivo, sin datos, nombres duplicados),
   pide la carpeta de destino y el nombre del reporte, renombra y genera el Excel.

La tabla colorea las filas por estado (rojo sin archivo, amarillo sin datos, morado duplicado),
la vista previa permite recorrer todas las páginas del PDF, y `Ctrl+Z` deshace hasta 30 pasos.
El informe se procesa en segundo plano con barra de progreso, así que la ventana nunca se
congela. Pulsando `F1` se abre la ayuda con el flujo completo y los atajos.

## Estructura

```
src/
  gui.py                 Interfaz Tkinter (RenamerApp) y diálogo de configuración por perfiles
  logica_renombrado.py   Extracción de registros, generación de nombres y ejecución del renombrado
  procesamiento_pdf.py   Lectura de PDFs con PyMuPDF, OCR con Tesseract y vista previa
  config.py              Perfiles, preferencias de uso y rutas de trabajo
  config.json            Perfiles guardados y preferencias (última carpeta, tamaño de ventana)
assets/
  icono.ico              Icono de la aplicación y del ejecutable
instalador/
  RenombradorPDF.iss     Script de Inno Setup
construir.bat            Compila, empaqueta Tesseract y genera el instalador
version_info.txt         Metadatos de versión del .exe
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

## Compilar y distribuir

Doble clic en `construir.bat` (o desde una consola en la raíz del proyecto). El script:

1. Compila con PyInstaller usando `RenombradorPDF-Experimental.spec` (icono y metadatos de
   versión incluidos).
2. Copia `src/config.json` junto al ejecutable.
3. Empaqueta Tesseract dentro de `dist/.../tesseract/` con los idiomas `spa`, `eng` y `osd`,
   de modo que **quien reciba el programa no necesita instalar Tesseract**.
4. Genera el instalador con [Inno Setup](https://jrsoftware.org/isdl.php) en
   `instalador/salida/`.

Si falta Inno Setup o Tesseract, avisa y continúa: la carpeta de `dist/` queda igualmente lista
para copiarse a mano. Ver `instalador/LEEME.md` para el detalle.

El ejecutable no está firmado, así que la primera ejecución muestra el aviso de SmartScreen
("Windows protegió tu PC" → Más información → Ejecutar de todas formas).

## Configuración por perfiles

Desde el botón **Configuración** se editan perfiles con: regex de acta, identificación y fecha,
plantilla del nombre, modo de extracción, preferencia de capa de texto, DPI del OCR y la lista de
números excluidos. Los perfiles se guardan en `src/config.json`.
