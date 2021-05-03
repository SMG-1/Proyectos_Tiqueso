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


def browse_directory_master(initial_dir):
    if initial_dir != '':
        initial_dir_ = initial_dir

    else:
        initial_dir_ = "/"

    filepath = filedialog.askdirectory(initialdir=initial_dir_,
                                       title="Seleccione un directorio")

    return filepath


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
                                    text='Exportar resultado',
                                    state='disabled',
                                    command=self.run_export)
        self.btn_export.pack(padx=5,
                             pady=10)

        center_window(self.master, self.screen_width, self.screen_height)

    def open_window_select_path(self):
        self.new_win = tk.Toplevel()
        WindowSelectWorkPath(self.new_win,
                             self.app,
                             self.screen_width,
                             self.screen_height,
                             'Orders')
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)

    def open_window_config(self):
        self.new_win = tk.Toplevel()
        WindowModelConfig(self.new_win, self.app, self.screen_width, self.screen_height)
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)

    def run_anomaly_check(self):

        try:
            self.app.anomaly_check()
            anomaly_count = self.app.anomaly_count
            self.list_box.insert(tk.END, f'{anomaly_count} anomalias encontradas.')
            self.btn_export['state'] = 'active'
        except FileNotFoundError:
            self.open_window_pop_up('Error',
                                    'El archivo indicado no existe.')

    def run_export(self):
        self.new_win = tk.Toplevel()
        WindowSelectWorkPath(self.new_win,
                             self.app,
                             self.screen_width,
                             self.screen_height,
                             'Export')
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)

    def open_window_pop_up(self, title, msg):

        # open new TopLevel as a popup window
        self.new_win = tk.Toplevel(self.master)
        WindowPopUpMessage(self.new_win, title, msg, self.screen_width, self.screen_height)

        # freeze master window until user closes the pop up
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)


class WindowSelectWorkPath:

    def __init__(self, master, app: AnomalyApp, screen_width_, screen_height_, file):

        self.master = master
        self.master.title("Selección de directorio")
        self.master.configure(background=bg_color)
        self.screen_width = screen_width_
        self.screen_height = screen_height_
        self.width = self.screen_width / 2
        self.height = self.screen_height / 5

        self.app = app

        self.file = file

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
                                      text='Directorio:',
                                      bg=bg_color,
                                      padx=5)

        # Name Label, first column
        self.lbl_name_path.grid(row=0,
                                column=0,
                                sticky='W')

        # Path Label, second column
        path = self.app.get_path(self.file)
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
                                    command=self.browse_files)

        # Browse Button, third column, to open the browse files window
        self.btn_browse.grid(row=0,
                             column=2,
                             padx=10,
                             pady=10,
                             sticky='WE')

        if file == 'Export':
            self.lbl_file_name = tk.Label(self.paths_frame,
                                          text='Nombre del archivo:',
                                          bg=bg_color,
                                          padx=5)
            self.lbl_file_name.grid(row=1,
                                    column=0,
                                    pady=10)
            self.entry_file_name = tk.Entry(self.paths_frame)
            self.entry_file_name.insert(tk.END,
                                        'Analisis Ordenes')
            self.entry_file_name.grid(row=1,
                                      column=1,
                                      padx=10,
                                      pady=10,
                                      sticky='W')

        center_window(self.master, self.screen_width, self.screen_height)

    def browse_files(self):

        # get the last path that the user selected
        ini_dir_ = self.app.get_path('Temp')

        # call function to open a file selection window
        if self.file == 'Orders':
            filepath, filename = browse_files_master(ini_dir_)

            # change the text content of the label
            if filename != '':
                # set the selected path as the new Temp path
                self.app.set_path('Temp', os.path.dirname(os.path.abspath(filename)))

                self.lbl_path.configure(text=filename)

        else:
            ini_dir_ = os.path.abspath(ini_dir_)
            filepath = browse_directory_master(ini_dir_)

            if filepath != '':

                self.app.set_path('Temp', filepath)

                self.lbl_path.configure(text=filepath)

    def save_selection(self):
        """"""

        path_ = self.lbl_path['text']

        # open PopUp warning if the Path Label is empty
        if path_ == '':
            self.open_window_pop_up('Error', 'Debe seleccionar un directorio válido.')

        if self.file == 'Orders':
            is_file = True
        else:
            is_file = False

        if validate_path(path_, is_file=is_file):
            self.app.set_path(self.file, path_)

            if self.file == 'Export':
               file_name = self.entry_file_name.get()
               if file_name != '':
                    self.app.set_path('Export_FileName', file_name)

            try:
                if self.file == 'Export':
                    self.app.export_anomaly_check()
                    win_name = 'Archivo exportado'
                    win_msg = 'El archivo fue exportado exitosamente.'
                else:
                    win_name = 'Archivo cargado.'
                    win_msg = 'El archivo fue cargado exitosamente.'

                self.open_window_pop_up(win_name, win_msg)
                self.successful_load = True
                self.close_window()

            except ValueError as e:
                self.open_window_pop_up('Error\n', e)

            except PermissionError as e:
                self.open_window_pop_up('Error', 'Debe cerrar el siguiente archivo antes de proceder:\n\n' + e.filename)

        else:
            self.open_window_pop_up('Error',
                                    f'El directorio indicado es inválido.')

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
                                     text=f'Modelo actualizado por última vez el {last_update_date}.',
                                     bg=bg_color)
        self.status_label.grid(row=0,
                               column=0,
                               columnspan=2,
                               pady=5)

        # Button - Show the path to the file that will be used to update the model.
        self.btn_update_model = tk.Button(self.master,
                                          text='Actualizar modelo',
                                          command=lambda: self.add_path_selection_to_grid(row=2))
        self.btn_update_model.grid(row=1,
                                   column=0,
                                   columnspan=2,
                                   pady=5)

        # Frame - Contains the path selection widgets
        self.frame_path = tk.Frame(self.master,
                                   bg=bg_color)
        # self.frame_path.grid(row=2,
        #                     column=0,
        #                     columnspan=2,
        #                     pady=5)

        # Label - Naming label for the path widgets
        self.file_path_label = tk.Label(self.frame_path,
                                        text='Directorio:',
                                        bg=bg_color)
        self.file_path_label.grid(row=0,
                                  column=0,
                                  padx=5)

        # Label - Shows the path the user selected.
        path_model = self.app.get_path('Anomaly_Model')
        self.lbl_path = tk.Label(self.frame_path,
                                 text=path_model,
                                 bg=bg_color,
                                 pady=10,
                                 borderwidth=2,
                                 width=150,
                                 relief="groove",
                                 anchor='w')
        self.lbl_path.grid(row=0,
                           column=1,
                           pady=5)

        # Button,opens the browse files window
        self.btn_browse = tk.Button(self.frame_path,
                                    text='...',
                                    command=self.browse_files)
        self.btn_browse.grid(row=0,
                             column=2,
                             padx=5)

        # accept and cancel buttons
        self.btn_accept = tk.Button(self.master,
                                    text='Aceptar',
                                    command=self.save_selection)
        self.btn_accept.grid(row=3,
                             column=0,
                             pady=5)

        self.btn_cancel = tk.Button(self.master,
                                    text='Cancelar',
                                    command=self.close_window)
        self.btn_cancel.grid(row=3,
                             column=1,
                             pady=5)

        center_window(self.master, self.screen_width, self.screen_height)

    def add_path_selection_to_grid(self, row):

        self.btn_update_model.grid_forget()

        # self.frame_path.grid(row=row,
        #                     column=0)

        self.frame_path.grid(row=row,
                             column=0,
                             columnspan=2,
                             pady=5)

        center_window(self.master, self.screen_width, self.screen_height)

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
            self.open_window_pop_up('Mensaje', 'Modelo actualizado.')
            today_date = datetime.datetime.today().strftime('%d/%m/%Y')
            self.status_label['text'] = f'Modelo actualizado por última vez el {today_date}.'
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
