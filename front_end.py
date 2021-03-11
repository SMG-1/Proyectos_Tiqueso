import copy
import datetime
import os
import queue
import threading
import pandas as pd
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from back_end import Application
from back_end import ConfigShelf
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
        self.height = self.screen_height - 100

        self.top_frame_height = int(self.height / 2.5)
        self.bottom_frame_height = self.height - self.top_frame_height

        self.tree_width = int(self.width * 0.2)
        print(self.tree_width)
        self.table_width = int(self.width * 0.8)
        print(self.table_width)

        self.plot_width = int(self.width * 0.6)
        print(self.plot_width)
        self.config_width = int(self.width * 0.2)
        print(self.config_width)

        self.master.geometry('%dx%d+0+0' % (self.width, self.height))

        # application instance
        self.back_end = Application(root_path)

        #
        self.new_win = None
        self.figure_data = None
        self.figure_model = None
        self.ax_data = None
        self.ax_model = None
        self.ax_2 = None
        self.data_plot = None
        self.model_plot = None
        self.pd_table = None

        # --- DECLARACION DE DROPDOWN MENU - TOOLBAR ---
        main_menu = Menu(self.master)

        # sub menu declarations
        sub_menu_file = Menu(main_menu, tearoff=False)
        sub_menu_config = Menu(main_menu, tearoff=False)
        sub_menu_model = Menu(main_menu, tearoff=False)

        # commands for the file sub menu
        sub_menu_file.add_command(label="Cambiar directorios")
        sub_menu_file.add_command(label="Cargar información",
                                  command=self.open_window_select_work_path)
        sub_menu_file.add_command(label='Exportar',
                                  command=self.open_window_export)

        # commands for the model sub menu
        sub_menu_model.add_command(label='Optimizar modelo',
                                   command=self.run_optimizer)

        # sub menu cascade
        main_menu.add_cascade(label='Archivo', menu=sub_menu_file)
        main_menu.add_cascade(label='Configuración', menu=sub_menu_config)
        main_menu.add_cascade(label='Modelo', menu=sub_menu_model)

        # configure menu in toplevel
        self.master.config(menu=main_menu)

        # ---NIVEL 0 ---
        self.main_paned = PanedWindow(self.master,
                                      width=self.width,
                                      height=self.height,
                                      orient=HORIZONTAL)

        self.tree_view = ttk.Treeview(self.master)
        self.tree_view.bind("<Double-1>", self.refresh_views)

        self.main_frame = Frame(self.main_paned,
                                width=self.width,
                                height=self.height,
                                bg=bg_color)

        self.main_paned.add(self.tree_view)
        self.main_paned.add(self.main_frame)
        self.main_paned.pack(fill=BOTH, expand=1)

        # --- NIVEL 1 ---

        # --- FRAMES CONTENEDORES ---
        # Top frame to cover the top half of the screen, will have another frame inside it with the pandastable
        self.top_frame = Frame(self.main_frame,
                               width=self.table_width,
                               height=self.top_frame_height,
                               bg=bg_color)
        self.top_frame.pack(fill='x', expand=True, anchor='n')

        # Frame that contains plots to the left and config parameters to the right
        self.bottom_frame = Frame(self.main_frame,
                                  width=self.table_width,
                                  height=self.bottom_frame_height,
                                  bg=bg_color)
        self.bottom_frame.pack(fill='x', expand=True, anchor='s')

        self.frame_table = Frame(self.top_frame,
                                 width=self.table_width,
                                 height=self.top_frame_height,
                                 bg=bg_color)
        self.frame_table.pack(fill='x', expand=True, anchor='n')

        # Frame for notebook
        self.frame_notebook = Frame(self.bottom_frame,
                                    width=self.plot_width,
                                    height=self.bottom_frame_height,
                                    # highlightbackground='black',
                                    # highlightthickness=0.5,
                                    bg=bg_color)
        self.frame_notebook.pack(fill='both', expand=True, side=LEFT)

        # Notebook to alternate between plot and metrics using a tab system
        self.notebook_frame = ttk.Notebook(self.frame_notebook)
        self.tab_data_plot = ttk.Frame(self.notebook_frame)
        self.tab_model_plot = ttk.Frame(self.notebook_frame)
        self.tab_metrics = ttk.Frame(self.notebook_frame)
        self.notebook_frame.add(self.tab_data_plot, text='Demanda Real')
        self.notebook_frame.add(self.tab_model_plot, text='Modelo', state='disabled')
        self.notebook_frame.add(self.tab_metrics, text='Métricas', state='disabled')
        self.notebook_frame.pack()

        # Frame for the metrics tab
        self.metrics_frame = Frame(self.tab_metrics)
        self.metrics_frame.pack(fill=BOTH, expand=True)

        self.metrics_frame.columnconfigure((0, 1, 2), uniform='equal', weight=1)

        # Frame for config
        self.frame_config = LabelFrame(self.bottom_frame,
                                       text='Configuración',
                                       width=self.config_width,
                                       height=self.bottom_frame_height,
                                       # highlightbackground='black',
                                       # highlightthickness=0.5,
                                       bg=bg_color)
        self.frame_config.pack(fill='both', expand=True, side=RIGHT)

        # --- NIVEL 2 ---

        # label for the combobox
        Label(self.frame_config, text='Nivel de detalle del tiempo:', bg=bg_color).pack(padx=10, anchor='w')
        # Combobox: change time frequency
        freqs_ = ['Diario', 'Semanal', 'Mensual']
        self.combobox_time_freq = ttk.Combobox(self.frame_config, value=freqs_)
        self.combobox_time_freq.current(0)
        self.combobox_time_freq.pack(padx=10, pady=(0, 10), anchor='w')

        # label for the entry
        Label(self.frame_config, text='Cantidad de períodos a pronosticar:', bg=bg_color).pack(padx=10, anchor='w')
        # Entry: change amount of periods forward to forecast
        saved_periods_fwd = self.back_end.config_shelf.send_parameter('periods_fwd')
        self.entry_periods_fwd = Entry(self.frame_config, width=15)
        self.entry_periods_fwd.insert(END, saved_periods_fwd)
        self.entry_periods_fwd.pack(padx=10, pady=(0, 10), anchor='w')

        # Button: refresh the views
        self.btn_refresh_view = Button(self.frame_config,
                                       text='Refrescar vistas',
                                       padx=10,
                                       command=lambda: self.refresh_views(0))
        self.btn_refresh_view.pack(side=BOTTOM, pady=10)

        # Automatic load on boot
        self.update_gui()

        center_window(self.master, self.screen_width, self.screen_height)

    def create_fig(self, df, plot_type):
        # if line plot isn't empty, destroy the widget before adding a new one

        # add matplotlib Figure
        dpi = 100

        if plot_type == 'Demand':
            if self.data_plot is not None:
                self.data_plot.get_tk_widget().destroy()

            # raw data
            self.figure_data = Figure(figsize=(self.plot_width / dpi, self.bottom_frame_height / dpi), dpi=dpi)
            self.ax_data = self.figure_data.add_subplot(1, 1, 1)
            self.data_plot = FigureCanvasTkAgg(self.figure_data, self.tab_data_plot)
            self.data_plot.get_tk_widget().pack(side=LEFT, fill=BOTH, expand=1)

        else:
            if self.model_plot is not None:
                self.model_plot.get_tk_widget().destroy()

            # model
            self.figure_model = Figure(figsize=(self.plot_width / dpi, self.bottom_frame_height / dpi), dpi=dpi)
            self.ax_model = self.figure_model.add_subplot(1, 1, 1)
            self.model_plot = FigureCanvasTkAgg(self.figure_model, self.tab_model_plot)
            self.model_plot.get_tk_widget().pack(side=LEFT, fill=BOTH, expand=1)

        df = df.reset_index()

        if plot_type == 'Demand':
            df.plot(x='Fecha', y='Demanda', legend=False, ax=self.ax_data)

        if plot_type == 'Forecast':
            col_names = ['Fecha', 'Demanda', 'Modelo', 'Pronóstico']
            df.columns = col_names
            df.plot(x=col_names[0], y=col_names[1], color='b', ax=self.ax_model)
            df.plot(x=col_names[0], y=col_names[2], color='r', ax=self.ax_model)
            df.plot(x=col_names[0], y=col_names[3], color='g', ax=self.ax_model)

    def show_table(self, df, table_type):

        if table_type == 'Demand':
            df.drop(columns=['Codigo', 'Nombre'], inplace=True)

        if self.combobox_time_freq.get() == 'Semanal':
            df = df.groupby(pd.Grouper(freq='1W')).sum()
            df = df.reset_index()
            df['Fecha'] = df['Fecha'].dt.strftime('Semana %U')
            df = df.set_index('Fecha')

        elif self.combobox_time_freq.get() == 'Mensual':
            df = df.groupby(pd.Grouper(freq='M')).sum()
            df = df.reset_index()
            df['Fecha'] = df['Fecha'].dt.strftime('%b-%Y')
            df = df.set_index('Fecha')

        elif self.combobox_time_freq.get() == 'Diario':
            df = df.reset_index()
            # df = df[['Fecha', 'Demanda']]
            df['Fecha'] = df['Fecha'].dt.strftime('%d/%m/%Y')
            df = df.set_index('Fecha')

        if table_type == 'Forecast':
            df = df.fillna('-')
            df = df.round(2)

        df = df.T

        if self.pd_table is not None:
            print('Redrawing.')
            # self.frame_table.pack_forget()
            # self.frame_table.pack(fill='x', expand=True, anchor='n')

        self.pd_table = pandastable.Table(self.frame_table,
                                          dataframe=df,
                                          showtoolbar=False,
                                          showstatusbar=True)

        self.pd_table.showindex = True
        self.pd_table.autoResizeColumns()
        self.pd_table.show()
        self.pd_table.redraw()

    def update_gui(self):
        """set a new combobox on the choose_sku combobox that assigns the sku name to its options, and assign the
         combobox to the same location in the grid"""

        try:
            self.back_end.create_segmented_data()

            # declare columns
            self.tree_view['columns'] = '1'
            self.tree_view.column('1', anchor='w')

            # declare headings
            self.tree_view['show'] = 'headings'
            self.tree_view.heading('1', text='Producto', anchor='w')

            # insert row for every key in the segmented_data_sets dictionary from the backend
            for i in list(self.back_end.segmented_data_sets.keys()):
                self.tree_view.insert("", "end", text=i, values=(i,))

            # bind the refresh_views function to a double click on the tree view
            self.tree_view.bind("<Double-1>", self.refresh_views)

            # call function to update the plot and the table on the GUI
            self.show_plot_and_table('DEFAULT', 'Demand', 0)

        except ValueError:
            # temporary label in table frame
            Label(self.frame_table,
                  text='Cargar un archivo para ver información aquí.',
                  height=self.top_frame_height,
                  anchor='center').pack(fill=BOTH, expand=1)

            # temporary label in bottom frame
            Label(self.bottom_frame,
                  text='Cargar un archivo para ver información aquí.',
                  width=self.plot_width,
                  anchor='center').pack(side=LEFT, fill=BOTH)

    def show_plot_and_table(self, sku, plot_type, event):
        """Call the create figure function with the data of the passed sku parameter.

        sku: name of the SKU or DEFAULT, if DEFAULT, shows the currently selected SKU on the tree view
        plot_type: Demand plots the raw data, Forecast shows the fitted values and the forecast.
        """
        if plot_type == 'Demand':
            # get dictionary of datasets
            sep_df_dict = self.back_end.segmented_data_sets

        else:
            sep_df_dict = self.back_end.dict_fitted_dfs

        if sku == 'DEFAULT':
            temp_sku = list(sep_df_dict.keys())[0]
            df = sep_df_dict[temp_sku]

        else:
            df = sep_df_dict[sku]

        # call function to show table on top frame
        if self.back_end.dict_fitted_dfs != {} and plot_type != 'Demand':
            self.show_table(df, 'Forecast')
        elif plot_type == 'Demand' and df.columns[0] == 'Codigo':
            self.show_table(df, 'Demand')

        self.create_fig(df, plot_type)

    def run_optimizer(self):

        self.spawn_thread('Optimizador')

    def open_window_select_work_path(self):
        """Open TopLevel to select path where the input files are located."""

        # new toplevel with master root, grab_set and wait_window to wait for the main screen to freeze until
        # this window is closed
        self.new_win = Toplevel(self.master)
        WindowSelectWorkPath(self.new_win, self.back_end, self.screen_width, self.screen_height)
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)

        # update combobox with new data
        # self.update_tree_and_plot()

    def open_window_export(self):
        self.new_win = Toplevel(self.master)
        WindowExportFile(self.new_win, self.back_end, self.screen_width * (1 / 3), self.screen_height * (1 / 3))
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)

    def spawn_thread(self, process):
        """Create ThreadedClient class and pass it to a periodic call function."""

        if process == 'Optimizador':
            # self.btn_run_optimizer.config(state='disabled')
            queue_ = queue.Queue()

            thread = ThreadedClient(queue_, self.back_end, process)
            thread.start()

            self.new_win = Toplevel(self.master)
            WindowTraining(self.new_win, self.back_end, queue_, thread, 540,
                           300)
            self.new_win.grab_set()
            self.master.wait_window(self.new_win)

            self.notebook_frame.tab(self.tab_model_plot, state='normal')

            self.show_plot_and_table('DEFAULT', 'Forecast', 0)

            # enable the metrics tab
            self.update_metrics('DEFAULT')

            # self.periodic_call(process, thread, queue_)

    def periodic_call(self, process, thread, queue_):

        self.check_queue(queue_)

        if thread.is_alive():
            self.master.after(100, lambda: self.periodic_call(process, thread, queue_))

        else:
            if process == 'Optimizador':
                # self.btn_run_optimizer.config(state='active')
                pass

    def check_queue(self, queue_):

        while queue_.qsize():

            try:

                msg = queue_.get(False)

                if msg[0] != '':
                    print(msg[0])

                if msg[0] == 'Listo':
                    print(msg[0])

            except queue_.empty():
                pass

    def refresh_views(self, event):

        new_periods_fwd = int(self.entry_periods_fwd.get())
        if new_periods_fwd != self.back_end.config_shelf.send_parameter('periods_fwd'):
            print('Old: ', type(self.back_end.config_shelf.send_parameter('periods_fwd')))
            print('New: ', type(new_periods_fwd))
            print('Periods forward changed.')
            self.back_end.config_shelf.write_to_shelf('periods_fwd', new_periods_fwd)

            self.back_end.refresh_predictions()

        # get selected item from the tree view, if not available, use DEFAULT, which uses the first key
        try:
            item = self.tree_view.selection()[0]
            item_name = self.tree_view.item(item, "text")
        except IndexError:
            item_name = 'DEFAULT'

        self.show_plot_and_table(item_name, 'Demand', event)

        if self.back_end.dict_fitted_dfs != {}:
            self.show_plot_and_table(item_name, 'Forecast', event)
            self.update_metrics(item_name)


    def update_metrics(self, sku):

        self.notebook_frame.tab(self.tab_metrics, state='normal')

        sep_df_dict = self.back_end.dict_fitted_dfs

        if sku == 'DEFAULT':
            sku = list(sep_df_dict.keys())[0]

        metrics_dict = self.back_end.dict_metrics[sku]

        for idx, (metric, value) in enumerate(metrics_dict.items()):
            Label(self.metrics_frame, text=metric, padx=10).grid(row=idx, column=0, padx=10, pady=5)

            rounded_val = round(float(value), 2)
            Label(self.metrics_frame, text=rounded_val, padx=10).grid(row=idx, column=1, padx=10, pady=5)

            metric_desc = self.back_end.dict_metric_desc[metric]
            Label(self.metrics_frame, text=metric_desc, padx=10, wraplength=250).grid(row=idx,
                                                                                      column=2,
                                                                                      padx=10,
                                                                                      pady=5)


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
        self.app.create_segmented_data()
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
                                 text='Cancelar',
                                 command=self.close_window)
        self.btn_cancel.grid(row=1, column=1)

        # --- LEVEL 1: CONFIG WIDGETS ---
        # get possible values for all parameters from dictionary of models and parameters
        shelf_dict = ConfigShelf(self.app.path_config_shelf).send_dict()

        # get possible values key of active model
        model_params = shelf_dict[self.model]['params']

        # table headers
        Label(self.main_frame, text='Parámetro').grid(row=0, column=0, padx=10, pady=10)
        Label(self.main_frame, text='Valor').grid(row=0, column=1, padx=10, pady=10)

        # loop over all the items in the possible values dictionary
        for idx, item in enumerate(model_params.items()):

            # the enumerate function returns and index as idx and a tuple as item
            # the first item of the tuple is the parameter name
            # the second item of the tuple is the parameter value

            param_name = item[0]
            curr_value = item[1][0]
            possible_values = item[1][1]

            # set parameter name to label
            lbl = Label(self.main_frame,
                        text=param_name)
            # index + 1 because of the headers
            lbl.grid(row=idx + 1, column=0, padx=10, pady=10)

            # according to the type, choose type of widget
            # if the itemtype is a list, the widget must be a combobox with said list as possible values
            if type(possible_values) == tuple:
                # shelf_dict = ConfigShelf(self.app.path_config_shelf).send_dict()

                try:
                    # try to convert to int
                    curr_value = int(curr_value)
                except ValueError:
                    pass

                # declare combobox with the values as the possible parameter values
                widget = ttk.Combobox(self.main_frame, value=possible_values)
                widget.current(possible_values.index(curr_value))
                widget.grid(row=idx + 1, column=1, padx=10)

                # set widget type to key of dict selected, to save parameters to the right key
                self.dict_selected[param_name] = widget

            # if the item type is type, the widget must be an entry to allow for user input
            if type(possible_values) == type:
                # get the current parameter value from the params key of the dictionary
                widget = Entry(self.main_frame, width=30)
                widget.insert(END, curr_value)
                widget.grid(row=idx + 1, column=1, padx=10)

                # set widget type to key of dict selected, to save parameters to the right key
                self.dict_selected[param_name] = widget

    def save_to_shelf(self):
        """Save chosen parameters to the config shelf."""

        # loop over the saved parameters
        for key, widget in self.dict_selected.items():
            # get current value from the widget
            val = widget.get()

            # declare ConfigShelf instance to be able to write to the shelf
            shelf_dict = ConfigShelf(self.app.path_config_shelf)

            # write to shelf using the key as a parameter, and the value currently selected with the widget as value
            shelf_dict.write_to_shelf(parameter=key, value=val, model=self.model)

        # close window after saving
        self.close_window()

    def close_window(self):
        self.master.destroy()


class WindowTraining:
    def __init__(self, master, app: Application, queue_, thread_, width, height):
        self.master = master
        self.app = app
        self.width = width
        self.height = height
        self.queue_ = queue_
        self.thread_ = thread_

        # --- WIDGETS ---

        # listbox to print status
        self.listbox = Listbox(self.master,
                               width=100)
        self.listbox.pack()

        # progress bar to show progress
        self.progress_bar = ttk.Progressbar(self.master,
                                            orient='horizontal',
                                            length=300,
                                            mode='determinate')
        self.progress_bar['maximum'] = 1.0
        self.progress_bar.pack()

        center_window(self.master, self.width, self.height)

        self.periodic_call()

    def periodic_call(self):

        self.check_queue()

        if self.thread_.is_alive():
            self.master.after(100, self.periodic_call)

        else:
            # close window
            self.close_window()

    def check_queue(self):
        while self.queue_.qsize():
            try:
                msg = self.queue_.get(False)
                self.listbox.insert('end', msg[0])
                if msg[1] > 0:
                    self.progress_bar['value'] = msg[1]

                print(f'Progress: {msg[1]}')

            except self.queue_.empty:
                pass

    def close_window(self):
        self.master.destroy()


class WindowExportFile:
    def __init__(self, master, app: Application, width, height):
        self.master = master
        self.app = app
        self.width = width
        self.height = height
        self.thread_ = None

        # configure columns
        self.master.grid_columnconfigure((0, 1), uniform='equal', weight=1)

        # Master frame
        self.frame_master = Frame(self.master, bg=bg_color, borderwidth=2, width=75, padx=10, pady=10)
        self.frame_master.pack(fill=BOTH, expand=True)

        # Button to change the path
        self.btn_path = Button(self.frame_master,
                               text=self.app.file_paths_shelf.send_path('Demand'),
                               bg=bg_color,
                               width=100,
                               command=self.browse_files)
        self.btn_path.grid(row=0, column=0, pady=5, sticky='WE')

        self.entry_output_file = Entry(self.frame_master)
        file_name = self.app.config_shelf.send_parameter('File_name')
        today_date = datetime.datetime.today().strftime('%d-%m-%Y')
        self.entry_output_file.insert(END, file_name + f' {today_date}')
        self.entry_output_file.grid(row=1, column=0, pady=5, sticky='WE')

        # Combobox to choose extension
        #  exts = [('Libro de Excel (*.xlsx)', '.xlsx'), ('CSV UTF-8 (*.csv)', '.csv')]
        self.exts = {'Libro de Excel (*.xlsx)': '.xlsx',
                     'CSV UTF-8 (*.csv)': '.csv'}
        self.combobox_extensions = ttk.Combobox(self.frame_master, value=list(self.exts.keys()))
        self.combobox_extensions.current(0)
        self.combobox_extensions.grid(row=2, column=0, pady=5, sticky='WE')

        # Button to accept
        self_btn_accept = Button(self.frame_master, text='Guardar', padx=10, command=self.call_backend_export)
        self_btn_accept.grid(row=2, column=1, padx=10)

    def call_backend_export(self):
        ext_ = self.exts[self.combobox_extensions.get()]
        self.app.export_data(self.btn_path['text'], self.entry_output_file.get(), ext_)

    def spawn_thread(self):
        pass

    def periodic_call(self):

        self.check_queue()

        if self.thread_.is_alive():
            self.master.after(100, self.periodic_call)

        else:
            # close window
            self.close_window()

    def check_queue(self):
        while self.queue_.qsize():
            try:
                msg = self.queue_.get(False)
                if msg[1] > 0:
                    pass

            except self.queue_.empty:
                pass

    def close_window(self):
        self.master.destroy()

    def browse_files(self):
        filename = filedialog.askdirectory(initialdir=self.app.file_paths_shelf.send_path('Working'),
                                           title="Seleccione un folder de destino.")

        # Change label contents
        self.btn_path.configure(text=filename)


class ThreadedClient(threading.Thread):
    def __init__(self, queue, application: Application, process):
        threading.Thread.__init__(self)
        self.queue = queue
        self.application = application
        self.process = process
        self.daemon = True

    def run(self):
        if self.process == 'Optimizador':
            self.application.get_best_models(self.queue)
            self.application.evaluate_fit()  # todo: temporary


if __name__ == '__main__':
    bg_color = 'white'
    path = os.path.join(os.path.expanduser("~"), r'AppData\Roaming\Modulo_Demanda')

    root = Tk()
    root.state('zoomed')
    Main(root, path)
    root.mainloop()
