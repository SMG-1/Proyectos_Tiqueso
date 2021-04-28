import datetime
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
import os
from win32api import GetSystemMetrics

from anomalas_back_end import AnomalyApp

bg_color = 'white'


def center_window(toplevel, screen_width, screen_height):
    """Funcion para centrar las ventanas."""
    toplevel.update_idletasks()

    size = tuple(int(_) for _ in toplevel.geometry().split('+')[0].split('x'))
    x = screen_width / 2 - size[0] / 2
    y = screen_height / 2 - size[1] / 2

    toplevel.geometry("+%d+%d" % (x, y))


def browse_files_master(initial_dir):
    if initial_dir != '':
        initial_dir_ = initial_dir

    else:
        initial_dir_ = "/"

    filename = filedialog.askopenfilename(initialdir=initial_dir_,
                                          title="Seleccione un archivo",
                                          filetypes=(("Archivo de Excel",
                                                      "*.xlsx*"),
                                                     ("Archivo CSV",
                                                      "*.csv*")))

    filepath = os.path.dirname(os.path.abspath(filename))

    return filepath, filename


def validate_path(path: str, is_file):
    """Check if a path is valid, if is_file is True, check if it's the correct extension."""

    # first check if path exists, else return False
    if os.path.exists(path):
        # if is_file is true, check if it's the correct extension
        if is_file:
            _, file_ext = os.path.splitext(path)
            if file_ext in ['.xlsx', '.csv']:
                return True
            else:
                return False

        return True

    else:
        return False


class Main:
    def __init__(self, master, path_):
        # tkinter root
        self.master = master

        # window parameters
        self.master.title("Módulo para Detección de Órdenes Anómalas - COPROLAC")
        self.master.configure(background=bg_color)

        # New window default parameter
        self.new_win = None

        # Anomaly App instance declaration
        self.app = AnomalyApp(path_)

        # screen width and height, and toplevel width and height
        self.screen_width = GetSystemMetrics(0)
        self.screen_height = GetSystemMetrics(1)
        self.width = self.screen_width / 2
        self.height = self.screen_height / 2

        # Paned Window that contains the tree view and a master frame
        self.main_paned = tk.PanedWindow(self.master,
                                         orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=1)

        # Listbox - Shows status of the program and relevant information for the user.
        self.list_box = tk.Listbox(self.master,
                                   bg=bg_color,
                                   width=150,
                                   height=20)
        self.main_paned.add(self.list_box)
        self.list_box.insert(tk.END, 'Hola')
        self.list_box.insert(tk.END, '42 anomalias encontradas.')

        # Frame - Contains Load, Execute and Export buttons
        self.config_frame = tk.Frame(self.master,
                                     bg=bg_color)
        self.main_paned.add(self.config_frame)

        # Button - Load files
        self.btn_load_files = tk.Button(self.config_frame,
                                        bg=bg_color,
                                        text='Cargar archivos',
                                        command=self.open_window_select_path)
        self.btn_load_files.pack(padx=5,
                                 pady=10)

        # Button - Search
        self.btn_search = tk.Button(self.config_frame,
                                    bg=bg_color,
                                    text='Buscar anomalías',
                                    command=self.run_anomaly_check)
        self.btn_search.pack(padx=5,
                             pady=10)

        # Button - Config
        self.btn_config = tk.Button(self.config_frame,
                                    bg=bg_color,
                                    text='Configuración',
                                    command=self.open_window_config)
        self.btn_config.pack(padx=5,
                             pady=10)

        # Button - Export result
        self.btn_export = tk.Button(self.config_frame,
                                    bg=bg_color,
                                    text='Exportar resultado')
        self.btn_export.pack(padx=5,
                             pady=10)

        center_window(self.master, self.screen_width, self.screen_height)

    def open_window_select_path(self):
        self.new_win = tk.Toplevel()
        WindowSelectWorkPath(self.new_win, self.app, self.screen_width, self.screen_height)
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)

    def open_window_config(self):
        self.new_win = tk.Toplevel()
        WindowModelConfig(self.new_win, self.app, self.screen_width, self.screen_height)
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)

    def run_anomaly_check(self):
        self.app.create_verification_table()


class WindowSelectWorkPath:

    def __init__(self, master, app: AnomalyApp, screen_width_, screen_height_):
        self.master = master
        self.master.title("Selección de directorio")
        self.master.configure(background=bg_color)
        self.screen_width = screen_width_
        self.screen_height = screen_height_
        self.width = self.screen_width / 2
        self.height = self.screen_height / 5
        self.app = app
        self.new_win = None
        self.successful_load = False
        self.canceled = False

        # --- LEVEL 0 ---
        self.paths_frame = tk.LabelFrame(self.master,
                                         text='Escoja un directorio:',
                                         bg=bg_color,
                                         width=screen_width_ / 5,
                                         padx=10,
                                         pady=10)
        self.paths_frame.grid(padx=10,
                              pady=10,
                              row=0,
                              column=0,
                              columnspan=2)

        # accept and cancel buttons
        self.btn_accept = tk.Button(self.master,
                                    text='Aceptar',
                                    command=self.save_selection)
        self.btn_accept.grid(pady=10, row=1, column=0)

        self.btn_cancel = tk.Button(self.master,
                                    text='Cancelar',
                                    command=self.close_window)
        self.btn_cancel.grid(pady=10, row=1, column=1)

        # --- LEVEL 1 ---

        # Paths Frame

        #  ROW 0: LABEL THAT SHOWS THE PATH
        # Name Label, first column
        self.lbl_name_path = tk.Label(self.paths_frame,
                                      text='Directorio',
                                      bg=bg_color,
                                      padx=5)

        # Name Label, first column
        self.lbl_name_path.grid(row=0,
                                column=0,
                                sticky='W')

        # Path Label, second column
        path = self.app.get_path('Orders')
        self.lbl_path = tk.Label(self.paths_frame,
                                 text=path,
                                 bg=bg_color,
                                 pady=10,
                                 borderwidth=2,
                                 width=150,
                                 relief="groove",
                                 anchor='w')

        # Path Label, second column
        self.lbl_path.grid(row=0,
                           column=1,
                           padx=10,
                           pady=10,
                           sticky='WE')

        # Browse Button, third column, to open the browse files window
        self.btn_browse = tk.Button(self.paths_frame,
                                    text='...',
                                    command=lambda: self.browse_files('Level_1'))

        # Browse Button, third column, to open the browse files window
        self.btn_browse.grid(row=0,
                             column=2,
                             padx=10,
                             pady=10,
                             sticky='WE')

        center_window(self.master, self.screen_width, self.screen_height)

    def browse_files(self, label_name):

        # get the last path that the user selected
        ini_dir_ = self.app.get_path('Temp')

        # call function to open a file selection window
        filepath, filename = browse_files_master(ini_dir_)

        # change the text content of the label
        if filename != '':
            # set the selected path as the new Temp path
            self.app.set_path('Temp', os.path.dirname(os.path.abspath(filename)))

            self.lbl_path.configure(text=filename)

    def save_selection(self):
        """"""

        # open PopUp warning if the Path Label is empty
        if self.lbl_path['text'] == '':
            self.open_window_pop_up('Error', 'Debe seleccionar un directorio válido.')

        path = self.lbl_path['text']
        if validate_path(path, is_file=True):
            self.app.set_path('Orders', path)

        else:
            self.open_window_pop_up('Error',
                                    f'El directorio al archivo de órdenes indicado es inválido.')

        # create separate datasets for each of the unique products
        try:
            self.app.create_segmented_data(process)
            self.open_window_pop_up('Mensaje', 'Archivos cargados.')
            self.successful_load = True
            self.app.set_parameter('Mode', process)
            self.close_window()

        except ValueError as e:
            self.open_window_pop_up('Error', e)

        except PermissionError as e:
            self.open_window_pop_up('Error', 'Debe cerrar el archivo antes de proceder:\n' + e.filename)

    def open_window_pop_up(self, title, msg):
        # open new TopLevel as a popup window
        self.new_win = tk.Toplevel(self.master)
        WindowPopUpMessage(self.new_win, title, msg, self.screen_width, self.screen_height)

        # freeze master window until user closes the pop up
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)

    def close_window(self):
        self.canceled = True
        self.master.destroy()


class WindowModelConfig:

    def __init__(self, master, app: AnomalyApp, screen_width_, screen_height_):
        self.master = master
        self.app = app

        self.master.title("Configuración del modelo")
        self.master.configure(background=bg_color)

        self.screen_width = screen_width_
        self.screen_height = screen_height_
        self.width = self.screen_width / 2
        self.height = self.screen_height / 5

        self.new_win = None
        self.successful_load = False
        self.canceled = False

        # --- LEVEL 0 ---

        # Label - Shows the last time the model was updated.
        last_update_date = datetime.datetime(2021, 4, 26).strftime('%d/%m/%Y')
        self.status_label = tk.Label(self.master,
                                     text=f'Modelo actualizado por última vez el {last_update_date}.')
        self.status_label.grid(row=0, column=0, columnspan=3)

        # Button - Show the path to the file that will be used to update the model.
        self.btn_update_model = tk.Button(self.master,
                                    text='Actualizar modelo')
        self.btn_update_model.grid(row=1, column=1)

        # Label - Naming label for the path widgets
        self.file_path_label = tk.Label(self.master,
                                        text='Directorio:')

        # Label - Shows the path the user selected.
        path_model = self.app.get_path('Anomaly_Model')
        self.lbl_path = tk.Label(self.master,
                                 text=path_model,
                                 bg=bg_color,
                                 pady=10,
                                 borderwidth=2,
                                 width=150,
                                 relief="groove",
                                 anchor='w')

        # Button,opens the browse files window
        self.btn_browse = tk.Button(self.master,
                                    text='...',
                                    command=lambda: self.browse_files('Level_1'))

        # accept and cancel buttons
        self.btn_accept = tk.Button(self.master,
                                    text='Aceptar',
                                    command=self.save_selection)

        self.btn_cancel = tk.Button(self.master,
                                    text='Cancelar',
                                    command=self.close_window)

        center_window(self.master, self.screen_width, self.screen_height)

    def add_path_selection_to_grid(self, row):

        self.file_path_label.grid(row=row, column=0)
        self.lbl_path.grid(row=row, column=1)
        self.btn_browse.grid(row=row, column=2)

        self.btn_accept.grid(row=row+1, column=0)
        self.btn_cancel.grid(row=row+1, column=2)

    def browse_files(self):

        # get the last path that the user selected
        ini_dir_ = self.app.get_path('Temp')

        # call function to open a file selection window
        filepath, filename = browse_files_master(ini_dir_)

        # change the text content of the label
        if filename != '':
            # set the selected path as the new Temp path
            self.app.set_path('Temp', os.path.dirname(os.path.abspath(filename)))

            self.lbl_path.configure(text=filename)

    def save_selection(self):
        """"""

        # open PopUp warning if the Path Label is empty
        if self.lbl_path['text'] == '':
            self.open_window_pop_up('Error', 'Debe seleccionar un directorio válido.')

        path = self.lbl_path['text']
        if validate_path(path, is_file=True):
            self.app.set_path('Anomaly_Model', path)

        else:
            self.open_window_pop_up('Error',
                                    f'El directorio al archivo indicado es inválido.')

        # create separate datasets for each of the unique products
        try:
            self.app.update_model()
            self.open_window_pop_up('Mensaje', 'Archivos cargados.')
            self.successful_load = True
            self.close_window()

        except ValueError as e:
            self.open_window_pop_up('Error', e)

        except PermissionError as e:
            self.open_window_pop_up('Error', 'Debe cerrar el archivo antes de proceder:\n' + e.filename)

    def open_window_pop_up(self, title, msg):
        # open new TopLevel as a popup window
        self.new_win = tk.Toplevel(self.master)
        WindowPopUpMessage(self.new_win, title, msg, self.screen_width, self.screen_height)

        # freeze master window until user closes the pop up
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)

    def close_window(self):
        self.canceled = True
        self.master.destroy()


class WindowPopUpMessage:
    def __init__(self, master, title: str, message: str, screen_width_, screen_height_):
        self.master = master
        self.master.title(title)
        self.master.configure(background=bg_color)
        self.screen_width_ = screen_width_
        self.screen_height_ = screen_height_
        self.width = self.screen_width_ / 5
        self.height = self.screen_height_ / 4

        # --- NIVEL 0 ---

        # Label para desplegar el mensaje
        self.message = tk.Label(self.master,
                                text=message,
                                bg=bg_color,
                                padx=100,
                                pady=50,
                                font=("Calibri Light", 12))
        self.message.pack()

        # Boton para aceptar y cerrar
        self.btn_accept = tk.Button(self.master,
                                    text='Aceptar',
                                    command=self.close_window)
        self.btn_accept.pack(padx=10, pady=10)

        center_window(self.master, self.screen_width_, self.screen_height_)

    def close_window(self):
        self.master.destroy()


if __name__ == '__main__':
    path = os.path.join(os.path.expanduser("~"), r'AppData\Roaming\Modulo_Anomalas')

    root = tk.Tk()
    Main(root, path)
    root.mainloop()
