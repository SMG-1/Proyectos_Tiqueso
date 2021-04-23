import pandas as pd
import matplotlib.pyplot as plt



path = ''
df_ventas = pd.read_csv(r"C:\Users\smirand27701\Desktop\Varios Tiqueso\Ventas_Total.csv")

try:
    df_ventas['Fecha de contabilización'] = pd.to_datetime(df_ventas['Fecha de contabilización'])
except ValueError:
    df_ventas['Fecha de contabilización'] = pd.to_datetime(df_ventas['Fecha de contabilización'],
                                                           format='%d/%m/%Y')

df_ventas = df_ventas.sort_values(['Nombre de cliente/proveedor', 'Fecha de contabilización'])

df_ventas = df_ventas[['Nombre de cliente/proveedor', 'Fecha de contabilización', 'Cantidad KG']]


df_ventas_25 = df_ventas.groupby(['Nombre de cliente/proveedor'])['Cantidad KG'].quantile(0.05).reset_index()
df_ventas_25.columns = ['Nombre de cliente/proveedor', 'Min']
df_ventas_75 = df_ventas.groupby(['Nombre de cliente/proveedor'])['Cantidad KG'].quantile(0.95).reset_index()
df_ventas_75.columns = ['Nombre de cliente/proveedor', 'Max']

df_ventas = df_ventas.merge(df_ventas_25, on='Nombre de cliente/proveedor', how='left')
df_ventas = df_ventas.merge(df_ventas_75, on='Nombre de cliente/proveedor', how='left')

df_ventas['Alerta'] = 0


df_ventas.loc[(df_ventas['Cantidad KG'] < df_ventas['Min']) |
              (df_ventas['Cantidad KG'] > df_ventas['Hax']), 'Alerta'] = 1

test = df_ventas[df_ventas['Alerta'] == 1]

trained = df_ventas.drop_duplicates(subset=['Nombre de cliente/proveedor'])
trained = trained[['Nombre de cliente/proveedor', 'Low', 'High']]
trained.loc[trained['Low'] < 0, 'Low'] = 0






