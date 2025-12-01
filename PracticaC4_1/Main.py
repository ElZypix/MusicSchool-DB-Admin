import sys
import os
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication
from db.databaseManager import DatabaseManager
from Gui.LoginWindows import LoginWindow
from Gui.ControlWindows import ControlWindows
import logging

load_dotenv()

class MainApplication():
    def __init__(self):
        self.db_manager = DatabaseManager(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        self.login_win = LoginWindow(self.db_manager)
        self.control_win = ControlWindows(self.db_manager)
        self.login_win.login_exitoso.connect(self.mostrar_control)
        self.control_win.sesion_cerrada.connect(self.mostrar_login)

    def run(self):
        self.login_win.show()

    def mostrar_control(self, nombre_completo, puesto, genero, login, password, cv_user):
        self.control_win.set_user_info(nombre_completo, puesto, genero, login, password, cv_user)
        self.control_win.show()

    def mostrar_login(self):
        self.control_win.hide()
        self.login_win.ui.txt_password.clear()
        self.login_win.ui.txt_login.clear()
        self.login_win.show()

if __name__ == '__main__':
    logging.basicConfig(
        filename='system_errors.log',  # El nombre de tu archivo .log
        level=logging.ERROR,  # Solo registra ERRORES o peores (CRITICAL)
        format='%(asctime)s - %(levelname)s - %(message)s',
        encoding='utf-8'  # Para asegurar que acepte acentos
    )
    app = QApplication(sys.argv)
    main_app = MainApplication()
    main_app.run()
    sys.exit(app.exec())