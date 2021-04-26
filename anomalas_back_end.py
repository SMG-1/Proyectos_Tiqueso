import pandas as pd
import matplotlib.pyplot as plt
import os
import shelve


class FilePathShelf:
    @staticmethod
    def close_shelf(shelf: shelve):

        shelf.close()

    def __init__(self, _path):

        # path to save the shelve files
        self._path = _path

        # open shelve
        paths_shelf = shelve.open(self._path)

        # set keys list
        self._shelve_keys = ['Working',
                             'Orders',
                             'Anomaly_Model'
                             'Temp']

        # try to get value from key, if empty initialize
        for _path in self._shelve_keys:
            try:
                paths_shelf[_path]

            except KeyError:
                paths_shelf[_path] = ''

        # close shelf
        paths_shelf.close()

    def open_shelf(self):
        paths_shelf = shelve.open(self._path)

        return paths_shelf

    def write_to_shelf(self, file_name, path_):
        """Set value (path_) to key (file_name)."""

        # open saved values
        paths_shelf = self.open_shelf()

        if file_name not in self._shelve_keys:
            raise ValueError(f'You tried to save {file_name} to the dictionary. '
                             f'The accepted values are {self._shelve_keys}.')

        # set value to key
        paths_shelf[file_name] = path_

        # save and close shelf
        self.close_shelf(paths_shelf)

    def print_shelf(self):
        """Print the shelf."""

        shelf = self.open_shelf()

        for key, value in shelf.items():
            print(key, ': ', value)

            if key is None or value is None:
                pass

        # save and close shelf
        self.close_shelf(shelf)

    def send_path(self, file_name):
        """Return path from key (file_name)."""

        paths_shelf = self.open_shelf()

        if file_name not in self._shelve_keys:
            raise ValueError(f'{file_name} is not a valid file name.')

        path = paths_shelf[file_name]

        # save and close shelf
        self.close_shelf(paths_shelf)

        return path


class AnomalyApp:
    def __init__(self, path_):
        # installation path
        self.path_ = path_
        self.path_config_shelf = os.path.join(path_, 'config')
        self.path_file_paths = os.path.join(path_, 'paths')

        # initial routine
        if not self.check_if_installed():
            self.setup()

        # shelves for storing data in computer memory
        self.file_paths_shelf = FilePathShelf(self.path_file_paths)

    def setup(self):
        if not os.path.exists(self.path_):
            print('Instalando el programa.')
            os.makedirs(self.path_)

    def check_if_installed(self):
        if os.path.exists(self.path_):
            return True
        else:
            return False

    def set_path(self, filename, path):

        self.file_paths_shelf.write_to_shelf(filename, path)

    def get_path(self, filename):

        return self.file_paths_shelf.send_path(filename)

    def read_data(self):
        """Returns pandas dataframe with raw sales data."""

        # Get Demand path from parameters shelf
        # path = self.file_paths_shelf.send_path('Orders') # todo: temp, use this line instead
        path = r"C:\Users\smirand27701\OneDrive\TESIS COPROLAC S.A\Datos Fuente\Ventas_Total.csv"

        # Read the file into a pandas dataframe.
        if path.endswith('xlsx'):
            df = pd.read_excel(path)
        else:
            df = pd.read_csv(path)

        return df

    def clean_data(self):

        df = self.read_data()

        df = df[['Fecha de contabilización',
                 'Número de artículo',
                 'Descripción artículo/serv.',
                 'Peso presentación (KG)',
                 'Cantidad (unidades sistema)',
                 'Código clientes SAP',
                 'Nombre de cliente/proveedor']]

        df = df[df['Peso presentación (KG)'].notnull()]

        df['Cantidad'] = df['Peso presentación (KG)'] * df['Cantidad (unidades sistema)']
        df.drop(columns=['Peso presentación (KG)', 'Cantidad (unidades sistema)'],
                inplace=True)

        df.columns = ['Fecha',
                      'Producto_Cod',
                      'Producto_Nombre',
                      'Cliente_Cod',
                      'Cliente_Nombre',
                      'Cantidad']

        return df

    def read_clean_anomaly_model(self):

        # path = self.file_paths_shelf.send_path('Anomaly_Model') # todo: use this instead
        path = r"C:\Users\smirand27701\OneDrive\TESIS COPROLAC S.A\Diseño\Entrada y captura\Herramienta Ordenes Anomalas\Anomalas_Modelo.csv"

        # Read the file as a dataframe.
        df = pd.read_csv(path)

        return df

    def create_verification_table(self):

        df_sales = self.clean_data()
        df_anomaly_model = self.read_clean_anomaly_model()

        df_verification = df_sales.merge(df_anomaly_model,
                                         on=['Cliente_Cod', 'Producto_Cod'],
                                         how='left')

        df_verification['Alerta'] = 0

        df_verification.loc[(df_verification['Cantidad'] < df_verification['Min']) |
                            (df_verification['Cantidad'] > df_verification['Max']), 'Alerta'] = 1

        df_anomalies = df_verification[df_verification['Alerta'] == 1]
        anomalies_count = df_anomalies.shape[0] # todo: print this out in listbox

        # Set 'Alerta' to 'No hay datos históricos para esta combinación' if Client-Product combination is not
        # in the anomaly model.
        df_verification.loc[df_verification['Alerta'].isna(),
                            'Alerta'] = 'No hay datos históricos para esta combinacíon.'

        return df_verification
