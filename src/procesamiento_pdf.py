# src/procesamiento_pdf.py

from PIL import Image, ImageTk
import pytesseract
import fitz
from pathlib import Path
import logging
import sys
import os

import config


if getattr(sys, "frozen", False):
    tesseract_path = Path(sys.executable).parent / "tesseract" / "tesseract.exe"
    pytesseract.pytesseract.tesseract_cmd = str(tesseract_path)
    os.environ["TESSDATA_PREFIX"] = str(Path(sys.executable).parent / "tesseract" / "tessdata")
else:
    t_cmd = config.get_tesseract_cmd()
    if t_cmd and Path(t_cmd).exists():
        pytesseract.pytesseract.tesseract_cmd = t_cmd
    else:
        logging.warning("Ruta de Tesseract OCR no valida o no configurada.")


def extraer_texto_de_informe(ruta_informe: Path) -> str:
    texto_completo = ""
    logging.info(f"Iniciando extraccion multi-pagina para '{ruta_informe.name}'.")

    try:
        with fitz.open(ruta_informe) as documento:
            num_paginas = len(documento)
            if num_paginas == 0:
                logging.error(f"El PDF '{ruta_informe.name}' no tiene paginas.")
                return ""

            logging.info(f"El informe tiene {num_paginas} pagina(s).")

            usar_capa_texto = config.PREFERIR_CAPA_TEXTO
            ocr_usado = False

            for i in range(num_paginas):
                pagina = documento.load_page(i)
                logging.info(f"Procesando pagina {i + 1} de {num_paginas}...")

                texto_pagina = ""
                if usar_capa_texto:
                    texto_capa = pagina.get_text("text")
                    palabras = texto_capa.split()
                    if len(palabras) > 5:
                        texto_pagina = texto_capa
                        logging.info(f"Pagina {i + 1}: texto extraido de capa ({len(palabras)} palabras).")
                    else:
                        logging.info(f"Pagina {i + 1}: capa de texto insuficiente, aplicando OCR.")

                if not texto_pagina:
                    ocr_usado = True
                    dpi = config.OCR_DPI
                    matriz = fitz.Matrix(dpi / 72, dpi / 72)
                    pixmap = pagina.get_pixmap(matrix=matriz)
                    imagen = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                    texto_pagina = pytesseract.image_to_string(imagen, lang=config.OCR_LANG)

                texto_completo += texto_pagina + "\n--- Fin de Pagina ---\n"

            if ocr_usado:
                logging.info("OCR fue necesario para al menos una pagina.")
            else:
                logging.info("Todas las paginas procesadas desde capa de texto (sin OCR).")

            return texto_completo

    except Exception as e:
        logging.error(f"Error inesperado al procesar el informe '{ruta_informe.name}': {e}", exc_info=True)
        return ""


def contar_paginas(ruta_pdf: Path) -> int:
    """Numero de paginas del PDF, 0 si no se puede abrir."""
    try:
        with fitz.open(ruta_pdf) as documento:
            return len(documento)
    except Exception as e:
        logging.error(f"No se pudo contar las paginas de '{Path(ruta_pdf).name}': {e}")
        return 0


def generar_imagen_tk_de_pdf(ruta_pdf: Path, zoom_factor: float = 1.0,
                             numero_pagina: int = 0) -> ImageTk.PhotoImage | None:
    try:
        with fitz.open(ruta_pdf) as documento:
            if not documento or len(documento) == 0:
                return None
            indice = max(0, min(numero_pagina, len(documento) - 1))
            pagina = documento.load_page(indice)
            matriz = fitz.Matrix(zoom_factor, zoom_factor)
            pixmap = pagina.get_pixmap(matrix=matriz)
            imagen = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            return ImageTk.PhotoImage(imagen)
    except Exception as e:
        logging.error(f"Error al generar la vista previa de '{ruta_pdf.name}': {e}", exc_info=True)
        return None
