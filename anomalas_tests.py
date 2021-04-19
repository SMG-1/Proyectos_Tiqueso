import pandas as pd
import matplotlib.pyplot as plt

df_ventas2019 = pd.read_excel(r"C:\Users\smirand27701\Desktop\Varios Tiqueso\VENTAS 2019 + SAP (2).xlsm",
                              sheet_name='2019 + SAP')
df_ventas2020 = pd.read_excel(r"C:\Users\smirand27701\Desktop\Varios Tiqueso\ventas AGO - OCT 2020.xlsx",
                              sheet_name='VENTA con clientes nuevos categ')

df_ventas_total = pd.concat([df_ventas2019, df_ventas2020], axis=0)
df_ventas_total = df_ventas_total.iloc[:, :-2]

df_ventas_total.to_csv(r'C:\Users\smirand27701\Desktop\Varios Tiqueso\Ventas_Total.csv', index=False)