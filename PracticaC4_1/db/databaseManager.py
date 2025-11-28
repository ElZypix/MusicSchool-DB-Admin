import pymysql
import logging
class DatabaseManager:

    def __init__(self, host, database, user, password):
        self.connection = None
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.connect()

    def connect(self):
        """Establece la conexión con la base de datos usando PyMySQL."""
        try:
            self.connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                autocommit=True,
                # Esto permite que execute acepte %s como placeholder igual que el anterior
                cursorclass=pymysql.cursors.Cursor
            )
            if self.is_connected():
                print("Conexión exitosa a MariaDB (vía PyMySQL)")
        except pymysql.Error as e:
            print(f"Error al conectar con MariaDB: {e}")
            logging.error(f"Error al conectar con MariaDB: {e}")
            self.connection = None

    def is_connected(self):
        """Verifica si la conexión está abierta (Compatible con PyMySQL)."""
        if self.connection and self.connection.open:
            return True
        return False

    def validar_usuario(self, login, password):
        if not self.is_connected():
            return None

        cursor = self.connection.cursor()
        query = """
                    SELECT
                        u.CvUser, u.EdoCta, u.FecIni, u.FecVen,
                        n.DsNombre, 
                        ap.DsApellid, 
                        am.DsApellid,
                        p.DsPuesto,
                        g.DsGenero
                    FROM
                        mUsuario u
                    JOIN mDtsPerson dp ON u.CvPerson = dp.CvPerson
                    JOIN cNombre n ON dp.CvNombre = n.CvNombre
                    JOIN cApellid ap ON dp.CvApePat = ap.CvApellid
                    JOIN cApellid am ON dp.CvApeMat = am.CvApellid
                    LEFT JOIN cPuesto p ON dp.CvPuesto = p.CvPuesto
                    LEFT JOIN cGenero g ON dp.CvGenero = g.CvGenero
                    WHERE
                        BINARY u.Login = %s AND BINARY u.Password = %s;
                """

        try:
            cursor.execute(query, (login, password))
            resultado = cursor.fetchone()

            if resultado is None:
                return -1
            return resultado

        except pymysql.Error as e:
            print(f"ERROR EN LA CONSULTA DE VALIDACIÓN: {e}")
            logging.error(f"Error en validar_usuario (Login: {login}): {e}")
            return None
        finally:
            cursor.close()

    def actualizar_estado_cuenta(self, cv_user, nuevo_estado):
        if not self.is_connected():
            print("Error: No hay conexión a la base de datos.")
            return False

        cursor = self.connection.cursor()
        query = "UPDATE mUsuario SET EdoCta = %s WHERE CvUser = %s;"
        try:
            cursor.execute(query, (nuevo_estado, cv_user))
            self.connection.commit()

            if cursor.rowcount > 0:
                print(f"Estado actualizado para CvUser {cv_user} a '{nuevo_estado}'")
                return True
            else:
                print(f"No se encontró el CvUser {cv_user} para actualizar.")
                return False

        except pymysql.Error as e:
            print(f"ERROR AL ACTUALIZAR: {e}")
            logging.error(f"Error en actualizar_estado_cuenta (CvUser: {cv_user}): {e}")
            self.connection.rollback()
            return False
        finally:
            cursor.close()

    def registrar_acceso(self, usuario_intento, exito, detalle_evento, ip_address="192.168.0.225"):
        if not self.is_connected():
            print("Error no hay conexion en la base de datos para la bitacora.")
            return False

        cursor = self.connection.cursor()
        query = """
        INSERT INTO bitacora_accesos
            (usuario_intento, direccion_ip, fecha_hora, exito, detalle_evento)
        VALUES
            (%s, %s, NOW(), %s, %s);"""

        try:
            datos = (usuario_intento, ip_address, 1 if exito else 0, detalle_evento)
            cursor.execute(query, datos)
            self.connection.commit()
            return True
        except pymysql.Error as e:
            print(f"Error en mostrar en bitacora: {e}")
            return False
        finally:
            cursor.close()

    def verificar_password_existente(self, nuevo_password):
        if not self.is_connected():
            return True

        cursor = self.connection.cursor()
        query = "SELECT CvUser FROM mUsuario WHERE Password = %s;"

        try:
            cursor.execute(query, (nuevo_password,))
            resultado = cursor.fetchone()
            return resultado is not None
        except pymysql.Error as e:
            print(f"ERROR AL VERIFICAR PASSWORD: {e}")
            return True
        finally:
            cursor.close()

    def actualizar_password(self, login_usuario, nuevo_password):
        if not self.is_connected():
            print("Error: No hay conexión a la base de datos.")
            return False

        cursor = self.connection.cursor()
        query = "UPDATE mUsuario SET Password = %s WHERE Login = %s;"
        try:
            cursor.execute(query, (nuevo_password, login_usuario))
            self.connection.commit()

            detalle_evento = "AUDITORIA SEGURIDAD: Cambio de contraseña exitoso."
            self.registrar_acceso(login_usuario, True, detalle_evento)

            return cursor.rowcount > 0

        except pymysql.Error as e:
            print(f"ERROR AL ACTUALIZAR PASSWORD: {e}")
            self.connection.rollback()
            return False
        finally:
            cursor.close()

    # --- Pagos ---
    def get_pagos_por_usuario(self, cv_user):
        if not self.is_connected():
            return []

        query = """
        SELECT 
            f.CvCobro, f.FechaCobro, f.Tipo, f.Monto, f.Descuento, f.Estado,
            CONCAT(n.DsNombre, ' ', ap.DsApellid) AS NombreAlumno
        FROM fCobro f
        JOIN mUsuario u ON f.CvUsuario = u.CvUser
        JOIN mDtsPerson dp ON u.CvPerson = dp.CvPerson
        JOIN cNombre n ON dp.CvNombre = n.CvNombre
        JOIN cApellid ap ON dp.CvApePat = ap.CvApellid
        WHERE f.CvUsuario = %s
        ORDER BY f.FechaCobro DESC;
        """
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (cv_user,))
            return cursor.fetchall()
        except pymysql.Error as e:
            print(f"Error al obtener pagos por usuario: {e}")
            return []
        finally:
            cursor.close()

    def get_todos_los_pagos(self):
        if not self.is_connected():
            return []
        query = """
        SELECT 
            f.CvCobro, f.FechaCobro, f.Tipo, f.Monto, f.Descuento, f.Estado,
            CONCAT(n.DsNombre, ' ', ap.DsApellid) AS NombreAlumno,
            f.CvUsuario
        FROM fCobro f
        JOIN mUsuario u ON f.CvUsuario = u.CvUser
        JOIN mDtsPerson dp ON u.CvPerson = dp.CvPerson
        JOIN cNombre n ON dp.CvNombre = n.CvNombre
        JOIN cApellid ap ON dp.CvApePat = ap.CvApellid
        ORDER BY f.FechaCobro DESC;
        """
        cursor = self.connection.cursor()
        try:
            cursor.execute(query)
            return cursor.fetchall()
        except pymysql.Error as e:
            print(f"Error al obtener todos los pagos: {e}")
            return []
        finally:
            cursor.close()

    def get_alumnos_para_combobox(self):
        if not self.is_connected():
            return []
        query = """
            SELECT 
            u.CvUser,
            CONCAT(n.DsNombre, ' ', ap.DsApellid, ' ', am.DsApellid) AS NombreCompleto
        FROM mUsuario u
        JOIN mDtsPerson dp ON u.CvPerson = dp.CvPerson
        JOIN cTpPerso tp ON dp.CvTpPerso = tp.CvTpPerson
        JOIN cNombre n ON dp.CvNombre = n.CvNombre
        JOIN cApellid ap ON dp.CvApePat = ap.CvApellid
        JOIN cApellid am ON dp.CvApeMat = am.CvApellid
        WHERE tp.DsTpPerson = 'Alumno'
        ORDER BY NombreCompleto;
        """
        cursor = self.connection.cursor()
        try:
            cursor.execute(query)
            return cursor.fetchall()
        except pymysql.Error as e:
            print(f"Error al obtener la lista de alumnos: {e}")
            return []
        finally:
            cursor.close()

    def add_pago(self, cv_usuario, fecha, tipo, monto, descuento, estado, admin_login):
        if not self.is_connected():
            return False
        query = """
                INSERT INTO fCobro (CvUsuario, FechaCobro, Tipo, Monto, Descuento, Estado)
                VALUES (%s, %s, %s, %s, %s, %s);
                """
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (cv_usuario, fecha, tipo, monto, descuento, estado))
            self.connection.commit()

            nuevo_pago_id = cursor.lastrowid
            detalle_evento = f"AUDITORIA BD: INSERT en fCobro. ID: {nuevo_pago_id}, Alumno ID: {cv_usuario}"
            self.registrar_acceso(admin_login, True, detalle_evento)

            return True
        except pymysql.Error as e:
            print(f"Error al añadir pago {e}")
            self.connection.rollback()
            return False
        finally:
            cursor.close()

    def get_tipos_pago(self):
        if not self.is_connected():
            return []
        query = "SELECT CvTipoPago, DsTipoPago, Monto FROM cTiposPago ORDER BY DsTipoPago;"
        cursor = self.connection.cursor()
        try:
            cursor.execute(query)
            return cursor.fetchall()
        except pymysql.Error as e:
            print(f"Error al obtener tipos de pago: {e}")
            return []
        finally:
            cursor.close()

    def get_descuentos(self):
        if not self.is_connected():
            return []
        query = "SELECT CvDescuento, DsDescuento, Porcentaje FROM cDescuentos ORDER BY Porcentaje;"
        cursor = self.connection.cursor()
        try:
            cursor.execute(query)
            return cursor.fetchall()
        except pymysql.Error as e:
            print(f"Error al obtener descuentos: {e}")
            return []
        finally:
            cursor.close()

    def update_pago(self, cv_cobro, cv_usuario, fecha, tipo, monto, descuento, estado, admin_login):
        if not self.is_connected():
            return False

        query = """
                UPDATE fCobro
                SET CvUsuario  = %s,
                    FechaCobro = %s,
                    Tipo       = %s,
                    Monto      = %s,
                    Descuento  = %s,
                    Estado     = %s
                WHERE CvCobro = %s;
                """
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (cv_usuario, fecha, tipo, monto, descuento, estado, cv_cobro))
            self.connection.commit()

            detalle_evento = f"AUDITORIA BD: UPDATE en fCobro. ID: {cv_cobro}"
            self.registrar_acceso(admin_login, True, detalle_evento)

            return True
        except pymysql.Error as e:
            print(f"Error al actualizar pago: {e}")
            self.connection.rollback()
            return False
        finally:
            cursor.close()

    def delete_pago(self, cv_cobro, admin_login):
        if not self.is_connected():
            return False

        query = "DELETE FROM fCobro WHERE CvCobro = %s;"
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (cv_cobro,))
            self.connection.commit()

            detalle_evento = f"AUDITORIA BD: DELETE en fCobro. ID: {cv_cobro}"
            self.registrar_acceso(admin_login, True, detalle_evento)

            return True
        except pymysql.Error as e:
            print(f"Error al eliminar pago: {e}")
            self.connection.rollback()
            return False
        finally:
            cursor.close()

    # --- FUNCIONES PARA MÓDULO DE PERSONAS ---

    def _get_catalog_data(self, query):
        if not self.is_connected():
            return []
        cursor = self.connection.cursor()
        try:
            cursor.execute(query)
            return cursor.fetchall()
        except pymysql.Error as e:
            print(f"Error al obtener catálogo: {e}")
            return []
        finally:
            cursor.close()

    def get_generos(self):
        return self._get_catalog_data("SELECT CvGenero, DsGenero FROM cGenero ORDER BY DsGenero")

    def get_puestos(self):
        return self._get_catalog_data("SELECT CvPuesto, DsPuesto FROM cPuesto ORDER BY DsPuesto")

    def get_tipos_persona(self):
        return self._get_catalog_data("SELECT CvTpPerson, DsTpPerson FROM cTpPerso ORDER BY DsTpPerson")

    def get_all_personas_info(self):
        if not self.is_connected():
            return []

        query = """
                SELECT u.CvUser,
                       u.Login,
                       CONCAT(n.DsNombre, ' ', ap.DsApellid, ' ', am.DsApellid) AS NombreCompleto,
                       tp.DsTpPerson                                            AS Tipo,
                       p.DsPuesto                                               AS Puesto,
                       dp.E_mail,
                       dp.Telefono,
                       u.EdoCta
                FROM mUsuario u
                         JOIN mDtsPerson dp ON u.CvPerson = dp.CvPerson
                         JOIN cNombre n ON dp.CvNombre = n.CvNombre
                         JOIN cApellid ap ON dp.CvApePat = ap.CvApellid
                         JOIN cApellid am ON dp.CvApeMat = am.CvApellid
                         LEFT JOIN cTpPerso tp ON dp.CvTpPerso = tp.CvTpPerson
                         LEFT JOIN cPuesto p ON dp.CvPuesto = p.CvPuesto
                ORDER BY NombreCompleto;
                """
        cursor = self.connection.cursor()
        try:
            cursor.execute(query)
            return cursor.fetchall()
        except pymysql.Error as e:
            print(f"Error al obtener toda la info de personas: {e}")
            return []
        finally:
            cursor.close()

    def _get_or_create_catalog_id(self, cursor, tabla, pk_col, ds_col, valor_str):
        cursor.execute(f"SELECT {pk_col} FROM {tabla} WHERE {ds_col} = %s", (valor_str,))
        resultado = cursor.fetchone()

        if resultado:
            return resultado[0]
        else:
            cursor.execute(f"INSERT INTO {tabla} ({ds_col}) VALUES (%s)", (valor_str,))
            return cursor.lastrowid

    def check_login_exists(self, login, current_user_id=None):
        if not self.is_connected():
            return True

        cursor = self.connection.cursor()
        try:
            if current_user_id:
                query = "SELECT CvUser FROM mUsuario WHERE Login = %s AND CvUser != %s;"
                cursor.execute(query, (login, current_user_id))
            else:
                query = "SELECT CvUser FROM mUsuario WHERE Login = %s;"
                cursor.execute(query, (login,))

            return cursor.fetchone() is not None
        except pymysql.Error as e:
            print(f"Error al verificar login: {e}")
            return True
        finally:
            cursor.close()

    def add_persona_y_usuario(self, datos_persona, datos_usuario, admin_login):
        if not self.is_connected():
            return False

        cursor = self.connection.cursor()
        try:
            self.connection.begin()  # Inicio de transacción en PyMySQL

            # 1. Catálogos
            cv_nombre = self._get_or_create_catalog_id(cursor, "cNombre", "CvNombre", "DsNombre",
                                                       datos_persona['Nombre'])
            cv_apepat = self._get_or_create_catalog_id(cursor, "cApellid", "CvApellid", "DsApellid",
                                                       datos_persona['ApePat'])
            cv_apemat = self._get_or_create_catalog_id(cursor, "cApellid", "CvApellid", "DsApellid",
                                                       datos_persona['ApeMat'])

            # 2. Insertar en mDtsPerson
            query_person = """
                           INSERT INTO mDtsPerson
                           (CvNombre, CvApePat, CvApeMat, FecNac, E_mail, Telefono,
                            CvGenero, CvPuesto, CvTpPerso,
                            CvGdoAca, CvAficion, CvDirecc, CvDepto,
                            RedSoc, Edad) 
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, 1, 1, 1, %s, %s);
                           """
            cursor.execute(query_person, (
                cv_nombre, cv_apepat, cv_apemat,
                datos_persona['FecNac'], datos_persona['E_mail'], datos_persona['Telefono'],
                datos_persona['CvGenero'], datos_persona['CvPuesto'], datos_persona['CvTpPerso'],
                datos_persona['RedSoc'], datos_persona['Edad']
            ))
            cv_person_nuevo = cursor.lastrowid

            # 3. Insertar en mUsuario
            query_user = """
                         INSERT INTO mUsuario
                             (CvPerson, Login, Password, FecIni, FecVen, EdoCta)
                         VALUES (%s, %s, %s, %s, %s, %s);
                         """
            cursor.execute(query_user, (
                cv_person_nuevo,
                datos_usuario['Login'], datos_usuario['Password'],
                datos_usuario['FecIni'], datos_usuario['FecVen'], datos_usuario['EdoCta']
            ))

            self.connection.commit()

            detalle_evento = f"AUDITORIA BD: INSERT en mDtsPerson (ID: {cv_person_nuevo}) y mUsuario (Login: {datos_usuario['Login']})"
            self.registrar_acceso(admin_login, True, detalle_evento)

            return True

        except pymysql.Error as e:
            print(f"Error en la transacción de añadir persona: {e}")
            self.connection.rollback()
            return False
        finally:
            cursor.close()

    def get_persona_info_by_id(self, cv_user):
        if not self.is_connected():
            return None

        query = """
                SELECT dp.CvPerson,
                       n.DsNombre,
                       ap.DsApellid AS ApePat,
                       am.DsApellid AS ApeMat,
                       dp.FecNac, 
                       dp.E_mail,
                       dp.Telefono,
                       dp.CvGenero,
                       dp.CvPuesto,
                       dp.CvTpPerso,
                       u.Login,
                       u.Password,
                       u.FecIni,
                       u.FecVen,
                       u.EdoCta
                FROM mUsuario u
                         JOIN mDtsPerson dp ON u.CvPerson = dp.CvPerson
                         JOIN cNombre n ON dp.CvNombre = n.CvNombre
                         JOIN cApellid ap ON dp.CvApePat = ap.CvApellid
                         JOIN cApellid am ON dp.CvApeMat = am.CvApellid
                WHERE u.CvUser = %s;
                """
        # IMPORTANTE: Usamos DictCursor para obtener resultados como diccionario
        cursor = self.connection.cursor(pymysql.cursors.DictCursor)
        try:
            cursor.execute(query, (cv_user,))
            return cursor.fetchone()
        except pymysql.Error as e:
            print(f"Error al obtener datos de la persona: {e}")
            return None
        finally:
            cursor.close()

    def update_persona_y_usuario(self, cv_user, cv_person, datos_persona, datos_usuario, admin_login):
        if not self.is_connected():
            return False

        cursor = self.connection.cursor()
        try:
            self.connection.begin()

            cv_nombre = self._get_or_create_catalog_id(cursor, "cNombre", "CvNombre", "DsNombre",
                                                       datos_persona['Nombre'])
            cv_apepat = self._get_or_create_catalog_id(cursor, "cApellid", "CvApellid", "DsApellid",
                                                       datos_persona['ApePat'])
            cv_apemat = self._get_or_create_catalog_id(cursor, "cApellid", "CvApellid", "DsApellid",
                                                       datos_persona['ApeMat'])

            query_person = """
                           UPDATE mDtsPerson
                           SET CvNombre  = %s,
                               CvApePat  = %s,
                               CvApeMat  = %s,
                               FecNac    = %s,
                               E_mail    = %s,
                               Telefono  = %s,
                               CvGenero  = %s,
                               CvPuesto  = %s,
                               CvTpPerso = %s,
                               Edad      = %s,
                               RedSoc    = %s
                           WHERE CvPerson = %s;
                           """
            cursor.execute(query_person, (
                cv_nombre, cv_apepat, cv_apemat,
                datos_persona['FecNac'], datos_persona['E_mail'], datos_persona['Telefono'],
                datos_persona['CvGenero'], datos_persona['CvPuesto'], datos_persona['CvTpPerso'],
                datos_persona['Edad'], datos_persona['RedSoc'],
                cv_person
            ))

            query_user = """
                         UPDATE mUsuario
                         SET Login    = %s,
                             Password = %s,
                             FecIni   = %s,
                             FecVen   = %s,
                             EdoCta   = %s
                         WHERE CvUser = %s;
                         """
            cursor.execute(query_user, (
                datos_usuario['Login'], datos_usuario['Password'],
                datos_usuario['FecIni'], datos_usuario['FecVen'], datos_usuario['EdoCta'],
                cv_user
            ))

            self.connection.commit()

            detalle_evento = f"AUDITORIA BD: UPDATE en mDtsPerson (ID: {cv_person}) y mUsuario (ID: {cv_user})"
            self.registrar_acceso(admin_login, True, detalle_evento)

            return True

        except pymysql.Error as e:
            print(f"Error en la transacción de actualizar persona: {e}")
            self.connection.rollback()
            return False
        finally:
            cursor.close()

    def delete_persona_y_usuario(self, cv_user_a_borrar, admin_login):
        if not self.is_connected():
            return False

        cursor = self.connection.cursor()
        cv_person = None
        login_borrado = None
        try:
            cursor.execute("SELECT CvPerson, Login FROM mUsuario WHERE CvUser = %s", (cv_user_a_borrar,))
            resultado = cursor.fetchone()
            if resultado:
                cv_person = resultado[0]
                login_borrado = resultado[1]
            else:
                print(f"No se encontró CvPerson para CvUser {cv_user_a_borrar}")
                return False
        except pymysql.Error as e:
            print(f"Error al buscar CvPerson: {e}")
            return False

        try:
            self.connection.begin()

            # Al borrar la persona, el usuario se borra por cascada
            cursor.execute("DELETE FROM mDtsPerson WHERE CvPerson = %s;", (cv_person,))
            self.connection.commit()

            detalle_evento = f"AUDITORIA BD: DELETE en mDtsPerson (ID: {cv_person}) y mUsuario (Login: {login_borrado})"
            self.registrar_acceso(admin_login, True, detalle_evento)

            return True

        except pymysql.Error as e:
            print(f"Error en la transacción de eliminar persona: {e}")
            self.connection.rollback()
            return False
        finally:
            cursor.close()

    def registrar_error(self, mensaje_error, modulo, usuario_activo="Desconocido", ip_address="192.168.0.225"):
        if not self.is_connected():
            print(f"Fallo crítico: No se pudo guardar el error en BD: {mensaje_error}")
            return False

        cursor = self.connection.cursor()
        query = """
            INSERT INTO mErrores (mensaje_error, modulo, fecha_hora, usuario_activo, direccion_ip)
            VALUES (%s, %s, NOW(), %s, %s);
        """
        try:
            cursor.execute(query, (str(mensaje_error), modulo, usuario_activo, ip_address))
            self.connection.commit()
            return True
        except pymysql.Error as e:
            print(f"Error al registrar en mErrores: {e}")
            return False
        finally:
            cursor.close()

    def get_catalogo_dinamico(self, nombre_tabla, col_id, col_desc):
        if not self.is_connected():
            return []

        query = f"SELECT {col_id}, {col_desc} FROM {nombre_tabla} ORDER BY {col_desc};"
        cursor = self.connection.cursor()
        try:
            cursor.execute(query)
            return cursor.fetchall()
        except pymysql.Error as e:
            print(f"Error al obtener catálogo dinámico ({nombre_tabla}): {e}")
            return []
        finally:
            cursor.close()