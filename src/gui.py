# src/gui.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import logging
import os
import pandas as pd
import re
import json

import config
import procesamiento_pdf
import logica_renombrado


def setup_logging():
    log_dir = config.LOG_DIR
    log_file = config.LOG_FILE
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", filename=log_file, filemode="w")
    logging.info("Aplicacion iniciada.")


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Configuracion y Perfiles")
        self.geometry("650x550")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.parent = parent

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        frame_perfiles = ttk.Frame(notebook, padding="10")
        notebook.add(frame_perfiles, text="Perfiles")
        self._build_perfiles_tab(frame_perfiles)

        frame_extraccion = ttk.Frame(notebook, padding="10")
        notebook.add(frame_extraccion, text="Extraccion")
        self._build_extraccion_tab(frame_extraccion)

        frame_excluidos = ttk.Frame(notebook, padding="10")
        notebook.add(frame_excluidos, text="Numeros Excluidos")
        self._build_excluidos_tab(frame_excluidos)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(btn_frame, text="Guardar y Cerrar", command=self._save_and_close).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def _build_perfiles_tab(self, frame):
        perfil_frame = ttk.LabelFrame(frame, text="Perfiles guardados", padding="5")
        perfil_frame.pack(fill=tk.X, pady=5)

        list_frame = ttk.Frame(perfil_frame)
        list_frame.pack(fill=tk.X)

        self.perfil_listbox = tk.Listbox(list_frame, height=5)
        self.perfil_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.perfil_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.perfil_listbox.configure(yscrollcommand=scrollbar.set)

        self._refresh_perfil_list()

        btn_row = ttk.Frame(perfil_frame)
        btn_row.pack(fill=tk.X, pady=5)
        ttk.Button(btn_row, text="Cargar", command=self._load_perfil).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Eliminar", command=self._delete_perfil).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Nuevo desde actual", command=self._new_perfil).pack(side=tk.LEFT, padx=2)

        ttk.Label(frame, text="El perfil activo determina regex, plantilla y deteccion de secciones.", wraplength=600).pack(fill=tk.X, pady=10)

    def _refresh_perfil_list(self):
        self.perfil_listbox.delete(0, tk.END)
        perfiles = config.get_perfiles()
        activo = config.get_perfil_activo_nombre()
        for nombre, datos in perfiles.items():
            label = f"{nombre} {'(activo)' if nombre == activo else ''}"
            self.perfil_listbox.insert(tk.END, label)

    def _load_perfil(self):
        sel = self.perfil_listbox.curselection()
        if not sel:
            messagebox.showinfo("Info", "Selecciona un perfil primero.", parent=self)
            return
        nombre = self.perfil_listbox.get(sel[0]).replace(" (activo)", "")
        config.set_perfil_activo(nombre)
        self._refresh_perfil_list()
        self.parent.status_var.set(f"Perfil activo: {nombre}")

    def _delete_perfil(self):
        sel = self.perfil_listbox.curselection()
        if not sel:
            return
        nombre = self.perfil_listbox.get(sel[0]).replace(" (activo)", "")
        perfiles = config.get_perfiles()
        if len(perfiles) <= 1:
            messagebox.showwarning("Aviso", "Debe haber al menos un perfil.", parent=self)
            return
        if messagebox.askyesno("Confirmar", f"Eliminar perfil '{nombre}'?", parent=self):
            config.delete_perfil(nombre)
            self._refresh_perfil_list()

    def _new_perfil(self):
        nombre = tk.simpledialog.askstring("Nuevo perfil", "Nombre del nuevo perfil:", parent=self)
        if not nombre:
            return
        perfil_actual = config.get_perfiles().get(config.get_perfil_activo_nombre(), {})
        perfil_nuevo = dict(perfil_actual)
        perfil_nuevo["nombre"] = nombre
        config.save_perfil(nombre, perfil_nuevo)
        self._refresh_perfil_list()
        self.parent.status_var.set(f"Perfil '{nombre}' creado.")

    def _build_extraccion_tab(self, frame):
        fields = [
            ("regex_acta", "Regex Acta:", 3),
            ("regex_identificacion", "Regex Identificacion:", 3),
            ("regex_fecha", "Regex Fecha:", 3),
            ("nombre_plantilla", "Plantilla Nombre:", 3),
        ]
        self.extr_entries = {}
        for i, (key, label, cols) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", pady=3)
            e = ttk.Entry(frame, width=60)
            perfil = config.get_perfiles().get(config.get_perfil_activo_nombre(), {})
            e.insert(0, perfil.get(key, config.DEFAULTS[key]))
            e.grid(row=i, column=1, sticky="ew", pady=3)
            self.extr_entries[key] = e

        ttk.Label(frame, text="Modo extraccion:").grid(row=len(fields), column=0, sticky="w", pady=3)
        self.modo_var = tk.StringVar(value=config.MODO_EXTRACCION)
        ttk.Radiobutton(frame, text="Por filas (recomendado)", variable=self.modo_var, value="por_filas").grid(row=len(fields), column=1, sticky="w")
        ttk.Radiobutton(frame, text="Dos listas", variable=self.modo_var, value="dos_listas").grid(row=len(fields)+1, column=1, sticky="w")

        self.capa_texto_var = tk.BooleanVar(value=config.PREFERIR_CAPA_TEXTO)
        ttk.Checkbutton(frame, text="Preferir capa de texto del PDF (OCR solo si es necesario)", variable=self.capa_texto_var).grid(row=len(fields)+2, column=0, columnspan=2, sticky="w", pady=5)

        self.ocr_dpi_var = tk.StringVar(value=str(config.OCR_DPI))
        ttk.Label(frame, text="DPI OCR:").grid(row=len(fields)+3, column=0, sticky="w", pady=3)
        ttk.Entry(frame, textvariable=self.ocr_dpi_var, width=10).grid(row=len(fields)+3, column=1, sticky="w", pady=3)

    def _build_excluidos_tab(self, frame):
        ttk.Label(frame, text="Numeros que se ignoran durante la extraccion (uno por linea):").pack(fill=tk.X, pady=5)
        self.excluidos_text = tk.Text(frame, width=60, height=12)
        self.excluidos_text.pack(fill=tk.BOTH, expand=True)
        for num in sorted(config.NUMEROS_EXCLUIDOS):
            self.excluidos_text.insert(tk.END, num + "\n")

    def _save_and_close(self):
        perfil_actual = config.get_perfiles().get(config.get_perfil_activo_nombre(), {})
        for key, entry in self.extr_entries.items():
            valor = entry.get().strip()
            if valor:
                perfil_actual[key] = valor

        perfil_actual["modo_extraccion"] = self.modo_var.get()
        perfil_actual["preferir_capa_texto"] = self.capa_texto_var.get()
        try:
            perfil_actual["ocr_dpi"] = int(self.ocr_dpi_var.get())
        except ValueError:
            perfil_actual["ocr_dpi"] = 300

        excluidos = [line.strip() for line in self.excluidos_text.get("1.0", tk.END).splitlines() if line.strip()]
        perfil_actual["numeros_excluidos"] = excluidos

        nombre_activo = config.get_perfil_activo_nombre()
        config.save_perfil(nombre_activo, perfil_actual)
        self.parent.status_var.set(f"Perfil '{nombre_activo}' guardado y recargado.")
        self.destroy()


class RenamerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Asistente de Renombrado de PDFs v3.0 (Experimental)")
        self.root.geometry("1400x800")

        self.report_path: Path | None = None
        self.pdf_paths: list[Path] = []
        self.guide_df: pd.DataFrame | None = None
        self.preview_image = None
        self.current_preview_path: Path | None = None
        self.current_zoom: float = 1.0
        self.row_count_var = tk.StringVar(value="Filas: 0")
        self.doc_type_var = tk.StringVar(value=config.DOC_TYPE_DEFAULT)
        self.is_co_var = tk.BooleanVar(value=False)

        self._create_widgets()

    def _create_widgets(self):
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)
        paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        bottom_frame = ttk.Frame(self.root, padding="10")
        bottom_frame.pack(fill=tk.X)

        main_controls_frame = ttk.Frame(top_frame)
        main_controls_frame.pack(side=tk.LEFT)

        ttk.Button(main_controls_frame, text="Configuracion", command=self._open_settings).pack(side=tk.LEFT, padx=5)
        self.btn_load_report = ttk.Button(main_controls_frame, text="1. Cargar Informe", command=self._load_report)
        self.btn_load_report.pack(side=tk.LEFT, padx=5)
        self.btn_view_report = ttk.Button(main_controls_frame, text="Ver Informe", state="disabled", command=self._view_report_pdf)
        self.btn_view_report.pack(side=tk.LEFT, padx=5)
        self.btn_load_pdfs = ttk.Button(main_controls_frame, text="2. Cargar PDFs", command=self._load_pdfs)
        self.btn_load_pdfs.pack(side=tk.LEFT, padx=5)

        modifier_frame = ttk.LabelFrame(top_frame, text="Modificar Seleccion", padding=5)
        modifier_frame.pack(side=tk.LEFT, padx=20)
        for dt in config.DOC_TYPES:
            ttk.Radiobutton(modifier_frame, text=dt, variable=self.doc_type_var, value=dt).pack(side=tk.LEFT)
        ttk.Separator(modifier_frame, orient="vertical").pack(side=tk.LEFT, padx=10, fill="y")
        ttk.Checkbutton(modifier_frame, text="Contributivo (CO)", variable=self.is_co_var).pack(side=tk.LEFT)
        self.btn_apply_changes = ttk.Button(modifier_frame, text="Aplicar", state="disabled", command=self._apply_naming_changes)
        self.btn_apply_changes.pack(side=tk.LEFT, padx=10)

        self.btn_move_up = ttk.Button(top_frame, text="Subir", state="disabled", command=self._move_row_up)
        self.btn_move_up.pack(side=tk.LEFT, padx=(30, 5))
        self.btn_move_down = ttk.Button(top_frame, text="Bajar", state="disabled", command=self._move_row_down)
        self.btn_move_down.pack(side=tk.LEFT, padx=5)
        self.btn_swap = ttk.Button(top_frame, text="Intercambiar", state="disabled", command=self._swap_selected_pdfs)
        self.btn_swap.pack(side=tk.LEFT, padx=5)
        self.btn_add_manual = ttk.Button(top_frame, text="+ Editar/Anadir", state="disabled", command=self._open_edit_add_dialog)
        self.btn_add_manual.pack(side=tk.LEFT, padx=5)

        exec_controls_frame = ttk.Frame(top_frame)
        exec_controls_frame.pack(side=tk.RIGHT)
        self.btn_clear = ttk.Button(exec_controls_frame, text="Limpiar Todo", command=self._clear_all_with_confirmation)
        self.btn_clear.pack(side=tk.RIGHT, padx=5)
        self.btn_execute = ttk.Button(exec_controls_frame, text="Ejecutar", style="Accent.TButton", state="disabled", command=self._execute_renaming)
        self.btn_execute.pack(side=tk.RIGHT, padx=5)
        style = ttk.Style()
        style.configure("Accent.TButton", foreground="white", background="green")

        table_frame = ttk.Frame(paned_window, padding=5)
        paned_window.add(table_frame, weight=2)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        columns = ("acta", "identificacion", "tipo", "nuevo_nombre")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("acta", text="Acta")
        self.tree.heading("identificacion", text="Identificacion")
        self.tree.heading("tipo", text="Tipo")
        self.tree.heading("nuevo_nombre", text="Nuevo Nombre Propuesto")
        self.tree.column("acta", width=100)
        self.tree.column("identificacion", width=150)
        self.tree.column("tipo", width=80)
        self.tree.column("nuevo_nombre", width=400)
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Control-Return>", self._shift_pdfs_down)
        self.tree.bind("<Delete>", self._delete_selected_rows)
        self.tree.bind("<Shift-Up>", lambda e: self._change_doc_type(direction=-1))
        self.tree.bind("<Shift-Down>", lambda e: self._change_doc_type(direction=1))
        self.tree.bind("<Shift-Right>", lambda e: self._toggle_cont_suffix(action="add"))
        self.tree.bind("<Shift-Left>", lambda e: self._toggle_cont_suffix(action="remove"))
        self.tree.bind("<Tab>", self._move_selection_down)

        preview_frame = ttk.Frame(paned_window, padding=5)
        paned_window.add(preview_frame, weight=1)

        preview_header = ttk.LabelFrame(preview_frame, text="Verificacion", padding=5)
        preview_header.pack(fill=tk.X, pady=(0, 5))
        self.preview_original_var = tk.StringVar(value="")
        self.preview_nombre_var = tk.StringVar(value="Selecciona una fila para ver el PDF y su nombre propuesto.")
        ttk.Label(preview_header, textvariable=self.preview_original_var,
                  anchor="w", foreground="gray25", wraplength=700).pack(fill=tk.X)
        self.preview_nombre_label = ttk.Label(
            preview_header, textvariable=self.preview_nombre_var, anchor="w",
            font=("Segoe UI", 11, "bold"), wraplength=700
        )
        self.preview_nombre_label.pack(fill=tk.X)

        self.preview_canvas = tk.Canvas(preview_frame, background="gray", relief="sunken", borderwidth=2)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        self.preview_canvas.bind("<MouseWheel>", self._on_mouse_wheel_zoom)
        self.preview_canvas.bind("<Button-4>", self._on_mouse_wheel_zoom)
        self.preview_canvas.bind("<Button-5>", self._on_mouse_wheel_zoom)
        self.preview_canvas.bind("<ButtonPress-1>", self._start_pan)
        self.preview_canvas.bind("<B1-Motion>", self._do_pan)
        self.root.bind("<KeyPress>", self._on_key_press)

        self.status_var = tk.StringVar(value="Bienvenido.")
        self.row_count_label = ttk.Label(bottom_frame, textvariable=self.row_count_var, anchor="e")
        self.row_count_label.pack(side=tk.RIGHT, padx=5)
        self.status_label = ttk.Label(bottom_frame, textvariable=self.status_var, anchor="w")
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        perfil_nombre = config.get_perfil_activo_nombre()
        if perfil_nombre:
            self.status_var.set(f"Perfil activo: {perfil_nombre}")

    def _open_settings(self):
        SettingsDialog(self.root)

    def _get_row_doc_type(self, row):
        nombre = str(row.get("Nuevo_Nombre_Propuesto", ""))
        for prefix in config.DOC_TYPES:
            if nombre.startswith(prefix + "_"):
                return prefix
        return config.DOC_TYPE_DEFAULT

    def _apply_naming_changes(self):
        selected_items = self.tree.selection()
        if not selected_items or self.guide_df is None:
            return

        doc_type = self.doc_type_var.get()
        is_co = self.is_co_var.get()

        omitidas = 0
        aplicadas = 0
        for iid in selected_items:
            idx = int(iid)
            if not self._fila_tiene_archivo(idx):
                omitidas += 1
                continue
            aplicadas += 1
            current_name = str(self.guide_df.loc[idx, "Nuevo_Nombre_Propuesto"])
            rest_of_name = current_name
            for prefix in config.DOC_TYPES:
                if rest_of_name.startswith(prefix + "_"):
                    rest_of_name = rest_of_name[len(prefix) + 1:]
                    break

            name_part, extension = os.path.splitext(rest_of_name)
            if name_part.endswith("_CO"):
                name_part = name_part[:-3]

            new_name = f"{doc_type}_{name_part}"
            if is_co:
                new_name += "_CO"
            new_name += extension

            self.guide_df.loc[idx, "Nuevo_Nombre_Propuesto"] = new_name
            self.guide_df.loc[idx, "EsContributivo"] = is_co

        self._populate_table()
        self.tree.selection_set(selected_items)
        mensaje = f"Cambios aplicados a {aplicadas} fila(s)."
        if omitidas:
            mensaje += f" {omitidas} sin archivo: no se propone nombre."
        self.status_var.set(mensaje)

    def _change_doc_type(self, direction: int):
        selected_items = self.tree.selection()
        if not selected_items or self.guide_df is None:
            return

        con_archivo = [iid for iid in selected_items if self._fila_tiene_archivo(int(iid))]
        if not con_archivo:
            self.status_var.set("Sin archivo asignado: no se propone nombre.")
            return

        reference_iid = con_archivo[0]
        reference_idx = int(reference_iid)
        reference_name = str(self.guide_df.loc[reference_idx, "Nuevo_Nombre_Propuesto"])

        match = re.match(r"(\w+)_", reference_name)
        current_prefix = match.group(1) if match else config.DOC_TYPES[0]

        try:
            current_index = config.DOC_TYPES.index(current_prefix)
        except ValueError:
            current_index = 0

        new_index = (current_index + direction) % len(config.DOC_TYPES)
        new_prefix = config.DOC_TYPES[new_index]

        for iid in con_archivo:
            idx = int(iid)
            current_name = str(self.guide_df.loc[idx, "Nuevo_Nombre_Propuesto"])
            rest_of_name = str(current_name.split("_", 1)[-1])
            is_co = current_name.endswith("_CO.pdf") or "_CO.pdf" in current_name
            suffix = "_CO" if is_co else ""
            name_base, ext = os.path.splitext(rest_of_name)
            if name_base.endswith("_CO"):
                name_base = name_base[:-3]
            new_name = f"{new_prefix}_{name_base}{suffix}{ext}"
            self.guide_df.loc[idx, "Nuevo_Nombre_Propuesto"] = new_name

        self._populate_table()
        self.tree.selection_set(selected_items)
        self.status_var.set(f"Tipo cambiado a '{new_prefix}'.")

    def _toggle_cont_suffix(self, action: str):
        selected_items = self.tree.selection()
        if not selected_items or self.guide_df is None:
            return

        for iid in selected_items:
            idx = int(iid)
            if not self._fila_tiene_archivo(idx):
                continue
            current_name = str(self.guide_df.loc[idx, "Nuevo_Nombre_Propuesto"])
            name_part, extension = os.path.splitext(current_name)
            if action == "add" and not name_part.endswith("_CO"):
                name_part += "_CO"
                self.guide_df.loc[idx, "EsContributivo"] = True
            elif action == "remove" and name_part.endswith("_CO"):
                name_part = name_part[:-3]
                self.guide_df.loc[idx, "EsContributivo"] = False
            self.guide_df.loc[idx, "Nuevo_Nombre_Propuesto"] = f"{name_part}{extension}"

        self._populate_table()
        self.tree.selection_set(selected_items)

    def _move_selection_down(self, event=None):
        selection = self.tree.selection()
        if not selection:
            return "break"
        first_item = selection[0]
        next_item = self.tree.next(first_item)
        if next_item:
            self.tree.selection_set(next_item)
            self.tree.focus(next_item)
            self.tree.see(next_item)
        return "break"

    def _on_row_select(self, event):
        selection = self.tree.selection()
        if selection:
            self.btn_apply_changes.config(state="normal")
        else:
            self.btn_apply_changes.config(state="disabled")
        if len(selection) == 1:
            self.btn_move_up.config(state="normal")
            self.btn_move_down.config(state="normal")
            self.btn_swap.config(state="disabled")
        elif len(selection) == 2:
            self.btn_move_up.config(state="disabled")
            self.btn_move_down.config(state="disabled")
            self.btn_swap.config(state="normal")
        else:
            self.btn_move_up.config(state="disabled")
            self.btn_move_down.config(state="disabled")
            self.btn_swap.config(state="disabled")
        self._actualizar_cabecera_preview()

        if not selection or self.guide_df is None:
            return
        last_selected_iid = selection[-1]
        ruta_str = self.guide_df.loc[int(last_selected_iid), "Ruta_Archivo_Original"]
        if ruta_str and isinstance(ruta_str, str):
            self.current_preview_path = Path(ruta_str)
            self.current_zoom = 1.0
            self._update_preview_image()
        else:
            self.current_preview_path = None
            self.preview_canvas.delete("all")

    def _actualizar_cabecera_preview(self):
        """Muestra, junto a la vista previa, el archivo actual y el nombre propuesto."""
        if not hasattr(self, "preview_nombre_var"):
            return

        seleccion = self.tree.selection()
        if not seleccion or self.guide_df is None:
            self.preview_original_var.set("")
            self.preview_nombre_var.set("Selecciona una fila para ver el PDF y su nombre propuesto.")
            self.preview_nombre_label.config(foreground="gray25")
            return

        if len(seleccion) > 1:
            self.preview_original_var.set(f"{len(seleccion)} filas seleccionadas")
            self.preview_nombre_var.set("Selecciona una sola fila para verificar el nombre.")
            self.preview_nombre_label.config(foreground="gray25")
            return

        idx = int(seleccion[-1])
        if idx not in self.guide_df.index:
            return
        row = self.guide_df.loc[idx]

        ruta = row.get("Ruta_Archivo_Original")
        if logica_renombrado.tiene_archivo(row):
            self.preview_original_var.set(f"Fila {idx + 1}  |  Actual: {Path(str(ruta)).name}")
        else:
            self.preview_original_var.set(f"Fila {idx + 1}  |  Sin archivo asignado")

        nombre = str(row.get("Nuevo_Nombre_Propuesto", ""))
        if nombre in (logica_renombrado.NOMBRE_SIN_ARCHIVO, logica_renombrado.NOMBRE_SIN_DATOS, ""):
            self.preview_nombre_var.set(nombre or "Sin nombre propuesto")
            self.preview_nombre_label.config(foreground="#B00000")
        else:
            self.preview_nombre_var.set(f"-> {nombre}")
            self.preview_nombre_label.config(foreground="#0A6B2E")

    def _clear_all_with_confirmation(self):
        if not self.report_path and not self.pdf_paths:
            return
        if messagebox.askyesno("Confirmar Limpieza", "Esto eliminara todos los datos cargados.\nEstas seguro?"):
            self._reset_app()

    def _reset_app(self, message="Listo. Comienza cargando un nuevo informe."):
        self.report_path, self.pdf_paths, self.guide_df = None, [], None
        for item in self.tree.get_children():
            self.tree.delete(item)
        for btn in [self.btn_execute, self.btn_move_up, self.btn_move_down, self.btn_swap, self.btn_view_report, self.btn_add_manual, self.btn_apply_changes]:
            btn.config(state="disabled")
        self.preview_canvas.delete("all")
        self.status_var.set(message)
        self.current_preview_path, self.current_zoom = None, 1.0
        self.row_count_var.set("Filas: 0")
        self.doc_type_var.set(config.DOC_TYPE_DEFAULT)
        self.is_co_var.set(False)

    def _open_edit_add_dialog(self):
        selection = self.tree.selection()
        if len(selection) > 1:
            messagebox.showwarning("Accion no permitida", "Selecciona solo una fila para editar, o ninguna para anadir.")
            return
        index_to_edit = int(selection[0]) if selection else None
        dialog = tk.Toplevel(self.root)
        dialog.title("Editar / Anadir Fila")
        dialog.geometry("320x180")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Numero de Acta:").grid(row=0, column=0, sticky="w", pady=5)
        acta_entry = ttk.Entry(frame)
        acta_entry.grid(row=0, column=1, sticky="ew")

        ttk.Label(frame, text="Numero de Identificacion:").grid(row=1, column=0, sticky="w", pady=5)
        id_entry = ttk.Entry(frame)
        id_entry.grid(row=1, column=1, sticky="ew")

        co_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Contributivo (CO)", variable=co_var).grid(row=2, column=0, columnspan=2, sticky="w", pady=3)

        if index_to_edit is not None and self.guide_df is not None:
            current_data = self.guide_df.loc[index_to_edit]
            acta_entry.insert(0, str(current_data.get("Acta", "")))
            id_entry.insert(0, str(current_data.get("Identificacion", "")))
            co_var.set(bool(current_data.get("EsContributivo", False)))

        def _save():
            acta, id_num = acta_entry.get().strip(), id_entry.get().strip()
            if not acta.isdigit() or not id_num.isdigit():
                messagebox.showerror("Error", "Ambos campos deben ser numeros.", parent=dialog)
                return
            if index_to_edit is not None:
                self._edit_row_logic(index_to_edit, acta, id_num, co_var.get())
            else:
                self._add_row_logic(acta, id_num, co_var.get())
            dialog.destroy()

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=3, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Aceptar", command=_save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def _add_row_logic(self, acta: str, id_num: str, es_co: bool = False):
        if self.guide_df is None:
            self.guide_df = pd.DataFrame(columns=["Acta", "Identificacion", "EsContributivo", "Seccion"])
        new_row = pd.DataFrame([{"Acta": acta, "Identificacion": id_num, "EsContributivo": es_co, "Seccion": ""}])
        self.guide_df = pd.concat([self.guide_df, new_row], ignore_index=True)
        self.guide_df = logica_renombrado.generar_guia_completa(self.guide_df, self.pdf_paths)
        self._populate_table()

    def _edit_row_logic(self, index: int, acta: str, id_num: str, es_co: bool = False):
        if self.guide_df is None:
            return
        self.guide_df.loc[index, "Acta"] = acta
        self.guide_df.loc[index, "Identificacion"] = id_num
        self.guide_df.loc[index, "EsContributivo"] = es_co
        self.guide_df = logica_renombrado.generar_guia_completa(self.guide_df, self.pdf_paths)
        self._populate_table()

    def _load_report(self):
        path = filedialog.askopenfilename(title="Selecciona el Informe PDF", filetypes=[("PDF Files", "*.pdf")], initialdir=str(config.INFORME_DIR))
        if not path:
            return
        self.report_path = Path(path)
        self.status_var.set("Informe cargado. Procesando...")
        self.root.update_idletasks()
        try:
            self.guide_df = logica_renombrado.procesar_tabla_de_informe(self.report_path)
            if self.pdf_paths:
                self.guide_df = logica_renombrado.generar_guia_completa(self.guide_df, self.pdf_paths)
            self._populate_table()
            self.btn_view_report.config(state="normal")
            self.btn_add_manual.config(state="normal")
            self.status_var.set(f"Informe procesado: {len(self.guide_df)} filas encontradas.")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrio un error al procesar el informe: {e}\n\nConsulta app_log.log.")
        self._check_if_ready_to_execute()

    def _load_pdfs(self):
        mode = "replace"
        if self.pdf_paths:
            answer = messagebox.askyesnocancel("Cargar PDFs", f"Ya hay {len(self.pdf_paths)} archivos cargados.\n\nDeseas ANADIR (Si) o REEMPLAZAR (No)?", icon="question")
            if answer is True:
                mode = "add"
            elif answer is False:
                mode = "replace"
            else:
                return
        paths = filedialog.askopenfilenames(title="Selecciona los PDFs a Renombrar", filetypes=[("PDF Files", "*.pdf")], initialdir=str(config.PDFS_A_RENOMBRAR_DIR))
        if not paths:
            return
        new_paths = [Path(p) for p in paths]
        if mode == "add":
            self.pdf_paths.extend(new_paths)
        else:
            self.pdf_paths = new_paths
        self.status_var.set(f"Total de {len(self.pdf_paths)} PDFs cargados. Vinculando...")
        self.root.update_idletasks()
        if self.guide_df is not None:
            self.guide_df = logica_renombrado.generar_guia_completa(self.guide_df, self.pdf_paths)
            self._populate_table()
            self.status_var.set("Archivos vinculados.")
        self._check_if_ready_to_execute()

    def _check_if_ready_to_execute(self):
        if self.guide_df is not None and "Ruta_Archivo_Original" in self.guide_df.columns and not self.guide_df.dropna(subset=["Ruta_Archivo_Original"]).empty:
            self.btn_execute.config(state="normal")
        else:
            self.btn_execute.config(state="disabled")

    def _swap_selected_pdfs(self):
        selected_items = self.tree.selection()
        if len(selected_items) != 2 or self.guide_df is None:
            return
        idx1, idx2 = int(selected_items[0]), int(selected_items[1])
        route1, route2 = self.guide_df.loc[idx1, "Ruta_Archivo_Original"], self.guide_df.loc[idx2, "Ruta_Archivo_Original"]
        self.guide_df.loc[idx1, "Ruta_Archivo_Original"], self.guide_df.loc[idx2, "Ruta_Archivo_Original"] = route2, route1
        self._refrescar_nombres([idx1, idx2])
        self._populate_table()
        self.tree.selection_set(selected_items)

    def _move_row_up(self):
        if not self.tree.selection() or self.guide_df is None:
            return
        selected_iid = self.tree.selection()[0]
        prev_iid = self.tree.prev(selected_iid)
        if not prev_iid:
            return
        idx_selected, idx_prev = int(selected_iid), int(prev_iid)
        row_selected, row_prev = self.guide_df.loc[idx_selected].copy(), self.guide_df.loc[idx_prev].copy()
        self.guide_df.loc[idx_selected], self.guide_df.loc[idx_prev] = row_prev, row_selected
        self._populate_table()
        self.tree.selection_set(prev_iid)
        self.tree.focus(prev_iid)

    def _move_row_down(self):
        if not self.tree.selection() or self.guide_df is None:
            return
        selected_iid = self.tree.selection()[0]
        next_iid = self.tree.next(selected_iid)
        if not next_iid:
            return
        idx_selected, idx_next = int(selected_iid), int(next_iid)
        row_selected, row_next = self.guide_df.loc[idx_selected].copy(), self.guide_df.loc[idx_next].copy()
        self.guide_df.loc[idx_selected], self.guide_df.loc[idx_next] = row_next, row_selected
        self._populate_table()
        self.tree.selection_set(next_iid)
        self.tree.focus(next_iid)

    def _start_pan(self, event):
        self.preview_canvas.scan_mark(event.x, event.y)

    def _do_pan(self, event):
        self.preview_canvas.scan_dragto(event.x, event.y, gain=1)

    def _on_key_press(self, event):
        if self.current_preview_path:
            if event.keysym == "Up":
                self.preview_canvas.yview_scroll(-1, "units")
            elif event.keysym == "Down":
                self.preview_canvas.yview_scroll(1, "units")
            elif event.keysym == "Left":
                self.preview_canvas.xview_scroll(-1, "units")
            elif event.keysym == "Right":
                self.preview_canvas.xview_scroll(1, "units")

    def _on_mouse_wheel_zoom(self, event):
        if not self.current_preview_path:
            return
        zoom_step = 0.1
        if event.num == 5 or event.delta < 0:
            self.current_zoom -= zoom_step
        if event.num == 4 or event.delta > 0:
            self.current_zoom += zoom_step
        self.current_zoom = max(0.2, self.current_zoom)
        self.status_var.set(f"Zoom: {self.current_zoom:.1f}x")
        self._update_preview_image()

    def _update_preview_image(self):
        if not self.current_preview_path or not self.current_preview_path.exists():
            self.preview_canvas.delete("all")
            return
        self.preview_image = procesamiento_pdf.generar_imagen_tk_de_pdf(self.current_preview_path, zoom_factor=self.current_zoom)
        self.preview_canvas.delete("all")
        if self.preview_image:
            self.preview_canvas.create_image(0, 0, anchor="nw", image=self.preview_image)
            bbox = (0, 0, self.preview_image.width(), self.preview_image.height())
            self.preview_canvas.config(scrollregion=bbox)

    def _shift_pdfs_down(self, event=None):
        selection = self.tree.selection()
        if not selection or self.guide_df is None:
            return

        idx = int(selection[0])
        rutas = self.guide_df['Ruta_Archivo_Original'].tolist()

        pdfs_from_idx = [r for r in rutas[idx:] if pd.notna(r) and str(r).strip() != ""]
        if not pdfs_from_idx:
            return

        new_rutas = rutas[:idx] + [None] + pdfs_from_idx
        current_len = len(self.guide_df)

        self.guide_df['Ruta_Archivo_Original'] = (new_rutas + [None] * current_len)[:current_len]

        for r in new_rutas[current_len:]:
            if r:
                new_row = pd.DataFrame([{
                    "Acta": "", "Identificacion": "", "EsContributivo": False, "Seccion": "",
                    "Ruta_Archivo_Original": r, "Nuevo_Nombre_Propuesto": logica_renombrado.NOMBRE_SIN_DATOS
                }])
                self.guide_df = pd.concat([self.guide_df, new_row], ignore_index=True)

        self._update_all_names()
        self._populate_table()
        self.status_var.set(f"Archivos desplazados desde la fila {idx + 1}.")

    def _fila_tiene_archivo(self, idx) -> bool:
        """Una fila sin PDF asignado no puede tener nombre propuesto."""
        if self.guide_df is None or idx not in self.guide_df.index:
            return False
        return logica_renombrado.tiene_archivo(self.guide_df.loc[idx])

    def _nombre_para_fila(self, row) -> str:
        if not logica_renombrado.tiene_archivo(row):
            return logica_renombrado.NOMBRE_SIN_ARCHIVO
        nombre = logica_renombrado._generar_nombre(row)
        return nombre if nombre is not None else logica_renombrado.NOMBRE_SIN_DATOS

    def _refrescar_nombres(self, indices):
        """Recalcula el nombre solo de las filas indicadas, conservando ediciones
        manuales de las filas que ya tenian archivo y nombre valido."""
        if self.guide_df is None:
            return
        for idx in indices:
            if idx not in self.guide_df.index:
                continue
            row = self.guide_df.loc[idx]
            actual = str(row.get("Nuevo_Nombre_Propuesto", ""))
            if not logica_renombrado.tiene_archivo(row):
                self.guide_df.loc[idx, "Nuevo_Nombre_Propuesto"] = logica_renombrado.NOMBRE_SIN_ARCHIVO
            elif actual in ("", logica_renombrado.NOMBRE_SIN_ARCHIVO):
                self.guide_df.loc[idx, "Nuevo_Nombre_Propuesto"] = self._nombre_para_fila(row)

    def _update_all_names(self):
        if self.guide_df is None:
            return
        for i, row in self.guide_df.iterrows():
            self.guide_df.loc[i, "Nuevo_Nombre_Propuesto"] = self._nombre_para_fila(row)

    def _delete_selected_rows(self, event=None):
        selected_items = self.tree.selection()
        if not selected_items or self.guide_df is None:
            return
        if not messagebox.askyesno("Confirmar", f"Eliminar {len(selected_items)} fila(s)?"):
            return
        indices_to_drop = [int(iid) for iid in selected_items]
        self.guide_df.drop(indices_to_drop, inplace=True)
        self.guide_df.reset_index(drop=True, inplace=True)
        self._populate_table()

    def _view_report_pdf(self):
        if self.report_path and self.report_path.exists():
            try:
                os.startfile(self.report_path)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir el archivo PDF:\n{e}")

    def _populate_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        count = 0
        if self.guide_df is not None:
            for index, row in self.guide_df.iterrows():
                nuevo_nombre = row.get("Nuevo_Nombre_Propuesto", "Esperando PDFs...")
                tipo = "CO" if row.get("EsContributivo", False) else ""
                self.tree.insert("", tk.END, iid=int(index), values=(row["Acta"], row["Identificacion"], tipo, nuevo_nombre))
            count = len(self.guide_df)
        self.row_count_var.set(f"Filas: {count}")
        self._actualizar_cabecera_preview()

    def _on_double_click(self, event):
        if self.guide_df is None:
            return
        if self.tree.identify("region", event.x, event.y) == "cell" and self.tree.identify_column(event.x) == "#4":
            selected_iid = self.tree.focus()
            x, y, width, height = self.tree.bbox(selected_iid, "#4")
            entry = ttk.Entry(self.tree)
            entry.place(x=x, y=y, width=width, height=height)
            entry.insert(0, self.tree.item(selected_iid, "values")[3])
            entry.focus()
            entry.bind("<Return>", lambda e: self._update_cell_value(selected_iid, entry))
            entry.bind("<Escape>", lambda e: entry.destroy())

    def _update_cell_value(self, iid, entry):
        if self.guide_df is None:
            return
        new_value = entry.get()
        if not self._fila_tiene_archivo(int(iid)):
            entry.destroy()
            self.status_var.set("Esa fila no tiene archivo asignado: no se propone nombre.")
            return
        current_values = list(self.tree.item(iid, "values"))
        current_values[3] = new_value
        self.tree.item(iid, values=tuple(current_values))
        self.guide_df.loc[int(iid), "Nuevo_Nombre_Propuesto"] = new_value
        entry.destroy()

    def _execute_renaming(self):
        if self.guide_df is None:
            messagebox.showwarning("Advertencia", "No hay datos procesados.")
            return
        files_to_rename_count = len(self.guide_df.dropna(subset=["Ruta_Archivo_Original"]))
        if files_to_rename_count == 0:
            messagebox.showinfo("Informacion", "No hay archivos para renombrar.")
            return
        if messagebox.askyesno("Confirmar", f"Renombrar {files_to_rename_count} archivos?"):
            destination_folder = filedialog.askdirectory(title="Selecciona la carpeta de destino", initialdir=str(config.RENAMED_DIR))
            if not destination_folder:
                self.status_var.set("Operacion cancelada.")
                return
            exitosos, fallidos, reporte_path = logica_renombrado.ejecutar_renombrado(self.guide_df, Path(destination_folder))
            messagebox.showinfo("Proceso Completado", f"Renombrado finalizado.\n\nExitosos: {exitosos}\nFallidos: {fallidos}\n\nGuardados en: {destination_folder}\n\nReporte Excel:\n{reporte_path}")
            self._reset_app()


if __name__ == "__main__":
    setup_logging()
    root = tk.Tk()
    app = RenamerApp(root)
    root.mainloop()
