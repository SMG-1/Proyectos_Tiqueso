import collections
import datetime
import os
import queue
import threading
from tkinter import *
from tkinter import filedialog
from tkinter import ttk
from functools import partial

import pandas as pd
import pandastable
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg)
from matplotlib.figure import Figure
from win32api import GetSystemMetrics

from back_end import Application
from back_end import ConfigShelf

plt.style.use('ggplot')
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

        # top and bottom frame heights
        self.top_frame_height = int(self.height / 2.5)
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
        self.figure_data = None
        self.figure_model = None
        self.ax_data = None
        self.ax_model = None
        self.ax_2 = None
        self.data_plot = None
        self.model_plot = None
        self.pd_table = None
        self.model_ready = False
        self.active_process = 'Demand'

        # --- DROPDOWN MENU DECLARATION - TOOLBAR ---
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
                                  # command=self.open_window_export) # todo: temporary
                                  command=self.open_window_segment)

        # commands for the model sub menu
        sub_menu_model.add_command(label='Optimizar modelo',
                                   command=self.run_optimizer)

        # sub menu cascade
        main_menu.add_cascade(label='Archivo', menu=sub_menu_file)
        main_menu.add_cascade(label='Configuración', menu=sub_menu_config)
        main_menu.add_cascade(label='Modelo', menu=sub_menu_model)

        # configure menu in toplevel
        self.master.config(menu=main_menu)

        # --- Level 0 --- Contains the Paned Window, the Tree View and the Main Frame

        # Frame for top control buttons
        self.button_control_frame = LabelFrame(self.master, bg=bg_color)
        self.button_control_frame.pack(fill=X)

        # Button for a new template
        self.img_new = PhotoImage(file=r"C:\icons\new.png")
        self.btn_new = Button(self.button_control_frame, text='Nuevo', image=self.img_new, compound='left',
                              bg=bg_color, width=75, padx=10, command=self.clear_gui)
        self.btn_new.pack(side=LEFT)

        # Button to open a file
        self.img_open = PhotoImage(file=r"C:\icons\open.png")
        self.btn_open = Button(self.button_control_frame, text='Abrir', image=self.img_open, compound='left',
                               bg=bg_color, width=75, padx=10, command=self.open_window_select_work_path)
        self.btn_open.pack(side=LEFT)

        # Button to export files
        self.img_save = PhotoImage(file=r"C:\icons\save.png")
        self.btn_save = Button(self.button_control_frame, text='Exportar', image=self.img_save, compound='left',
                               bg=bg_color, width=75, padx=10, command=self.open_window_export)
        self.btn_save.pack(side=LEFT)

        # Button to refresh the views
        self.img_refresh = PhotoImage(file=r"C:\icons\refresh.png")
        self.btn_refresh = Button(self.button_control_frame, text='Refrescar', image=self.img_refresh, compound='left',
                                  bg=bg_color, width=75, padx=10, command=lambda: self.refresh_views(0))
        self.btn_refresh.pack(side=LEFT)

        # Button to run a process
        self.img_run = PhotoImage(file=r"C:\icons\run.png")
        self.btn_run = Button(self.button_control_frame, text='Ejecutar', image=self.img_run, compound='left',
                              bg=bg_color, width=75, padx=10, command=self.run_optimizer)
        self.btn_run.pack(side=LEFT)

        # Horizon Label
        self.lbl_horizon = Label(self.button_control_frame, text='Horizonte:', bg=bg_color)
        self.lbl_horizon.pack(side=LEFT, padx=(10, 0))

        # Spinbox to select the amount of periods to forecast in the future
        saved_periods_fwd = self.back_end.config_shelf.send_parameter('periods_fwd')
        var = DoubleVar(value=int(saved_periods_fwd))
        self.spinbox_periods = Spinbox(self.button_control_frame, from_=0, to=500, textvariable=var)
        self.spinbox_periods.pack(side=LEFT)

        # Horizon label
        self.lbl_days = Label(self.button_control_frame, text='días', bg=bg_color)
        self.lbl_days.pack(side=LEFT)

        # Paned Window that contains the tree view and a master frame
        self.main_paned = PanedWindow(self.master,
                                      width=self.width,
                                      height=self.height,
                                      orient=HORIZONTAL)

        # Tree View declaration, double click is binded to the tree view
        self.tree_view = ttk.Treeview(self.master)
        self.tree_view.bind("<Double-1>", self.refresh_views)  # Todo: Possible duplicate?

        # declare columns for the Tree View
        self.tree_view['columns'] = '1'
        self.tree_view.column('1', anchor='w')

        # declare headings for the Tree View
        self.tree_view['show'] = 'headings'
        self.tree_view.heading('1', text='Producto', anchor='w')

        # Main Frame declaration, on the right of the tree view, inside the Paned Window
        self.main_frame = Frame(self.main_paned,
                                width=self.width,
                                height=self.height,
                                bg=bg_color)

        # Add the tree view and te main frame to the Paned Window, and pack it to fill the screen
        self.main_paned.add(self.tree_view)
        self.main_paned.add(self.main_frame)
        self.main_paned.pack(fill=BOTH, expand=1)

        # --- Level 1 --- Top and Bottom Frames

        # Top Frame that covers the top half of the screen
        # Contains the Table Frame
        self.top_frame = Frame(self.main_frame,
                               width=self.table_width,
                               height=self.top_frame_height,
                               bg=bg_color)

        # Bottom Frame that contains the bottom half of the screen
        # Contains Plot Frame to the left and Config Frame to the right
        self.bottom_frame = Frame(self.main_frame,
                                  width=self.table_width,
                                  height=self.bottom_frame_height,
                                  bg=bg_color)

        # Pack the Top and Bottom Frames
        self.pack_to_main_frame()

        # --- Level 2 --- Table Frame, Notebook Frame, Config Frame

        # Table Frame that contains the pandastable
        # Packed to the Top Frame
        self.frame_table = Frame(self.top_frame,
                                 width=self.table_width,
                                 height=self.top_frame_height,
                                 bg=bg_color)
        self.frame_table.pack(fill='x',
                              expand=True,
                              anchor='n')

        # Frame that contains the Notebook
        self.frame_notebook = Frame(self.bottom_frame,
                                    width=self.plot_width,
                                    height=self.bottom_frame_height,
                                    bg=bg_color)
        self.frame_notebook.pack(fill='both', expand=True, side=LEFT)

        # Notebook contains the Raw Data plot, the Model plot and the Metrics Tab
        # User switches between tabs as needed
        # Model and Metrics tabs default to disabled, as user needs to run the optimizer before seeing data there
        self.notebook_plotting = ttk.Notebook(self.frame_notebook)
        self.tab_data_plot = ttk.Frame(self.notebook_plotting)
        self.tab_model_plot = ttk.Frame(self.notebook_plotting)
        self.tab_metrics = ttk.Frame(self.notebook_plotting)
        self.notebook_plotting.add(self.tab_data_plot, text='Datos')
        self.notebook_plotting.add(self.tab_model_plot, text='Modelo', state='disabled')
        self.notebook_plotting.add(self.tab_metrics, text='Métricas', state='disabled')
        self.notebook_plotting.pack()

        # Metrics Frame, contains three columns
        # Metric Name | Metric Value | Metric Description
        self.metrics_frame = Frame(self.tab_metrics)
        self.metrics_frame.pack(fill=BOTH, expand=True)
        self.metrics_frame.columnconfigure((0, 1, 2), uniform='equal', weight=1)

        # Config Frame, contains several configuration widgets
        self.frame_config = LabelFrame(self.bottom_frame,
                                       text='Configuración',
                                       width=self.config_width,
                                       height=self.bottom_frame_height,
                                       bg=bg_color)
        self.frame_config.pack(fill='both', expand=True, side=RIGHT)

        # --- Level 3 --- Time Granularity Combobox, N Periods Entry, Refresh Views Button

        # Label for the combobox
        Label(self.frame_config, text='Nivel de detalle del tiempo:', bg=bg_color).pack(padx=10, anchor='w')

        # Combobox: Changes time frequency to daily, weekly, monthly
        # This option changes the table and plot LOD
        freqs_ = ['Diario', 'Semanal', 'Mensual']
        self.combobox_time_freq = ttk.Combobox(self.frame_config, value=freqs_)
        self.combobox_time_freq.current(0)
        self.combobox_time_freq.bind("<<ComboboxSelected>>", self.refresh_views)
        self.combobox_time_freq.pack(padx=10, pady=(0, 10), anchor='w')

        # Label for the entry
        Label(self.frame_config, text='Cantidad de períodos a pronosticar:', bg=bg_color).pack(padx=10, anchor='w')

        # Entry: change amount of periods forward to forecast
        saved_periods_fwd = self.back_end.config_shelf.send_parameter('periods_fwd')
        self.entry_periods_fwd = Entry(self.frame_config, width=15)
        self.entry_periods_fwd.insert(END, saved_periods_fwd)
        self.entry_periods_fwd.pack(padx=10, pady=(0, 10), anchor='w')

        # Button: Refresh the views
        self.btn_refresh_view = Button(self.frame_config,
                                       text='Refrescar vistas',
                                       padx=10,
                                       command=lambda: self.refresh_views(0))
        self.btn_refresh_view.pack(side=BOTTOM, pady=10)

        # Automatic load on boot, uses the last known Mode setting, Demand or Forecast
        # Loads data accordingly
        process_ = self.back_end.config_shelf.send_parameter('Mode')
        # process_= self.active_process # todo: temporary
        self.update_gui(process_)

        center_window(self.master, self.screen_width, self.screen_height)

    def pack_to_main_frame(self):

        # Pack the Top Frame
        # Fill the x axis
        self.top_frame.pack(fill='x',
                            expand=True,
                            anchor='n')

        # Pack the Bottom Frame, fill the x axis
        self.bottom_frame.pack(fill='x',
                               expand=True,
                               anchor='s')

        try:
            self.temp_label.pack_forget()
        except AttributeError:
            pass

    def populate_tree(self, item_list):
        """
        Insert row for every item in the list.
        Bind the double click action to the refresh_views function."""

        # populate the tree view with the items inside the item_list
        for i in item_list:
            self.tree_view.insert("", "end", text=i, values=(i,))

        # bind the refresh_views function to a double click on the tree view
        self.tree_view.bind("<Double-1>", self.refresh_views)

    def clear_tree(self):
        """Clear information from the tree view."""

        self.tree_view.delete(*self.tree_view.get_children())

    def get_tree_selection(self):
        """Get selected item from the tree view, if not available, returns DEFAULT."""

        try:
            item = self.tree_view.selection()[0]
            return self.tree_view.item(item, "text")
        except IndexError:
            return 'DEFAULT'

    def clear_gui(self):
        """Function to clear data from the back end and the GUI."""

        # Change the model ready status
        if self.model_ready:
            self.model_ready = False

        # Disable the model tabs
        self.notebook_plotting.tab(self.tab_model_plot, state='disabled')
        self.notebook_plotting.tab(self.tab_metrics, state='disabled')

        # Clear information from the tree view
        self.clear_tree()

        # Unpack the top and bottom frames
        # Unpack the temporary label to avoid having more than one temporary labels active, if the user clicks New
        # more than one time.
        try:
            self.top_frame.pack_forget()
            self.bottom_frame.pack_forget()
            self.temp_label.pack_forget()

        except AttributeError:
            pass

        # Add a Label telling user to load files on the Top and Bottom Frames
        temp_text = 'Cargue archivos para ver algo aquí.'
        self.temp_label = Label(self.main_frame, text=temp_text)
        self.temp_label.pack(fill=BOTH, expand=True)

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

        # If the plot type is Demand or Forecast:
        # Data is packed into the data plot widget.
        if plot_type in ['Demand', 'Forecast']:
            if self.data_plot is not None:
                self.data_plot.get_tk_widget().destroy()

            self.figure_data = Figure(figsize=(self.plot_width / dpi, self.bottom_frame_height / dpi), dpi=dpi)
            self.ax_data = self.figure_data.add_subplot(1, 1, 1)
            self.data_plot = FigureCanvasTkAgg(self.figure_data, self.tab_data_plot)
            self.data_plot.get_tk_widget().pack(side=LEFT, fill=BOTH, expand=1)

        # If the plot type is Model:
        # Data is packed into the model plot widget.
        else:
            if self.model_plot is not None:
                self.model_plot.get_tk_widget().destroy()

            self.figure_model = Figure(figsize=(self.plot_width / dpi, self.bottom_frame_height / dpi), dpi=dpi)
            self.ax_model = self.figure_model.add_subplot(1, 1, 1)
            self.model_plot = FigureCanvasTkAgg(self.figure_model, self.tab_model_plot)
            self.model_plot.get_tk_widget().pack(side=LEFT, fill=BOTH, expand=1)

        # Reset the index of the data frame to use the date as an axis.
        df = df.reset_index()

        # Drop the string formatted column.
        # If it doesn't exist, skip this step.
        try:
            df.drop(columns=['Fecha_strf'], inplace=True)
        except KeyError:
            pass

        # If the plot type is Demand or Forecast, use a single axis plot.
        # Names change based on the plot type.
        if plot_type in ['Demand', 'Forecast']:
            if plot_type == 'Demand':
                y_name = 'Demanda'
                plot_title = 'Demanda Real'
            else:
                y_name = plot_title = 'Pronóstico'

            df.plot(x='Fecha', y=y_name, legend=False, ax=self.ax_data)
            self.ax_data.set_ylabel('Cantidad (kg)')
            self.ax_data.set_title(plot_title)

        # If the plot type is Model, use a triple axis plot.
        if plot_type == 'Model':
            col_names = ['Fecha', 'Demanda', 'Modelo', 'Pronóstico']
            df.columns = col_names
            df.plot(x=col_names[0], y=col_names[1], color='b', ax=self.ax_model)
            df.plot(x=col_names[0], y=col_names[2], color='r', ax=self.ax_model)
            df.plot(x=col_names[0], y=col_names[3], color='g', ax=self.ax_model)
            self.ax_model.set_ylabel('Cantidad (kg)')
            self.ax_model.set_title('Demanda Real y Pronóstico')

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
        if table_type in ['Demand', 'Forecast']:
            try:
                df.drop(columns=['Codigo', 'Nombre'], inplace=True)
            # when the models havent been trained, the df only contains the values column
            except KeyError:
                pass

        # If the table type is Model fill null values with "-" and round numbers to two places.
        elif table_type == 'Model':
            df = df.fillna('-')
            df = df.round(2)

        # Transpose the table.
        df = df.T

        # Destroy widgets inside the Table Frame before packing the new one.
        for widget in self.frame_table.winfo_children():
            widget.destroy()

        # Declare the pandas table widget.
        #
        self.pd_table = pandastable.Table(self.frame_table,
                                          dataframe=df,
                                          showtoolbar=False,
                                          showstatusbar=True)

        # Show the table.
        self.pd_table.showindex = True
        self.pd_table.autoResizeColumns()
        self.pd_table.show()
        self.pd_table.redraw()

    def show_plot_and_table(self, sku, process, event):
        """
        Call the create figure function with the data of the passed sku parameter.

        sku: name of the SKU or DEFAULT, if DEFAULT, shows the currently selected SKU on the tree view
        plot_type: Demand plots the raw data, Forecast shows the fitted values and the forecast.
        """

        # If the process parameter is Demand or Forecast, use the segmented data sets from the backend.
        if process in ['Demand', 'Forecast']:
            sep_df_dict = self.back_end.segmented_data_sets
        # If the process parameter is Model, use the fitted datasets from the backend.
        else:
            sep_df_dict = self.back_end.dict_fitted_dfs

        # Get selected data frame based on the sku parameter.
        # If sku is DEFAULT use the first item on the tree view.
        if sku == 'DEFAULT':
            temp_sku = list(sep_df_dict.keys())[0]
            df = sep_df_dict[temp_sku]
        else:
            df = sep_df_dict[sku]

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
        df['Fecha_strf'] = df['Fecha'].dt.strftime(strf_format)
        df = df.set_index('Fecha')

        # Show the data on the table.
        self.show_table(df, process)

        # call function to show plot on the bottom frame
        self.create_fig(df, process)

    def update_periods_fwd(self):
        """
        Check if the user changed the periods forward parameter.
        If changed, update the parameter on the backend."""

        # get the actual value from the spinbox
        new_periods_fwd = int(self.spinbox_periods.get())

        # if the value is different from the stored one, change it on the backend
        if new_periods_fwd != self.back_end.config_shelf.send_parameter('periods_fwd'):
            self.back_end.config_shelf.write_to_shelf('periods_fwd', new_periods_fwd)

    def run_optimizer(self):
        """Spawns the optimizer thread to train the models based on the actual data."""

        # update the periods_fwd parameter in the back end
        self.update_periods_fwd()

        # spawn the thread which finds the best model
        # uses a thread to avoid freezing the program
        self.spawn_thread('Optimizador')

    def spawn_thread(self, process):
        """Create ThreadedClient class and pass it to a periodic call function."""

        if process == 'Optimizador':
            # self.btn_run_optimizer.config(state='disabled')
            queue_ = queue.Queue()

            thread = ThreadedClient(queue_, self.back_end, process)
            thread.start()

            self.new_win = Toplevel(self.master)
            self.new_win.overrideredirect(1)  # todo> temporary
            WindowTraining(self.new_win, self.back_end, queue_, thread, self.screen_width,
                           self.screen_height)
            self.new_win.grab_set()
            self.master.wait_window(self.new_win)

            self.notebook_plotting.tab(self.tab_model_plot, state='normal')

            self.show_plot_and_table('DEFAULT', 'Model', 0)

            # enable the metrics tab
            self.update_metrics('DEFAULT')
            self.model_ready = True

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
        """Refresh the views on the GUI based on the tree view selection."""

        # If the model is ready:
        # 1. Update the periods forward on the back end.
        # 2. Refresh predictions with the new periods forward parameter.
        if self.model_ready:
            self.update_periods_fwd()
            self.back_end.refresh_predictions()

        # Get the selected item from the tree view.
        item_name = self.get_tree_selection()

        # Populate the plot and the table based on the selected item.
        self.show_plot_and_table(item_name, self.active_process, event)

        # If the fitted datasets from the back end aren't empty.
        # Show the Model plot and table and update the metrics.
        if self.back_end.dict_fitted_dfs != {}:
            self.show_plot_and_table(item_name, 'Model', event)
            self.update_metrics(item_name)

    def update_metrics(self, sku):

        # change state of the metrics tab of the notebook
        self.notebook_plotting.tab(self.tab_metrics, state='normal')

        # get the model data frames
        sep_df_dict = self.back_end.dict_fitted_dfs

        # if sku parameter is default use the first key of the dictionary
        # which represents the first data frame
        if sku == 'DEFAULT':
            sku = list(sep_df_dict.keys())[0]

        # get the metrics list from the metrics dictionary
        metrics_dict = self.back_end.dict_metrics[sku]

        # position the metric on a grid in the metrics tab
        # first column is the name of the metric
        # second column is the rounded value of the metric
        # third column is the description of the metric
        for idx, (metric, value) in enumerate(metrics_dict.items()):
            Label(self.metrics_frame, text=metric, padx=10).grid(row=idx,
                                                                 column=0,
                                                                 padx=10,
                                                                 pady=5)

            rounded_val = round(float(value), 2)
            Label(self.metrics_frame, text=rounded_val, padx=10).grid(row=idx,
                                                                      column=1,
                                                                      padx=10,
                                                                      pady=5)

            metric_desc = self.back_end.dict_metric_desc[metric]
            Label(self.metrics_frame, text=metric_desc, padx=10, wraplength=250).grid(row=idx,
                                                                                      column=2,
                                                                                      padx=10,
                                                                                      pady=5)

    def update_gui(self, process_: str):
        """
        Update the GUI based on the process parameter.
        Read the data and separate it into subsets on the backend based on the process_ parameter.
        Clear the tree view and populate it with the subset keys.
        Call the show_plot_and_table function to show the loaded data on the plot and the table.
        """

        try:
            # the path to the data has been validated, so the data can be separated into several datasets
            # process must be specified to read the correct filepath
            self.back_end.create_segmented_data(process_)

            # clear tree view
            self.clear_tree()

            # Pack Top and Bottom Frames to the Main Frame
            self.pack_to_main_frame()

            # get items from the segmented data sets dictionary to populate the tree view
            item_list = list(self.back_end.segmented_data_sets.keys())
            self.populate_tree(item_list)

            # call function to update the plot and the table on the GUI
            self.show_plot_and_table('DEFAULT', process_, 0)

        # if the segmented datasets haven't been created, clear the GUI
        except (KeyError, ValueError):
            self.clear_gui()

    def open_window_select_work_path(self):
        """Open TopLevel to select path where the input files are located."""

        # new toplevel with master root, grab_set and wait_window to wait for the main screen to freeze until
        # this window is closed

        self.new_win = Toplevel(self.master)
        win_obj = WindowSelectWorkPath(self.new_win, self.back_end, self.screen_width, self.screen_height)
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)

        if win_obj.carga_exitosa:
            print('Carga exitosa.')

            # If the user loads new data, a new model must be trained.
            if self.model_ready:
                self.model_ready = False
                self.notebook_plotting.add(self.tab_model_plot, state='disabled')
                self.notebook_plotting.add(self.tab_metrics, state='disabled')

        # update the GUI, the layout changes based on the process
        self.active_process = win_obj.process
        self.update_gui(win_obj.process)

    def open_window_export(self):

        process_ = self.back_end.config_shelf.send_parameter('Mode')

        self.new_win = Toplevel(self.master)
        WindowExportFile(self.new_win, self.back_end, self.screen_width, self.screen_height, process_)
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)

    def open_window_segment(self):
        self.new_win = Toplevel(self.master)
        WindowSegmentOptions(self.new_win, self.back_end, self.screen_width, self.screen_height)
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
        self.carga_exitosa = False
        self.process = None

        # --- LEVEL 0 ---

        # Container Frame
        self.main_frame = LabelFrame(self.master,
                                     text='Escoja un directorio:',
                                     bg=bg_color,
                                     width=screen_width_ / 5,
                                     padx=10,
                                     pady=10)
        self.main_frame.grid(padx=10,
                             pady=10,
                             row=0,
                             column=0,
                             columnspan=2)

        # accept and cancel buttons
        self.btn_accept = Button(self.master,
                                 text='Aceptar',
                                 command=self.save_selection)
        self.btn_accept.grid(pady=10, row=1, column=0)

        self.btn_cancel = Button(self.master,
                                 text='Cancelar',
                                 command=self.close_window)
        self.btn_cancel.grid(pady=10, row=1, column=1)

        # --- NIVEL 1 ---

        #  ROW 0: LABEL THAT SHOWS THE PATH

        # Name Label, first column
        self.lbl_name_path = Label(self.main_frame,
                                   text='Directorio:',
                                   bg=bg_color,
                                   padx=5)
        self.lbl_name_path.grid(row=0,
                                column=0,
                                sticky='W')

        # Path Label, second column
        self.last_process = self.app.config_shelf.send_parameter('Mode')
        self.lbl_path = Label(self.main_frame,
                              text=self.app.get_path(self.last_process),
                              bg=bg_color,
                              pady=10,
                              borderwidth=2,
                              width=150,
                              relief="groove",
                              anchor='w')
        self.lbl_path.grid(row=0,
                           column=1,
                           padx=10,
                           pady=10,
                           sticky='WE')

        # Browse Button, third column, to open the browse files window
        self.btn_browse = Button(self.main_frame,
                                 text='...',
                                 command=lambda: self.browse_files('Demand'))
        self.btn_browse.grid(row=0,
                             column=2,
                             padx=10,
                             pady=10,
                             sticky='WE')

        # ROW 1: COMBOBOX THAT SHOWS THE FILE TYPE

        # Name Label, first column
        self.lbl_name_file_type = Label(self.main_frame,
                                        text='Archivo:',
                                        bg=bg_color,
                                        padx=5)
        self.lbl_name_file_type.grid(row=1,
                                     column=0,
                                     pady=10,
                                     sticky='W')

        # Selection Combobox, second column,  to choose which type of file to open, demand or forecast
        file_types = ['Demanda',
                      'Pronóstico']
        self.cbx_file_type = ttk.Combobox(self.main_frame,
                                          value=file_types)

        if self.last_process == 'Forecast':
            self.cbx_file_type.current(1)
        else:
            self.cbx_file_type.current(0)

        self.cbx_file_type.bind("<<ComboboxSelected>>", self.cbx_callback)
        self.cbx_file_type.grid(row=1,
                                column=1,
                                columnspan=2,
                                padx=10,
                                pady=10,
                                sticky='WE')

        # NEXT WIDGETS ARE NOT PACKED BY DEFAULT

        # ROW 2: CHECKBUTTON TO APPLY BOM OR NOT

        # Name Label
        self.lbl_name_cb_bom = Label(self.main_frame,
                                     text='Aplicar recetas?',
                                     bg=bg_color,
                                     padx=5,
                                     anchor='w')

        # Checkbutton to control the BOM Explosion parameter
        self.cb_bom_state = IntVar()
        self.cb_bom = Checkbutton(self.main_frame, variable=self.cb_bom_state, bg='white',
                                  command=self.cb_callback)

        # ROW 3:  LABEL THAT SHOWS THE PATH TO BILL OF MATERIALS

        # Name Label
        self.lbl_name_path_bom = Label(self.main_frame,
                                       text='Directorio de recetas:',
                                       bg=bg_color,
                                       padx=5)

        # BOM Path Label
        self.lbl_path_bom = Label(self.main_frame,
                                  text=self.app.get_path('BOM'),
                                  bg=bg_color,
                                  pady=10,
                                  borderwidth=2,
                                  width=150,
                                  relief="groove",
                                  anchor=W)

        # if Demand is selected, add the demand section to grid upon initializing
        if self.cbx_file_type.get() == 'Demanda':

            self.add_demand_section_to_grid()

            # if the BOM explosion parameter on the backend is true, select the checkbutton
            # and add the BOM section to the grid
            if self.app.config_shelf.send_parameter('BOM_Explosion'):
                self.cb_bom.select()
                self.add_bom_section_to_grid()
            else:
                self.cb_bom.deselect()

        center_window(self.master, self.screen_width, self.screen_height)

    def close_window(self):
        self.master.destroy()

    def browse_files(self, label_name):

        # get the last path that the user selected
        ini_dir_ = self.app.get_path('Temp')

        # call function to open a file selection window
        filepath, filename = browse_files_master(ini_dir_)

        # set the selected path as the new Temp path
        self.app.set_path('Temp', os.path.dirname(os.path.abspath(filename)))

        # change the text content of the label
        if label_name == 'Demand':
            self.lbl_path.configure(text=filename)

        elif label_name == 'BOM':
            self.lbl_path_bom.configure(text=filename)

    def save_selection(self):
        """"""

        # open PopUp warning if the Path Label is empty
        if self.lbl_path['text'] == '':
            self.open_window_pop_up('Error', 'Debe seleccionar un directorio válido.')
            # raise ValueError('Debe seleccionar un directorio válido.')

        if self.cbx_file_type.get() == 'Demanda':
            self.process = process = 'Demand'
        else:
            self.process = process = 'Forecast'

        # validate the path before saving it to the backend
        curr_path = self.lbl_path['text']
        if validate_path(curr_path, is_file=True):

            # set selected path to the Demand key of the paths shelf
            self.app.set_path(process, curr_path)

            if process == 'Demand':
                # set the selected parameter to the BOM_Explosion key of the parameters shelf
                self.app.set_parameter('BOM_Explosion', bool(self.cb_bom_state.get()))

                if bool(self.cb_bom_state.get()):
                    # set selected bom path to the BOM key of the paths shelf
                    self.app.set_path('BOM', self.lbl_path_bom['text'])

            # create separate datasets for each of the unique products
            try:
                self.app.create_segmented_data(process)
                self.open_window_pop_up('Mensaje', 'Archivos cargados.')
                self.carga_exitosa = True
                self.app.set_parameter('Mode', process)
                self.close_window()

            except ValueError as e:
                self.open_window_pop_up('Error', e)

            except PermissionError as e:
                self.open_window_pop_up('Error', 'Debe cerrar el archivo antes de proceder:\n' + e.filename)

        else:
            self.open_window_pop_up('Error', 'El directorio indicado es inválido.')

    def open_window_pop_up(self, title, msg):

        # open new TopLevel as a popup window
        self.new_win = Toplevel(self.master)
        WindowPopUpMessage(self.new_win, title, msg, self.screen_width, self.screen_height)

        # freeze master window until user closes the pop up
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)

    def add_demand_section_to_grid(self):
        """If the combobox == Demand, add this section to the grid."""

        self.lbl_name_cb_bom.grid(row=2, column=0)
        self.cb_bom.grid(row=2, column=1)

    def remove_section_from_grid(self, widgets_list: list):
        """Remove widget list from the grid."""
        for widget in widgets_list:
            widget.grid_forget()

    def add_bom_section_to_grid(self):

        self.lbl_name_path_bom.grid(row=3, column=0)
        self.lbl_path_bom.grid(row=3, column=1, padx=10, pady=10)

        self.btn_browse_bom = Button(self.main_frame,
                                     text='...',
                                     command=lambda: self.browse_files('BOM'))
        self.btn_browse_bom.grid(row=3, column=2)

    def cbx_callback(self, event):
        if self.cbx_file_type.get() == 'Demanda':
            self.add_demand_section_to_grid()

            if self.cb_bom_state.get():
                self.add_bom_section_to_grid()

        else:
            self.remove_section_from_grid([self.lbl_name_cb_bom, self.cb_bom, self.lbl_name_path_bom,
                                           self.lbl_path_bom, self.btn_browse_bom])

    def cb_callback(self):
        if self.cb_bom_state.get():
            self.add_bom_section_to_grid()
        else:
            self.remove_section_from_grid([self.lbl_name_path_bom, self.lbl_path_bom, self.btn_browse_bom])


class WindowSegmentOptions:

    def __init__(self, master, app: Application, screen_width_, screen_height_):
        self.master = master
        self.master.title("Carga de pronóstico")
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
                                 command=self.close_window)
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
                widget.destroy()
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
        self.lbl_total_val['text'] = round(sum(sv_values), 2)

    def callback(self, *args):
        """
        Each time a value Entry is changed, this function is called.
        """

        self.calc_sv_sum()

    def pack_add_button(self):
        """Add a button to the last row on the grid where a Value Entry exists."""

        # Button declaration
        self.add_seg_btn = Button(self.main_frame,
                                  text='+',
                                  command=self.add_segment)

        # Place it in the grid, on the row equal to the length of the groups list
        self.add_seg_btn.grid(row=len(self.groups),
                              column=3)

    def remove_last_button(self):
        """Remove the last button on the grid."""

        self.add_seg_btn.destroy()

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

        # If there are duplicated groups, show an error on a pop up window
        if len([item for item, count in collections.Counter(self.groups).items() if count > 1])> 0:
            self.open_window_pop_up('Error', 'No puede haber grupos duplicados.')

        # If the total isn't 1, show an Error on a pop up window.
        elif round(sum(self.values), 2) != 1:
            self.open_window_pop_up('Error', 'El total debe sumar 100.')

        else:
            new_dict = dict(zip(self.groups, self.values))

            self.app.set_parameter('Segmentacion', new_dict)

            self.close_window()

    def close_window(self):
        self.master.destroy()

    def open_window_pop_up(self, title, msg):
        self.new_win = Toplevel(self.master)
        WindowPopUpMessage(self.new_win, title, msg, self.screen_width, self.screen_height)
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
    def __init__(self, master, app: Application, screen_width, screen_height, process):
        self.master = master
        self.app = app
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.width = screen_width / 2
        self.height = screen_height / 5
        self.thread_ = None
        self.process = process

        # configure columns
        self.master.grid_columnconfigure((0, 1), uniform='equal', weight=1)

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
        self.btn_path.grid(row=0, column=0, pady=5, sticky='WE')

        self.entry_output_file = Entry(self.frame_master)
        if process == 'Demand' or self.process == 'Model':
            file_name = self.app.config_shelf.send_parameter('File_name')
        else:
            file_name = self.app.config_shelf.send_parameter('File_name_segmented')
        today_date = datetime.datetime.today().strftime('%d-%m-%Y')
        self.entry_output_file.insert(END, file_name + f' {today_date}')
        self.entry_output_file.grid(row=1, column=0, pady=5, sticky='WE')

        # Combobox to choose extension
        self.exts = {'Libro de Excel (*.xlsx)': '.xlsx',
                     'CSV UTF-8 (*.csv)': '.csv'}
        self.combobox_extensions = ttk.Combobox(self.frame_master, value=list(self.exts.keys()))
        self.combobox_extensions.current(0)
        self.combobox_extensions.grid(row=2, column=0, pady=5, sticky='WE')

        # Button to accept
        self_btn_accept = Button(self.frame_master, text='Guardar', padx=10, command=self.call_backend_export)
        self_btn_accept.grid(row=2, column=1, padx=10)

        # center window on screen
        center_window(self.master, self.screen_width, self.screen_height)

    def call_backend_export(self):

        ext_ = self.exts[self.combobox_extensions.get()]
        try:
            self.app.export_data(self.btn_path['text'], self.entry_output_file.get(), ext_, self.process)
            new_win = Toplevel(self.master)
            WindowPopUpMessage(new_win, 'Mensaje', 'Archivo exportado.', self.width, self.height)
            new_win.grab_set()
            self.master.wait_window(new_win)

        except ValueError:
            new_win = Toplevel(self.master)
            WindowPopUpMessage(new_win, 'Advertencia', 'Debe ejecutar el pronóstico antes'
                                                       ' de exportar la información.',
                               self.width, self.height)
            new_win.grab_set()
            self.master.wait_window(new_win)

    def open_window_popup(self):
        """Open TopLevel to select path where the input files are located."""

        # new toplevel with master root, grab_set and wait_window to wait for the main screen to freeze until
        # this window is closed
        self.new_win = Toplevel(self.master)
        WindowSelectWorkPath(self.new_win, self.back_end, self.screen_width, self.screen_height)
        self.new_win.grab_set()
        self.master.wait_window(self.new_win)

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
    path = os.path.join(os.path.expanduser("~"), r'AppData\Roaming\Modulo_Demanda')

    root = Tk()
    root.state('zoomed')
    Main(root, path)
    root.mainloop()
