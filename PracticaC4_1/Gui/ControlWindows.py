import re
import ctypes  # <--- NUEVO: Para conectar con C++
import os  # <--- NUEVO: Para encontrar la ruta del archivo
from PyQt6.QtCore import (
    pyqtSignal, QPropertyAnimation,
    QEasingCurve, QParallelAnimationGroup
)
from PyQt6.QtGui import QMouseEvent, QIcon, QDoubleValidator
from PyQt6.QtWidgets import QDialog, QHeaderView, QLineEdit, QMessageBox, QTableWidgetItem, QAbstractItemView, \
    QCompleter
from PyQt6.QtCore import QDate, QLocale, Qt
from datetime import date
import socket
from .ui_ControlWindows import Ui_Dialog


class ControlWindows(QDialog):
    sesion_cerrada = pyqtSignal()

    def __init__(self, db_manager):
        super().__init__()

        self.db_manager = db_manager
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        # Propiedades para guardar los datos del usuario actual
        self.current_login = None
        self.current_password = None
        self.current_puesto = None
        self.current_cv_user = None
        self.current_nombre_completo = None

        # --- INTEGRACIÓN C++ (NUEVO BLOQUE) ---
        self.cpp_lib = None
        try:
            # 1. Construir la ruta absoluta hacia la DLL
            # Estamos en Gui/, subimos uno (..) y entramos a cpp/
            base_path = os.path.dirname(os.path.abspath(__file__))
            dll_path = os.path.join(base_path, "..", "cpp", "calculos.dll")

            # 2. Cargar la librería
            if os.path.exists(dll_path):
                self.cpp_lib = ctypes.CDLL(dll_path)

                # 3. Configurar los tipos de datos de la función C++
                # int calcular_edad_cpp(int, int, int, int, int, int)
                self.cpp_lib.calcular_edad_cpp.argtypes = [
                    ctypes.c_int, ctypes.c_int, ctypes.c_int,  # Fecha Nacimiento
                    ctypes.c_int, ctypes.c_int, ctypes.c_int  # Fecha Actual
                ]
                self.cpp_lib.calcular_edad_cpp.restype = ctypes.c_int
                print(f"--- [ÉXITO] Librería C++ cargada desde: {dll_path} ---")
            else:
                print(f"--- [AVISO] No se encontró la DLL en: {dll_path} ---")

        except Exception as e:
            print(f"--- [ERROR] Fallo al cargar librería C++: {e} ---")
            self.cpp_lib = None
        # --------------------------------------

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        # --- ESTILOS PARA VALIDACIÓN (PASSWORD) ---
        self.style_qline_ok = """
            font-size: 10pt; color: white;
            background-color: #000000ff;
            border: 1px solid rgb(20, 200, 220);
            border-radius: 5px; padding: 4px;
        """
        self.style_qline_error = """
            font-size: 10pt; color: red;
            background-color: #000000ff;
            border: 1px solid red;
            border-radius: 5px; padding: 4px;
        """
        self.style_crit_ok = "color: white;"
        self.style_crit_error = "color: red;"

        # --- CONFIGURACIÓN DE BOTONES DE OJO (CAMBIAR PASS) ---
        try:
            ruta_icono = "Gui/../../Imagenes/eye_on_see_show_view_vision_watch_icon_123215.png"
            eye_icono = QIcon(ruta_icono)

            self.ui.txt_pass_nuevo.textChanged.connect(self.validar_password_nuevo)
            self.ui.txt_pass_repetir.textChanged.connect(self.validar_password_repetido)

            self.ui.txt_pass_anterior.setEchoMode(QLineEdit.EchoMode.Password)
            eye_action_anterior = self.ui.txt_pass_anterior.addAction(eye_icono,
                                                                      QLineEdit.ActionPosition.TrailingPosition)
            eye_action_anterior.triggered.connect(
                lambda: self.toggle_password_visibility(self.ui.txt_pass_anterior)
            )

            self.ui.txt_pass_nuevo.setEchoMode(QLineEdit.EchoMode.Password)
            eye_action_nuevo = self.ui.txt_pass_nuevo.addAction(eye_icono, QLineEdit.ActionPosition.TrailingPosition)
            eye_action_nuevo.triggered.connect(
                lambda: self.toggle_password_visibility(self.ui.txt_pass_nuevo)
            )

            self.ui.txt_pass_repetir.setEchoMode(QLineEdit.EchoMode.Password)
            eye_action_repetir = self.ui.txt_pass_repetir.addAction(eye_icono,
                                                                    QLineEdit.ActionPosition.TrailingPosition)
            eye_action_repetir.triggered.connect(
                lambda: self.toggle_password_visibility(self.ui.txt_pass_repetir)
            )
        except AttributeError as e:
            print(f"ADVERTENCIA (Botones Ojo): {e}")
        except Exception as e:
            print(f"Error inesperado configurando botones de ojo: {e}")

        # --- ESTADO INICIAL DE MÓDULOS ---
        self.estado_compras = "navegando"
        self.estado_actual_pagos = "consultando"
        self.estado_actual_personas = "consultando"
        self.estado_actual_catalogos = "consultando"
        self.estado_actual_asistencia = "consultando"
        self.estado_actual_evaluaciones = "consultando"

        # --- ANIMACIÓN MENÚ PRINCIPAL ---
        self.menu_ancho_desplegado = 220
        self.menu_esta_oculto = False
        self.animacion_grupo_main = None
        self.ui.frame_4.setMinimumWidth(self.menu_ancho_desplegado)
        self.ui.frame_4.setMaximumWidth(self.menu_ancho_desplegado)

        self.compras_menu_ancho = 180
        self.compras_menu_oculto = False
        self.animacion_grupo_compras = None

        # --- CONEXIONES DE BOTONES DE LA VENTANA ---
        self.ui.btn_cerrar.clicked.connect(self.close)
        self.ui.btn_minimizar.clicked.connect(self.showMinimized)
        self.ui.btn_maximizar.clicked.connect(self.Maximizar)
        self.ui.btn_toggle_menu.clicked.connect(self.toggle_menu_main)
        self.ui.btn_toggle_menu.setText("<")

        # --- CONEXIONES DE BOTONES DEL MENÚ PRINCIPAL ---
        self.ui.pushButton_4.clicked.connect(self.mostrar_pagina_cambiarpass)
        self.ui.btn_cerrarsesion.clicked.connect(self.cerrar_sesion)
        self.ui.btn_Personas.clicked.connect(self.mostrar_pagina_personas)
        self.ui.btn_catalogos.clicked.connect(self.mostrar_pagina_catalogos)
        self.ui.btn_asistencia.clicked.connect(self.mostrar_pagina_asistencia)
        self.ui.btn_evaluaciones.clicked.connect(self.mostrar_pagina_evaluaciones)

        try:
            self.ui.btn_pagos.clicked.connect(self.mostrar_pagina_pagos)
        except AttributeError:
            pass

        self.dragging = False
        self.offset = None

        # --- CONEXIONES DEL MÓDULO DE PAGOS ---
        try:
            self.ui.btn_pagos_nuevo.clicked.connect(self.accion_pagos_nuevo)
            self.ui.btn_pagos_actualizar.clicked.connect(self.accion_pagos_actualizar)
            self.ui.btn_pagos_borrar.clicked.connect(self.accion_pagos_borrar)
            self.ui.btn_pagos_consultar.clicked.connect(self.accion_pagos_consultar)
            self.ui.btn_pagos_cancelar.clicked.connect(self.accion_pagos_cancelar)
            self.ui.btn_pagos_regresar.clicked.connect(self.accion_pagos_regresar)
            self.ui.filtro_pagos_nombre.textChanged.connect(self.actualizar_filtros_tabla)
            self.ui.filtro_pagos_estado.currentIndexChanged.connect(self.actualizar_filtros_tabla)

            self.ui.combo_pagos_tipo.currentIndexChanged.connect(self.actualizar_monto_y_total)
            self.ui.combo_pagos_descuento.currentIndexChanged.connect(self.actualizar_monto_y_total)
            self.ui.combo_pagos_estado.addItems(["Pagado", "Pendiente"])

            locale = QLocale(QLocale.Language.Spanish, QLocale.Country.Mexico)
            validator = QDoubleValidator(0.0, 99999.99, 2)
            validator.setLocale(locale)
            validator.setNotation(QDoubleValidator.Notation.StandardNotation)

            self.ui.txt_pagos_monto.setValidator(validator)
            self.ui.txt_pagos_total.setValidator(validator)

        except AttributeError:
            pass

        try:
            # Botones de acción Personas
            self.ui.btn_per_nuevo.clicked.connect(self.accion_personas_nuevo)
            self.ui.btn_per_actualizar.clicked.connect(self.accion_personas_actualizar)
            self.ui.btn_per_borrar.clicked.connect(self.accion_personas_borrar)
            self.ui.btn_per_consultar.clicked.connect(self.accion_personas_consultar)
            self.ui.btn_per_cancelar.clicked.connect(self.accion_personas_cancelar)
            self.ui.btn_per_regresar.clicked.connect(self.accion_personas_regresar)

            self.ui.filtro_personas_nombre.textChanged.connect(self.actualizar_filtros_tabla_personas)
            self.ui.filtro_personas_tipo.currentIndexChanged.connect(self.actualizar_filtros_tabla_personas)

            self.ui.tabla_personas.itemSelectionChanged.connect(
                lambda: self.configurar_botones_personas(
                    "consultando") if self.estado_actual_personas == "consultando" else None
            )
            self.ui.combo_per_edocta.addItems(["True", "False"])

        except AttributeError:
            pass

        # --- CONEXIONES OTROS MÓDULOS ---
        try:
            self.ui.btn_cata_nuevo.clicked.connect(self.accion_catalogos_nuevo)
            self.ui.btn_cata_actualizar.clicked.connect(self.accion_catalogos_actualizar)
            self.ui.btn_cata_borrar.clicked.connect(self.accion_catalogos_borrar)
            self.ui.btn_cata_consultar.clicked.connect(self.accion_catalogos_consultar)
            self.ui.btn_cata_cancelar.clicked.connect(self.accion_catalogos_consultar)
            self.ui.btn_cata_regresar.clicked.connect(self.accion_pagos_regresar)
        except AttributeError:
            pass

        try:
            self.ui.btn_asis_nuevo.clicked.connect(self.accion_asistencia_nuevo)
            self.ui.btn_asis_actualizar.clicked.connect(self.accion_asistencia_actualizar)
            self.ui.btn_asis_borrar.clicked.connect(self.accion_asistencia_borrar)
            self.ui.btn_asis_consultar.clicked.connect(self.accion_asistencia_consultar)
            self.ui.btn_asis_cancelar.clicked.connect(self.accion_asistencia_consultar)
            self.ui.btn_asis_regresar.clicked.connect(self.accion_pagos_regresar)
        except AttributeError:
            pass

        try:
            self.ui.btn_eva_nuevo.clicked.connect(self.accion_evaluaciones_nuevo)
            self.ui.btn_eva_actualizar.clicked.connect(self.accion_evaluaciones_actualizar)
            self.ui.btn_eva_borrar.clicked.connect(self.accion_evaluaciones_borrar)
            self.ui.btn_eva_consultar.clicked.connect(self.accion_evaluaciones_consultar)
            self.ui.btn_eva_cancelar.clicked.connect(self.accion_evaluaciones_consultar)
            self.ui.btn_eva_regresar.clicked.connect(self.accion_pagos_regresar)
        except AttributeError:
            pass

    # --- MÉTODOS DE LA CLASE ---

    def _calcular_edad(self, fecha_nacimiento):
        """
        Calcula la edad. Intenta usar C++ primero (híbrido),
        si falla, usa Python (respaldo).
        """
        hoy = date.today()
        nac = fecha_nacimiento.toPyDate()

        # 1. INTENTO CON C++
        if self.cpp_lib:
            try:
                # Llamada a la función externa
                edad = self.cpp_lib.calcular_edad_cpp(
                    nac.day, nac.month, nac.year,
                    hoy.day, hoy.month, hoy.year
                )
                print(f"[C++] Edad calculada nativamente: {edad}")
                return edad
            except Exception as e:
                print(f"[ERROR C++] Fallo la llamada a la DLL: {e}. Usando Python...")

        # 2. RESPALDO CON PYTHON
        edad = hoy.year - nac.year - ((hoy.month, hoy.day) < (nac.month, nac.day))
        print(f"[PYTHON] Edad calculada: {edad}")
        return edad

    def mostrar_pagina_personas(self):
        try:
            # 1. Cambiar a la página de personas
            self.ui.stackedWidget.setCurrentWidget(self.ui.Personas)

            # 2. Registrar auditoría
            self.db_manager.registrar_acceso(
                self.current_login, True, "AUDITORIA APP: Acceso al módulo de Personas", self.obtener_ip()
            )

            # 3. Cargar combos y filtros
            self.cargar_combobox_catalogos_personas()
            self.cargar_combobox_filtro_tipo_persona()

            # 4. Ocultar el menú lateral si está visible
            if not self.menu_esta_oculto:
                self.toggle_menu_main()

            # 5. Poner en estado de consulta (mostrar tabla)
            self.accion_personas_consultar()

        except Exception as e:
            print(f"Error crítico al mostrar 'page_personas': {e}")

    def mostrar_pagina_pagos(self):
        try:
            self.ui.stackedWidget.setCurrentWidget(self.ui.Pagos)
            self.db_manager.registrar_acceso(
                self.current_login, True, "AUDITORIA APP: Acceso al módulo de Pagos", self.obtener_ip()
            )
            self.cargar_tabla_pagos()
            self.cargar_combobox_alumnos()
            self.cargar_combobox_pagos_y_descuentos()
            self.cargar_combobox_filtro_estado()
            if not self.menu_esta_oculto:
                self.toggle_menu_main()
            self.accion_pagos_consultar()
        except Exception as e:
            print(f"Error en Pagos: {e}")

    def mostrar_pagina_cambiarpass(self):
        try:
            self.ui.stackedWidget.setCurrentWidget(self.ui.Cambiarpass)
            self.db_manager.registrar_acceso(
                self.current_login, True, "AUDITORIA APP: Acceso al módulo CambiarPass", self.obtener_ip()
            )
            self.limpiar_campos_password()
            try:
                self.ui.btn_aceptar_pass.clicked.disconnect()
                self.ui.btn_cancel_pass.clicked.disconnect()
            except TypeError:
                pass
            self.ui.btn_aceptar_pass.clicked.connect(self.procesar_cambio_password)
            self.ui.btn_cancel_pass.clicked.connect(self.limpiar_campos_password)
        except Exception as e:
            print(f"Error en cambiarpass: {e}")

    def mostrar_pagina_catalogos(self):
        try:
            self.ui.stackedWidget.setCurrentWidget(self.ui.Catalogos)
            self.cargar_lista_de_catalogos()
            try:
                self.ui.combo_catalogo_seleccion.currentIndexChanged.disconnect()
            except:
                pass
            self.ui.combo_catalogo_seleccion.currentIndexChanged.connect(self.cargar_tabla_catalogos)
            self.db_manager.registrar_acceso(
                self.current_login, True, "AUDITORIA APP: Acceso al modulo de Catalogos", self.obtener_ip()
            )
            self.cargar_tabla_catalogos()
            self.accion_catalogos_consultar()
            if not self.menu_esta_oculto:
                self.toggle_menu_main()
        except Exception as e:
            print(f"Error en catalogos: {e}")

    def mostrar_pagina_asistencia(self):
        try:
            self.ui.stackedWidget.setCurrentWidget(self.ui.Asistencia)
            self.db_manager.registrar_acceso(
                self.current_login, True, "Auditoria APP: Acceso al modulo de Asistencia", self.obtener_ip()
            )
            self.accion_asistencia_consultar()
            if not self.menu_esta_oculto:
                self.toggle_menu_main()
        except Exception as e:
            print(f"Error en asistencia: {e}")

    def mostrar_pagina_evaluaciones(self):
        try:
            self.ui.stackedWidget.setCurrentWidget(self.ui.Evaluaciones)
            self.db_manager.registrar_acceso(
                self.current_login, True, "Auditoria APP: Acceso al modulo de Evaluaciones", self.obtener_ip()
            )
            self.accion_evaluaciones_consultar()
            if not self.menu_esta_oculto:
                self.toggle_menu_main()
        except Exception as e:
            print(f"Error en evaluaciones: {e}")

    def toggle_menu_main(self):
        if self.animacion_grupo_main and self.animacion_grupo_main.state() == QParallelAnimationGroup.State.Running:
            return
        ancho_fin = 0
        if self.menu_esta_oculto:
            ancho_fin = self.menu_ancho_desplegado
            self.ui.btn_toggle_menu.setText("<")
            self.menu_esta_oculto = False
        else:
            self.ui.btn_toggle_menu.setText("☰")
            self.menu_esta_oculto = True
        self.animacion_min = QPropertyAnimation(self.ui.frame_4, b"minimumWidth")
        self.animacion_max = QPropertyAnimation(self.ui.frame_4, b"maximumWidth")
        self.animacion_min.setDuration(300)
        self.animacion_min.setEndValue(ancho_fin)
        self.animacion_min.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animacion_max.setDuration(300)
        self.animacion_max.setEndValue(ancho_fin)
        self.animacion_max.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animacion_grupo_main = QParallelAnimationGroup()
        self.animacion_grupo_main.addAnimation(self.animacion_min)
        self.animacion_grupo_main.addAnimation(self.animacion_max)
        self.animacion_grupo_main.start()

    def Maximizar(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.ui.frame_2.underMouse():
                self.dragging = True
                self.offset = event.pos()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging:
            self.move(self.mapToGlobal(event.pos() - self.offset))

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.offset = None

    def set_user_info(self, nombre_completo, puesto, genero, login, password, cv_user):
        saludo = "Bienvenido(a)"
        if genero.lower() == 'masculino':
            saludo = "Bienvenido"
        elif genero.lower() == 'femenino':
            saludo = "Bienvenida"
        texto_bienvenida = f"{saludo}:\n{nombre_completo}\n({puesto})"
        self.ui.lbl_bienvenida.setText(texto_bienvenida)
        self.current_login = login
        self.current_password = password
        self.current_puesto = puesto
        self.current_cv_user = cv_user
        self.current_nombre_completo = nombre_completo
        self.ui.stackedWidget.setCurrentWidget(self.ui.Inicio)

    def cerrar_sesion(self):
        self.ui.lbl_bienvenida.setText("Bienvenido(a):")
        self.sesion_cerrada.emit()

    def toggle_password_visibility(self, line_edit_widget):
        if line_edit_widget.echoMode() == QLineEdit.EchoMode.Password:
            line_edit_widget.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            line_edit_widget.setEchoMode(QLineEdit.EchoMode.Password)

    def validar_password_nuevo(self):
        password = self.ui.txt_pass_nuevo.text()
        all_criteria_valid = True
        try:
            if 4 <= len(password) <= 10:
                self.ui.caracter.setStyleSheet(self.style_crit_ok)
            else:
                self.ui.caracter.setStyleSheet(self.style_crit_error)
                all_criteria_valid = False
            if re.search(r"[A-Z]", password):
                self.ui.mayus.setStyleSheet(self.style_crit_ok)
            else:
                self.ui.mayus.setStyleSheet(self.style_crit_error)
                all_criteria_valid = False
            if re.search(r"[a-z]", password):
                self.ui.minus.setStyleSheet(self.style_crit_ok)
            else:
                self.ui.minus.setStyleSheet(self.style_crit_error)
                all_criteria_valid = False
            if re.search(r"[0-9]", password):
                self.ui.numer.setStyleSheet(self.style_crit_ok)
            else:
                self.ui.numer.setStyleSheet(self.style_crit_error)
                all_criteria_valid = False
            if re.search(r"[^a-zA-Z0-9]", password):
                self.ui.caracter_especial.setStyleSheet(self.style_crit_ok)
            else:
                self.ui.caracter_especial.setStyleSheet(self.style_crit_error)
                all_criteria_valid = False
            if not password:
                self.limpiar_estilos_password(reset_field_color=False)
                all_criteria_valid = False
            if all_criteria_valid:
                self.ui.txt_pass_nuevo.setStyleSheet(self.style_qline_ok)
            else:
                self.ui.txt_pass_nuevo.setStyleSheet(self.style_qline_error if password else self.style_qline_ok)
            self.validar_password_repetido()
            return all_criteria_valid
        except AttributeError:
            return False

    def validar_password_repetido(self):
        pass_nuevo = self.ui.txt_pass_nuevo.text()
        pass_repetir = self.ui.txt_pass_repetir.text()
        try:
            if not pass_repetir and not pass_nuevo:
                self.ui.txt_pass_repetir.setStyleSheet(self.style_qline_ok)
                return True
            if pass_nuevo == pass_repetir:
                self.ui.txt_pass_repetir.setStyleSheet(self.style_qline_ok)
                return True
            else:
                self.ui.txt_pass_repetir.setStyleSheet(self.style_qline_error)
                return False
        except AttributeError:
            return False

    def procesar_cambio_password(self):
        password_anterior = self.ui.txt_pass_anterior.text()
        password_nuevo = self.ui.txt_pass_nuevo.text()
        password_repetir = self.ui.txt_pass_repetir.text()
        password_actual_guardado = self.current_password

        if not password_actual_guardado == password_anterior:
            QMessageBox.warning(self, "Acción denegada", "La contraseña anterior no es igual a la ingresada.")
            self.limpiar_campos_password()
            return
        if not password_nuevo or not password_repetir:
            QMessageBox.warning(self, "Error", "El campo 'Password Nuevo' y 'Repetir' no pueden estar vacíos.")
            self.limpiar_campos_password()
            return
        if password_nuevo != password_repetir:
            QMessageBox.warning(self, "Error", "Las nuevas contraseñas no coinciden.")
            self.limpiar_campos_password()
            return
        if password_nuevo == password_actual_guardado:
            QMessageBox.warning(self, "Error", "La nueva contraseña no puede ser igual a la anterior.")
            self.limpiar_campos_password()
            return
        if not (4 <= len(password_nuevo) <= 10) or \
                not re.search(r"[A-Z]", password_nuevo) or \
                not re.search(r"[a-z]", password_nuevo) or \
                not re.search(r"[0-9]", password_nuevo) or \
                not re.search(r"[^a-zA-Z0-9]", password_nuevo):
            self.limpiar_campos_password()
            QMessageBox.warning(self, "Error", "La contraseña nueva no cumple con los criterios.")
            return
        if self.db_manager.verificar_password_existente(password_nuevo):
            QMessageBox.warning(self, "Error", "Esa contraseña ya está en uso por otro usuario.")
            self.limpiar_campos_password()
            return
        exito = self.db_manager.actualizar_password(self.current_login, password_nuevo)
        if exito:
            QMessageBox.information(self, "Éxito", "¡Contraseña actualizada correctamente!")
            self.current_password = password_nuevo
            self.limpiar_campos_password()
        else:
            QMessageBox.critical(self, "Error de Base de Datos", "No se pudo actualizar la contraseña.")

    def limpiar_campos_password(self):
        try:
            self.ui.txt_pass_anterior.clear()
            self.ui.txt_pass_nuevo.clear()
            self.ui.txt_pass_repetir.clear()
            self.limpiar_estilos_password()
        except AttributeError:
            pass

    def limpiar_estilos_password(self, reset_field_color=True):
        try:
            if reset_field_color:
                self.ui.txt_pass_anterior.setStyleSheet(self.style_qline_ok)
                self.ui.txt_pass_nuevo.setStyleSheet(self.style_qline_ok)
                self.ui.txt_pass_repetir.setStyleSheet(self.style_qline_ok)
            self.ui.caracter.setStyleSheet(self.style_crit_error)
            self.ui.mayus.setStyleSheet(self.style_crit_error)
            self.ui.minus.setStyleSheet(self.style_crit_error)
            self.ui.numer.setStyleSheet(self.style_crit_error)
            self.ui.caracter_especial.setStyleSheet(self.style_crit_error)
        except AttributeError:
            pass

    def configurar_botones_pagos(self, estado):
        self.estado_actual_pagos = estado
        fila_seleccionada = self.ui.tabla_pagos.currentRow()
        if estado == "consultando":
            self.ui.btn_pagos_nuevo.setText("Nuevo")
            self.ui.btn_pagos_nuevo.setEnabled(True)
            self.ui.btn_pagos_actualizar.setText("Actualizar")
            self.ui.btn_pagos_actualizar.setEnabled(fila_seleccionada != -1)
            self.ui.btn_pagos_borrar.setText("Borrar")
            self.ui.btn_pagos_borrar.setEnabled(fila_seleccionada != -1)
            self.ui.btn_pagos_cancelar.setEnabled(False)
            self.ui.btn_pagos_consultar.setEnabled(True)
        elif estado == "nuevo":
            self.ui.btn_pagos_nuevo.setText("Guardar")
            self.ui.btn_pagos_nuevo.setEnabled(True)
            self.ui.btn_pagos_actualizar.setEnabled(False)
            self.ui.btn_pagos_borrar.setEnabled(False)
            self.ui.btn_pagos_cancelar.setEnabled(True)
            self.ui.btn_pagos_consultar.setEnabled(True)
        elif estado == "actualizando":
            self.ui.btn_pagos_nuevo.setEnabled(False)
            self.ui.btn_pagos_actualizar.setText("Guardar")
            self.ui.btn_pagos_actualizar.setEnabled(True)
            self.ui.btn_pagos_borrar.setEnabled(False)
            self.ui.btn_pagos_cancelar.setEnabled(True)
            self.ui.btn_pagos_consultar.setEnabled(True)

    def cargar_tabla_pagos(self):
        if self.current_puesto == 'Estudiante':
            datos_pagos = self.db_manager.get_pagos_por_usuario(self.current_cv_user)
            headers = ["ID Cobro", "Fecha", "Tipo", "Monto", "Descuento", "Estado", "Alumno"]
        else:
            datos_pagos = self.db_manager.get_todos_los_pagos()
            headers = ["ID Cobro", "Fecha", "Tipo", "Monto", "Descuento", "Estado", "Alumno", "ID Usuario"]
        self.ui.tabla_pagos.setColumnCount(len(headers))
        self.ui.tabla_pagos.setHorizontalHeaderLabels(headers)
        self.ui.tabla_pagos.setRowCount(len(datos_pagos))
        for row_idx, row_data in enumerate(datos_pagos):
            for col_idx, col_data in enumerate(row_data):
                item = QTableWidgetItem(str(col_data))
                self.ui.tabla_pagos.setItem(row_idx, col_idx, item)
        header = self.ui.tabla_pagos.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ui.tabla_pagos.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ui.tabla_pagos.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ui.tabla_pagos.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.ui.tabla_pagos.itemSelectionChanged.connect(
            lambda: self.configurar_botones_pagos("consultando") if self.estado_actual_pagos == "consultando" else None
        )

    def cargar_combobox_alumnos(self):
        self.ui.combo_pagos_alumno.clear()
        if self.current_puesto == 'Estudiante':
            self.ui.combo_pagos_alumno.addItem(self.current_nombre_completo, self.current_cv_user)
            self.ui.combo_pagos_alumno.setEnabled(False)
            self.ui.combo_pagos_alumno.setEditable(False)
        else:
            self.ui.combo_pagos_alumno.setEnabled(True)
            self.ui.combo_pagos_alumno.setEditable(True)
            alumnos = self.db_manager.get_alumnos_para_combobox()
            nombres_alumnos = []
            self.ui.combo_pagos_alumno.addItem("Seleccionar alumno...", None)
            for cv_user, nombre_completo in alumnos:
                self.ui.combo_pagos_alumno.addItem(nombre_completo, cv_user)
                nombres_alumnos.append(nombre_completo)
            completer = QCompleter(nombres_alumnos)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            self.ui.combo_pagos_alumno.setCompleter(completer)

    def cargar_combobox_pagos_y_descuentos(self):
        self.ui.combo_pagos_tipo.clear()
        tipos_pago = self.db_manager.get_tipos_pago()
        self.ui.combo_pagos_tipo.addItem("Seleccione un tipo...", (None, 0.0))
        for cv, ds, monto in tipos_pago:
            self.ui.combo_pagos_tipo.addItem(f"{ds} (${monto})", (cv, monto))
        self.ui.combo_pagos_descuento.clear()
        descuentos = self.db_manager.get_descuentos()
        self.ui.combo_pagos_descuento.addItem("Seleccione descuento...", (None, 0.0))
        for cv, ds, porcentaje in descuentos:
            self.ui.combo_pagos_descuento.addItem(f"{ds} ({porcentaje * 100}%)", (cv, porcentaje))
        if self.current_puesto == 'Estudiante':
            self.ui.combo_pagos_tipo.setEnabled(False)
            self.ui.combo_pagos_descuento.setEnabled(False)
        else:
            self.ui.combo_pagos_tipo.setEnabled(True)
            self.ui.combo_pagos_descuento.setEnabled(True)

    def actualizar_monto_y_total(self):
        tipo_data = self.ui.combo_pagos_tipo.currentData()
        desc_data = self.ui.combo_pagos_descuento.currentData()
        monto = 0.0
        porcentaje_desc = 0.0
        if tipo_data and tipo_data[0] is not None:
            monto = float(tipo_data[1])
        if desc_data and desc_data[0] is not None:
            porcentaje_desc = float(desc_data[1])
        monto_descuento = monto * porcentaje_desc
        total = monto - monto_descuento
        locale = QLocale(QLocale.Language.Spanish, QLocale.Country.Mexico)
        self.ui.txt_pagos_monto.setText(locale.toString(monto, 'f', 2))
        self.ui.txt_pagos_total.setText(locale.toString(total, 'f', 2))

    def limpiar_formulario_pagos(self):
        self.ui.lbl_pagos_user_dinamico.setText(self.current_nombre_completo)
        self.ui.date_pagos_fecha.setDate(QDate.currentDate())
        self.ui.combo_pagos_tipo.setCurrentIndex(0)
        self.ui.combo_pagos_descuento.setCurrentIndex(0)
        self.ui.txt_pagos_monto.clear()
        self.ui.txt_pagos_total.clear()
        self.ui.combo_pagos_estado.setCurrentIndex(0)
        if self.current_puesto != 'Estudiante':
            self.ui.combo_pagos_alumno.setCurrentIndex(0)

    def accion_pagos_nuevo(self):
        if self.estado_actual_pagos == "nuevo":
            self.guardar_nuevo_pago()
        else:
            self.ui.stackedWidget_pagos.setCurrentWidget(self.ui.pagos_page_formulario)
            self.limpiar_formulario_pagos()
            self.current_pago_id_edicion = None
            self.configurar_botones_pagos("nuevo")

    def accion_pagos_actualizar(self):
        if self.estado_actual_pagos == "actualizando":
            self.guardar_actualizacion_pago()
        else:
            fila = self.ui.tabla_pagos.currentRow()
            if fila == -1:
                QMessageBox.warning(self, "Error", "No has seleccionado ningún pago para actualizar.")
                return
            headers = [self.ui.tabla_pagos.horizontalHeaderItem(c).text() for c in
                       range(self.ui.tabla_pagos.columnCount())]
            try:
                datos_fila = {}
                for idx, header in enumerate(headers):
                    datos_fila[header] = self.ui.tabla_pagos.item(fila, idx).text()
                self.current_pago_id_edicion = int(datos_fila["ID Cobro"])
                self.limpiar_formulario_pagos()
                self._set_combo_by_text(self.ui.combo_pagos_alumno, datos_fila["Alumno"])
                self._set_combo_by_text(self.ui.combo_pagos_tipo, datos_fila["Tipo"])
                monto = float(datos_fila["Monto"])
                descuento = float(datos_fila["Descuento"])
                if monto > 0:
                    porcentaje_buscado = (descuento / monto) * 100
                    self._set_combo_by_text(self.ui.combo_pagos_descuento, f"({porcentaje_buscado:.2f}%)")
                else:
                    self.ui.combo_pagos_descuento.setCurrentIndex(0)
                self.ui.combo_pagos_estado.setCurrentText(datos_fila["Estado"])
                fecha = QDate.fromString(datos_fila["Fecha"], "yyyy-MM-dd")
                self.ui.date_pagos_fecha.setDate(fecha)
                self.ui.stackedWidget_pagos.setCurrentWidget(self.ui.pagos_page_formulario)
                self.configurar_botones_pagos("actualizando")
            except Exception as e:
                print(f"Error al leer tabla: {e}")

    def accion_pagos_borrar(self):
        fila = self.ui.tabla_pagos.currentRow()
        if fila == -1:
            QMessageBox.warning(self, "Error", "No has seleccionado ningún pago para borrar.")
            return
        try:
            id_cobro_item = self.ui.tabla_pagos.item(fila, 0)
            id_a_borrar = int(id_cobro_item.text())
            col_alumno_idx = -1
            for col in range(self.ui.tabla_pagos.columnCount()):
                header = self.ui.tabla_pagos.horizontalHeaderItem(col).text()
                if header == "Alumno":
                    col_alumno_idx = col
                    break
            nombre_alumno = self.ui.tabla_pagos.item(fila,
                                                     col_alumno_idx).text() if col_alumno_idx != -1 else "pago seleccionado"
            confirmacion = QMessageBox.question(self, "Confirmar Eliminación",
                                                f"¿Deseas eliminar el pago de {nombre_alumno} (ID: {id_a_borrar})?",
                                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirmacion == QMessageBox.StandardButton.Yes:
                exito = self.db_manager.delete_pago(id_a_borrar, self.current_login)
                if exito:
                    QMessageBox.information(self, "Éxito", "Pago eliminado.")
                    self.cargar_tabla_pagos()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo eliminar.")
        except Exception as e:
            print(f"Error al borrar pago: {e}")

    def accion_pagos_consultar(self):
        self.ui.stackedWidget_pagos.setCurrentWidget(self.ui.pagos_page_consulta)
        self.configurar_botones_pagos("consultando")
        self.ui.filtro_pagos_nombre.clear()
        self.ui.filtro_pagos_estado.setCurrentIndex(0)
        self.cargar_tabla_pagos()

    def accion_pagos_cancelar(self):
        self.accion_pagos_consultar()

    def accion_pagos_regresar(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.Inicio)
        if self.menu_esta_oculto:
            self.toggle_menu_main()

    def guardar_nuevo_pago(self):
        texto_alumno = self.ui.combo_pagos_alumno.currentText()
        cv_usuario = None
        if texto_alumno != "Seleccione un alumno...":
            index = self.ui.combo_pagos_alumno.findText(texto_alumno, Qt.MatchFlag.MatchExactly)
            if index != -1:
                cv_usuario = self.ui.combo_pagos_alumno.itemData(index)
        fecha = self.ui.date_pagos_fecha.date().toString("yyyy-MM-dd")
        tipo_data = self.ui.combo_pagos_tipo.currentData()
        desc_data = self.ui.combo_pagos_descuento.currentData()
        estado = self.ui.combo_pagos_estado.currentText()
        if not cv_usuario:
            QMessageBox.warning(self, "Error", "Alumno no válido o no seleccionado.")
            return
        if not tipo_data or tipo_data[0] is None:
            QMessageBox.warning(self, "Error", "Seleccione un Tipo de Pago.")
            return
        if not desc_data or desc_data[0] is None:
            QMessageBox.warning(self, "Error", "Seleccione un Descuento.")
            return
        tipo_str = self.ui.combo_pagos_tipo.currentText().split(" (")[0]
        monto_final = float(tipo_data[1])
        porcentaje_final = float(desc_data[1])
        descuento_calculado = monto_final * porcentaje_final
        exito = self.db_manager.add_pago(
            cv_usuario=cv_usuario,
            fecha=fecha,
            tipo=tipo_str,
            monto=monto_final,
            descuento=descuento_calculado,
            estado=estado,
            admin_login=self.current_login
        )
        if exito:
            QMessageBox.information(self, "Éxito", "Pago registrado.")
            self.accion_pagos_consultar()
        else:
            QMessageBox.critical(self, "Error", "No se registró en BD.")

    def cargar_combobox_filtro_estado(self):
        self.ui.filtro_pagos_estado.clear()
        self.ui.filtro_pagos_estado.addItem("Todos")
        self.ui.filtro_pagos_estado.addItem("Pagado")
        self.ui.filtro_pagos_estado.addItem("Pendiente")

    def actualizar_filtros_tabla(self):
        filtro_nombre = self.ui.filtro_pagos_nombre.text().lower()
        filtro_estado = self.ui.filtro_pagos_estado.currentText()
        col_alumno_idx = -1
        col_estado_idx = -1
        for col in range(self.ui.tabla_pagos.columnCount()):
            header = self.ui.tabla_pagos.horizontalHeaderItem(col).text()
            if header == "Alumno":
                col_alumno_idx = col
            elif header == "Estado":
                col_estado_idx = col
        for fila in range(self.ui.tabla_pagos.rowCount()):
            item_alumno = self.ui.tabla_pagos.item(fila, col_alumno_idx).text().lower()
            item_estado = self.ui.tabla_pagos.item(fila, col_estado_idx).text()
            match_nombre = filtro_nombre in item_alumno
            match_estado = (filtro_estado == "Todos" or filtro_estado == item_estado)
            self.ui.tabla_pagos.setRowHidden(fila, not (match_nombre and match_estado))

    def _set_combo_by_text(self, combobox, texto_a_buscar):
        if not texto_a_buscar:
            combobox.setCurrentIndex(0)
            return
        index = combobox.findText(texto_a_buscar, Qt.MatchFlag.MatchContains)
        if index != -1:
            combobox.setCurrentIndex(index)
        else:
            combobox.setCurrentIndex(0)

    def guardar_actualizacion_pago(self):
        if self.current_pago_id_edicion is None:
            return
        cv_cobro = self.current_pago_id_edicion
        texto_alumno = self.ui.combo_pagos_alumno.currentText()
        cv_usuario = None
        if texto_alumno != "Seleccione un alumno...":
            index = self.ui.combo_pagos_alumno.findText(texto_alumno, Qt.MatchFlag.MatchExactly)
            if index != -1:
                cv_usuario = self.ui.combo_pagos_alumno.itemData(index)
        fecha = self.ui.date_pagos_fecha.date().toString("yyyy-MM-dd")
        tipo_data = self.ui.combo_pagos_tipo.currentData()
        desc_data = self.ui.combo_pagos_descuento.currentData()
        estado = self.ui.combo_pagos_estado.currentText()
        if not cv_usuario or not tipo_data[0] or not desc_data[0]:
            QMessageBox.warning(self, "Error", "Datos incompletos.")
            return
        tipo_str = self.ui.combo_pagos_tipo.currentText().split(" (")[0]
        monto_final = float(tipo_data[1])
        porcentaje_final = float(desc_data[1])
        descuento_calculado = monto_final * porcentaje_final
        exito = self.db_manager.update_pago(
            cv_cobro=cv_cobro,
            cv_usuario=cv_usuario,
            fecha=fecha,
            tipo=tipo_str,
            monto=monto_final,
            descuento=descuento_calculado,
            estado=estado,
            admin_login=self.current_login
        )
        if exito:
            QMessageBox.information(self, "Éxito", "Pago actualizado.")
            self.accion_pagos_consultar()
        else:
            QMessageBox.critical(self, "Error", "No se actualizó.")

    def cargar_combobox_catalogos_personas(self):
        self.ui.combo_per_genero.clear()
        self.ui.combo_per_genero.addItem("Seleccione...", None)
        for cv, ds in self.db_manager.get_generos():
            self.ui.combo_per_genero.addItem(ds, cv)
        self.ui.combo_per_puesto.clear()
        self.ui.combo_per_puesto.addItem("Seleccione...", None)
        for cv, ds in self.db_manager.get_puestos():
            self.ui.combo_per_puesto.addItem(ds, cv)
        self.ui.combo_per_tipopersona.clear()
        self.ui.combo_per_tipopersona.addItem("Seleccione...", None)
        for cv, ds in self.db_manager.get_tipos_persona():
            self.ui.combo_per_tipopersona.addItem(ds, cv)

    def cargar_combobox_filtro_tipo_persona(self):
        self.ui.filtro_personas_tipo.clear()
        self.ui.filtro_personas_tipo.addItem("Todos")
        for cv, ds in self.db_manager.get_tipos_persona():
            self.ui.filtro_personas_tipo.addItem(ds)

    def cargar_tabla_personas(self):
        datos_personas = self.db_manager.get_all_personas_info()
        headers = ["ID Usuario", "Login", "Nombre Completo", "Tipo", "Puesto", "E-mail", "Telefono", "EdoCta"]
        self.ui.tabla_personas.setColumnCount(len(headers))
        self.ui.tabla_personas.setHorizontalHeaderLabels(headers)
        self.ui.tabla_personas.setRowCount(len(datos_personas))
        for row_idx, row_data in enumerate(datos_personas):
            for col_idx, col_data in enumerate(row_data):
                item = QTableWidgetItem(str(col_data))
                self.ui.tabla_personas.setItem(row_idx, col_idx, item)
        header = self.ui.tabla_personas.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ui.tabla_personas.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ui.tabla_personas.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ui.tabla_personas.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

    def limpiar_formulario_personas(self):
        self.ui.lbl_per_user_dinamico.setText(self.current_nombre_completo)
        self.ui.txt_per_nombre.clear()
        self.ui.txt_per_apepat.clear()
        self.ui.txt_per_apemat.clear()
        self.ui.txt_per_email.clear()
        self.ui.txt_per_telefono.clear()
        self.ui.txt_per_login.clear()
        self.ui.txt_per_password.clear()
        self.ui.date_per_fecnac.setDate(QDate(2000, 1, 1))
        self.ui.date_per_fecini.setDate(QDate.currentDate())
        self.ui.date_per_fecven.setDate(QDate.currentDate().addYears(1))
        self.ui.combo_per_genero.setCurrentIndex(0)
        self.ui.combo_per_puesto.setCurrentIndex(0)
        self.ui.combo_per_tipopersona.setCurrentIndex(0)
        self.ui.combo_per_edocta.setCurrentIndex(0)
        self.current_persona_id_edicion = None

    def configurar_botones_personas(self, estado):
        self.estado_actual_personas = estado
        fila_seleccionada = self.ui.tabla_personas.currentRow()
        if estado == "consultando":
            self.ui.btn_per_nuevo.setText("Nuevo")
            self.ui.btn_per_nuevo.setEnabled(True)
            self.ui.btn_per_actualizar.setText("Actualizar")
            self.ui.btn_per_actualizar.setEnabled(fila_seleccionada != -1)
            self.ui.btn_per_borrar.setText("Borrar")
            self.ui.btn_per_borrar.setEnabled(fila_seleccionada != -1)
            self.ui.btn_per_cancelar.setEnabled(False)
            self.ui.btn_per_consultar.setEnabled(True)
        elif estado == "nuevo":
            self.ui.btn_per_nuevo.setText("Guardar")
            self.ui.btn_per_nuevo.setEnabled(True)
            self.ui.btn_per_actualizar.setText("Actualizar")
            self.ui.btn_per_actualizar.setEnabled(False)
            self.ui.btn_per_borrar.setEnabled(False)
            self.ui.btn_per_cancelar.setEnabled(True)
            self.ui.btn_per_consultar.setEnabled(True)
        elif estado == "actualizando":
            self.ui.btn_per_nuevo.setText("Nuevo")
            self.ui.btn_per_nuevo.setEnabled(False)
            self.ui.btn_per_actualizar.setText("Guardar")
            self.ui.btn_per_actualizar.setEnabled(True)
            self.ui.btn_per_borrar.setEnabled(False)
            self.ui.btn_per_cancelar.setEnabled(True)
            self.ui.btn_per_consultar.setEnabled(True)

    def actualizar_filtros_tabla_personas(self):
        filtro_nombre = self.ui.filtro_personas_nombre.text().lower()
        filtro_tipo = self.ui.filtro_personas_tipo.currentText()
        col_nombre_idx = 2
        col_tipo_idx = 3
        for fila in range(self.ui.tabla_personas.rowCount()):
            item_nombre = self.ui.tabla_personas.item(fila, col_nombre_idx).text().lower()
            item_tipo = self.ui.tabla_personas.item(fila, col_tipo_idx).text()
            match_nombre = filtro_nombre in item_nombre
            match_tipo = (filtro_tipo == "Todos" or filtro_tipo == item_tipo)
            self.ui.tabla_personas.setRowHidden(fila, not (match_nombre and match_tipo))

    def accion_personas_nuevo(self):
        if self.estado_actual_personas == "nuevo":
            self.guardar_nueva_persona()
        else:
            self.ui.stackedWidget_personas.setCurrentWidget(self.ui.personas_page_formulario)
            self.limpiar_formulario_personas()
            self.configurar_botones_personas("nuevo")

    def accion_personas_consultar(self):
        self.ui.stackedWidget_personas.setCurrentWidget(self.ui.personas_page_consulta)
        self.configurar_botones_personas("consultando")
        self.ui.filtro_personas_nombre.clear()
        self.ui.filtro_personas_tipo.setCurrentIndex(0)
        self.cargar_tabla_personas()

    def accion_personas_cancelar(self):
        self.accion_personas_consultar()

    def accion_personas_regresar(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.Inicio)
        if self.menu_esta_oculto:
            self.toggle_menu_main()

    def guardar_nueva_persona(self):
        campos_texto = {
            "Nombre": self.ui.txt_per_nombre,
            "Apellido Paterno": self.ui.txt_per_apepat,
            "Apellido Materno": self.ui.txt_per_apemat,
            "E-mail": self.ui.txt_per_email,
            "Login": self.ui.txt_per_login,
            "Password": self.ui.txt_per_password
        }
        for nombre, widget in campos_texto.items():
            if not widget.text().strip():
                QMessageBox.warning(self, "Error", f"El campo '{nombre}' no puede estar vacío.")
                return
        if self.ui.combo_per_genero.currentIndex() <= 0:
            QMessageBox.warning(self, "Error", "Seleccione un Género.")
            return
        if self.ui.combo_per_puesto.currentIndex() <= 0:
            QMessageBox.warning(self, "Error", "Seleccione un Puesto.")
            return
        if self.ui.combo_per_tipopersona.currentIndex() <= 0:
            QMessageBox.warning(self, "Error", "Seleccione Tipo de Persona.")
            return
        login_nuevo = self.ui.txt_per_login.text().strip()
        if self.db_manager.check_login_exists(login_nuevo):
            QMessageBox.warning(self, "Error", "El login ya existe.")
            return

        fecha_nac = self.ui.date_per_fecnac.date()
        edad_calculada = self._calcular_edad(fecha_nac)

        datos_persona = {
            "Nombre": self.ui.txt_per_nombre.text().strip(),
            "ApePat": self.ui.txt_per_apepat.text().strip(),
            "ApeMat": self.ui.txt_per_apemat.text().strip(),
            "FecNac": fecha_nac.toString("yyyy-MM-dd"),
            "E_mail": self.ui.txt_per_email.text().strip(),
            "Telefono": self.ui.txt_per_telefono.text().strip(),
            "CvGenero": self.ui.combo_per_genero.currentData(),
            "CvPuesto": self.ui.combo_per_puesto.currentData(),
            "CvTpPerso": self.ui.combo_per_tipopersona.currentData(),
            "Edad": edad_calculada,
            "RedSoc": "N/A"
        }
        datos_usuario = {
            "Login": login_nuevo,
            "Password": self.ui.txt_per_password.text(),
            "FecIni": self.ui.date_per_fecini.date().toString("yyyy-MM-dd"),
            "FecVen": self.ui.date_per_fecven.date().toString("yyyy-MM-dd"),
            "EdoCta": self.ui.combo_per_edocta.currentText()
        }
        exito = self.db_manager.add_persona_y_usuario(datos_persona, datos_usuario, self.current_login)
        if exito:
            QMessageBox.information(self, "Éxito", f"Usuario '{login_nuevo}' creado.")
            self.accion_personas_consultar()
        else:
            QMessageBox.critical(self, "Error", "No se pudo crear el usuario.")

    def _set_combo_by_data(self, combobox, data_to_find):
        if data_to_find is None:
            combobox.setCurrentIndex(0)
            return
        index = combobox.findData(data_to_find)
        if index != -1:
            combobox.setCurrentIndex(index)
        else:
            combobox.setCurrentIndex(0)

    def accion_personas_actualizar(self):
        if self.estado_actual_personas == "actualizando":
            self.guardar_actualizacion_persona()
        else:
            self.cargar_datos_persona_en_formulario()

    def cargar_datos_persona_en_formulario(self):
        fila = self.ui.tabla_personas.currentRow()
        if fila == -1:
            QMessageBox.warning(self, "Error", "Seleccione una persona.")
            return
        try:
            cv_user_a_editar = int(self.ui.tabla_personas.item(fila, 0).text())
            datos = self.db_manager.get_persona_info_by_id(cv_user_a_editar)
            if not datos:
                QMessageBox.critical(self, "Error", "No se pudieron obtener los datos.")
                return
            self.limpiar_formulario_personas()
            self.current_persona_id_edicion = cv_user_a_editar
            self.current_person_id_edicion = datos['CvPerson']
            self.ui.txt_per_nombre.setText(datos['DsNombre'])
            self.ui.txt_per_apepat.setText(datos['ApePat'])
            self.ui.txt_per_apemat.setText(datos['ApeMat'])
            self.ui.txt_per_email.setText(datos['E_mail'])
            self.ui.txt_per_telefono.setText(datos['Telefono'])
            self.ui.txt_per_login.setText(datos['Login'])
            self.ui.txt_per_password.setText(datos['Password'])
            self._set_combo_by_data(self.ui.combo_per_genero, datos['CvGenero'])
            self._set_combo_by_data(self.ui.combo_per_puesto, datos['CvPuesto'])
            self._set_combo_by_data(self.ui.combo_per_tipopersona, datos['CvTpPerso'])
            self.ui.combo_per_edocta.setCurrentText(datos['EdoCta'])
            self.ui.date_per_fecnac.setDate(QDate.fromString(str(datos['FecNac']), "yyyy-MM-dd"))
            self.ui.date_per_fecini.setDate(QDate.fromString(str(datos['FecIni']), "yyyy-MM-dd"))
            self.ui.date_per_fecven.setDate(QDate.fromString(str(datos['FecVen']), "yyyy-MM-dd"))
            self.ui.stackedWidget_personas.setCurrentWidget(self.ui.personas_page_formulario)
            self.configurar_botones_personas("actualizando")
        except Exception as e:
            print(f"Error cargando persona: {e}")

    def guardar_actualizacion_persona(self):
        cv_user = self.current_persona_id_edicion
        cv_person = self.current_person_id_edicion
        if not cv_user:
            return
        campos_texto = {
            "Nombre": self.ui.txt_per_nombre,
            "Apellido Paterno": self.ui.txt_per_apepat,
            "Apellido Materno": self.ui.txt_per_apemat,
            "E-mail": self.ui.txt_per_email,
            "Login": self.ui.txt_per_login,
            "Password": self.ui.txt_per_password
        }
        for nombre, widget in campos_texto.items():
            if not widget.text().strip():
                QMessageBox.warning(self, "Error", f"El campo '{nombre}' está vacío.")
                return
        login_nuevo = self.ui.txt_per_login.text().strip()
        if self.db_manager.check_login_exists(login_nuevo, current_user_id=cv_user):
            QMessageBox.warning(self, "Error", "El login ya existe.")
            return
        fecha_nac = self.ui.date_per_fecnac.date()
        edad_calculada = self._calcular_edad(fecha_nac)
        datos_persona = {
            "Nombre": self.ui.txt_per_nombre.text().strip(),
            "ApePat": self.ui.txt_per_apepat.text().strip(),
            "ApeMat": self.ui.txt_per_apemat.text().strip(),
            "FecNac": fecha_nac.toString("yyyy-MM-dd"),
            "E_mail": self.ui.txt_per_email.text().strip(),
            "Telefono": self.ui.txt_per_telefono.text().strip(),
            "CvGenero": self.ui.combo_per_genero.currentData(),
            "CvPuesto": self.ui.combo_per_puesto.currentData(),
            "CvTpPerso": self.ui.combo_per_tipopersona.currentData(),
            "Edad": edad_calculada,
            "RedSoc": "N/A"
        }
        datos_usuario = {
            "Login": login_nuevo,
            "Password": self.ui.txt_per_password.text(),
            "FecIni": self.ui.date_per_fecini.date().toString("yyyy-MM-dd"),
            "FecVen": self.ui.date_per_fecven.date().toString("yyyy-MM-dd"),
            "EdoCta": self.ui.combo_per_edocta.currentText()
        }
        exito = self.db_manager.update_persona_y_usuario(cv_user, cv_person, datos_persona, datos_usuario,
                                                         self.current_login)
        if exito:
            QMessageBox.information(self, "Éxito", "Usuario actualizado.")
            self.accion_personas_consultar()
        else:
            QMessageBox.critical(self, "Error", "No se pudo actualizar.")

    def accion_personas_borrar(self):
        fila = self.ui.tabla_personas.currentRow()
        if fila == -1:
            QMessageBox.warning(self, "Error", "Seleccione una persona.")
            return
        try:
            cv_user = int(self.ui.tabla_personas.item(fila, 0).text())
            nombre = self.ui.tabla_personas.item(fila, 2).text()
            if cv_user == self.current_cv_user:
                QMessageBox.critical(self, "Error", "No puedes borrar tu propia cuenta.")
                return
            confirmacion = QMessageBox.question(self, "Confirmar",
                                                f"¿Eliminar a {nombre} (ID: {cv_user})?\nSe borrarán sus pagos y asistencias.",
                                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirmacion == QMessageBox.StandardButton.Yes:
                exito = self.db_manager.delete_persona_y_usuario(cv_user, self.current_login)
                if exito:
                    QMessageBox.information(self, "Éxito", "Usuario eliminado.")
                    self.cargar_tabla_personas()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo eliminar.")
        except Exception as e:
            print(f"Error al borrar: {e}")

    def _configurar_botones_crud(self, estado, btn_nuevo, btn_actualizar, btn_borrar, btn_cancelar, btn_consultar):
        if estado == "consultando":
            btn_nuevo.setText("Nuevo")
            btn_nuevo.setEnabled(True)
            btn_actualizar.setText("Actualizar")
            btn_actualizar.setEnabled(True)
            btn_borrar.setText("Borrar")
            btn_borrar.setEnabled(True)
            btn_cancelar.setEnabled(False)
            btn_consultar.setEnabled(True)
        elif estado == "nuevo":
            btn_nuevo.setText("Guardar")
            btn_nuevo.setEnabled(True)
            btn_actualizar.setEnabled(False)
            btn_borrar.setEnabled(False)
            btn_cancelar.setEnabled(True)
            btn_consultar.setEnabled(True)
        elif estado == "actualizando":
            btn_nuevo.setEnabled(False)
            btn_actualizar.setText("Guardar")
            btn_actualizar.setEnabled(True)
            btn_borrar.setEnabled(False)
            btn_cancelar.setEnabled(True)
            btn_consultar.setEnabled(True)
        elif estado == "borrando":
            btn_nuevo.setEnabled(False)
            btn_actualizar.setEnabled(False)
            btn_borrar.setText("Borrar")
            btn_borrar.setEnabled(True)
            btn_cancelar.setEnabled(True)
            btn_consultar.setEnabled(True)

    def accion_catalogos_nuevo(self):
        catalogo = self.ui.combo_catalogo_seleccion.currentText()
        if self.estado_actual_catalogos == "nuevo":
            self.db_manager.registrar_acceso(self.current_login, True, f"INSERT catalogo '{catalogo}' (Sim)",
                                             self.obtener_ip())
            QMessageBox.information(self, "Simulación", f"Registro guardado en '{catalogo}'.")
            self.accion_catalogos_consultar()
        else:
            self.estado_actual_catalogos = "nuevo"
            self._configurar_botones_crud("nuevo", self.ui.btn_cata_nuevo, self.ui.btn_cata_actualizar,
                                          self.ui.btn_cata_borrar, self.ui.btn_cata_cancelar,
                                          self.ui.btn_cata_consultar)

    def accion_catalogos_actualizar(self):
        catalogo = self.ui.combo_catalogo_seleccion.currentText()
        if self.estado_actual_catalogos == "actualizando":
            self.db_manager.registrar_acceso(self.current_login, True, f"UPDATE catalogo '{catalogo}' (Sim)",
                                             self.obtener_ip())
            QMessageBox.information(self, "Simulación", f"Registro actualizado en '{catalogo}'.")
            self.accion_catalogos_consultar()
        else:
            self.estado_actual_catalogos = "actualizando"
            self._configurar_botones_crud("actualizando", self.ui.btn_cata_nuevo, self.ui.btn_cata_actualizar,
                                          self.ui.btn_cata_borrar, self.ui.btn_cata_cancelar,
                                          self.ui.btn_cata_consultar)

    def accion_catalogos_borrar(self):
        catalogo = self.ui.combo_catalogo_seleccion.currentText()
        self.estado_actual_catalogos = "borrando"
        self._configurar_botones_crud("borrando", self.ui.btn_cata_nuevo, self.ui.btn_cata_actualizar,
                                      self.ui.btn_cata_borrar, self.ui.btn_cata_cancelar, self.ui.btn_cata_consultar)
        self.db_manager.registrar_acceso(self.current_login, True, f"DELETE catalogo '{catalogo}' (Sim)",
                                         self.obtener_ip())
        QMessageBox.information(self, "Simulación", f"Registro borrado de '{catalogo}'.")

    def accion_catalogos_consultar(self):
        self.estado_actual_catalogos = "consultando"
        self._configurar_botones_crud(self.estado_actual_catalogos, self.ui.btn_cata_nuevo, self.ui.btn_cata_actualizar,
                                      self.ui.btn_cata_borrar, self.ui.btn_cata_cancelar, self.ui.btn_cata_consultar)

    def accion_asistencia_nuevo(self):
        if self.estado_actual_asistencia == "nuevo":
            self.db_manager.registrar_acceso(self.current_login, True, "INSERT asistencia (Sim)", self.obtener_ip())
            QMessageBox.information(self, "Simulación", "Asistencia guardada.")
            self.accion_asistencia_consultar()
        else:
            self.estado_actual_asistencia = "nuevo"
            self._configurar_botones_crud(self.estado_actual_asistencia, self.ui.btn_asis_nuevo,
                                          self.ui.btn_asis_actualizar, self.ui.btn_asis_borrar,
                                          self.ui.btn_asis_cancelar, self.ui.btn_asis_consultar)

    def accion_asistencia_actualizar(self):
        if self.estado_actual_asistencia == "actualizando":
            self.db_manager.registrar_acceso(self.current_login, True, "UPDATE asistencia (Sim)", self.obtener_ip())
            QMessageBox.information(self, "Simulación", "Asistencia actualizada.")
            self.accion_asistencia_consultar()
        else:
            self.estado_actual_asistencia = "actualizando"
            self._configurar_botones_crud(self.estado_actual_asistencia, self.ui.btn_asis_nuevo,
                                          self.ui.btn_asis_actualizar, self.ui.btn_asis_borrar,
                                          self.ui.btn_asis_cancelar, self.ui.btn_asis_consultar)

    def accion_asistencia_borrar(self):
        self.estado_actual_asistencia = "borrando"
        self._configurar_botones_crud(self.estado_actual_asistencia, self.ui.btn_asis_nuevo,
                                      self.ui.btn_asis_actualizar, self.ui.btn_asis_borrar, self.ui.btn_asis_cancelar,
                                      self.ui.btn_asis_consultar)
        self.db_manager.registrar_acceso(self.current_login, True, "DELETE asistencia (Sim)", self.obtener_ip())
        QMessageBox.information(self, "Simulación", "Asistencia borrada.")

    def accion_asistencia_consultar(self):
        self.estado_actual_asistencia = "consultando"
        self._configurar_botones_crud(self.estado_actual_asistencia, self.ui.btn_asis_nuevo,
                                      self.ui.btn_asis_actualizar, self.ui.btn_asis_borrar, self.ui.btn_asis_cancelar,
                                      self.ui.btn_asis_consultar)

    def accion_evaluaciones_nuevo(self):
        if self.estado_actual_evaluaciones == "nuevo":
            self.db_manager.registrar_acceso(self.current_login, True, "INSERT evaluacion (Sim)", self.obtener_ip())
            QMessageBox.information(self, "Simulación", "Evaluación guardada.")
            self.accion_evaluaciones_consultar()
        else:
            self.estado_actual_evaluaciones = "nuevo"
            self._configurar_botones_crud(self.estado_actual_evaluaciones, self.ui.btn_eva_nuevo,
                                          self.ui.btn_eva_actualizar, self.ui.btn_eva_borrar, self.ui.btn_eva_cancelar,
                                          self.ui.btn_eva_consultar)

    def accion_evaluaciones_actualizar(self):
        if self.estado_actual_evaluaciones == "actualizando":
            self.db_manager.registrar_acceso(self.current_login, True, "UPDATE evaluacion (Sim)", self.obtener_ip())
            QMessageBox.information(self, "Simulación", "Evaluación actualizada.")
            self.accion_evaluaciones_consultar()
        else:
            self.estado_actual_evaluaciones = "actualizando"
            self._configurar_botones_crud(self.estado_actual_evaluaciones, self.ui.btn_eva_nuevo,
                                          self.ui.btn_eva_actualizar, self.ui.btn_eva_borrar, self.ui.btn_eva_cancelar,
                                          self.ui.btn_eva_consultar)

    def accion_evaluaciones_borrar(self):
        self.estado_actual_evaluaciones = "borrando"
        self._configurar_botones_crud(self.estado_actual_evaluaciones, self.ui.btn_eva_nuevo,
                                      self.ui.btn_eva_actualizar, self.ui.btn_eva_borrar, self.ui.btn_eva_cancelar,
                                      self.ui.btn_eva_consultar)
        self.db_manager.registrar_acceso(self.current_login, True, "DELETE evaluacion (Sim)", self.obtener_ip())
        QMessageBox.information(self, "Simulación", "Evaluación borrada.")

    def accion_evaluaciones_consultar(self):
        self.estado_actual_evaluaciones = "consultando"
        self._configurar_botones_crud(self.estado_actual_evaluaciones, self.ui.btn_eva_nuevo,
                                      self.ui.btn_eva_actualizar, self.ui.btn_eva_borrar, self.ui.btn_eva_cancelar,
                                      self.ui.btn_eva_consultar)

    def cargar_lista_de_catalogos(self):
        self.catalogo_config = {
            "Nombre de Personas": ("cNombre", "CvNombre", "DsNombre"),
            "Apellidos de Personas": ("cApellid", "CvApellid", "DsApellid"),
            "Géneros": ("cGenero", "CvGenero", "DsGenero"),
            "Puestos": ("cPuesto", "CvPuesto", "DsPuesto"),
            "Tipos de Persona": ("cTpPerso", "CvTpPerson", "DsTpPerson"),
            "Aficiones": ("cAficion", "CvAficion", "DsAficion"),
            "Departamentos": ("cDepto", "CvDepto", "DsDepto"),
            "Calles": ("cCalle", "CvCalle", "DsCalle"),
            "Colonias": ("cColon", "CvColon", "DsColon"),
            "Municipios": ("cMunicp", "CvMunicp", "DsMunicp"),
            "Estados": ("cEstado", "CvEstado", "DsEstado"),
            "Países": ("cPais", "CvPais", "DsPais"),
            "Grados Académicos": ("CGdoAca", "CvGdoAca", "DsGdoAca"),
            "Marcas": ("cMarca", "CvMarca", "DsMarca"),
            "Presentaciones": ("cPresent", "CvPresent", "DsPresent")
        }
        self.ui.combo_catalogo_seleccion.clear()
        self.ui.combo_catalogo_seleccion.addItems(sorted(self.catalogo_config.keys()))

    def cargar_tabla_catalogos(self):
        seleccion = self.ui.combo_catalogo_seleccion.currentText()
        if not seleccion or seleccion not in self.catalogo_config:
            return
        tabla, col_id, col_desc = self.catalogo_config[seleccion]
        datos = self.db_manager.get_catalogo_dinamico(tabla, col_id, col_desc)
        self.ui.tabla_catalogos.setColumnCount(2)
        self.ui.tabla_catalogos.setHorizontalHeaderLabels(["ID", "Descripción"])
        self.ui.tabla_catalogos.setRowCount(len(datos))
        for row_idx, (id_val, desc_val) in enumerate(datos):
            self.ui.tabla_catalogos.setItem(row_idx, 0, QTableWidgetItem(str(id_val)))
            self.ui.tabla_catalogos.setItem(row_idx, 1, QTableWidgetItem(str(desc_val)))
        self.ui.tabla_catalogos.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ui.tabla_catalogos.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ui.tabla_catalogos.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ui.tabla_catalogos.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

    def obtener_ip(self):
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except:
            return "127.0.0.1"