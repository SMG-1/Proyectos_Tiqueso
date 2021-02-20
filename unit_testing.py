import os
import threading
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from back_end import Application
import time
from win32api import GetSystemMetrics
import pandastable
from back_end import *

data = generate_testing_data()

df = pd.DataFrame(data)

"""auto = AutoRegression(data.values, 1)
preds = auto.fit().predict()
preds = pd.DataFrame(index=[i for i in range(auto.ar_lags[0], len(preds) + auto.ar_lags[0], 1)], data=preds)

dftot = pd.concat([df, preds], axis=1)"""

auto = AutoRegression(data.values, 4, 50)
df_tot = auto.fit_predict()
# auto.show_plot_fitted()
test = auto.predict_fwd()
auto.show_plot_predicted()


default_dict = {'AutoReg': {'params': {'lags': 1,
                                       'trend': 'ct',
                                       'n_forward': 50},
                            'possible_values': {'lags': list(range(1, 50, 1)),
                                                'trend':['ct', 'c', 't']}}}
print(default_dict['AutoReg']['params']['lags'])
