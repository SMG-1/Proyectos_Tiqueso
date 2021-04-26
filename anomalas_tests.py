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

df_ventas = df_ventas[['Código clientes SAP', 'Nombre de cliente/proveedor', 'Número de artículo',
                       'Descripción artículo/serv.', 'Fecha de contabilización', 'Cantidad KG']]
df_ventas.columns = ['Cliente_Cod', 'Cliente_Nombre', 'Producto_Cod', 'Producto_Nombre', 'Fecha', 'Cantidad_KG']

group_cols = ['Cliente_Cod',
              'Producto_Cod']
df_ventas_25 = df_ventas.groupby(group_cols)['Cantidad_KG'].quantile(0.05).reset_index()
df_ventas_25 = df_ventas_25.rename(columns={'Cantidad_KG': 'Min'})
df_ventas_75 = df_ventas.groupby(group_cols)['Cantidad_KG'].quantile(0.95).reset_index()
df_ventas_75 = df_ventas_75.rename(columns={'Cantidad_KG': 'Max'})

df_ventas = df_ventas.merge(df_ventas_25, on=group_cols, how='left')
df_ventas = df_ventas.merge(df_ventas_75, on=group_cols, how='left')

df_ventas['Alerta'] = 0

df_ventas.loc[(df_ventas['Cantidad_KG'] < df_ventas['Min']) |
              (df_ventas['Cantidad_KG'] > df_ventas['Max']), 'Alerta'] = 1

test = df_ventas[df_ventas['Alerta'] == 1]

trained = df_ventas.drop_duplicates(subset=['Cliente_Cod', 'Producto_Cod'])
trained = trained[['Cliente_Cod', 'Producto_Cod', 'Min', 'Max']]
trained.loc[trained['Min'] < 0, 'Min'] = 0

trained.to_csv('Anomalas_Modelo.csv',
               index=False,
               sep=',')
