# AR example
from statsmodels.tsa.ar_model import AutoReg
from statsmodels.tools.eval_measures import rmse
from random import random
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from sklearn.model_selection import RandomizedSearchCV

params = {'p_fwd':50,
          'lags': 1}

# contrived dataset
data = [x + random() for x in range(1, 100)]
df = pd.DataFrame(np.random.randint(10, size=(100,)))


# fit model
model = AutoReg(df.iloc[:, 0], lags=params['lags'])
model_fit = model.fit()
df['Predicted'] = model_fit.predict()
df.columns = ['Demand', 'Predicted']
df = df.reset_index()

parameters = {'lags': range(0, 10)}

# randomsearch
rm = RandomizedSearchCV(estimator=model, param_distributions=parameters)


# create evaluation dataframe
df_eval = df.iloc[params['lags']:, :]
df_eval['Error'] = df_eval['Predicted'] - df_eval['Demand']
df_eval['Abs_Error'] = df_eval['Error'].abs()
mae = df_eval['Abs_Error'].mean()
mae_perc = mae/df['Demand'].mean()

# predict p periods forward
df_preds = pd.DataFrame(index=[i for i in range(df.shape[0], df.shape[0] + params['p_fwd'])])
df_preds['Demand'] = model_fit.predict(df_preds.index[0], df_preds.index[-1])
print('Demand predictions: ', df_preds['Demand'])

# create dataframe with original data and predictions
df_real_preds = pd.concat([df, df_preds], axis=0)

# plot original data and predictions
ax = df_real_preds['Demand'].plot(color='y')
df_real_preds.loc[df_real_preds.index >= df.shape[0], 'Demand'].plot(color='r', ax=ax)
# plt.show()







