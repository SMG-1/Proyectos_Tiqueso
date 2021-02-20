# back_end.py - Backend para leer datos históricos, ejecutar pronósticos, calcular errores, mostrar gráficos y
#                comparar entre modelos.
import copy

from statsmodels.tsa.ar_model import AutoReg
from statsmodels.tools.eval_measures import rmse
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import shelve
from itertools import product

pd.options.mode.chained_assignment = None

plt.style.use('ggplot')

def generate_testing_data():
    # generar data de prueba
    data = pd.DataFrame(np.random.randint(10, size=(100,)))
    return data

class AutoRegression(AutoReg):
    def __init__(self, endog, lags):
        super().__init__(endog, lags)

        self.df = pd.DataFrame(endog)

        AutoReg.old_names = False

        self.df_real_vs_fitted = None

    def fit_predict(self):


        predictions = self.fit().predict()
        predictions = pd.DataFrame(index=[i for i in range(self.ar_lags[0], len(predictions) + self.ar_lags[0], 1)],
                             data=predictions)

        df_tot = pd.concat([self.df, predictions], axis=1)

        df_tot.columns = ['Demanda', 'Pronóstico']

        self.df_real_vs_fitted = df_tot

        return df_tot

    def show_plot(self):

        df = copy.deepcopy(self.df_real_vs_fitted)
        df = df.reset_index()
        # create and show plot
        ax =df.plot(x='index', y='Demanda', legend=False)
        ax2 = ax.twinx()
        df.plot(x='index', y='Pronóstico', ax=ax2, legend=False, color="r")
        ax.figure.legend()
        plt.show()


class AutoRegression2:
    def __init__(self, periods_fwd: int, lags: int, trend):
        self.periods_fwd = periods_fwd
        self.lags = lags
        self.fitted_model = None
        self.X = None
        self.fitted_values = None
        self.predictions = None
        self.trend = trend

    def fit(self, X):
        """Fit a model using the statsmodels fit method.

        PARAMETERS:
        X: pandas Series with numeric data and a datetime or Series-like index."""

        self.X = X
        model = AutoReg(X, lags=self.lags, old_names=False)
        self.fitted_model = model.fit()
        self.fitted_values = self.fitted_model.predict()

    def show_real_vs_fitted_plot(self):
        df_real_fitted = self.create_real_fitted_dataframe()

        # create and show plot
        ax = df_real_fitted.plot(x='index', y='Demanda', legend=False)
        ax2 = ax.twinx()
        df_real_fitted.plot(x='index', y='Pronóstico', ax=ax2, legend=False, color="r")
        ax.figure.legend()
        plt.show()

    def create_real_fitted_dataframe(self):
        df_real_fitted = pd.concat([self.X, self.fitted_values], axis=1)
        df_real_fitted.columns = ['Demanda', 'Pronóstico']
        df_real_fitted = df_real_fitted.reset_index()

        return df_real_fitted

    def evaluate_fit(self):
        df_real_fitted = self.create_real_fitted_dataframe()

        df_eval = df_real_fitted.iloc[self.lags:, :]

        df_eval.loc[:, 'Error'] = df_eval['Pronóstico'] - df_eval['Demanda']

        df_eval.loc[:, 'Abs_Error'] = df_eval['Error'].abs()

        mae = df_eval['Abs_Error'].mean()

        mae_perc = mae / df_eval['Demanda'].mean()

        # print('MAE: ', round(mae, 2))
        # print('MAE %: ', round(mae_perc * 100, 2), ' %')

        return mae

    def predict(self):
        # set an index from original X shape, to periods_fwd
        self.predictions = pd.DataFrame(index=[i for i in range(self.X.shape[0], self.X.shape[0] + self.periods_fwd)])

        # use the predict method to populate the index on a column called Demanda
        self.predictions.loc[:, 0] = self.fitted_model.predict(self.predictions.index[0], self.predictions.index[-1])

        # create dataframe with original data and predictions
        self.df_real_preds = pd.concat([self.X, self.predictions], axis=0)

        return self.df_real_preds

    def plot_predicted(self):
        fig, ax = plt.subplots()
        ax.plot(self.df_real_preds.loc[self.df_real_preds.index <= self.X.shape[0]], label='Demanda')
        ax.plot(self.df_real_preds.loc[self.df_real_preds.index >= self.X.shape[0]], label='Pronóstico')
        leg = ax.legend()
        plt.show()

    def test_params(self, lags: list, trends: list):

        lags_best = ""
        trends_best = ""
        score_best = 9999

        X = generate_testing_data()

        for lag in lags:
            for trend in trends:

                model = AutoReg(X, lags=lag, trend=trend, old_names=False)
                fitted_model = model.fit()
                fitted_values = fitted_model.predict()

                score = model.evaluate_fit()

                if score < score_best:
                    lags_best = lag
                    trends_best = trend
                    score_best = score

        print(f'Best score {score_best}. Lags: {lags_best}, trend: {trends_best}.')


class FilePathShelf:
    def __init__(self, _path):

        # path to save the shelve files
        self._path = _path

        # shelf key
        self._shelve_name = 'paths'

        # open shelve
        paths_shelf = shelve.open(os.path.join(self._path, self._shelve_name))

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
        paths_shelf = shelve.open(os.path.join(self._path, self._shelve_name))

        return paths_shelf

    def close_shelf(self, shelf: shelve):

        shelf.close()

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

        # shelf key
        self._shelve_name = 'config'

        # open shelve
        config_shelf = shelve.open(os.path.join(self._path, self._shelve_name))

        # set keys list
        self.default_dict = {'model': ['autoreg'],
                             'autoreg_params': {'lags': 1,
                                                'trend': 'c',
                                                'n_forward': 50}}

        # try to get value from key, if empty initialize
        for key, value in self.default_dict.items():
            try:
                config_shelf[key]
            except KeyError:
                config_shelf[key] = value

        # close shelf
        config_shelf.close()

    def open_shelf(self):
        shelf = shelve.open(os.path.join(self._path, self._shelve_name))

        return shelf

    def close_shelf(self, shelf: shelve):

        shelf.close()

    def write_to_shelf(self, parameter, value):
        """Set value (value) to key (parameter)."""

        # open saved values
        shelf = self.open_shelf()

        if value not in self.default_dict.keys():
            raise ValueError(f'You tried to save {parameter} to the dictionary. '
                             f'The accepted values are {self.default_dict.keys()}.')

        # set value to key
        shelf[value] = parameter

        # save and close shelf
        self.close_shelf(shelf)

    def print_shelf(self):
        """Print the shelf."""

        shelf = self.open_shelf()

        for key, value in shelf.items():
            print(key, ': ', value)

            if key is None or value is None:
                pass

        # save and close shelf
        self.close_shelf(shelf)

    def send_parameter(self, parameter):
        """Return value from key (parameter)."""

        shelf = self.open_shelf()

        if parameter not in self.default_dict.keys():
            raise ValueError(f'{parameter} is not a valid parameter.')

        value = shelf[parameter]

        # save and close shelf
        self.close_shelf(shelf)

        return value


class Application:

    def __init__(self, path_):

        # installation path
        self.path_ = path_

        # initial routine
        if not self.check_if_installed():
            self.setup()

        # shelves for storing data in computer memory
        self.file_paths_shelf = FilePathShelf(self.path_)
        self.config_shelf = ConfigShelf(self.path_)

        # master data variable
        self.data_ = pd.DataFrame()
        self.separate_data_sets = {}

        # available forecasting models
        self.models = ['Auto-regresión']

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
        df.index = pd.DatetimeIndex(df.index).to_period('D')

        # save df as a class attribute
        self.data_ = df

    def create_new_data_sets(self):
        """Separate the original data into n datasets, where n is the number of unique data combinations in the df."""

        # Clean data upon function call
        self.clean_data()

        # variable to set the unique values
        var_name = 'Nombre'

        # create copy to be able to modify the dataset
        df = copy.deepcopy(self.data_)

        # todo: ahorita agarra solo el codigo, ajustar para codigo-canal
        unique_combinations = [uni for uni in df.loc[:, var_name].unique()]
        df_list = []

        # for all the unique var_name values, get the filtered dataframe and add to list
        for unique in unique_combinations:
            df_list.append(df[df[var_name] == unique])

        # create total demand df grouped by date
        grouped_df = df.reset_index()
        grouped_df = grouped_df.groupby('Fecha').sum().reset_index()

        # append grouped df to list, and label as Total
        unique_combinations.append('Total')
        df_list.append(grouped_df)

        # create dictionary from zipped lists
        data_sets_dict = dict(zip(unique_combinations, df_list))

        # assign the dictionary to class attribute
        self.separate_data_sets = data_sets_dict


    def evaluate_fit(self, data, fitted_values):
        """"""

        df_real_fitted = pd.concat([data, fitted_values], axis=1)
        df_real_fitted.columns = ['Demanda', 'Pronóstico']
        df_real_fitted = df_real_fitted.reset_index()

        df_eval = df_real_fitted.dropna()

        df_eval.loc[:, 'Error'] = df_eval['Pronóstico'] - df_eval['Demanda']

        df_eval.loc[:, 'Abs_Error'] = df_eval['Error'].abs()

        mae = df_eval['Abs_Error'].mean()

        mae_perc = mae / df_eval['Demanda'].mean()

        return mae

    def get_best_model(self, data, model_name, parameters):
        lags_best = ""
        trends_best = ""
        score_best = 9999

        if model_name == 'autoreg':

            for i in product(*parameters.values()):
                temp_dict = dict(zip(parameters.keys(), i))

                model = AutoReg(data, lags=temp_dict['lags'], trend=temp_dict['trend'], old_names=False)

                fitted_model = model.fit()

                fitted_values = fitted_model.predict()

                score = self.evaluate_fit(data, fitted_values)

                if score < score_best:
                    lags_best = temp_dict['lags']
                    trends_best = temp_dict['trend']
                    score_best = score

            print(f'Best score {score_best}. Lags: {lags_best}, trend: {trends_best}.')

    def workflow(self):
        df = self.read_data()
        df = self.clean_data(df)
        dfs = self.create_new_datasets(df)

        params = {'lags': range(1, 15, 1),
                  'trend': ['c', 'ct', 't']}

        for key, df in dfs.items():
            print(f'Getting best parameters for {key}')
            self.get_best_model(df.iloc[:, -1], 'autoreg', params)

        return dfs


if __name__ == '__main__':
    root_path = os.path.join(os.path.expanduser("~"), r'AppData\Roaming\Modulo_Demanda')

    app = Application(root_path)
    # app.set_path('Demand', r"C:\Users\Usuario\Desktop\Data Ticheese\Ventas sample.xlsx")
    app.set_path('Demand', r"C:\Users\smirand27701\Desktop\Nueva carpeta\Ventas sample.csv")

    test = app.workflow()
