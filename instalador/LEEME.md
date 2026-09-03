# Generar el instalador

## Requisitos (solo en la máquina que construye)

- El entorno virtual del proyecto (`venv`) con PyInstaller instalado.
- [Inno Setup 6](https://jrsoftware.org/isdl.php) — gratuito.
- Tesseract OCR instalado (por defecto en `C:\Program Files\Tesseract-OCR`),
  con los idiomas `spa`, `eng` y `osd`. Se copia dentro del programa, así que
  quien lo instale **no necesita instalar Tesseract**.

## Cómo se hace

Doble clic en `construir.bat`, en la raíz del proyecto. Hace cuatro cosas:

1. Compila con PyInstaller usando `RenombradorPDF-Experimental.spec`.
2. Copia `src/config.json` junto al ejecutable (perfiles y regex).
3. Copia Tesseract dentro de `dist\...\tesseract\` con los tres idiomas.
4. Llama a Inno Setup y deja el instalador en `instalador\salida\`.

Si falta Inno Setup o Tesseract, el script avisa y continúa con lo que puede:
la carpeta de `dist\` queda igualmente lista para copiarse a mano.

## Qué hace el instalador en el equipo de destino

- Instala en `C:\Program Files\RenombradorPDF`.
- Crea accesos directos en el menú inicio y, si se marca, en el escritorio.
- Registra el desinstalador en "Agregar o quitar programas".
- Crea las carpetas de trabajo (`logs`, `archivos_entrada`, `archivos_salida`)
  con permiso de escritura, porque el programa guarda ahí el log y la
  configuración.

## Aviso de SmartScreen

El ejecutable no está firmado digitalmente, así que la primera vez Windows
mostrará "Windows protegió tu PC" → *Más información* → *Ejecutar de todas
formas*. Quitar ese aviso requiere un certificado de firma de código de pago.
