# src/config.py

import sys
from pathlib import Path
import re
import json
import logging

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.parent

CONFIG_PATH = BASE_DIR / "src" / "config.json"

if not CONFIG_PATH.exists():
    CONFIG_PATH = BASE_DIR / "config.json"

INPUT_DIR = BASE_DIR / "archivos_entrada"
INFORME_DIR = INPUT_DIR / "informe"
PDFS_A_RENOMBRAR_DIR = INPUT_DIR / "pdfs_a_renombrar"
OUTPUT_DIR = BASE_DIR / "archivos_salida"
RENAMED_DIR = OUTPUT_DIR / "renombrados"

LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "app_log.log"

DEFAULTS = {
    "regex_acta": r"\b(\d{4,6})\b",
    "regex_identificacion": r"\b(\d{7,11})\b",
    "regex_fecha": r"\b\d{2}/\d{2}/\d{4}\b",
    "nombre_plantilla": "{DocType}_{Identificacion}_{Acta}.pdf",
    "doc_types": ["CC", "TI", "PT", "RC"],
    "doc_type_default": "CC",
    "numeros_excluidos": ["2025", "2026"],
    "secciones_contributivo_keywords": ["CONTRIBUTIVO"],
    "secciones_header_regex": r"Administradora\s+[A-ZÁÉÍÓÚÑ]+\s+EPS\s+S\.?A\.?(?:\s*[-,]\s*(\w+)\s+Contrato|\s+Contrato\s+(\S+))",
    "modo_extraccion": "por_filas",
    "preferir_capa_texto": True,
    "ocr_dpi": 300,
    "ocr_lang": "spa",
}


def _load_json_config():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"No se pudo cargar config.json ({e}), usando valores por defecto.")
    return {}


_json_cfg = _load_json_config()


def get_perfiles():
    return _json_cfg.get("perfiles", {})


def get_perfil_activo_nombre():
    return _json_cfg.get("perfil_activo", list(get_perfiles().keys())[0] if get_perfiles() else None)


def set_perfil_activo(nombre):
    global _json_cfg
    _json_cfg["perfil_activo"] = nombre
    _apply_perfil()


def _apply_perfil():
    global REGEX_ACTA, REGEX_IDENTIFICACION, REGEX_FECHA, NOMBRE_PLANTILLA
    global DOC_TYPES, DOC_TYPE_DEFAULT, NUMEROS_EXCLUIDOS
    global SECCION_HEADER_RE, SECCION_CO_KEYWORDS
    global MODO_EXTRACCION, PREFERIR_CAPA_TEXTO, OCR_DPI, OCR_LANG

    perfiles = get_perfiles()
    nombre = get_perfil_activo_nombre()
    perfil = perfiles.get(nombre, {}) if nombre else {}

    def cfg(key):
        return perfil.get(key, DEFAULTS.get(key))

    REGEX_ACTA = re.compile(cfg("regex_acta"))
    REGEX_IDENTIFICACION = re.compile(cfg("regex_identificacion"))
    REGEX_FECHA = re.compile(cfg("regex_fecha"))
    NOMBRE_PLANTILLA = cfg("nombre_plantilla")
    DOC_TYPES = cfg("doc_types")
    DOC_TYPE_DEFAULT = cfg("doc_type_default")
    NUMEROS_EXCLUIDOS = set(cfg("numeros_excluidos"))
    SECCION_CO_KEYWORDS = cfg("secciones_contributivo_keywords")
    SECCION_HEADER_RE = re.compile(cfg("secciones_header_regex"), re.IGNORECASE)
    MODO_EXTRACCION = cfg("modo_extraccion")
    PREFERIR_CAPA_TEXTO = cfg("preferir_capa_texto")
    OCR_DPI = cfg("ocr_dpi")
    OCR_LANG = cfg("ocr_lang")


def get_tesseract_cmd():
    return _json_cfg.get("tesseract_cmd", DEFAULTS.get("tesseract_cmd"))


def _guardar_config():
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(_json_cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.warning(f"No se pudo guardar config.json ({e}).")


def get_pref(clave, defecto=None):
    """Preferencias de uso (ultimas carpetas, tamano de ventana...)."""
    return _json_cfg.get("preferencias", {}).get(clave, defecto)


def set_pref(clave, valor, guardar=True):
    prefs = _json_cfg.setdefault("preferencias", {})
    prefs[clave] = valor
    if guardar:
        _guardar_config()


def save_perfil(nombre, datos):
    perfiles = get_perfiles()
    perfiles[nombre] = datos
    _json_cfg["perfiles"] = perfiles
    _json_cfg["perfil_activo"] = nombre
    _guardar_config()
    _apply_perfil()


def delete_perfil(nombre):
    perfiles = get_perfiles()
    if nombre in perfiles:
        del perfiles[nombre]
        _json_cfg["perfiles"] = perfiles
        if get_perfil_activo_nombre() == nombre and perfiles:
            _json_cfg["perfil_activo"] = list(perfiles.keys())[0]
        _guardar_config()
        _apply_perfil()
        return True
    return False


_apply_perfil()
