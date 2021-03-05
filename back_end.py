# back_end.py - Backend para leer datos históricos, ejecutar pronósticos, calcular errores, mostrar gráficos y
#                comparar entre modelos.
import copy

from statsmodels.tsa.ar_model import AutoReg
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tools.eval_measures import rmse
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import shelve
from itertools import product
import datetime
from sklearn.model_selection import TimeSeriesSplit
import pmdarima as pm

pd.options.mode.chained_assignment = None

plt.style.use('ggplot')


def generate_testing_data():
    # generar data de prueba
    data = pd.DataFrame(np.random.randint(10, size=(100,)))
    return data


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
        self._shelve_keys = ['Working', 'Demand']

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
            raise ValueError(f'You tried to save {path_} to the dictionary. '
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


class ConfigShelf:

    def __init__(self, _path):

        # path to save the shelve files
        self._path = _path

        # open shelve
        config_shelf = shelve.open(self._path)

        # set keys list
        self.model_dict = {'AutoReg': {'params': {'lags': [1, tuple(range(1, 50, 1))],
                                                  'trend': ['ct', ('n', 'ct', 'c', 't')],
                                                  'periods_fwd': [50, int]}},

                           'ARIMA': {'params': {'p': [1, tuple(range(1, 10, 1))],
                                                'd': [1, tuple(range(1, 10, 1))],
                                                'q': [1, tuple(range(1, 10, 1))],
                                                'trend': ['ct', ('n', 'ct', 'c', 't')],
                                                'periods_fwd': [50, int]}}}

        # try to get value from key, if empty initialize
        for key, value in self.model_dict.items():
            try:
                config_shelf[key]
            except KeyError:
                config_shelf[key] = value

        # close shelf
        config_shelf.close()

    def open_shelf(self, writeback: bool):
        shelf = shelve.open(self._path, writeback=writeback)

        return shelf

    def close_shelf(self, shelf: shelve):

        shelf.close()

    def write_to_shelf(self, parameter, value, **kwargs):
        """Set value (value) to key (parameter)."""

        # open saved values
        shelf = self.open_shelf(True)

        if 'model' in kwargs.keys():
            model_ = kwargs['model']

            shelf[model_]['params'][parameter][0] = value

        else:
            # set value to key
            shelf[value] = parameter

        self.model_dict = shelf

        # save and close shelf
        self.close_shelf(shelf)

    def print_shelf(self):
        """Print the shelf."""

        shelf = self.open_shelf(False)

        for key, value in shelf.items():
            print(key, ': ', value)

            if key is None or value is None:
                pass

        # save and close shelf
        self.close_shelf(shelf)

    def send_parameter(self, parameter, **kwargs):
        """Return value from key (parameter)."""

        shelf = self.open_shelf(False)

        """if parameter not in self.model_dict.keys():
            raise ValueError(f'{parameter} is not a valid parameter.')"""

        if 'model' in kwargs.keys():
            model_ = kwargs['model']

            value = shelf[model_]['params'][parameter][0]

        else:
            value = shelf[parameter]

        # save and close shelf
        self.close_shelf(shelf)

        return value

    def send_dict(self):
        shelf = self.open_shelf(False)

        dict_ = dict(shelf)

        self.close_shelf(shelf)

        return dict_


class Application:

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
        self.config_shelf = ConfigShelf(self.path_config_shelf)

        # master data variable
        self.raw_data = pd.DataFrame()
        self.segmented_data_sets = {}

        # available forecasting models
        self.models = {'SARIMAX': 'ARIMA'}

        # MODEL ATTRIBUTES

        # model chosen by the user
        self.active_model = None

        # model fitted to the data
        self.fitted_model = None

        # data used for modelling
        self.model_df = None

        # amount of periods to forecast out of sample
        self.periods_fwd = int(self.config_shelf.send_parameter('periods_fwd', model='ARIMA'))

        # feature names for the modelling data
        self.var_names = ['Demanda', 'Pronóstico']

        # dataframe to compare real data vs fitted data
        self.df_real_vs_fitted = None

        # OOS predictions made by the model
        self.predictions = None

        # real data + OOS predictions
        self.df_real_preds = None

        # dataframe with original data, fitted values and OOS predictions
        self.df_total = pd.DataFrame()

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

    def set_parameter(self, parameter, value):

        self.config_shelf.write_to_shelf(parameter, value)

    def get_parameter(self, parameter):

        return self.config_shelf.send_parameter(parameter)

    def read_data(self):
        """Returns pandas dataframe with time series data."""

        # Get Demand path from parameters shelf
        path = self.file_paths_shelf.send_path('Demand')

        if path == '':
            err = "El directorio hacia el archivo de demanda no esta definido."
            raise ValueError(err)

        # if file ends with CSV, read as CSV
        if path.endswith('.csv'):
            print('Reading CSV.')
            df = pd.read_csv(path, sep=",", decimal=",", header=0)
            return df

        # if file ends with xlsx, read as Excel
        elif path.endswith('.xlsx'):
            print('Reading Excel.')
            df = pd.read_excel(path)
            return df

    def clean_data(self):
        """Cleans the time series data.
        First column is assumed to have datetime like values.
        Second column is assumed to be SKU.
        Third column is assumed to be the name of the SKU.
        Last column is assumed to be the demand values, numerical.
        Columns in between the third and the last are treated as extra aggregation parameters for the forecast."""

        # read the data
        df = self.read_data()

        # rename columns with dictionary
        mapping = {df.columns[0]: 'Fecha',
                   df.columns[1]: 'Codigo',
                   df.columns[2]: 'Nombre',
                   df.columns[-1]: 'Demanda'}

        df = df.rename(columns=mapping)

        # convert first column to datetime or raise ValueError
        try:
            df['Fecha'] = pd.to_datetime(df['Fecha'])
        except ValueError:
            raise ValueError('Error: en la primera columna de los datos de entrada hay filas que no contienen fechas.')

        # convert last column to numerical or raise ValueError
        try:
            df.iloc[:, -1] = pd.to_numeric(df.iloc[:, -1])
        except ValueError:
            raise ValueError('Error: en la ultima columna de los datos de entrada hay filas que no contienen'
                             ' datos numericos.')

        # extract date from datetime values
        df['Fecha'] = df['Fecha'].dt.date

        # group demand by date and categorical features (sum)
        df = df.groupby(df.columns[:-1].to_list()).sum().reset_index()

        # set date as index
        df.set_index(['Fecha'], inplace=True)
        df.index = pd.DatetimeIndex(df.index)

        # save df as a class attribute
        self.raw_data = df

    def create_segmented_data(self):
        """Separate the original data into n datasets, where n is the number of unique data combinations in the df."""

        # Clean data upon function call
        self.clean_data()

        # variable to set the unique values
        var_name = 'Nombre'

        # create copy to be able to modify the dataset
        df = copy.deepcopy(self.raw_data)

        unique_combinations = [uni for uni in df.loc[:, var_name].unique()]
        df_list = []

        # for all the unique var_name values, get the filtered dataframe and add to list
        for unique in unique_combinations:
            df_ = df[df[var_name] == unique]

            # fill missing dates with 0
            df_ = df_.asfreq('D')
            df_['Demanda'].fillna(0, inplace=True)
            df_.fillna(method='ffill', inplace=True)
            df_list.append(df_)

        # create total demand dataset, grouped by date
        grouped_df = df.reset_index()
        grouped_df = grouped_df.groupby('Fecha').sum().reset_index()

        # append grouped df to list, and label as Total
        unique_combinations.append('Total')
        df_list.append(grouped_df)

        # create dictionary from zipped lists
        data_sets_dict = dict(zip(unique_combinations, df_list))

        # assign the dictionary to class attribute
        self.segmented_data_sets = data_sets_dict

    def fit_to_data(self, df: pd.DataFrame, model_name: str):
        """Fit any of the supported models to the data and save the model used."""

        # get parameter names
        param_names = self.config_shelf.send_dict()[model_name]['params'].keys()

        # get parameter values
        param_values = [self.config_shelf.send_parameter(param, model=model_name) for param in param_names]

        # try to convert parameter values to int, some are saved in str format by the combobox
        for idx, param in enumerate(param_values):
            try:
                param_values[idx] = int(param)
            except ValueError:
                pass
            except TypeError:
                pass

        # create temporary parameter dictionary with names and values to be used
        param_dict = dict(zip(param_names, param_values))

        # get only column of values of the dataframe
        df = df.iloc[:, -1]

        # save the df parameter as a class attribute to be used for predictions
        self.model_df = pd.DataFrame(df)
        self.df_total = copy.deepcopy(self.model_df)

        # create the model with the selected parameters
        if model_name == 'AutoReg':
            # create model AutoRegression model with DataFrame parameter and assign parameters according to dictionary
            self.active_model = AutoReg(df,
                                        lags=param_dict['lags'],
                                        trend=param_dict['trend'],
                                        old_names=False)

        if model_name == 'ARIMA':
            results = pm.auto_arima(self.model_df,
                                    out_of_sample_size=20,
                                    stepwise=True)
            print('Auto-ARIMA Results: ', results.summary())

            # queue_.put(['Listo', results.summary()])

            self.active_model = SARIMAX(df,
                                        order=(param_dict['p'],
                                               param_dict['d'],
                                               param_dict['q']))

        # set periods forward using the value set in the parameter dictionary
        self.periods_fwd = param_dict['periods_fwd']

        # get model fitted to the input data
        self.fitted_model = self.active_model.fit()

        # predict on original index to obtain fitted values
        fitted_vals = self.fitted_model.predict()

        # add the fitted values to the original data as a new column
        df_tot = pd.concat([df, fitted_vals], axis=1)

        # change column names
        df_tot.columns = self.var_names
        df_tot.dropna(subset=[self.var_names[-1]], inplace=True)

        # assign to instance attribute
        self.df_real_vs_fitted = df_tot

        return df_tot

    def evaluate_fit(self):
        """"""

        # copy dataframe of real vs fitted values to be able to modify it
        df_eval = copy.deepcopy(self.df_real_vs_fitted)

        # calculate error
        df_eval.loc[:, 'Error'] = df_eval['Pronóstico'] - df_eval['Demanda']

        # calculate absolute error
        df_eval.loc[:, 'Abs_Error'] = df_eval['Error'].abs()

        print('AIC: ', self.fitted_model.aic)
        print('BIC: ', self.fitted_model.bic)

        # calculate the mean absolute error
        mae = df_eval['Abs_Error'].mean()
        print('MAE: ', mae)
    
        # calculate the mean percentage absolute error
        mae_perc = mae / df_eval['Demanda'].mean()
        print('MAE %: ', mae_perc)

        return [self.fitted_model.aic, self.fitted_model.bic, mae, mae_perc]

    def get_best_model(self, queue_):

        for sku, df in self.segmented_data_sets.items():
            results = pm.auto_arima(df.loc[:, 'Demanda'],
                                    out_of_sample_size=20,
                                    stepwise=True)
            fitted_model = results.fit(df.loc[:, 'Demanda'])

            df_total = pd.DataFrame(df.loc[:, 'Demanda'], columns=['Demanda'])
            fitted_values = pd.DataFrame(results.arima_res_.fittedvalues, columns=['Fitted'], index=df_total.index)
            df_total = pd.concat([df_total, fitted_values], axis=1)

            preds = self.predict_fwd(df, fitted_model)

            df_total = pd.concat([df_total, preds], axis=1)

            print(f'SKU: {sku}\nAuto-ARIMA Results: ', results.summary())

        # queue_.put(['Listo', results.summary()])

    def predict_fwd(self, df, fitted_model):
        """Predict N periods forward using self.periods_fwd as N."""

        # create index from the max date in the original dataset to periods_fwd days forward
        pred_index = pd.date_range(start=df.index.max(),
                                   end=df.index.max() + datetime.timedelta(days=self.periods_fwd-1))

        # predict on OOS using the fitted model
        predictions = fitted_model.predict(n_periods=self.periods_fwd)
        predictions = pd.DataFrame(predictions, index=pred_index)
        predictions.columns = [self.var_names[0]]

        return predictions


if __name__ == '__main__':
    root_path = os.path.join(os.path.expanduser("~"), r'AppData\Roaming\Modulo_Demanda')

    app = Application(root_path)
    # app.set_path('Demand', r"C:\Users\Usuario\Desktop\Data Ticheese\Ventas sample.xlsx")
    app.set_path('Demand', r"C:\Users\smirand27701\Desktop\Nueva carpeta\Ventas sample.csv")
