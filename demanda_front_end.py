import collections
import datetime
import os
import queue
import threading
import tkinter
from tkinter import *
from tkinter import filedialog
from tkinter import ttk
from functools import partial

import pandas as pd
import pandastable
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.figure import Figure
from win32api import GetSystemMetrics

from demanda_back_end import Application
from demanda_back_end import ConfigShelf

plt.style.use('ggplot')
bg_color = 'white'
pd.set_option('display.float_format', lambda x: '%,g' % x)
brand_green = '#005c2c'  # ticheese green\


def get_longest_str_length_from_list(list_: list):
    max_length = 0
    for item in list_:
        if len(item) > max_length:
            max_length = len(item)

    return max_length


def _from_rgb(rgb):
    """translates an rgb tuple of int to a tkinter friendly color code
    """
    return "#%02x%02x%02x" % rgb


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


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class Main:

    @staticmethod
    def check_queue(queue_):

        while queue_.qsize():

            try:

                msg = queue_.get(False)

                if msg[0] != '':
                    print(msg[0])

                if msg[0] == 'Listo':
                    print(msg[0])

            except queue_.empty():
                pass

    def __init__(self, master, root_path):
        # tkinter root
        self.master = master

        # window parameters
        self.master.title("Módulo de Demanda - COPROLAC")
        self.master.configure(background=bg_color)

        # ttk parameters
        ttk_style = ttk.Style()
        ttk_style.configure('TFrame', background='white')
        ttk_style.configure('FrameGreen.TFrame', background='green')

        # screen width and height, and toplevel width and height
        self.screen_width = GetSystemMetrics(0)
        self.screen_height = GetSystemMetrics(1)
        self.width = self.screen_width
        self.height = self.screen_height

        # top and bottom frame heights
        self.top_frame_height = int(self.height / 4)
        self.bottom_frame_height = self.height - self.top_frame_height

        # treeview and table widths
        self.tree_width = int(self.width * 0.2)
        self.table_width = int(self.width * 0.8)

        # bottom frame widths
        self.plot_width = int(self.width * 0.6)
        self.config_width = int(self.width * 0.2)

        # master geometry, width and height definition
        self.master.geometry('%dx%d+0+0' % (self.width, self.height))

        # application instance
        self.back_end = Application(root_path)

        # the layout of the GUI depends on the mode attribute
        # mode = Demand or Forecast
        self.mode = self.back_end.get_parameter('Mode')

        # initializing parameters
        self.new_win = None

        # Data Figure
        self.figure_data = None
        self.ax_data = None
        self.data_plot = None
        self.data_toolbar = None

        # Model Figure
        self.figure_model = None
        self.ax_model = None
        self.model_plot = None
        self.model_toolbar = None
        self.ax_2 = None

        # Pandas table
        self.pd_table = None

        # Model ready boolean
        self.model_ready = False

        # Active process determines the layout of the GUI
        self.active_process = self.back_end.get_parameter('Mode')

        # --- DROPDOWN MENU DECLARATION - TOOLBAR ---
        self.main_menu = Menu(self.master)

        # sub menu declarations
        self.sub_menu_file = Menu(self.main_menu, tearoff=False)
        self.sub_menu_config = Menu(self.main_menu, tearoff=False)
        self.sub_menu_data = Menu(self.main_menu, tearoff=False)
        self.sub_menu_model = Menu(self.main_menu, tearoff=False)

        # commands for the file sub menu
        self.sub_menu_file.add_command(label="Nuevo",
                                       command=self.clear_gui)
        self.sub_menu_file.add_command(label="Abrir",
                                       command=self.open_window_select_work_path)
        self.sub_menu_file.add_command(label='Exportar',
                                       command=self.open_window_export)

        # commands for the config sub menu
        self.sub_menu_config.add_command(label='Segmentación',
                                         command=self.open_window_segment)
        if self.active_process == 'Forecast':
            self.sub_menu_config.entryconfig('Segmentación',
                                             state='normal')
        else:
            self.sub_menu_config.entryconfig('Segmentación',
                                             state='disabled')

        # commands for the model sub menu
        self.sub_menu_data.add_command(label='Convertir a familias',
                                       command=self.sub_menu_convert_callback)  # todo

        # commands for the model sub menu
        self.sub_menu_model.add_command(label='Optimizar modelo',
                                        command=self.run_optimizer)

        # sub menu cascade
        self.main_menu.add_cascade(label='Archivo',
                                   menu=self.sub_menu_file)
        self.main_menu.add_cascade(label='Configuración',
                                   menu=self.sub_menu_config)
        self.main_menu.add_cascade(label='Datos',
                                   menu=self.sub_menu_data)
        self.main_menu.add_cascade(label='Modelo',
                                   menu=self.sub_menu_model)

        # configure menu in toplevel
        self.master.config(menu=self.main_menu)

        # --- Level 0 --- Contains the Paned Window, the Tree View and the Main Frame

        # Frame for top control buttons
        self.frame_btn_control = LabelFrame(self.master, bg=_from_rgb((0, 128, 61)))
        self.frame_btn_control.pack(fill=X)

        # Button for a new template
        self.img_new = PhotoImage(file=resource_path(r'res\new.png'))
        self.btn_new = Button(self.frame_btn_control,
                              text='Nuevo',
                              image=self.img_new,
                              compound='left',
                              bg=bg_color,
                              width=75,
                              padx=10,
                              command=self.clear_gui)
        self.btn_new.pack(side=LEFT)

        # Button to open a file
        self.img_open = PhotoImage(file=resource_path(r'res\open.png'))
        self.btn_open = Button(self.frame_btn_control,
                               text='Abrir',
                               image=self.img_open,
                               compound='left',
                               bg=bg_color,
                               width=75,
                               padx=10,
                               command=self.open_window_select_work_path)
        self.btn_open.pack(side=LEFT)

        # Button to export files
        self.img_save = PhotoImage(file=resource_path(r'res\save.png'))
        self.btn_save = Button(self.frame_btn_control,
                               text='Exportar',
                               image=self.img_save,
                               compound='left',
                               bg=bg_color,
                               width=75,
                               padx=10,
                               command=self.open_window_export,
                               state='normal')
        self.btn_save.pack(side=LEFT)

        # Button to refresh the views
        self.img_refresh = PhotoImage(file=resource_path(r'res\refresh.png'))
        self.btn_refresh = Button(self.frame_btn_control,
                                  text='Refrescar',
                                  image=self.img_refresh,
                                  compound='left',
                                  bg=bg_color,
                                  width=75,
                                  padx=10,
                                  command=lambda: self.refresh_views(0))
        self.btn_refresh.pack(side=LEFT)

        # Button to run a process
        if self.mode in ['Demand', 'Demand_Agent']:
            btn_run_state = 'normal'
        else:
            btn_run_state = 'disabled'
        self.img_run = PhotoImage(file=resource_path(r'res\run.png'))
        self.btn_run = Button(self.frame_btn_control,
                              text='Ejecutar',
                              image=self.img_run,
                              compound='left',
                              bg=bg_color,
                              width=75,
                              padx=10,
                              command=lambda: self.run_optimizer(self.active_process),
                              state=btn_run_state)
        self.btn_run.pack(side=LEFT)

        # Horizon Label
        self.lbl_horizon = Label(self.frame_btn_control,
                                 text='Horizonte:',
                                 fg=bg_color,
                                 font=("Calibri Light", 14),
                                 bg=_from_rgb((0, 128, 61)))
        self.lbl_horizon.pack(side=LEFT,
                              padx=(10, 0))

        # Spinbox to select the amount of periods to forecast in the future
        saved_periods_fwd = self.back_end.config_shelf.send_parameter('periods_fwd')
        var = DoubleVar(value=int(saved_periods_fwd))
        self.spinbox_periods = Spinbox(self.frame_btn_control, from_=0, to=500, textvariable=var)
        self.spinbox_periods.pack(side=LEFT)

        # Horizon label
        self.lbl_days = Label(self.frame_btn_control,
                              text='días',
                              fg=bg_color,
                              font=("Calibri Light", 14),
                              bg=_from_rgb((0, 128, 61)))
        self.lbl_days.pack(side=LEFT,
                           padx=(10, 0))

        # Label for the combobox
        Label(self.frame_btn_control,
              text='Despliegue:',
              fg=bg_color,
              font=("Calibri Light", 14),
              bg=_from_rgb((0, 128, 61))).pack(padx=(50, 0), side=LEFT)

        # Combobox: Changes time frequency to daily, weekly, monthly
        # This option changes the table and plot LOD
        freqs_ = ['Diario',
                  'Semanal',
                  'Mensual']
        self.combobox_time_freq = ttk.Combobox(self.frame_btn_control,
                                               value=freqs_)
        self.combobox_time_freq.current(0)
        self.combobox_time_freq.bind("<<ComboboxSelected>>",
                                     lambda event: self.refresh_views(event, ('Granularidad',
                                                                              self.combobox_time_freq.get())))
        self.combobox_time_freq.pack(padx=10,
                                     side=LEFT)

        # Paned Window that contains the tree view and a master frame
        self.paned_win_main = PanedWindow(self.master,
                                          width=self.width,
                                          height=self.height,
                                          orient=HORIZONTAL)

        # Tree View declaration, double click is binded to the tree view
        self.tree_view = ttk.Treeview(self.master)

        self.frame_filters = ttk.Frame(self.master,
                                       style='TFrame')
        self.frame_filters.pack(fill=BOTH,
                                expand=True)

        # Main Frame declaration, on the right of the tree view, inside the Paned Window
        self.main_frame = Frame(self.paned_win_main,
                                bg=bg_color)

        # Paned Window that contains the tree view and a master frame
        self.paned_win_tbl_plot = PanedWindow(self.main_frame,
                                              width=self.width,
                                              height=self.height,
                                              orient=VERTICAL)

        # Add the tree view and te main frame to the Paned Window, and pack it to fill the screen
        self.paned_win_main.pack(fill=BOTH, expand=True)
        self.paned_win_main.add(self.frame_filters)
        self.paned_win_main.add(self.main_frame)

        # --- Level 1 --- Top and Bottom Frames

        #
        temp_text = 'Cargue archivos para ver algo aquí.'
        self.temp_label = Label(self.main_frame,
                                text=temp_text)

        # Top Frame that covers the top half of the screen
        # Contains the Table Frame
        self.top_frame = Frame(self.master,
                               borderwidth=2,
                               width=150,
                               relief="groove",
                               bg=bg_color)

        # Bottom Frame that contains the bottom half of the screen
        # Contains Plot Frame to the left and Config Frame to the right
        self.bottom_frame = Frame(self.master,
                                  borderwidth=2,
                                  width=150,
                                  relief="groove",
                                  bg=bg_color)

        # Pack the Top and Bottom Frames
        self.pack_to_main_frame()

        # --- Level 2 --- Table Frame, Notebook Frame, Config Frame

        # Table Frame that contains the pandastable
        # Packed to the Top Frame
        self.frame_table = Frame(self.top_frame,
                                 bg=bg_color)
        self.frame_table.pack(fill='both',
                              expand=True,
                              )

        # Frame that contains the Notebook
        self.frame_notebook = Frame(self.bottom_frame,
                                    bg=bg_color)
        self.frame_notebook.pack(fill='both', expand=True, side=LEFT)

        # Notebook contains the Raw Data plot, the Model plot and the Metrics Tab
        # User switches between tabs as needed
        # Model and Metrics tabs default to disabled, as user needs to run the optimizer before seeing data there
        # Notebook declaration
        self.notebook_plotting = ttk.Notebook(self.frame_notebook)

        # Tab declaration
        self.tab_data_plot = ttk.Frame(self.notebook_plotting)
        self.tab_model_plot = ttk.Frame(self.notebook_plotting)
        self.tab_metrics = ttk.Frame(self.notebook_plotting)

        # Add tabs to Notebook and pack the notebook to the frame
        self.notebook_plotting.add(self.tab_data_plot,
                                   text='Datos')
        self.notebook_plotting.add(self.tab_model_plot,
                                   text='Modelo',
                                   state='disabled')
        self.notebook_plotting.add(self.tab_metrics,
                                   text='Métricas',
                                   state='disabled')
        self.notebook_plotting.pack(fill=BOTH,
                                    expand=1)

        # Metrics Frame, contains three columns
        # Metric Name | Metric Value | Metric Description
        self.metrics_frame = Frame(self.tab_metrics)
        self.metrics_frame.pack(fill='y')
        self.metrics_frame.columnconfigure((0, 1, 2), uniform='equal', weight=1)

        # Automatic load on boot, uses the last known Mode setting, Demand or Forecast
        # Loads data accordingly
        process_ = self.back_end.config_shelf.send_parameter('Mode')
        self.update_gui(process_)

        # Center the tkinter window on screen
        center_window(self.master,
                      self.screen_width,
                      self.screen_height)

    def pack_to_main_frame(self):

        self.paned_win_tbl_plot.add(self.top_frame, stretch='always')
        self.paned_win_tbl_plot.add(self.bottom_frame, stretch='always')
        self.paned_win_tbl_plot.pack(fill=BOTH, expand=True)

        try:
            self.temp_label.pack_forget()
        except AttributeError:
            pass

    def update_gui(self, process: str, apply_bom=False):
        """
        Function is called on init or after loading new data.

        Update the GUI based on the process parameter.
        Enable or disable buttons according to process parameter.
        Read the data and separate it into subsets on the backend based on the process_ parameter.

        Clear the tree view and populate it with the subset keys.
        Call the show_plot_and_table function to show the loaded data on the plot and the table.
        """

        # clear GUI
        self.clear_gui()

        # --- MENU STATES ---
        # Enable the Segmentation menu option when the process is Forecast
        if process == 'Forecast':
            segment_btn_state = 'normal'
        else:
            segment_btn_state = 'disabled'
        self.sub_menu_config.entryconfig('Segmentación',
                                         state=segment_btn_state)

        # --- MASTER BUTTON STATES ---

        # Enable save, refresh buttons for every process
        self.btn_refresh['state'] = 'normal'

        # Enable Run button for Demand, Demand Agent and Model processes
        if process in ['Demand', 'Demand_Agent']:
            btn_run_state = 'normal'
            btn_save_state = 'disabled'
        else:
            btn_run_state = 'disabled'
            btn_save_state = 'normal'

        self.btn_save['state'] = btn_save_state
        self.btn_run['state'] = btn_run_state

        try:
            # the path to the data has been validated, so the data can be separated into several datasets
            # process must be specified to read the correct filepath

            self.master.withdraw()

            queue_ = queue.Queue()
            initializing_thread = ThreadedClient_exp(queue_, self.back_end.create_input_df, [process, apply_bom])
            initializing_thread.start()

            self.new_win = Toplevel(self.master)
            self.new_win.overrideredirect(1)
            self.win_obj = WindowLoading(self.new_win, initializing_thread, self.screen_width, self.screen_height)
            self.new_win.grab_set()
            self.master.wait_window(self.new_win)

            self.master.deiconify()

            # Pack Top and Bottom Frames to the Main Frame
            self.pack_to_main_frame()

            # self.populate_tree(item_list)
            self.add_filters(process)

            # call function to update the plot and the table on the GUI
            self.show_plot_and_table(process, ['DEFAULT', 'DEFAULT'], 0)

        # if the segmented data sets haven't been created, clear the GUI
        except (KeyError, ValueError, FileNotFoundError, PermissionError, tkinter.TclError) as e:
            self.open_window_pop_up('Error', e)
            self.clear_gui()

    def add_filters(self, process: str):
        """
        Add filters to the filters frame on the left panel.
        The filters added depend on the process parameter.
        """

        self.lbl_name_agent = Label(self.frame_filters,
                                    bg=bg_color,
                                    text='Agente')

        self.cbx_agent = ttk.Combobox(self.frame_filters,
                                      value=self.back_end.available_agents,
                                      width=get_longest_str_length_from_list(self.back_end.available_agents) + 5)

        self.lbl_name_prod = Label(self.frame_filters,
                                   bg=bg_color,
                                   text='Producto')

        if process == 'Demand_Agent':
            agent = self.back_end.available_agents[0]
            prod_list = self.back_end.prods_per_agent[agent]

        else:
            prod_list = list(self.back_end.dict_products.values())

        self.cbx_prod = ttk.Combobox(self.frame_filters,
                                     value=prod_list,
                                     width=get_longest_str_length_from_list(prod_list) + 5)

        # If process is Demand_Agent add an extra Agent filter on top
        if process == 'Demand_Agent':
            self.lbl_name_agent.grid(row=0,
                                     column=0)
            self.cbx_agent.current(0)
            self.cbx_agent.bind("<<ComboboxSelected>>",
                                self.cbx_agent_callback)
            self.cbx_agent.grid(row=1,
                                column=0)

            row_lbl_prod = 2
            row_cbx_prod = 3

        else:
            row_lbl_prod = 0
            row_cbx_prod = 1

        # Add the product filter (label and combobox.
        self.lbl_name_prod.grid(row=row_lbl_prod,
                                column=0)
        self.cbx_prod.current(0)
        self.cbx_prod.bind("<<ComboboxSelected>>",
                           self.refresh_views)
        self.cbx_prod.grid(row=row_cbx_prod,
                           column=0)

    def cbx_agent_callback(self, event):
        """Callback for the agent filter combobox."""

        # Get the selected agent from the combobox.
        agent = self.cbx_agent.get()

        # Refresh the GUI (table and plot)
        self.refresh_views(event)

        # Change the content of the product filter.
        # Shown products depend on the agent's context.
        self.configure_product_filter(self.back_end.prods_per_agent[agent])

    def get_sku_name(self, sku):
        """Returns the SKU name for an SKU."""

        df_master = self.back_end.df_master_data
        sku_name = df_master[df_master['Codigo'] == sku]['Nombre']

        return sku_name

    def get_sku(self, sku_name):
        """Returns the SKU for an SKU name."""

        df_master = self.back_end.df_master_data
        sku = df_master[df_master['Nombre'] == sku_name]['Codigo']

        return sku

    def configure_product_filter(self, product_list: list):
        """Change the product filter based on the agent's context."""

        self.cbx_prod['values'] = product_list

    def clear_gui(self):
        """Function to clear data from the back end and the GUI."""

        # Change the model ready status
        if self.model_ready:
            self.model_ready = False

        # Disable the model tabs
        self.notebook_plotting.tab(self.tab_model_plot, state='disabled')
        self.notebook_plotting.tab(self.tab_metrics, state='disabled')

        # Disable the Export, Refresh and Run buttons
        self.btn_save.config(state='disabled')
        self.btn_refresh.config(state='disabled')
        self.btn_run.config(state='disabled')

        # Clear information from the tree view
        # self.clear_tree()

        for widget in self.frame_filters.winfo_children():
            widget.destroy()

        # Unpack the top and bottom frames
        # Unpack the temporary label to avoid having more than one temporary labels active, if the user clicks New
        # more than one time.
        try:
            self.top_frame.pack_forget()
            self.bottom_frame.pack_forget()
            self.temp_label.pack_forget()
            self.paned_win_tbl_plot.pack_forget()

        except AttributeError:
            pass

        # Add a Label telling user to load files on the Top and Bottom Frames
        self.temp_label.pack(fill=BOTH, expand=True)

    def show_plot_and_table(self, process, filters: list, event):
        """
        Call the create figure function with the data of the passed sku parameter.

        sku: name of the SKU or DEFAULT, if DEFAULT, shows the currently selected SKU on the tree view
        plot_type: Demand plots the raw data, Forecast shows the fitted values and the forecast.
        """

        # If the process parameter is Demand, Forecast or Metrics, use the segmented data sets from the backend.
        if process in ['Demand', 'Forecast', 'Metrics', 'Demand_Agent']:
            df_total = self.back_end.df_total_input

        # If the process parameter is Model, use the fitted data sets from the backend.
        else:
            df_total = self.back_end.df_total_demand_fcst

        if process in ['Demand_Agent', 'Model_Agent']:
            agent = filters[1]
            if agent == 'DEFAULT':
                agent = self.back_end.available_agents[0]
            df_total = df_total[df_total['Agente'] == agent]

        # Get selected data frame based on the sku parameter.
        sku_name = filters[0]

        if sku_name == 'DEFAULT':
            sku_name = self.back_end.list_product_names[0]

        # Filter by product
        df = df_total[df_total['Nombre'] == sku_name]

        # Group the dataframe by date. The aggregation is controlled by the Combobox combobox_time_freq selection.
        if self.combobox_time_freq.get() == 'Semanal':
            strf_format = 'Semana %U'
            df = df.groupby(pd.Grouper(freq='1W')).sum()
        elif self.combobox_time_freq.get() == 'Mensual':
            strf_format = '%b-%Y'
            df = df.groupby(pd.Grouper(freq='M')).sum()
        else:
            strf_format = '%d/%m/%Y'

        # Create a formatted string column based on the date.
        # The format depends on level of aggregation.
        df = df.reset_index()
        df = df.rename(columns={'index': 'Fecha'})
        df['Fecha_strf'] = df['Fecha'].dt.strftime(strf_format)
        df = df.set_index('Fecha')

        # Show the data on the table.
        self.show_table(df, process)

        # call function to show plot on the bottom frame
        self.create_fig(df, process)

        if process == 'Model':
            self.create_fig(df, 'Demand')
        elif process == 'Model_Agent':
            self.create_fig(df, 'Demand_Agent')

    def create_fig(self, df, plot_type):
        """
        Create a matplotlib plot and pack it to the GUI as a Figure.
        If the plot type is Demand or Forecast, the Figure is added to the data_plot on the Data tab of the notebook.
        If the plot type is Model, the Figure is added to the model_plot on the Model tab of the notebook.
        Demand and Forecast use a single axis plot.
        Model uses a triple axis plot to show the real data, the fitted values and the forecast on the same plot.
        """

        # Set the default DPI to be used.
        dpi = 100
        x = self.plot_width / dpi
        y = self.bottom_frame_height / dpi

        # If the plot type is Demand or Forecast:
        # Data is packed into the data plot widget.
        if plot_type in ['Demand', 'Demand_Agent', 'Forecast', 'Metrics']:
            if self.data_plot is not None:
                self.data_plot.get_tk_widget().destroy()
            if self.data_toolbar is not None:
                self.data_toolbar.destroy()

            self.figure_data = Figure(figsize=(x, y),
                                      dpi=dpi)

            self.ax_data = self.figure_data.add_subplot(1, 1, 1)
            self.data_plot = FigureCanvasTkAgg(self.figure_data, self.tab_data_plot)
            self.data_toolbar = NavigationToolbar2Tk(self.data_plot, self.tab_data_plot)
            self.data_toolbar.update()
            self.data_plot.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)

        # If the plot type is Model:
        # Data is packed into the model plot widget.
        else:
            if self.model_plot is not None:
                self.model_plot.get_tk_widget().destroy()
            if self.model_toolbar is not None:
                self.model_toolbar.destroy()

            self.figure_model = Figure(figsize=(x, y), dpi=dpi)
            self.ax_model = self.figure_model.add_subplot(1, 1, 1)

            self.model_plot = FigureCanvasTkAgg(self.figure_model, self.tab_model_plot)
            self.model_toolbar = NavigationToolbar2Tk(self.model_plot, self.tab_model_plot)
            self.model_toolbar.update()
            self.model_plot.get_tk_widget().pack(side=LEFT, fill=BOTH, expand=1)

        # Reset the index of the data frame to use the date as an axis.
        df = df.reset_index()

        # Drop the string formatted column.
        # If it doesn't exist, skip this step.
        try:
            df.drop(columns=['Fecha_strf'], inplace=True)
        except KeyError:
            pass

        # Styles declaration
        brand_green = '#005c2c'  # ticheese green
        yellow = '#ffff00'
        orange = '#e5a700'
        title_font_size = 16
        title_font_weight = 'medium'

        # If the plot type is Demand or Forecast, create a single axis plot.
        # Names change based on the plot type.
        if plot_type in ['Demand', 'Demand_Agent', 'Forecast']:
            if plot_type in ['Demand', 'Demand_Agent']:
                y_name = 'Demanda'
                plot_title = 'Demanda Real'
            else:
                y_name = plot_title = 'Pronóstico'

            df.plot(x='Fecha',
                    y=y_name,
                    legend=False,
                    ax=self.ax_data,
                    color=brand_green)

            # Set title and title color
            self.ax_data.set_title(plot_title,
                                   fontdict={'fontsize': title_font_size,
                                             'fontweight': title_font_weight})
            self.ax_data.title.set_color(brand_green)

            # Set y label
            self.ax_data.set_ylabel('Cantidad (kg)')

        # If the plot type is Metrics, create a double axis plot.
        if plot_type == 'Metrics':
            df.plot(x='Fecha',
                    y='Demanda',
                    color=brand_green,
                    ax=self.ax_data)

            df.plot(x='Fecha',
                    y='Pronóstico',
                    color=orange,
                    ax=self.ax_data)

            # Set title and title color
            self.ax_data.set_title('Demanda Real vs. Pronóstico',
                                   fontdict={'fontsize': title_font_size,
                                             'fontweight': title_font_weight})
            self.ax_data.title.set_color(brand_green)

            # Set y label
            self.ax_data.set_ylabel('Cantidad (kg)')

        # If the plot type is Model, create a 5-axis plot.
        if plot_type in ['Model', 'Model_Agent']:
            df = df[['Fecha', 'Demanda', 'Ajuste', 'Pronóstico', 'Min', 'Max']]
            col = ['Fecha', 'Demanda', 'Modelo', 'Pronóstico', 'Min', 'Max']
            df.columns = col
            dates = df['Fecha'].values

            # Add Demand plot
            df.plot(x=col[0],
                    y=col[1],
                    color=brand_green,
                    ax=self.ax_model)

            # Add Model plot, fitted values
            df.plot(x=col[0],
                    y=col[2],
                    color=yellow,
                    ax=self.ax_model)

            # Add forecast plot (mean values)
            df.plot(x=col[0],
                    y=col[3],
                    color=orange,
                    ax=self.ax_model)

            # Add forecast plot (minimum values)
            df.plot(x=col[0],
                    y=col[4],
                    color=orange,
                    ax=self.ax_model)

            # Add forecast plot (maximum values)
            df.plot(x=col[0],
                    y=col[5],
                    color=orange,
                    ax=self.ax_model)

            # Set legend
            self.ax_model.legend(['Demanda', 'Ajuste', 'Pronóstico'], loc='lower center', ncol=3)

            # Fill forecast plot, between minimum and maximum values
            self.ax_model.fill_between(dates,
                                       df[col[4]],
                                       df[col[5]],
                                       alpha=0.5,
                                       facecolor=orange)

            # Set plot title and color
            self.ax_model.set_title('Demanda Real y Pronóstico',
                                    fontdict={'fontsize': title_font_size,
                                              'fontweight': title_font_weight})
            self.ax_model.title.set_color(brand_green)

            # Set y label
            self.ax_model.set_ylabel('Cantidad (kg)')

    def show_table(self, df, table_type):
        """
        Show a table on the pandastable widget positioned on the top frame.

        Data must be pre processed before showing it on the table.
        The date index must be replaced to a string formatted one.
        If the table type is Demand or Forecast, the Codigo and Nombre columns must be dropped.
        If the table type is Model, null values must be handled and numbers must be rounded.
        The data is transposed before being shown on the table.
        """

        # Drop the Fecha column and use the string formatted date as the new index.
        try:
            df = df.reset_index()
            df.drop(columns=['Fecha'], inplace=True)
            df.set_index('Fecha_strf', inplace=True)

        except KeyError:
            pass

        # If the table type is Demand or Forecast, drop the code and name values as they are redundant.
        # There can only be one selected item on the tree view.
        cols = ['Codigo', 'Nombre']
        if table_type in ['Demand_Agent', 'Model_Agent']:
            cols = cols + ['Agente']
        try:
            df.drop(columns=cols, inplace=True)
        # when the models haven't been trained, the df only contains the values column
        except KeyError:
            pass

        # If the table type is Model fill null values with "-".
        if table_type in ['Model', 'Model_Agent']:
            df = df.fillna('-')

        # Round numbers to two places.
        # df = df.round(2)

        # Transpose the table, show dates as columns in a timeline format.
        df = df.T

        # Destroy widgets inside the Table Frame before packing the new Table.
        for widget in self.frame_table.winfo_children():
            widget.destroy()

        # Declare the pandas table widget.
        self.pd_table = pandastable.Table(self.frame_table,
                                          dataframe=df,
                                          showtoolbar=True,
                                          showstatusbar=True)

        # Show the table.
        self.pd_table.showindex = True
        self.pd_table.autoResizeColumns()
        self.pd_table.show()
        self.pd_table.redraw()

    def update_periods_fwd(self):
        """
        Check if the user changed the periods forward parameter.
        If changed, update the parameter on the backend.
        """

        # get the actual value from the spinbox
        new_periods_fwd = int(self.spinbox_periods.get())

        # if the value is different from the stored one, change it on the backend
        if new_periods_fwd != self.back_end.config_shelf.send_parameter('periods_fwd'):
            self.back_end.config_shelf.write_to_shelf('periods_fwd', new_periods_fwd)

    def run_optimizer(self, process: str):
        """Spawns the optimizer thread to train the models based on the actual data."""

        # update the periods_fwd parameter in the back end
        self.update_periods_fwd()

        # Open confirmation pop up window.
        operation_canceled = self.open_window_training_confirmation()

        if operation_canceled is False:
            # spawn the thread which finds the best model
            # uses a thread to avoid freezing the program
            self.spawn_thread(process)

    def spawn_thread(self, process):
        """
        Create ThreadedClient class and pass it to a periodic call function.
        """

        queue_ = queue.Queue()
        thread = ThreadedClient(queue_,
                                self.back_end,
                                process)
        thread.start()

        # Create new window that shows the training status with a Listbox.
        self.new_win = Toplevel(self.master)
        self.new_win.overrideredirect(1)
        WindowTraining(self.new_win, self.back_end, queue_, thread, self.screen_width,
                       self.screen_height)
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)

        # Enable the model tab in the plot section
        self.notebook_plotting.tab(self.tab_model_plot, state='normal')

        # Change the active process
        if process == 'Demand':
            self.active_process = model_process = 'Model'
        else:
            self.active_process = model_process = 'Model_Agent'

        # Call function to show the plot and the table with the default filter selection.
        self.show_plot_and_table(model_process, ['DEFAULT', 'DEFAULT'], 0)

        # enable the metrics tab
        self.update_metrics(process, ['DEFAULT', 'DEFAULT'])
        self.model_ready = True

        # enable the export button
        self.btn_save['state'] = 'normal'

    def periodic_call(self, process, thread, queue_):
        self.check_queue(queue_)

        if thread.is_alive():
            self.master.after(100, lambda: self.periodic_call(process, thread, queue_))

        else:
            if process == 'Optimizador':
                # self.btn_run_optimizer.config(state='active')
                pass

    def refresh_views(self, event, *args):
        """Refresh the views on the GUI based on the filter selection."""

        # If the model is ready:
        # 1. Update the periods forward on the back end.
        # 2. Refresh predictions with the new periods forward parameter.
        if self.model_ready:
            self.update_periods_fwd()
            self.back_end.refresh_predictions(self.active_process)

        # Get the selected item from the tree view.
        # item_name = self.get_tree_selection()
        sku_name = self.cbx_prod.get()
        filters = [sku_name]
        try:
            agent = self.cbx_agent.get()
            filters = [sku_name, agent]
        except AttributeError:
            pass

        # Populate the plot and the table based on the selected item.
        if self.active_process == 'Model':
            process = 'Demand'
        elif self.active_process == 'Model_Agent':
            process = 'Demand_Agent'
        else:
            process = self.active_process

        # If the fitted datasets from the back end aren't empty
        # show the Model plot and table and update the metrics.
        if not self.back_end.df_total_fitted.empty:
            self.show_plot_and_table(self.active_process, filters, event)
            self.update_metrics(self.active_process, filters)

        else:
            self.show_plot_and_table(process, filters, event)

    def update_metrics(self, process: str, filters: list):

        # change state of the  tab of the notebook
        self.notebook_plotting.tab(self.tab_metrics, state='normal')

        df_metrics = self.back_end.df_total_metrics.merge(self.back_end.df_master_data,
                                                          on='Codigo')

        if process in ['Demand_Agent', 'Model_Agent']:
            agent = filters[1]
            if agent == 'DEFAULT':
                agent = self.back_end.available_agents[0]
            df_metrics = df_metrics[df_metrics['Agente'] == agent]

        sku = filters[0]

        if sku == 'DEFAULT':
            sku = self.back_end.list_product_names[0]

        df_metrics = df_metrics[df_metrics['Nombre'] == sku]

        for widget in self.metrics_frame.winfo_children():
            widget.pack_forget()

        # Declare tree view
        self.treev = ttk.Treeview(self.metrics_frame, selectmode='browse')
        self.treev.pack(side='top')

        # Configure self.treeview
        self.treev['columns'] = ('1', '2')
        self.treev['show'] = 'headings'
        self.treev.column("1", width=250, anchor='sw')
        self.treev.column("2", width=90, anchor='se')

        self.treev.heading("1", text="Métrica")
        self.treev.heading("2", text="Valor")

        # Double click callback
        self.treev.bind('<Double-1>', self.treeview_callback)

        for idx, metric in enumerate(list(df_metrics.columns)):

            if metric in ['Codigo', 'Agente', 'Nombre', 'Unidad_Medida']:
                pass

            else:
                metric_name, metric_desc = self.back_end.dict_metric_desc[metric]
                value = round(float(df_metrics[[metric]].values), 2)

                if metric.endswith('PERC'):
                    value = str(value) + ' %'
                else:
                    value = str(value) + ' kg'

                self.treev.insert('', 'end', text=metric,
                                  values=(metric_name, value))

    def treeview_callback(self, event):
        """Callback upon double click of a tree view item."""

        item = self.treev.selection()
        metric_name, metric_desc = self.back_end.dict_metric_desc[self.treev.item(item, "text")]
        # print("you clicked on", self.treev.item(metric, "text"))

        self.open_window_pop_up('Info', f'{metric_name}: {metric_desc}')

    def open_window_select_work_path(self):
        """Open TopLevel to select path where the input files are located."""

        # Declare a new Toplevel
        # grab_set and wait_window to wait for the main screen to freeze until this window is closed
        self.new_win = Toplevel(self.master)
        win_obj = WindowSelectWorkPath(self.new_win, self.back_end, self.screen_width, self.screen_height)
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)

        # If the files were loaded successfully, run this block.
        if win_obj.successful_load:

            # If the user loads new data, a new model must be trained.
            if self.model_ready:
                self.model_ready = False
                self.notebook_plotting.add(self.tab_model_plot, state='disabled')
                self.notebook_plotting.add(self.tab_metrics, state='disabled')

            # The process attribute of win_obj indicates the process that was chosen by the user.
            # The GUI is updated differently for each process.
            self.active_process = win_obj.process
            self.update_gui(win_obj.process)

        # If the load wasn't successful, keep the previous GUI state.
        else:
            pass

        # If the operation was canceled, keep the previous GUI state.
        if win_obj.canceled:
            pass

    def open_window_export(self):
        """Open TopLevel to export files to selected locations."""

        # Get the active process from the backend.
        process_ = self.back_end.config_shelf.send_parameter('Mode')

        # Declare Toplevel and a WindowExportFile class instance.
        # Grab_set and wait_window to freeze the screen until the user closes the popup window.
        self.new_win = Toplevel(self.master)

        if process_ in ['Demand', 'Model'] and self.model_ready is False:
            warning = 'El modelo se debe entrenar antes de exportar la información.'
            WindowPopUpMessage(self.new_win,
                               'Alerta',
                               warning,
                               self.screen_width,
                               self.screen_height)

        else:
            WindowExportFile(self.new_win, self.back_end, self.screen_width, self.screen_height, process_)

        self.new_win.grab_set()
        self.master.wait_window(self.new_win)

    def open_window_segment(self):
        """Open TopLevel to configure the forecast segmentation."""

        # Declare Toplevel and a WindowSegmentOptions class instance.
        # Grab_set and wait_window to freeze the screen until the user closes the popup window.
        self.new_win = Toplevel(self.master)
        WindowSegmentOptions(self.new_win, self.back_end, self.screen_width, self.screen_height)
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)

    def open_window_training_confirmation(self):
        """Open TopLevel to configure the forecast segmentation."""

        # Declare Toplevel and a WindowSegmentOptions class instance.
        # Grab_set and wait_window to freeze the screen until the user closes the popup window.
        self.new_win = Toplevel(self.master)
        warning = 'El entrenamiento de los modelos puede ser un proceso extenso.\n ¿Desea continuar?'
        win_obj = WindowPopUpMessageWithCancel(self.new_win,
                                               'Alerta',
                                               warning,
                                               self.screen_width,
                                               self.screen_height)

        self.new_win.grab_set()
        self.master.wait_window(self.new_win)

        return win_obj.canceled

    def open_window_pop_up(self, title, msg):
        # open new TopLevel as a popup window
        self.new_win = Toplevel(self.master)
        WindowPopUpMessage(self.new_win,
                           title,
                           msg,
                           self.screen_width,
                           self.screen_height)

        # freeze master window until user closes the pop up
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)

    def sub_menu_convert_callback(self):

        # Declare a new Toplevel
        # grab_set and wait_window to wait for the main screen to freeze until this window is closed
        self.new_win = Toplevel(self.master)
        win_obj = WindowSelectPath(self.new_win,
                                   self.back_end,
                                   self.screen_width,
                                   self.screen_height,
                                   'Recetas',
                                   'BOM')
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)

        # If the operation was not canceled, get the path.
        if not win_obj.canceled:
            self.back_end.apply_bom(self.back_end.raw_data, self.active_process)
            self.update_gui(self.active_process, apply_bom=True)


class WindowSelectPath:

    def __init__(self, master, app: Application, screen_width_, screen_height_, path_name, path_name_back_end):
        self.master = master
        self.master.title("Módulo de Demanda - COPROLAC")
        self.master.configure(background=bg_color)
        self.master.iconbitmap(resource_path(r'res/icon.ico'))
        self.screen_width = screen_width_
        self.screen_height = screen_height_
        self.width = self.screen_width / 2
        self.height = self.screen_height / 5
        self.app = app

        self.path_name = path_name
        self.path_name_back_end = path_name_back_end

        self.selected_path = None

        self.canceled = None

        # Container Frame for the paths
        self.paths_frame = LabelFrame(self.master,
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
        self.btn_accept = Button(self.master,
                                 text='Aceptar',
                                 command=self.save_path_to_back_end)
        self.btn_accept.grid(pady=10, row=2, column=0)

        self.btn_cancel = Button(self.master,
                                 text='Cancelar',
                                 command=lambda: self.close_window(canceled=True))
        self.btn_cancel.grid(pady=10, row=2, column=1)

        # Name Label, first column
        self.lbl_name_path = Label(self.paths_frame,
                                   text=self.path_name,
                                   bg=bg_color)
        self.lbl_name_path.grid(pady=10,
                                row=0,
                                column=0,
                                padx=5)

        # Path Label, second column
        self.lbl_path = Label(self.paths_frame,
                              text=self.app.get_path(self.path_name_back_end),
                              bg=bg_color,
                              pady=10,
                              borderwidth=2,
                              width=150,
                              relief="groove",
                              anchor='w')
        self.lbl_path.grid(pady=10,
                           row=0,
                           column=1,
                           padx=5)

        # Browse Button, third column, to open the browse files window
        self.btn_browse = Button(self.paths_frame,
                                 text='...',
                                 command=self.get_user_selected_path)
        self.btn_browse.grid(pady=10,
                             row=0,
                             column=2,
                             padx=5)

    def close_window(self, canceled: bool):
        self.canceled = canceled
        self.master.destroy()

    def get_user_selected_path(self):
        self.selected_path = browse_files_master(self.app.get_path('Temp'))
        self.lbl_path['text'] = self.selected_path[1]

    def save_path_to_back_end(self):

        # Get selected path from the label text.
        selected_path = self.lbl_path['text']

        # Validate path before saving to back end.
        if validate_path(selected_path, is_file=True):

            # Set selected path to back end.
            self.app.set_path(self.path_name_back_end, selected_path)
            self.close_window(canceled=False)

        # If path is invalid, open pop up warning.
        else:
            WindowPopUpMessage(self.master,
                               'Error',
                               'Debe seleccionar un archivo válido.\n'
                               'El archivo puede ser en formato Excel o CSV.',
                               self.screen_width,
                               self.screen_height)


class WindowSelectWorkPath:

    @staticmethod
    def remove_section_from_grid(widgets_list: list):
        """Remove widget list from the grid."""
        for widget in widgets_list:
            widget.grid_forget()

    def __init__(self, master, app: Application, screen_width_, screen_height_):
        self.master = master
        self.master.title("Módulo de Demanda - COPROLAC")
        self.master.configure(background=bg_color)
        self.master.iconbitmap(resource_path(r'res/icon.ico'))
        self.screen_width = screen_width_
        self.screen_height = screen_height_
        self.width = self.screen_width / 2
        self.height = self.screen_height / 5
        self.app = app
        self.new_win = None
        self.successful_load = False
        self.canceled = False
        self.process = None

        self.last_process = self.app.config_shelf.send_parameter('Mode')

        # --- LEVEL 0 ---

        # Container Frame for the routine combobox
        self.routine_frame = LabelFrame(self.master,
                                        text='Escoja una rutina:',
                                        bg=bg_color,
                                        width=screen_width_ / 5,
                                        padx=10,
                                        pady=10)
        self.routine_frame.grid(padx=10,
                                pady=10,
                                row=0,
                                column=0,
                                columnspan=2,
                                sticky='WE')

        # Container Frame for the paths
        self.paths_frame = LabelFrame(self.master,
                                      text='Escoja un directorio:',
                                      bg=bg_color,
                                      width=screen_width_ / 5,
                                      padx=10,
                                      pady=10)
        self.paths_frame.grid(padx=10,
                              pady=10,
                              row=1,
                              column=0,
                              columnspan=2)

        # accept and cancel buttons
        self.btn_accept = Button(self.master,
                                 text='Aceptar',
                                 command=self.save_selection)
        self.btn_accept.grid(pady=10, row=2, column=0)

        self.btn_cancel = Button(self.master,
                                 text='Cancelar',
                                 command=self.close_window)
        self.btn_cancel.grid(pady=10, row=2, column=1)

        # --- LEVEL 1 ---

        # Routine Frame
        # Selection Combobox, second column,  to choose which type of file to open, demand or forecast
        self.modes_user_options = ['Crear pronóstico de demanda',
                                   'Cargar pronóstico de demanda',
                                   'Calcular métricas',
                                   'Crear pronóstico por agente']
        self.back_end_modes = self.app.modes

        self.cbx_file_type = ttk.Combobox(self.routine_frame,
                                          value=self.modes_user_options,
                                          width=50)

        idx = self.back_end_modes.index(self.last_process)

        self.cbx_file_type.current(idx)

        self.cbx_file_type.bind("<<ComboboxSelected>>", self.cbx_callback)
        self.cbx_file_type.grid(row=0,
                                column=1,
                                columnspan=3,
                                padx=10,
                                pady=10,
                                sticky='WE')

        # Paths Frame

        #  ROW 0: LABEL THAT SHOWS THE PATH

        # Name Label, first column
        self.lbl_name_path = Label(self.paths_frame,
                                   text='',
                                   bg=bg_color,
                                   padx=5)

        # Path Label, second column
        self.lbl_path = Label(self.paths_frame,
                              text='',
                              bg=bg_color,
                              pady=10,
                              borderwidth=2,
                              width=150,
                              relief="groove",
                              anchor='w')

        # Browse Button, third column, to open the browse files window
        self.btn_browse = Button(self.paths_frame,
                                 text='...',
                                 command=lambda: self.browse_files('Level_1'))

        # Name Label
        self.lbl_name_cb_bom = Label(self.paths_frame,
                                     text='Aplicar recetas?',
                                     bg=bg_color,
                                     padx=5,
                                     anchor='w')

        # Checkbutton to control the BOM Explosion parameter
        self.cb_bom_state = IntVar()
        self.cb_bom = Checkbutton(self.paths_frame,
                                  variable=self.cb_bom_state,
                                  bg=bg_color,
                                  command=self.cb_callback)

        self.lbl_name_second_path = Label(self.paths_frame,
                                          text='',
                                          bg=bg_color,
                                          padx=5)

        self.lbl_second_path = Label(self.paths_frame,
                                     text='',
                                     bg=bg_color,
                                     pady=10,
                                     borderwidth=2,
                                     width=150,
                                     relief="groove",
                                     anchor=W)

        self.btn_browse_second_path = Button(self.paths_frame,
                                             text='...',
                                             command=lambda: self.browse_files('Level_2'))

        self.lbl_name_third_path = Label(self.paths_frame,
                                         text='Recetas:',
                                         bg=bg_color,
                                         padx=5)

        self.lbl_third_path = Label(self.paths_frame,
                                    text='',
                                    bg=bg_color,
                                    pady=10,
                                    borderwidth=2,
                                    width=150,
                                    relief="groove",
                                    anchor=W)

        self.btn_browse_third_path = Button(self.paths_frame,
                                            text='...',
                                            command=lambda: self.browse_files('Level_3'))

        self.add_to_grid(self.last_process)

        center_window(self.master, self.screen_width, self.screen_height)

    def add_first_path_to_grid(self, process: str, row: int):

        if process in ['Demand', 'Metrics', 'Demand_Agent']:
            lbl_name = 'Ventas:'
        else:
            lbl_name = 'Pronóstico:'

        # Name Label, first column
        self.lbl_name_path['text'] = lbl_name

        # Name Label, first column
        self.lbl_name_path.grid(row=row,
                                column=0,
                                sticky='W')

        # Path Label, second column
        if process == 'Metrics':
            path = self.app.get_path('Metrics_Demand')
        else:
            path = self.app.get_path(process)

        self.lbl_path['text'] = path

        # Path Label, second column
        self.lbl_path.grid(row=row,
                           column=1,
                           padx=10,
                           pady=10,
                           sticky='WE')

        # Browse Button, third column, to open the browse files window
        self.btn_browse.grid(row=row,
                             column=2,
                             padx=10,
                             pady=10,
                             sticky='WE')

    def add_second_path_to_grid(self, process: str, row: int):

        # Name Label
        if process in ['Forecast', 'Metrics']:
            lbl_name = 'Pronóstico:'
        else:
            lbl_name = 'Recetas:'

        self.lbl_name_second_path['text'] = lbl_name

        self.lbl_name_second_path.grid(row=row,
                                       column=0,
                                       sticky='W')

        # BOM Path Label
        if process == 'Metrics':
            path = self.app.get_path('Metrics_Forecast')
        else:
            path = self.app.get_path('BOM')

        self.lbl_second_path['text'] = path

        self.lbl_second_path.grid(row=row,
                                  column=1,
                                  padx=10,
                                  pady=10)

        self.btn_browse_second_path.grid(row=row,
                                         column=2)

    def add_third_path_to_grid(self, row: int):

        self.lbl_name_third_path.grid(row=row,
                                      column=0,
                                      sticky='W')

        self.lbl_third_path['text'] = self.app.get_path('BOM')

        self.lbl_third_path.grid(row=row,
                                 column=1,
                                 padx=10,
                                 pady=10)

        self.btn_browse_third_path.grid(row=row,
                                        column=2)

    def add_bom_checkbox(self, row: int):
        """If the combobox == Demand, add this section to the grid."""

        self.lbl_name_cb_bom.grid(row=row,
                                  column=0)

        self.cb_bom.grid(row=row,
                         column=1)

    def browse_files(self, label_name):

        # get the last path that the user selected
        ini_dir_ = self.app.get_path('Temp')

        # call function to open a file selection window
        filepath, filename = browse_files_master(ini_dir_)

        # change the text content of the label
        if filename != '':
            # set the selected path as the new Temp path
            self.app.set_path('Temp', os.path.dirname(os.path.abspath(filename)))

            if label_name == 'Level_1':
                self.lbl_path.configure(text=filename)

            elif label_name == 'Level_2':
                self.lbl_second_path.configure(text=filename)

            elif label_name == 'Level_3':
                self.lbl_third_path.configure(text=filename)

    def get_process_from_cbx_selection(self):

        selected_option = self.cbx_file_type.get()

        selected_idx = self.modes_user_options.index(selected_option)

        selected_process = self.back_end_modes[selected_idx]

        return selected_process

    def save_selection(self):
        """"""

        # open PopUp warning if the Path Label is empty
        if self.lbl_path['text'] == '':
            self.open_window_pop_up('Error', 'Debe seleccionar un directorio válido.')

        self.process = self.get_process_from_cbx_selection()

        if self.process == 'Metrics':

            lbl_dict_metrics = {self.lbl_path: ['Metrics_Demand', 'Ventas'],
                                self.lbl_second_path: ['Metrics_Forecast', 'Pronóstico'],
                                self.lbl_third_path: ['BOM', 'Recetas']}

            for key, values in lbl_dict_metrics.items():
                path_ = key['text']
                if validate_path(path_, is_file=True):
                    self.app.set_path(values[0], path_)
                else:
                    self.open_window_pop_up('Error',
                                            f'El directorio al archivo de {values[1]} indicado es inválido.')

        else:
            # Get selected path
            curr_first_path = self.lbl_path['text']

            # Validate the path before saving
            if validate_path(curr_first_path, is_file=True):
                # set selected path to the Demand key of the paths shelf
                self.app.set_path(self.process, curr_first_path)

                if self.process == 'Demand':
                    # set the selected parameter to the BOM_Explosion key of the parameters shelf
                    self.app.set_parameter('BOM_Explosion', bool(self.cb_bom_state.get()))

                    if bool(self.cb_bom_state.get()):
                        path_bom = self.lbl_second_path['text']
                        # set selected bom path to the BOM key of the paths shelf
                        if validate_path(path_bom, is_file=True):
                            self.app.set_path('BOM', path_bom)
                        else:
                            self.open_window_pop_up('Error',
                                                    'El directorio al archivo de Recetas indicado es inválido.')

            else:
                self.open_window_pop_up('Error', 'El directorio al archivo de Ventas indicado es inválido.')

        # create separate datasets for each of the unique products
        try:
            # self.open_window_pop_up('Mensaje', 'Archivos cargados.')
            self.successful_load = True
            self.app.set_parameter('Mode', self.process)
            self.close_window()

        except ValueError as e:
            self.open_window_pop_up('Error', e)

        except PermissionError as e:
            self.open_window_pop_up('Error', 'Debe cerrar el archivo antes de proceder:\n' + e.filename)

    def remove_children_from_paths_frame(self):
        try:
            for widget in self.paths_frame.winfo_children():
                widget.grid_forget()
        except AttributeError:
            pass

    def cbx_callback(self, event):

        # Remove all widgets from the Frame that contains the path labels
        self.remove_children_from_paths_frame()

        # Get the back end process selected by the user.
        selected_process = self.get_process_from_cbx_selection()

        self.add_to_grid(selected_process)

    def add_to_grid(self, process: str):

        self.add_first_path_to_grid(process, 0)

        if process == 'Demand':
            self.add_bom_checkbox(1)

            if self.app.config_shelf.send_parameter('BOM_Explosion'):
                self.cb_bom.select()
                self.add_second_path_to_grid(process, 2)
            else:
                self.cb_bom.deselect()

        elif process == 'Metrics':
            self.add_second_path_to_grid(process, 1)
            self.add_third_path_to_grid(3)

    def cb_callback(self):

        if self.cb_bom_state.get():
            self.add_second_path_to_grid('Demand', 3)
        else:
            self.remove_section_from_grid([self.lbl_name_second_path, self.lbl_second_path,
                                           self.btn_browse_second_path])

    def open_window_pop_up(self, title, msg):
        # open new TopLevel as a popup window
        self.new_win = Toplevel(self.master)
        WindowPopUpMessage(self.new_win,
                           title,
                           msg,
                           self.screen_width,
                           self.screen_height)

        # freeze master window until user closes the pop up
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)

    def close_window(self):
        self.canceled = True
        self.master.destroy()


class WindowSegmentManual:

    def __init__(self, master, app: Application, screen_width_, screen_height_):
        self.master = master
        self.master.title("Segmentación")
        self.master.iconbitmap(resource_path(r'res/icon.ico'))
        self.master.configure(background=bg_color)
        self.screen_width = screen_width_
        self.screen_height = screen_height_
        self.width = self.screen_width / 2
        self.height = self.screen_height / 5
        self.app = app
        self.new_win = None
        self.canceled = False

        # --- NIVEL 0 ---

        # FRAME CONTENEDOR
        self.main_frame = LabelFrame(self.master,
                                     text='Segmentación:',
                                     bg=bg_color,
                                     width=screen_width_ / 5,
                                     padx=10,
                                     pady=10)
        self.main_frame.grid(padx=10,
                             pady=10,
                             row=0,
                             column=0,
                             columnspan=3)

        self.total_frame = Frame(self.master,
                                 bg=bg_color,
                                 width=screen_width_ / 5,
                                 padx=10)
        self.total_frame.grid(padx=10,
                              pady=10,
                              row=1,
                              column=0,
                              columnspan=3,
                              sticky='WE')

        self.lbl_total = Label(self.total_frame,
                               text='Total',
                               bg=bg_color)
        self.lbl_total.pack(expand=True, fill=BOTH, side=LEFT)

        self.lbl_total_val = Label(self.total_frame,
                                   text='',
                                   bg=bg_color)
        self.lbl_total_val.pack(expand=True, fill=BOTH, side=LEFT)
        # self.lbl_total_val.grid(row=0,
        #                         column=1,
        #                         columnspan=2)

        self.btn_accept = Button(self.master,
                                 text='Aceptar',
                                 command=self.save_selection)
        self.btn_accept.grid(pady=10, row=2, column=0)

        self.btn_cancel = Button(self.master,
                                 text='Cancelar',
                                 command=lambda: self.close_window(True))
        self.btn_cancel.grid(pady=10, row=2, column=2)

        # --- NIVEL 1 ---

        #  First Column Title Label
        self.lbl_col_segment_path = Label(self.main_frame,
                                          text='Segmento',
                                          bg=bg_color,
                                          padx=5)
        self.lbl_col_segment_path.grid(row=0, column=0)

        #  Second Column Title Label
        self.lbl_col_value_path = Label(self.main_frame,
                                        text='Porcentaje',
                                        bg=bg_color,
                                        padx=5)
        self.lbl_col_value_path.grid(row=0, column=1)

        # declare empty lists to store the widgets
        self.string_vars = []
        self.entries_groups = []
        self.entries_values = []
        self.delete_buttons = []

        # Button declaration
        self.add_seg_btn = Button(self.main_frame,
                                  text='+',
                                  command=self.add_segment)

        # Get groups and values from the backend, convert them to separate lists to access the indices
        # and keep them ordered
        self.orig_segment_dict = self.app.get_parameter('Segmentacion')
        self.groups = list(self.orig_segment_dict.keys())
        self.values = list(self.orig_segment_dict.values())

        # populate the frame for the first time
        self.populate_frame(self.groups, self.values)

        # add the new segment button to the grid
        self.pack_add_button()

        # sum the string values and add them to the total Label
        self.calc_sv_sum()

        center_window(self.master, self.screen_width, self.screen_height)

    def populate_frame(self, groups: list, values: list):
        """For every group in a dictionary, create a name-value pair of label-entry."""

        # declare empty lists to store the widgets
        self.string_vars = []
        self.entries_groups = []
        self.entries_values = []
        self.delete_buttons = []

        try:
            for widget in self.main_frame.winfo_children():
                widget.grid_forget()
        except AttributeError:
            pass

        # add name entries for each group to the grid
        # add value entries for each group to the grid
        for idx, (group, value) in enumerate(zip(groups, values)):
            # name entry, column 0
            e = Entry(self.main_frame)
            e.insert(0, group)
            e.grid(row=idx + 1,
                   column=0)
            self.entries_groups.append(e)

            # value entry, add a StringVar to each one to trace changes
            # the trace action is connected to the callback function
            self.string_vars.append(StringVar())
            e_value = Entry(self.main_frame,
                            textvariable=self.string_vars[-1])
            e_value.insert(0,
                           value * 100)
            e_value.grid(row=idx + 1,
                         column=1)
            self.entries_values.append(e_value)
            self.string_vars[-1].trace('w', self.callback)

            # add delete buttons to each of the segments
            btn = Button(self.main_frame,
                         text='-',
                         padx=5,
                         command=partial(self.remove_segment, idx))
            btn.grid(row=idx + 1,
                     column=2)
            self.delete_buttons.append(btn)

        # add the new group button to the grid
        self.pack_add_button()

        # sum the string values and add them to the total Label
        self.calc_sv_sum()

    def calc_sv_sum(self):
        """
        Sums all the Value Entries and adds the total to a label in the lower section of the window.
        """

        sv_values = [float(var.get()) if var.get() != "" else 0 for var in self.string_vars]
        self.lbl_total_val['text'] = f'{round(sum(sv_values), 2)} %'

        return round(sum(sv_values), 2)

    def callback(self, *args):
        """
        Each time a value Entry is changed, this function is called.
        """

        self.calc_sv_sum()

    def pack_add_button(self):
        """Add a button to the last row on the grid where a Value Entry exists."""

        # Place it in the grid, on the row equal to the length of the groups list
        self.add_seg_btn.grid(row=len(self.groups),
                              column=3)

    def remove_last_button(self):
        """Remove the last button on the grid."""

        self.add_seg_btn.grid_remove()

    def add_segment(self):
        """Add a segment to the list."""

        # Add a new default group to the groups and values lists
        self.groups.append('Nuevo')
        self.values.append(0)

        # Repopulate the frame
        self.populate_frame(self.groups, self.values)

    def remove_segment(self, row):

        self.groups.pop(row)
        self.values.pop(row)
        self.remove_last_button()
        self.populate_frame(self.groups, self.values)

    def save_selection(self):

        groups = [entry.get() for entry in self.entries_groups]
        sv_values = [float(var.get()) / 100 if var.get() != "" else 0 for var in self.string_vars]

        # If there are duplicated groups, show an error on a pop up window
        if len([item for item, count in collections.Counter(groups).items() if count > 1]) > 0:
            self.open_window_pop_up('Error', 'No puede haber grupos duplicados.')

        # If the total isn't 1, show an Error on a pop up window.
        elif int(self.calc_sv_sum()) != 100:
            self.open_window_pop_up('Error', 'El total debe sumar 100.')

        else:
            new_dict = dict(zip(groups, sv_values))

            self.app.set_parameter('Segmentacion', new_dict)

            self.close_window()

    def close_window(self, canceled=False):

        if canceled:
            self.canceled = True

        self.master.destroy()

    def open_window_pop_up(self, title, msg):
        self.new_win = Toplevel(self.master)
        WindowPopUpMessage(self.new_win,
                           title,
                           msg,
                           self.screen_width,
                           self.screen_height)
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)


class WindowPopUpMessage:
    def __init__(self, master, title: str, message: str, screen_width_, screen_height_):
        self.master = master
        self.master.title(title)
        self.master.iconbitmap(resource_path(r'res/icon.ico'))
        self.master.configure(background=bg_color)
        self.screen_width_ = screen_width_
        self.screen_height_ = screen_height_
        self.width = self.screen_width_ / 5
        self.height = self.screen_height_ / 4

        # --- LEVEL 0 ---
        # Frame with border that contains the message and the button.
        self.main_frame = Frame(self.master,
                                bg=bg_color,
                                padx=20,
                                pady=20,
                                borderwidth=2,
                                relief='groove')
        self.main_frame.pack(padx=20,
                             pady=20)

        # Boton para aceptar y cerrar
        self.btn_accept = Button(self.master,
                                 text='Aceptar',
                                 command=self.close_window)
        self.btn_accept.pack(padx=10, pady=10)

        # --- LEVEL 1 ---

        # Label para desplegar el mensaje
        self.message = Label(self.main_frame,
                             text=message,
                             bg=bg_color,
                             font=("Calibri Light", 12))
        self.message.pack(padx=20,
                          pady=20)

        center_window(self.master, self.screen_width_, self.screen_height_)

    def close_window(self):
        self.master.destroy()


class WindowPopUpMessageWithCancel:
    def __init__(self, master, title: str, message: str, screen_width_, screen_height_):
        self.master = master
        self.master.title(title)
        self.master.iconbitmap(resource_path(r'res/icon.ico'))
        self.master.configure(background=bg_color)
        self.screen_width_ = screen_width_
        self.screen_height_ = screen_height_
        self.width = self.screen_width_ / 5
        self.height = self.screen_height_ / 4
        self.canceled = True

        # --- LEVEL 0 ---

        # Frame with border that contains the message and Accept-Cancel Buttons
        self.main_frame = Frame(self.master,
                                bg=bg_color,
                                padx=20,
                                pady=20,
                                borderwidth=2,
                                relief='groove')
        self.main_frame.grid(row=0,
                             column=0,
                             columnspan=2,
                             padx=5,
                             pady=5)

        # Boton para aceptar y cerrar
        self.btn_accept = Button(self.master,
                                 text='Aceptar',
                                 command=lambda: self.close_window('Aceptar'))
        self.btn_accept.grid(row=1,
                             column=0,
                             pady=(0, 5))

        # Boton para aceptar y cerrar
        self.btn_cancel = Button(self.master,
                                 text='Cancelar',
                                 command=lambda: self.close_window('Cancelar'))
        self.btn_cancel.grid(row=1,
                             column=1,
                             pady=(0, 5))

        # --- LEVEL 1 ---
        # Label para desplegar el mensaje
        self.message = Label(self.main_frame,
                             text=message,
                             bg=bg_color,
                             padx=100,
                             pady=50,
                             font=("Calibri Light", 12))
        self.message.pack()

        center_window(self.master, self.screen_width_, self.screen_height_)

    def close_window(self, canceled):

        if canceled == 'Cancelar':
            self.canceled = True
        else:
            self.canceled = False

        self.master.destroy()


class ConfigModel:
    def __init__(self, master, app: Application, screen_width, screen_height, model: str):
        self.master = master
        self.master.iconbitmap(resource_path(r'res/icon.ico'))
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
        self.master.iconbitmap(resource_path(r'res/icon.ico'))
        self.width = width
        self.height = height
        self.queue_ = queue_
        self.thread_ = thread_

        # --- WIDGETS ---

        # listbox to print status
        self.listbox = Listbox(self.master,
                               width=150,
                               height=20)
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

            except self.queue_.empty:
                pass

    def close_window(self):
        self.master.destroy()


class WindowExportFile:
    def __init__(self, master, app: Application, screen_width, screen_height, process, **kwargs):
        self.master = master
        self.app = app
        self.master.iconbitmap(resource_path(r'res/icon.ico'))
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.width = screen_width / 2
        self.height = screen_height / 5
        self.thread_ = None
        self.process = process
        self.new_win = None

        if kwargs['df'].keys().__contains__('df'):
            self.df = kwargs['df']

        # configure columns
        self.master.grid_columnconfigure((0, 1), uniform='equal', weight=1)

        column_span = 1

        # Master frame
        self.frame_master = Frame(self.master, bg=bg_color, borderwidth=2, width=75, padx=10, pady=10)
        self.frame_master.pack(fill=BOTH, expand=True)

        # Button to change the path
        abs_path = os.path.dirname(os.path.abspath(self.app.file_paths_shelf.send_path('Demand')))
        self.btn_path = Button(self.frame_master,
                               text=abs_path,
                               bg=bg_color,
                               width=100,
                               command=self.browse_files)
        self.btn_path.grid(row=0, column=0, pady=5, sticky='WE',
                           columnspan=column_span)

        # Entry - Choose filename
        self.entry_output_file = Entry(self.frame_master)
        if process in ['Demand', 'Model']:
            file_name = self.app.config_shelf.send_parameter('File_name')
        elif process == 'Forecast':
            file_name = self.app.config_shelf.send_parameter('File_name_segmented')
        elif process in ['Demand_Agent', 'Model_Agent']:
            file_name = self.app.config_shelf.send_parameter('File_name_agent')
        else:
            file_name = self.app.config_shelf.send_parameter('File_name_metrics')
        today_date = datetime.datetime.today().strftime('%d-%m-%Y')
        self.entry_output_file.insert(END, file_name + f' {today_date}')
        self.entry_output_file.grid(row=1, column=0, pady=5, sticky='WE',
                                    columnspan=column_span)

        # Combobox to choose extension
        self.exts = {'Libro de Excel (*.xlsx)': '.xlsx',
                     'CSV UTF-8 (*.csv)': '.csv'}
        self.combobox_extensions = ttk.Combobox(self.frame_master, value=list(self.exts.keys()))
        self.combobox_extensions.current(0)
        self.combobox_extensions.grid(row=2, column=0, pady=5, sticky='WE',
                                      columnspan=column_span)

        # Button to accept
        self_btn_accept = Button(self.frame_master,
                                 text='Guardar',
                                 padx=10,
                                 command=self.call_backend_export)
        self_btn_accept.grid(row=2, column=column_span + 1, padx=10)

        chk_args = {'row': 3,
                    'column': 0,
                    'sticky': 'W'}

        self.chk_var = IntVar()
        self.chk_btn = Checkbutton(self.frame_master,
                                   bg=bg_color,
                                   text='Aplicar segmentación?',
                                   variable=self.chk_var)

        self.var_weight_fcst = IntVar()
        self.chkbtn_weight_fcst = Checkbutton(self.frame_master,
                                              bg=bg_color,
                                              text='Ponderar pronóstico?',
                                              variable=self.var_weight_fcst)

        if self.process == 'Forecast':
            self.chk_btn.grid(chk_args)

        if self.process == 'Demand_Agent':
            self.chkbtn_weight_fcst.grid(chk_args)

        # center window on screen
        center_window(self.master, self.screen_width, self.screen_height)

    def call_backend_export(self):

        ext_ = self.exts[self.combobox_extensions.get()]

        list_args_export = [self.btn_path['text'],
                            self.entry_output_file.get(),
                            ext_,
                            self.process]

        dict_kwargs_export = {'disaggregate': self.chk_var.get(),
                              'weighted_forecast': self.var_weight_fcst.get(),
                              'df': self.df}

        try:
            self.app.export_data(*list_args_export, **dict_kwargs_export)

            win_title = 'Mensaje'
            win_msg = 'Archivo exportado.'

        except ValueError:

            win_title = 'Advertencia'
            win_msg = 'Archivo exportado.'

        except PermissionError:

            win_title = 'Error'
            win_msg = 'El archivo está abierto.\nDebe cerrarlo antes de proceder.'

        new_win = Toplevel(self.master)
        WindowPopUpMessage(new_win,
                           win_title,
                           win_msg,
                           self.screen_width,
                           self.screen_height)
        new_win.grab_set()
        self.master.wait_window(new_win)

    def open_window_popup(self):
        """Open TopLevel to select path where the input files are located."""

        # new toplevel with master root, grab_set and wait_window to wait for the main screen to freeze until
        # this window is closed
        self.new_win = Toplevel(self.master)
        WindowSelectWorkPath(self.new_win, self.app, self.screen_width, self.screen_height)
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)

    def close_window(self):
        self.master.destroy()

    def browse_files(self):
        filename = filedialog.askdirectory(initialdir=self.app.file_paths_shelf.send_path('Working'),
                                           title="Seleccione un folder de destino.")

        if filename != '':
            # Change label contents
            self.btn_path.configure(text=filename)


class WindowSegmentOptions:
    def __init__(self, master, app:Application, screen_width, screen_height):
        self.master = master
        self.app = app
        self.master.title("Segmentación de pronóstico")
        self.master.configure(background=bg_color)
        self.master.iconbitmap(resource_path(r'res/icon.ico'))
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.width = self.screen_width / 2
        self.height = self.screen_height / 5

        # Container Frame for the paths
        self.lbl_frame_segments = LabelFrame(self.master,
                                             text='Escoja un método de segmentación:',
                                             bg=bg_color,
                                             width=screen_width / 5,
                                             padx=10,
                                             pady=10)
        self.lbl_frame_segments.grid(padx=10,
                                     pady=10,
                                     row=0,
                                     column=0,
                                     columnspan=2)

        # accept and cancel buttons
        self.btn_accept = Button(self.master,
                                 text='Aceptar',
                                 command=self.accept_callback)
        self.btn_accept.grid(pady=10, row=2, column=0)

        self.btn_cancel = Button(self.master,
                                 text='Cancelar',
                                 command=self.close_window)
        self.btn_cancel.grid(pady=10, row=2, column=1)

        # Combobox to choose segmentation method
        cbx_options = ['Usar pronóstico ponderado',
                       'Método manual']
        self.cbx_segment_options = ttk.Combobox(self.lbl_frame_segments,
                                                value=cbx_options)
        self.cbx_segment_options.current(0)
        self.cbx_segment_options.grid(row=2,
                                      column=0,
                                      pady=5,
                                      sticky='WE')

    def close_window(self):
        self.master.destroy()

    def accept_callback(self):

        user_selection = self.cbx_segment_options.get()

        # Declare a new Toplevel
        # grab_set and wait_window to wait for the main screen to freeze until this window is closed
        self.new_win = Toplevel(self.master)

        if user_selection == 'Usar pronóstico ponderado':
            win_obj = WindowSelectPath(self.new_win,
                                       self.app,
                                       self.screen_width,
                                       self.screen_height,
                                       'Pronóstico ponderado',
                                       'Weighted_Forecast')
        else:
            win_obj = WindowSegmentManual(self.new_win,
                                          self.app,
                                          self.screen_width,
                                          self.screen_height)

        self.new_win.grab_set()
        self.master.wait_window(self.new_win)

        if win_obj.canceled:
            self.close_window()

        if user_selection == 'Usar pronóstico ponderado':
            disaggregation_method = 'Weighted_Forecast'
        else:
            disaggregation_method = 'Disaggregate_Dict'

        df_disaggregated = self.app.disaggregate_forecast_workflow(disaggregation_method)

        new_win_export = Toplevel(self.master)
        win_obj = WindowExportFile(new_win_export, self.app, self.screen_width, self.screen_height, 'Forecast',
                                   df=df_disaggregated)
        new_win_export.grab_set()
        new_win_export.wait_window()

class WindowLoading:
    def __init__(self, master, thread, screen_width, screen_height):
        self.master = master
        self.thread = thread
        self.master.iconbitmap(resource_path(r'res/icon.ico'))
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.width = screen_width / 2
        self.height = screen_height / 5
        self.master.configure(background=brand_green)

        main_frame = Frame(self.master, bg=brand_green, padx=100, pady=100)
        main_frame.pack()

        loading_label = Label(main_frame,
                              text='Cargando información',
                              bg=brand_green,
                              font=("Calibri Light", 28),
                              fg='white')
        loading_label.pack()

        loading_label_2 = Label(main_frame,
                                text='Por favor, espere.',
                                bg=brand_green,
                                font=("Calibri Light", 18),
                                fg='white')
        loading_label_2.pack()

        center_window(self.master, self.screen_width, self.screen_height)

        self.periodic_call()

    def close_window(self):
        self.master.destroy()

    def periodic_call(self):

        if self.thread.is_alive():
            self.master.after(100, self.periodic_call)

        else:
            self.close_window()


class ThreadedClient(threading.Thread):
    def __init__(self, queue_, application: Application, process):
        threading.Thread.__init__(self)
        self.queue = queue_
        self.application = application
        self.process = process
        self.daemon = True

    def run(self):
        self.application.fit_forecast_evaluate_pipeline(self.process, self.queue)


class ThreadedClient_exp(threading.Thread):

    def __init__(self, queue_, func, *args, **kwargs):
        threading.Thread.__init__(self)
        self.queue_ = queue_
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        self.func(*self.args[0], **self.kwargs)


if __name__ == '__main__':
    install_path = os.path.join(os.path.expanduser("~"), r'AppData\Roaming\Modulo_Demanda')

    root = Tk()
    root.iconbitmap(resource_path(r'res/icon.ico'))
    root.state('zoomed')
    Main(root, install_path)
    root.mainloop()
