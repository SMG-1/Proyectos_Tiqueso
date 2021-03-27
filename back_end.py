# back_end.py - Backend para leer datos históricos, ejecutar pronósticos, calcular errores, mostrar gráficos y
#                comparar entre modelos.
import copy
import datetime
import os
import shelve

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
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
        self._shelve_keys = ['Working',
                             'Demand',
                             'Forecast',
                             'BOM',
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

    @staticmethod
    def close_shelf(shelf: shelve):

        shelf.close()

    def __init__(self, _path):

        # path to save the shelve files
        self._path = _path

        # open shelve
        config_shelf = shelve.open(self._path)

        # set keys list
        self.config_dict = {'periods_fwd': 30,
                            'Last_process': 'Demand',
                            'File_name': 'Pronóstico',
                            'Agg_viz': 'Diario',
                            'BOM_Explosion': False}

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

        # parameter to define if BOM explosion should be applied or not
        self.bom_explosion = self.config_shelf.send_parameter('BOM_Explosion')

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

    def read_data(self, process_: str):
        """Returns pandas dataframe with time series data."""

        # Get Demand path from parameters shelf
        path = self.file_paths_shelf.send_path(process_)

        # raise value error if the key is empty
        if path == '':
            if process_ == 'Demand':
                err = "El directorio hacia el archivo de demanda no esta definido."
            else:
                err = "El directorio hacia el archivo de pronóstico no esta definido."
            raise KeyError(err)

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

    def clean_data(self, process_: str):
        """Cleans the time series data.
        First column is assumed to have datetime like values.
        Second column is assumed to be SKU.
        Third column is assumed to be the name of the SKU.
        Last column is assumed to be the demand values, numerical.
        Columns in between the third and the last are treated as extra aggregation parameters for the forecast."""

        # read the data
        df = self.read_data(process_)

        if df.shape[1] != 4:
            if process_ == 'Demand':
                raise ValueError('El archivo de demanda indicado tiene una estructura incorrecta.\n'
                                 'Se requieren cuatro columnas Fecha-Codigo-Nombre-Demanda.\n'
                                 f'El archivo cargado tiene {df.shape[1]} columnas.')
            else:
                raise ValueError('El archivo de demanda indicado tiene una estructura incorrecta.\n'
                                 'Se requieren cuatro columnas Fecha-Codigo-Nombre-Pronóstico.\n'
                                 f'El archivo cargado tiene {df.shape[1]} columnas.')

        if process_ == 'Demand':
            # rename columns with dictionary
            mapping = {df.columns[0]: 'Fecha',
                       df.columns[1]: 'Codigo',
                       df.columns[2]: 'Nombre',
                       df.columns[-1]: 'Demanda'}
        else:
            mapping = {df.columns[0]: 'Fecha',
                       df.columns[1]: 'Codigo',
                       df.columns[2]: 'Nombre',
                       df.columns[-1]: 'Pronóstico'}

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

    def apply_bom(self):
        """Convert the final product demand to its base components using a BOM (Bill of materials)."""

        # BOM path
        path_bom = self.file_paths_shelf.send_path('BOM')

        # raise value error if the key is empty
        if path_bom == '':
            err = "El directorio hacia el archivo de recetas no esta definido."
            raise KeyError(err)

        df_demand = copy.deepcopy(self.raw_data)

        # group original demand data by selected fields
        df_demand = df_demand.groupby(['Fecha', 'Codigo', 'Nombre']).sum().reset_index()
        df_demand.columns = ['Fecha', 'Cod_Prod', 'Nombre_Prod', 'Cantidad']

        # read BOM file
        bom = pd.read_excel(path_bom)

        # select columns and change column names
        bom = bom.loc[:, ['Cod Receta',
                          'Desc Receta',
                          'Cant',
                          'UND',
                          'Cod Art',
                          'Descripción del artículo',
                          'Cantidad',
                          'Unidad de medida de inventario']]
        bom.columns = ['Cod_Prod',
                       'Nombre_Prod',
                       'Cant_Prod',
                       'Ud_Prod',
                       'Cod_Comp',
                       'Nombre_Comp',
                       'Cant_Comp',
                       'Ud_Comp']

        # create table with intermediate products, that are not final components
        intermediate = pd.DataFrame(bom['Cod_Comp'].drop_duplicates()).dropna()
        intermediate.columns = ['Cod_Inter']

        # join intermediate products with BOM to get conversion factors between
        # intermediate products and final components
        intermediate = intermediate.merge(bom, left_on='Cod_Inter', right_on='Cod_Prod', how='left')
        intermediate.rename(columns={'Nombre_Prod': 'Nombre_Inter'}, inplace=True)
        intermediate.drop(columns=['Cod_Prod'], inplace=True)
        intermediate.dropna(subset=['Cod_Comp'], inplace=True)

        # apply the BOM explosion to the original demand data
        demand_bom = df_demand.merge(bom.drop(columns=['Nombre_Prod']), on='Cod_Prod', how='left')
        demand_bom['Cant_Req'] = demand_bom['Cantidad'] * demand_bom['Cant_Comp']

        # group the new data by the component demand
        demand_bom = demand_bom.groupby(['Cod_Comp', 'Nombre_Comp', 'Fecha'])['Cant_Req'].sum().reset_index()
        demand_bom = demand_bom[~demand_bom['Nombre_Comp'].str.contains('RECORTES')]
        demand_bom.columns = ['Cod_Prod', 'Nombre_Prod', 'Fecha', 'Cant_Req']

        # apply the BOM explosion to the dataset, to the get the demand for the final components
        demand_bom = demand_bom.merge(intermediate, left_on='Cod_Prod', right_on='Cod_Inter', how='left')
        demand_bom.loc[demand_bom['Cod_Inter'].notna(),
                       'Cant_Req_Final'] = demand_bom['Cant_Req'] * demand_bom['Cant_Comp']
        demand_bom.loc[demand_bom['Cod_Inter'].notna(), 'Codigo'] = demand_bom['Cod_Comp']
        demand_bom.loc[demand_bom['Cod_Inter'].notna(), 'Nombre'] = demand_bom['Nombre_Comp']

        demand_bom.loc[demand_bom['Cant_Req_Final'].isna(), 'Codigo'] = demand_bom[
            'Cod_Prod']
        demand_bom.loc[demand_bom['Cant_Req_Final'].isna(), 'Nombre'] = demand_bom[
            'Nombre_Prod']
        demand_bom.loc[demand_bom['Cant_Req_Final'].isna(), 'Cant_Req_Final'] = demand_bom[
            'Cant_Req']

        # keep selected columns and reorder
        demand_bom = demand_bom[['Codigo', 'Nombre', 'Fecha', 'Cant_Req_Final']]
        demand_bom.columns = ['Codigo', 'Nombre', 'Fecha', 'Demanda']

        # extract date from datetime values
        demand_bom['Fecha'] = demand_bom['Fecha'].dt.date

        # group demand by date and categorical features (sum)
        demand_bom = demand_bom.groupby(['Fecha', 'Codigo', 'Nombre']).sum().reset_index()

        # set date as index
        demand_bom.set_index(['Fecha'], inplace=True)
        demand_bom.index = pd.DatetimeIndex(demand_bom.index)

        # return dataset
        self.raw_data = demand_bom

    def create_segmented_data(self, process_: str):
        """Separate the raw data into N datasets, where N is the number of unique products in the raw data."""

        print("Creating separate datasets.")  # todo: temporary

        # Clean data upon function call
        self.clean_data(process_)

        # if bom_explosion is True, apply the BOM Explosion to the raw data
        if self.config_shelf.send_parameter('BOM_Explosion') and process_ == 'Demand':
            self.apply_bom()

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

            if process_ == 'Demand':
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

    def get_best_models(self, queue_):
        """Get an optimized model for each of the separate product data sets."""

        # check if data is loaded
        if self.segmented_data_sets is None:
            raise ValueError('No hay datos cargados para crear un modelo.')

        # check amount of data sets to use as a way of measuring progress bar
        num_keys = len(self.segmented_data_sets.keys())

        # iterate over data sets for training and predictions
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

            # create a dataset with the real data
            df_total = pd.DataFrame(df.loc[:, 'Demanda'], columns=['Demanda'])

            # create a dataset with the fitted values
            fitted_values = pd.DataFrame(results.arima_res_.fittedvalues, columns=['Fitted'], index=df_total.index)

            # join the real data with the fitted values on the rows axis
            df_total = pd.concat([df_total, fitted_values], axis=1)

            # call a function to get an out of sample prediction, result is a dataset with predictions
            preds = self.predict_fwd(df, fitted_model)

            # concat the predictions to the (data, fitted) dataset to get all values in one dataset
            df_total = pd.concat([df_total, preds], axis=1)

            # change column names
            df_total.columns = self.var_names

            # add the whole dataset to a dictionary with the product name as the key
            self.dict_fitted_dfs[sku] = df_total

            queue_.put([f'Modelo para {sku} listo.\n', idx / num_keys])

        queue_.put(['Listo', 1])

    def evaluate_fit(self):
        """Calculate forecasting metrics for each of the data sets with the fitted values."""

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
            rmse_ = mse ** (1 / 2)

            # calculate the rmse percentage
            rmse_perc = rmse_ / df[self.var_names[0]].mean()

            self.dict_metrics[sku] = {'AIC': self.dict_fitted_models[sku].aic(),
                                      'BIC': self.dict_fitted_models[sku].bic(),
                                      'Bias': bias,
                                      'MAE': mae,
                                      'MAE_PERC': mae_perc,
                                      'MSE': mse,
                                      'RMSE': rmse_,
                                      'RMSE_PERC': rmse_perc}

            print(f'Metrics for {sku}: ', self.dict_metrics[sku])

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
