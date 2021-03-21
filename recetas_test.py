import pandas as pd

# leer archivo de ventas
ventas = pd.read_csv(r"C:\Users\smirand27701\Desktop\Nueva carpeta\Ventas.csv")
ventas.columns = ['Fecha', 'Cod_Prod', 'Nombre_Prod', 'Cantidad']
ventas = ventas.groupby(['Fecha', 'Cod_Prod', 'Nombre_Prod']).sum().reset_index()

# leer Excel de recetas
recetas = pd.read_excel(r"C:\Users\smirand27701\Desktop\Nueva carpeta\Recetas.xlsx",
                        sheet_name='OIT RECETAS',
                        header=1)
# cambiar nombres
recetas = recetas.loc[:, ['Cod Receta',
                          'Desc Receta',
                          'Cant',
                          'UND',
                          'Cod Art',
                          'Descripción del artículo',
                          'Cantidad',
                          'Unidad de medida de inventario']]
recetas.columns = ['Cod_Prod', 'Nombre_Prod', 'Cant_Prod', 'Ud_Prod',
                   'Cod_Comp', 'Nombre_Comp', 'Cant_Comp', 'Ud_Comp']

# hacer un dataframe externo con los codigos duplicados de componentes removidos
test = pd.DataFrame(recetas['Cod_Comp'].drop_duplicates())

#
# test = test.merge(recetas[['Cod_Prod', 'Nombre_Prod']], left_on='Cod_Comp',
test = test.merge(recetas, left_on='Cod_Comp',
                  right_on='Cod_Prod', how='left')
test.dropna(subset=['Cod_Prod'], inplace=True)
test.drop_duplicates(subset=['Cod_Prod'], inplace=True)

recetas_sin_nom = recetas.drop(columns=['Nombre_Prod'])
ventas_test = ventas.merge(recetas_sin_nom,
                           on='Cod_Prod',
                           how='left')


ventas_test['Cant_Req'] = ventas_test['Cantidad'] * ventas_test['Cant_Comp']

mp = ventas_test.groupby(['Cod_Comp', 'Nombre_Comp', 'Fecha'])['Cant_Req'].sum().reset_index()
mp = mp[~mp['Nombre_Comp'].str.contains('RECORTES')]
mp = mp.merge(test, on=)