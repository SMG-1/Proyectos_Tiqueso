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
        self.config_dict = {'periods_fwd': 30,
                            'File_name': 'Pronóstico',
                            'Agg_viz': 'Diario'}

        # try to get value from key, if empty initialize
        for key, value in self.config_dict.items():
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
            shelf[parameter] = value

        self.config_dict = shelf

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

        if parameter not in shelf.keys():
            raise ValueError(f'{parameter} is not a valid parameter.')

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

        # product dictionary
        self.product_dict = {}

        # MODEL ATTRIBUTES

        # model chosen by the user
        self.active_model = None

        # model fitted to the data
        self.fitted_model = None

        # data used for modelling
        self.model_df = None

        # amount of periods to forecast out of sample
        self.periods_fwd = int(self.config_shelf.send_parameter('periods_fwd'))

        # feature names for the modelling data
        self.var_names = ['Demanda', 'Ajuste', 'Pronóstico']

        # dictionary to store fitted models for forecasting
        self.dict_fitted_models = {}

        # dictionary to store dataframes with original data, fitted values and OOS forecast
        self.dict_fitted_dfs = {}

        # dictionary to store dataframes with forecast errors
        self.dict_errors = {}

        # dictionary to store metrics for each model
        self.dict_metrics = {}

        # dictionary for metric descriptions

        self.dict_metric_desc = {'AIC': 'Criterio de información de Akaike',
                                 'BIC': 'Criterio de información Bayesiano',
                                 'Bias': 'Promedio del error: Un valor positivo indica una sobreestimación de la '
                                         'demanda y viceversa.',
                                 'MAE': 'Promedio del error absoluto: Indica el valor promedio del error en la unidad'
                                        'de medida de los datos de entrada.',
                                 'MAE_PERC': 'MAE Porcentual: indica el error promedio como proporción de la '
                                             'demanda promedio.',
                                 'MSE': 'Promedio del error cuadrático: indica el valor promedio del error elevado '
                                        'al cuadrado.',
                                 'RMSE': 'Raíz del error cuadrático: indica la raíz de MSE en la unidad de medida '
                                         'de los datos de entrada.',
                                 'RMSE_PERC': 'RMSE Porcentual: Indica el RMSE como proporción de la '
                                             'demanda promedio.'}

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
        # path = ''

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

        # get all the unique product codes
        unique_codes = [code for code in df.loc[:, 'Codigo'].unique()]

        # get all the unique products
        unique_products = [uni for uni in df.loc[:, var_name].unique()]

        # create a dictionary of codes and product names
        self.product_dict = dict(zip(unique_products, unique_codes))
        df_list = []

        # for all the unique var_name values, get the filtered dataframe and add to list
        for unique in unique_products:
            df_ = df[df[var_name] == unique]

            # fill missing dates with 0
            df_ = df_.asfreq('D')
            df_['Demanda'].fillna(0, inplace=True)
            df_.fillna(method='ffill', inplace=True)
            df_list.append(df_)

        # create total demand dataset, grouped by date
        grouped_df = df.reset_index()
        grouped_df = grouped_df.groupby('Fecha').sum().reset_index()
        grouped_df = grouped_df.set_index('Fecha')

        # append grouped df to list, and label as Total
        unique_products.append('Total')
        df_list.append(grouped_df)

        # create dictionary from zipped lists
        data_sets_dict = dict(zip(unique_products, df_list))

        # assign the dictionary to class attribute
        self.segmented_data_sets = data_sets_dict

    def evaluate_fit(self):
        """"""

        for sku, df in self.dict_fitted_dfs.items():
            df = copy.deepcopy(df)

            # error = forecast - demand
            df.loc[:, 'Error'] = df[self.var_names[1]] - df[self.var_names[0]]

            # absolute error = abs(error)
            df.loc[:, 'Abs_Error'] = df['Error'].abs()

            # squared error
            df.loc[:, 'Squared_Error'] = df['Error'] ** 2

            self.dict_errors[sku] = df

            # save individual metrics to the metrics dictionary
            print('AIC: ', self.dict_fitted_models[sku].aic())
            print('BIC: ', self.dict_fitted_models[sku].bic())

            # calculate the bias
            bias = df['Error'].mean()
            print('Bias:', bias)

            # calculate the mean absolute error
            mae = df['Abs_Error'].mean()
            print('MAE: ', mae)

            # calculate the mean percentage absolute error
            mae_perc = mae / df[self.var_names[0]].mean()
            print('MAE %: ', mae_perc)

            # calculate the mean squared error
            mse = df['Squared_Error'].mean()

            # calculate the rmse
            rmse = mse ** (1 / 2)

            # calculate the rmse percentage
            rmse_perc = rmse / df[self.var_names[0]].mean()

            self.dict_metrics[sku] = {'AIC': self.dict_fitted_models[sku].aic(),
                                      'BIC': self.dict_fitted_models[sku].bic(),
                                      'Bias': bias,
                                      'MAE': mae,
                                      'MAE_PERC': mae_perc,
                                      'MSE': mse,
                                      'RMSE': rmse,
                                      'RMSE_PERC': rmse_perc}

            print(f'Metrics for {sku}: ', self.dict_metrics[sku])

    def get_best_models(self, queue_):

        # check if data is loaded
        if self.segmented_data_sets is None:
            raise ValueError('No hay datos cargados para crear un modelo.')

        # check amount of datasets to use as a way of measuring progress bar
        num_keys = len(self.segmented_data_sets.keys())

        # iterate over dataframes for training and predictions
        for idx, (sku, df) in enumerate(self.segmented_data_sets.items(), 1):
            queue_.put([f'Entrenando modelo para {sku}.', 0])

            # get the best ARIMA model for each df
            results = pm.auto_arima(df.loc[:, 'Demanda'],
                                    out_of_sample_size=20,
                                    stepwise=True)
            print(results.summary())

            # fit the best model to the dataset
            fitted_model = results.fit(df.loc[:, 'Demanda'])

            # save fitted model to dictionary of fitted models
            self.dict_fitted_models[sku] = fitted_model

            # create a dataframe with the real data
            df_total = pd.DataFrame(df.loc[:, 'Demanda'], columns=['Demanda'])

            # create a dataframe with the fitted values
            fitted_values = pd.DataFrame(results.arima_res_.fittedvalues, columns=['Fitted'], index=df_total.index)

            # join the real data with the fitted values on the rows axis
            df_total = pd.concat([df_total, fitted_values], axis=1)

            # call a function to get an out of sample prediction, result is a dataframe with predictions
            preds = self.predict_fwd(df, fitted_model)

            # concat the predictions to the (data, fitted) dataset to get all values in one dataframe
            df_total = pd.concat([df_total, preds], axis=1)

            # change column names
            df_total.columns = self.var_names

            # add the whole dataframe to a dictionary with the product name as the key
            self.dict_fitted_dfs[sku] = df_total

            queue_.put([f'Modelo para {sku} listo.\n', idx / num_keys])

        queue_.put(['Listo', 1])

    def predict_fwd(self, df, fitted_model):
        """Predict N periods forward using self.periods_fwd as N."""

        periods_fwd = self.config_shelf.send_parameter('periods_fwd')

        # create index from the max date in the original dataset to periods_fwd days forward
        pred_index = pd.date_range(start=df.index.max(),
                                   end=df.index.max() + datetime.timedelta(days=periods_fwd - 1))

        # predict on OOS using the fitted model
        predictions = fitted_model.predict(n_periods=periods_fwd)
        predictions = pd.DataFrame(predictions, index=pred_index, columns=[self.var_names[0]])

        # allow only non-negative predictions
        predictions.loc[predictions[self.var_names[0]] < 0, self.var_names[0]] = 0

        return predictions

    def refresh_predictions(self):

        if self.dict_fitted_models == {}:
            raise NameError('No se tienen modelos entrenados, debe correr el optimizador primero.')

        else:
            # get new predictions for each dataset
            for sku, df in self.segmented_data_sets.items():
                # get the product's fitted model
                model = self.dict_fitted_models[sku]

                # get the product's fitted dataset (demand, fitted values, OOS forecast)
                total_df_old = self.dict_fitted_dfs[sku]

                # drop old predictions from the fitted dataset
                total_df_old = total_df_old.loc[df.index]
                total_df_old.drop(columns=[self.var_names[2]], inplace=True)

                # get new predictions
                new_preds = self.predict_fwd(df, model)

                # add new predictions to the old dataset
                total_df_new = pd.concat([total_df_old, new_preds], axis=1)
                total_df_new.columns = self.var_names

                # replace the new dataset with the old one on the fitted dataframes dictionary
                self.dict_fitted_dfs[sku] = total_df_new

    def export_data(self, path, file_name, extension):

        print('Exportando.')
        file_name = file_name + extension

        col_order = ['Fecha', 'Codigo', 'Nombre', 'Pronóstico']

        # check if model ran
        if self.dict_fitted_dfs == {}:
            raise ValueError('The model has to be trained first.')

        df_export = pd.DataFrame()
        for sku, df in self.dict_fitted_dfs.items():

            # skip totals
            if sku == 'Total':
                continue

            df['Codigo'] = self.product_dict[sku]
            df['Nombre'] = sku

            # keep only rows with the forecast, drop original data
            df = df.reset_index()
            df = df[df['Pronóstico'].notnull()]
            df = df.iloc[1:, :]

            # format date
            df['Fecha'] = df['Fecha'].dt.date

            df = df[col_order]
            df_export = pd.concat([df_export, df], axis=0)

        if extension == '.xlsx':
            df_export.to_excel(os.path.join(path, file_name),
                               sheet_name='Pronostico',
                               index=False)

        elif extension == '.csv':
            df_export.to_csv(os.path.join(path, file_name),
                             index=False)


if __name__ == '__main__':
    root_path = os.path.join(os.path.expanduser("~"), r'AppData\Roaming\Modulo_Demanda')

    app = Application(root_path)
    # app.set_path('Demand', r"C:\Users\Usuario\Desktop\Data Ticheese\Ventas sample.xlsx")
    # app.set_path('Demand', r"C:\Users\smirand27701\Desktop\Nueva carpeta\Ventas sample.csv")
