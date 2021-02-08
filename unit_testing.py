from back_end import *

model = AutoRegression(periods_fwd=50, lags=1)

X = model.generate_testing_data()

model.fit(X.iloc[:, 0])

model.evaluate_fit()

predictions = model.predict()

model.plot_predicted()



