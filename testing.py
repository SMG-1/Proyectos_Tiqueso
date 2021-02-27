from sklearn.model_selection import TimeSeriesSplit
import pandas as pd

df = pd.read_csv(r"C:\Users\Usuario\Desktop\Data Ticheese\Ventas sample.csv")
df = df.groupby('Fecha')['Cantidad KG'].sum().reset_index()
df = df.sort_values('Fecha')

kf = TimeSeriesSplit(n_splits=3)

# Iterate through each split
fold = 0
for train_index, test_index in kf.split(df):
    cv_train, cv_test = df.iloc[train_index], df.iloc[test_index]

    print('Fold :', fold)
    print('Train date range: from {} to {}'.format(cv_train.Fecha.min(), cv_train.Fecha.max()))
    print('Test date range: from {} to {}\n'.format(cv_test.Fecha.min(), cv_test.Fecha.max()))
    fold += 1


from sklearn.model_selection import RandomizedSearchCV