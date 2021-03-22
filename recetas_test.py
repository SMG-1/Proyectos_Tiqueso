import pandas as pd
import os

# leer archivo de ventas

path = r'C:\Users\Usuario\Desktop\Data Ticheese'

# leer archivo de ventas
ventas = pd.read_csv(os.path.join(path, "Ventas.csv"))
ventas.columns = ['Fecha', 'Cod_Prod', 'Nombre_Prod', 'Cantidad']

# agrupar ventas por fecha - producto
ventas = ventas.groupby(['Fecha', 'Cod_Prod', 'Nombre_Prod']).sum().reset_index()

# leer archivo de recetas
recetas = pd.read_excel(os.path.join(path, "Recetas.xlsx"),
                        sheet_name='OIT RECETAS',
                        header=1)
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

# crear tabla de productos intermedios, primero quitar codigos de componentes duplicados
intermedios = pd.DataFrame(recetas['Cod_Comp'].drop_duplicates()).dropna()
intermedios.columns = ['Cod_Inter']

# luego unir con recetas, usando cod intermedio como left key y cod prod como right key
# se obtienen los productos que son componentes pero tambien tienen sus propios componentes (intermedios)
intermedios = intermedios.merge(recetas, left_on='Cod_Inter', right_on='Cod_Prod', how='left')
intermedios.rename(columns={'Nombre_Prod': 'Nombre_Inter'}, inplace=True)
intermedios.drop(columns=['Cod_Prod'], inplace=True)
intermedios.dropna(subset=['Cod_Comp'], inplace=True)

# recetas_sin_nom = recetas.drop(columns=['Nombre_Prod'])
ventas_mp = ventas.merge(recetas.drop(columns=['Nombre_Prod']),
                           on='Cod_Prod',
                           how='left')

ventas_mp['Cant_Req'] = ventas_mp['Cantidad'] * ventas_mp['Cant_Comp']

ventas_mp = ventas_mp.groupby(['Cod_Comp', 'Nombre_Comp', 'Fecha'])['Cant_Req'].sum().reset_index()
ventas_mp = ventas_mp[~ventas_mp['Nombre_Comp'].str.contains('RECORTES')]
ventas_mp.columns = ['Cod_Prod', 'Nombre_Prod', 'Fecha', 'Cant_Req']
# mp = mp.merge(test, on=)

# volver a aplicar recetas para productos intermedios
ventas_mp_sin_inter = ventas_mp.merge(intermedios, left_on='Cod_Prod', right_on='Cod_Inter', how='left')
ventas_mp_sin_inter.loc[ventas_mp_sin_inter['Cod_Inter'].notna(), 'Cant_Req_Final'] = ventas_mp_sin_inter['Cant_Req'] * ventas_mp_sin_inter['Cant_Comp']
ventas_mp_sin_inter.loc[ventas_mp_sin_inter['Cod_Inter'].notna(), 'Codigo'] = ventas_mp_sin_inter['Cod_Comp']
ventas_mp_sin_inter.loc[ventas_mp_sin_inter['Cod_Inter'].notna(), 'Nombre'] = ventas_mp_sin_inter['Nombre_Comp']

ventas_mp_sin_inter.loc[ventas_mp_sin_inter['Cant_Req_Final'].isna(), 'Codigo'] = ventas_mp_sin_inter['Cod_Prod']
ventas_mp_sin_inter.loc[ventas_mp_sin_inter['Cant_Req_Final'].isna(), 'Nombre'] = ventas_mp_sin_inter['Nombre_Prod']
ventas_mp_sin_inter.loc[ventas_mp_sin_inter['Cant_Req_Final'].isna(), 'Cant_Req_Final'] = ventas_mp_sin_inter['Cant_Req']

ventas_mp_sin_inter = ventas_mp_sin_inter[['Codigo', 'Nombre', 'Fecha', 'Cant_Req_Final']]
ventas_mp_sin_inter.columns = ['Codigo', 'Nombre', 'Fecha', 'Demanda']

