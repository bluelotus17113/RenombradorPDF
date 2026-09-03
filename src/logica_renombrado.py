# src/logica_renombrado.py

import pandas as pd
import os
import re
from pathlib import Path
import logging

from procesamiento_pdf import extraer_texto_de_informe
import config


NOMBRE_SIN_DATOS = "SIN DATOS DEL INFORME"
NOMBRE_SIN_ARCHIVO = "ARCHIVO_NO_ASIGNADO"


CARACTERES_INVALIDOS = '\\/:*?"<>|'


def nombre_reporte_por_defecto() -> str:
    return f"reporte_renombrado_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"


def sanitizar_nombre_reporte(nombre: str) -> str:
    """Convierte lo que escriba el usuario en un nombre de archivo .xlsx valido."""
    limpio = "".join("_" if c in CARACTERES_INVALIDOS else c for c in str(nombre))
    limpio = limpio.strip().rstrip(". ").strip()
    if limpio.lower().endswith(".xlsx"):
        limpio = limpio[:-5].strip().rstrip(". ").strip()
    if not limpio:
        limpio = nombre_reporte_por_defecto()
    return limpio[:120] + ".xlsx"


def tiene_archivo(row) -> bool:
    """True si la fila tiene un PDF asignado. Sin archivo no se propone nombre."""
    ruta = row.get("Ruta_Archivo_Original")
    return pd.notna(ruta) and str(ruta).strip() != ""


def _extraer_por_filas(texto: str) -> list[dict]:
    """
    Parsing por filas: cada linea que empieza con una fecha se considera
    un registro con acta + identificacion vinculados.
    Detecta secciones automaticamente para marcar _CO.
    """
    lineas = texto.splitlines()
    registros = []
    seccion_actual = ""

    for linea in lineas:
        match_seccion = config.SECCION_HEADER_RE.search(linea)
        if match_seccion:
            seccion_actual = (match_seccion.group(1) or match_seccion.group(2) or "").upper()

        fecha_match = config.REGEX_FECHA.search(linea)
        if not fecha_match:
            continue

        resto = linea[fecha_match.end():]
        numeros = config.REGEX_IDENTIFICACION.findall(resto)
        numeros = [n for n in numeros if n not in config.NUMEROS_EXCLUIDOS]

        actas_en_linea = config.REGEX_ACTA.findall(resto)
        actas_en_linea = [a for a in actas_en_linea if a not in config.NUMEROS_EXCLUIDOS]

        if actas_en_linea and numeros:
            registros.append({
                "Acta": actas_en_linea[0],
                "Identificacion": numeros[0],
                "Seccion": seccion_actual,
                "EsContributivo": any(
                    kw in seccion_actual
                    for kw in config.SECCION_CO_KEYWORDS
                )
            })
        elif len(numeros) >= 2:
            registros.append({
                "Acta": numeros[0],
                "Identificacion": numeros[1],
                "Seccion": seccion_actual,
                "EsContributivo": any(
                    kw in seccion_actual
                    for kw in config.SECCION_CO_KEYWORDS
                )
            })

    logging.info(f"Extraccion por filas: {len(registros)} registros encontrados.")
    return registros


def _extraer_dos_listas(texto: str) -> list[dict]:
    """
    Metodo original de dos listas (actas por un lado, IDs por otro).
    Se mantiene como fallback configurable.
    """
    lista_actas = [a for a in config.REGEX_ACTA.findall(texto) if a not in config.NUMEROS_EXCLUIDOS]
    lista_ids = [i for i in config.REGEX_IDENTIFICACION.findall(texto) if i not in config.NUMEROS_EXCLUIDOS]

    logging.info(f"Actas (dos listas): {lista_actas}")
    logging.info(f"IDs (dos listas): {lista_ids}")

    num_filas = min(len(lista_actas), len(lista_ids))
    registros = []
    for i in range(num_filas):
        registros.append({
            "Acta": lista_actas[i],
            "Identificacion": lista_ids[i],
            "Seccion": "",
            "EsContributivo": False
        })

    return registros


def procesar_tabla_de_informe(ruta_pdf: Path, progreso=None) -> pd.DataFrame:
    logging.info("Iniciando extraccion de tabla de informe.")

    texto_ocr = extraer_texto_de_informe(ruta_pdf, progreso=progreso)
    if not texto_ocr:
        logging.error("La extraccion de texto devolvio una cadena vacia.")
        return pd.DataFrame()

    logging.info("--- INICIO DEL TEXTO EXTRAIDO ---")
    logging.info(texto_ocr)
    logging.info("--- FIN DEL TEXTO EXTRAIDO ---")

    modo = config.MODO_EXTRACCION
    if modo == "por_filas":
        registros = _extraer_por_filas(texto_ocr)
    else:
        registros = _extraer_dos_listas(texto_ocr)

    if not registros:
        logging.warning("No se encontraron registros validos.")
        return pd.DataFrame()

    df = pd.DataFrame(registros)
    df_limpio = df.drop_duplicates(subset=["Acta", "Identificacion"], keep="first")
    df_final = df_limpio.reset_index(drop=True)

    logging.info(f"DataFrame final tiene {len(df_final)} filas unicas.")
    co_count = df_final["EsContributivo"].sum() if "EsContributivo" in df_final.columns else 0
    logging.info(f"Registros marcados como CONTRIBUTIVO: {co_count}")
    return df_final


def _generar_nombre(row, doc_type=None):
    if doc_type is None:
        doc_type = config.DOC_TYPE_DEFAULT

    if not row.get("Acta") or not row.get("Identificacion"):
        return None

    nombre = config.NOMBRE_PLANTILLA.format(
        DocType=doc_type,
        Identificacion=row["Identificacion"],
        Acta=row["Acta"]
    )

    co_part, co_ext = os.path.splitext(nombre)
    if row.get("EsContributivo"):
        if not co_part.endswith("_CO"):
            co_part += "_CO"
        nombre = co_part + co_ext
    else:
        for prefix in config.DOC_TYPES:
            if co_part.endswith(f"_{prefix}_CO") or co_part == f"{prefix}_CO":
                co_part = co_part[:-3]
                nombre = co_part + co_ext
                break

    return nombre


def generar_guia_completa(df_informe: pd.DataFrame, rutas_pdfs_a_renombrar: list[Path]) -> pd.DataFrame:
    if df_informe.empty and not rutas_pdfs_a_renombrar:
        return pd.DataFrame()

    archivos_ordenados = sorted(rutas_pdfs_a_renombrar)
    num_filas_informe = len(df_informe)
    num_archivos = len(archivos_ordenados)

    if "EsContributivo" not in df_informe.columns:
        df_informe["EsContributivo"] = False
    if "Seccion" not in df_informe.columns:
        df_informe["Seccion"] = ""

    df_informe["Ruta_Archivo_Original"] = pd.Series([str(p) for p in archivos_ordenados[:num_filas_informe]])

    def generar_nombre(row):
        if not tiene_archivo(row):
            return NOMBRE_SIN_ARCHIVO
        nombre = _generar_nombre(row)
        if nombre is None:
            return NOMBRE_SIN_DATOS
        return nombre

    df_informe["Nuevo_Nombre_Propuesto"] = df_informe.apply(generar_nombre, axis=1)

    if num_archivos > num_filas_informe:
        logging.info(f"Añadiendo {num_archivos - num_filas_informe} archivos sobrantes.")
        archivos_sobrantes = archivos_ordenados[num_filas_informe:]
        nuevas_filas = []
        for path in archivos_sobrantes:
            nuevas_filas.append({
                "Acta": "",
                "Identificacion": "",
                "Ruta_Archivo_Original": str(path),
                "Nuevo_Nombre_Propuesto": NOMBRE_SIN_DATOS,
                "EsContributivo": False,
                "Seccion": ""
            })

        if nuevas_filas:
            df_sobrantes = pd.DataFrame(nuevas_filas)
            df_informe = pd.concat([df_informe, df_sobrantes], ignore_index=True)

    return df_informe


def ejecutar_renombrado(df_final: pd.DataFrame, destino_path: Path,
                        nombre_reporte: str | None = None) -> tuple[int, int, Path | None]:
    exitosos = 0
    fallidos = 0
    destino_path.mkdir(parents=True, exist_ok=True)
    logging.info(f"Archivos se guardaran en: {destino_path}")

    resultados = []

    for index, row in df_final.iterrows():
        acta = row.get("Acta", "")
        identificacion = row.get("Identificacion", "")
        seccion = row.get("Seccion", "")
        nombre_propuesto = row.get("Nuevo_Nombre_Propuesto", "")
        ruta_str = row.get("Ruta_Archivo_Original")

        tipo_doc = ""
        if nombre_propuesto not in (NOMBRE_SIN_DATOS, NOMBRE_SIN_ARCHIVO):
            parts = nombre_propuesto.split("_")
            if parts and parts[0]:
                tipo_doc = parts[0]

        if pd.isna(ruta_str) or str(ruta_str).strip() == "":
            resultados.append({
                "Nombre_Original": "",
                "Nombre_Nuevo": "",
                "Tipo": "",
                "Acta": acta,
                "Identificacion": identificacion,
                "Seccion": seccion,
                "Resultado": "Vacio (sin archivo asociado)"
            })
            continue

        if nombre_propuesto in (NOMBRE_SIN_DATOS, NOMBRE_SIN_ARCHIVO):
            resultados.append({
                "Nombre_Original": Path(ruta_str).name,
                "Nombre_Nuevo": nombre_propuesto,
                "Tipo": tipo_doc,
                "Acta": acta,
                "Identificacion": identificacion,
                "Seccion": seccion,
                "Resultado": "Sin datos del informe"
            })
            continue

        ruta_original = Path(ruta_str)
        ruta_destino = destino_path / nombre_propuesto

        try:
            if ruta_original.exists():
                os.rename(ruta_original, ruta_destino)
                exitosos += 1
                resultados.append({
                    "Nombre_Original": ruta_original.name,
                    "Nombre_Nuevo": nombre_propuesto,
                    "Tipo": tipo_doc,
                    "Acta": acta,
                    "Identificacion": identificacion,
                    "Seccion": seccion,
                    "Resultado": "Exitoso"
                })
            else:
                logging.warning(f"No se encontro el archivo '{ruta_original.name}'.")
                fallidos += 1
                resultados.append({
                    "Nombre_Original": ruta_original.name,
                    "Nombre_Nuevo": nombre_propuesto,
                    "Tipo": tipo_doc,
                    "Acta": acta,
                    "Identificacion": identificacion,
                    "Seccion": seccion,
                    "Resultado": "Fallido (archivo no encontrado)"
                })
        except Exception as e:
            logging.error(f"Error al renombrar '{ruta_original.name}': {e}", exc_info=True)
            fallidos += 1
            resultados.append({
                "Nombre_Original": ruta_original.name,
                "Nombre_Nuevo": nombre_propuesto,
                "Tipo": tipo_doc,
                "Acta": acta,
                "Identificacion": identificacion,
                "Seccion": seccion,
                "Resultado": f"Fallido ({e})"
            })

    df_resultados = pd.DataFrame(resultados)
    archivo_reporte = sanitizar_nombre_reporte(nombre_reporte or nombre_reporte_por_defecto())
    reporte_path = destino_path / archivo_reporte

    # No pisar un reporte existente: se agrega un consecutivo.
    base = reporte_path.stem
    consecutivo = 2
    while reporte_path.exists():
        reporte_path = destino_path / f"{base}_{consecutivo}.xlsx"
        consecutivo += 1
    df_resultados.to_excel(reporte_path, index=False, engine="openpyxl")
    logging.info(f"Reporte Excel generado: {reporte_path}")

    return exitosos, fallidos, reporte_path
