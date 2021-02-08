# back_end.py - Backend para leer datos históricos, ejecutar pronósticos, calcular errores, mostrar gráficos y
#                comparar entre modelos.

from statsmodels.tsa.ar_model import AutoReg
from statsmodels.tools.eval_measures import rmse
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

pd.options.mode.chained_assignment = None


class AutoRegression:
    def __init__(self, periods_fwd: int, lags: int):
        self.periods_fwd = periods_fwd
        self.lags = lags
        self.fitted_model = None
        self.X = None
        self.fitted_values = None
        self.predictions = None

    def generate_testing_data(self):
        # generar data de prueba
        data = pd.DataFrame(np.random.randint(10, size=(100,)))
        return data

    def fit(self, X):
        """Fit a model using the statsmodels fit method.

        PARAMETERS:
        X: pandas Series with numeric data and a datetime or Series-like index."""

        self.X = X
        model = AutoReg(X, lags=self.lags)
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

        print('MAE: ', round(mae, 2))
        print('MAE %: ', round(mae_perc * 100, 2), ' %')

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


if __name__ == '__main__':
    model_autoreg = AutoRegression(50, 1)
    X = model_autoreg.generate_data()
    model_autoreg.fit(X)

    model_autoreg.show_real_vs_fitted_plot()
    model_autoreg.evaluate()
    model_autoreg.predict()
    model_autoreg.plot_predicted()
