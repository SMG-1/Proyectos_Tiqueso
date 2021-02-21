import os
import threading
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from back_end import Application
from back_end import AutoRegression
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)
from matplotlib import pyplot as plt
import time
from win32api import GetSystemMetrics
import pandastable

plt.style.use('ggplot')


def center_window(toplevel, screen_width, screen_height):
    """Funcion para centrar las ventanas."""
    toplevel.update_idletasks()

    size = tuple(int(_) for _ in toplevel.geometry().split('+')[0].split('x'))
    x = screen_width / 2 - size[0] / 2
    y = screen_height / 2 - size[1] / 2

    toplevel.geometry("+%d+%d" % (x, y))


class Main:
    def __init__(self, master, root_path):
        # tkinter root
        self.master = master

        # window parameters
        self.master.title("Módulo de Demanda - COPROLAC")
        self.master.configure(background=bg_color)

        # screen width and height, and toplevel width and height
        self.screen_width = GetSystemMetrics(0)
        self.screen_height = GetSystemMetrics(1)
        self.width = self.screen_width
        self.height = self.screen_height

        # application instance
        self.back_end = Application(root_path)

        #
        self.new_win = None
        self.figure = ""
        self.ax = ""
        self.line_plot = ""

        # --- DECLARACION DE DROPDOWN MENU - TOOLBAR ---
        main_menu = Menu(self.master)

        # sub menu
        sub_menu_file = Menu(main_menu, tearoff=False)
        sub_menu_model = Menu(main_menu, tearoff=False)
        sub_menu_file.add_command(label="Cambiar directorios")
        sub_menu_file.add_command(label="Cargar información",
                                  command=self.open_window_select_work_path)
        sub_menu_model.add_command(label='Configurar modelo',
                                   command=self.open_window_config_model)

        # sub menu cascade
        main_menu.add_cascade(label='Archivo', menu=sub_menu_file)
        main_menu.add_cascade(label='Configuración', menu=sub_menu_model)

        # configure menu in toplevel
        self.master.config(menu=main_menu)

        # ---NIVEL 0 ---
        self.main_frame = Frame(self.master,
                                # width=self.screen_width,
                                # height=self.screen_height
                                )
        self.main_frame.pack()

        # --- NIVEL 1 ---

        # --- DECLARACION DE FRAMES CONTENEDORES ---
        # Frame contenedor para visualizacion de graficos y tablas
        self.frame_display = Frame(self.main_frame,
                                   bg=bg_color)
        self.frame_display.pack(fill=BOTH, side=LEFT)

        # --- Frame contenedor para parametros y ajustes
        self.frame_config = LabelFrame(self.main_frame,
                                       text='Configuración',
                                       bg=bg_color)
        self.frame_config.pack(fill=BOTH, side=RIGHT)

        # --- NIVEL 2 ---

        # Frame para desplegar graficos
        self.frame_plot = LabelFrame(self.frame_display,
                                     text='Gráfico',
                                     width=self.width * (2 / 5),
                                     height=self.height / 2,
                                     bg=bg_color)
        self.frame_plot.pack(side=TOP, fill=BOTH)

        # Frame para desplegar status e informacion
        self.frame_status = LabelFrame(self.frame_display,
                                       text='Estado',
                                       width=self.width * (2 / 5),
                                       height=self.height / 3,
                                       bg=bg_color)
        self.frame_status.pack(side=BOTTOM, fill=BOTH)

        # --- NIVEL 3 ---

        # LabelFrame para contener modelos y ajustes de parametros
        self.frame_modeler = LabelFrame(self.frame_config,
                                        text='Modelo',
                                        width=self.screen_width / 6,
                                        height=self.screen_height / 3,
                                        bg=bg_color)
        self.frame_modeler.grid(row=2, column=0, columnspan=1, padx=10, pady=10)

        # Label: Model
        self.lbl_choose_model_title = Label(self.frame_modeler,
                                            text='Modelo',
                                            padx=10,
                                            pady=10,
                                            bg=bg_color)
        self.lbl_choose_model_title.grid(row=0, column=0)

        # Combobox: available models
        self.combobox_choose_model = ttk.Combobox(self.frame_modeler,
                                                  value=self.back_end.models)
        # self.combobox_choose_model.bind("<<ComboboxSelected>>", self.combo_box_callback)
        self.combobox_choose_model.current(0)
        self.combobox_choose_model.grid(row=0, column=1, padx=10)

        # Label: SKU
        self.lbl_choose_sku_title = Label(self.frame_modeler,
                                          text='Producto',
                                          padx=10,
                                          pady=10,
                                          bg=bg_color)
        self.lbl_choose_sku_title.grid(row=1, column=0)

        # Combobox: available models
        self.combobox_choose_sku = ttk.Combobox(self.frame_modeler,
                                                value="")

        self.combobox_choose_sku.grid(row=1, column=1, padx=10)

        # Button to run forecast
        self.btn_run_fcst = Button(self.frame_modeler,
                                   text='Ejecutar modelo',
                                   padx=10,
                                   command=self.run_forecast)
        self.btn_run_fcst.grid(row=2, column=0, columnspan=2, pady=10)

        center_window(self.master, self.screen_width, self.screen_height)

    def show_raw_data_plot(self, event):
        # get dictionary of datasets
        sep_df_list = self.back_end.separate_data_sets

        # if line plot isn't empty, destroy the widget before adding a new one
        if self.line_plot != "":
            self.line_plot.get_tk_widget().destroy()

        # add a matplotlib figure
        self.figure = Figure(figsize=((self.width * (4 / 5)) / 96, (self.height / 2) / 96), dpi=96)
        self.ax = self.figure.add_subplot(111)
        self.line_plot = FigureCanvasTkAgg(self.figure, self.frame_plot)
        self.line_plot.get_tk_widget().pack(side=LEFT, fill=BOTH)

        # filter the dictionary using the current selected combobox value
        df = sep_df_list[self.combobox_choose_sku.get()]

        # get date column, and groupby date, finally plot demand vs date using the declared figure axis
        df = df.reset_index()
        df = df.groupby('Fecha').sum().reset_index()
        df.plot(x='Fecha', y='Demanda', legend=False, ax=self.ax)

    def update_sku_combobox(self):
        """set a new combobox on the choose_sku combobox that assings the sku name to its options, and assign the
         combobox to the same location in the grid"""

        self.combobox_choose_sku = ttk.Combobox(self.frame_modeler,
                                                value=list(self.back_end.separate_data_sets.keys()))
        self.combobox_choose_sku.current(0)
        self.combobox_choose_sku.bind("<<ComboboxSelected>>",
                                      self.show_raw_data_plot)
        self.combobox_choose_sku.grid(row=1, column=1, padx=10)

    def run_forecast(self):
        # get dictionary of datasets
        sep_df_list = self.back_end.separate_data_sets

        # filter the dictionary using the current selected combobox value
        df = sep_df_list[self.combobox_choose_sku.get()]

        # get selected model
        selected_model = self.combobox_choose_model.get()

        if selected_model == 'Auto-regresión':
            model_ = 'AutoReg'

            params = [self.back_end.config_shelf.send_parameter(param, model=model_) for param in
                      ['lags', 'trend', 'n_forward']]

            # self.back_end.config_shelf.send_parameter('lags')

            df = df.iloc[:, -1]

            model = AutoRegression(df.values, lags=params[0], trend=params[1], periods_fwd=params[2])
            df_tot = model.fit_predict()
            test = model.predict_fwd()

            # TODO: SHOW PLOTS

            print(df_tot.head())
            print(test.sample())

    def open_window_select_work_path(self):
        """Open TopLevel to select path where the input files are located."""

        # new toplevel with master root, grab_set and wait_window to wait for the main screen to freeze until
        # this new window is closed
        self.new_win = Toplevel(self.master)
        WindowSelectWorkPath(self.new_win, self.back_end, self.screen_width, self.screen_height)
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)

        # update combobox with new data
        self.update_sku_combobox()

    def open_window_config_model(self):
        # get selected model
        chosen_model = self.combobox_choose_model.get()

        # new toplevel with master root, grab_set and wait_window to wait for the main screen to freeze until
        # this new window is closed
        self.new_win = Toplevel(self.master)
        ConfigModel(self.new_win, self.back_end, self.screen_width, self.screen_height, chosen_model)
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)


class WindowSelectWorkPath:
    def __init__(self, master, app: Application, screen_width_, screen_height_):
        self.master = master
        self.master.title("Módulo de Demanda - COPROLAC")
        self.master.configure(background=bg_color)
        self.screen_width = screen_width_
        self.screen_height = screen_height_
        self.width = self.screen_width / 2
        self.height = self.screen_height / 5
        self.app = app
        self.new_win = None

        # --- NIVEL 0 ---

        # FRAME CONTENEDOR
        self.main_frame = LabelFrame(self.master,
                                     text='Escoja un directorio:',
                                     bg=bg_color,
                                     width=screen_width_ / 5,
                                     padx=10,
                                     pady=10)
        self.main_frame.pack(padx=10,
                             pady=10)

        # --- NIVEL 1 ---

        # Label title
        self.lbl_name_path = Label(self.main_frame,
                                   text='Directorio:',
                                   bg=bg_color,
                                   padx=5)
        self.lbl_name_path.grid(row=0, column=0)

        # Label that shows the selected path
        self.lbl_path = Label(self.main_frame,
                              text=self.app.get_path('Demand'),
                              bg=bg_color,
                              pady=10,
                              borderwidth=2,
                              width=55,
                              relief="groove",
                              anchor=W)
        self.lbl_path.grid(row=0, column=1, padx=10, pady=10)

        self.btn_browse = Button(self.main_frame,
                                 text='...',
                                 command=self.browse_files)
        self.btn_browse.grid(row=0, column=2)

        self.btn_accept = Button(self.master,
                                 text='Aceptar',
                                 command=self.save_path_to_shelf)
        self.btn_accept.pack(pady=10)

        center_window(self.master, self.screen_width, self.screen_height)

    def close_window(self):
        self.master.destroy()

    def browse_files(self):
        filename = filedialog.askopenfilename(initialdir="/",
                                              title="Seleccione un archivo",
                                              filetypes=(("Archivo de Excel",
                                                          "*.xlsx*"),
                                                         ("Archivo CSV",
                                                          "*.csv*")))

        # Change label contents
        self.lbl_path.configure(text=filename)

    def save_path_to_shelf(self):
        self.app.set_path('Demand', self.lbl_path['text'])
        self.app.create_new_data_sets()
        self.open_window_pop_up()

        self.close_window()

    def open_window_pop_up(self):
        self.new_win = Toplevel(self.master)
        WindowPopUpMessage(self.new_win, "Mensaje", "Archivo cargados.", self.screen_width, self.screen_height)
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)


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
        self.message = Label(self.master,
                             text=message,
                             bg=bg_color,
                             padx=100,
                             pady=50,
                             font=("Calibri Light", 12))
        self.message.pack()

        # Boton para aceptar y cerrar
        self.btn_accept = Button(self.master,
                                 text='Aceptar',
                                 command=self.close_window)
        self.btn_accept.pack(padx=10, pady=10)

        center_window(self.master, self.screen_width_, self.screen_height_)

    def close_window(self):
        self.master.destroy()


class ConfigModel:
    def __init__(self, master, app: Application, screen_width, screen_height, model: str):
        self.master = master
        self.app = app
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.model = model

        # dictionary to save models with respective widgets
        self.dict_selected = {}

        if self.model == 'Auto-regresión':
            self.model = 'AutoReg'

        # --- LEVEL 0: LABEL FRAME AND BUTTONS
        self.main_frame = LabelFrame(self.master,
                                     text='Configuración',
                                     padx=10,
                                     pady=10)
        self.main_frame.grid(row=0, column=0, columnspan=2)

        self.btn_accept = Button(self.master,
                                 text='Aceptar',
                                 command=self.save_to_shelf)
        self.btn_accept.grid(row=1, column=0)

        self.btn_cancel = Button(self.master,
                                 text='Cancelar')
        self.btn_cancel.grid(row=1, column=1)

        # --- LEVEL 1: CONFIG WIDGETS ---
        # get possible values for all parameters from dictionary of models and parameters
        model_params = self.app.config_shelf.model_dict[self.model]['possible_values']

        # loop over all the items in the possible values dictionary
        for idx, item in enumerate(model_params.items()):

            # set parameter name to label
            lbl = Label(self.main_frame,
                        text=item[0])
            lbl.grid(row=idx, column=0)

            print('type', type(item[1]))

            # according to the type, choose type of widget
            if type(item[1]) == list:
                widget = ttk.Combobox(self.main_frame, value=item[1])
                widget.current(0)
                widget.bind("<<ComboboxSelected>>", print('hola'))
                widget.grid(row=idx, column=1, padx=10)

                self.dict_selected[item[0]] = widget

            if type(item[1]) == type:
                entry_val = self.app.config_shelf.model_dict[self.model]['params'][item[0]]
                widget = Entry(self.main_frame, width=30)
                widget.insert(END, entry_val)
                widget.grid(row=idx, column=1, padx=10)

                self.dict_selected[item[0]] = widget

    def save_to_shelf(self):
        """Save chosen parameters to the config shelf."""

        for key, widget in self.dict_selected.items():
            val = widget.get()
            self.app.config_shelf.write_to_shelf(parameter=key, value=val, model=self.model)


class ThreadedClient(threading.Thread):
    def __init__(self, queue, application: Application, process):
        threading.Thread.__init__(self)
        self.queue = queue
        self.application = application
        self.process = process

    def run(self):
        """if self.process == 'Workflow_Load_Files':
            self.application.read_files_politicas(self.queue)"""


if __name__ == '__main__':
    bg_color = 'white'
    path = os.path.join(os.path.expanduser("~"), r'AppData\Roaming\Modulo_Demanda')

    root = Tk()
    Main(root, path)
    root.mainloop()
