import pandas as pd

ventas = pd.read_csv(r"C:\Users\Usuario\Documents\UCR\II-2020\Dirigida I\Diseño\Ventas.csv")
ventas.columns = ['Fecha', 'Cod_Prod', 'Nombre_Prod', 'Cantidad']
ventas = ventas.groupby(['Fecha', 'Cod_Prod', 'Nombre_Prod']).sum().reset_index()

recetas = pd.read_excel(r"C:\Users\Usuario\Documents\UCR\II-2020\Dirigida I\Diseño\Recetas.xlsx",
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

test = pd.DataFrame(recetas['Cod_Comp'].drop_duplicates())
test = test.merge(recetas[['Cod_Prod', 'Nombre_Prod']], left_on='Cod_Comp',
                  right_on='Cod_Prod', how='left')
test.dropna(subset=['Cod_Prod'], inplace=True)
test.drop_duplicates(subset=['Cod_Prod'], inplace=True)

recetas_sin_nom = recetas.drop(columns=['Nombre_Prod'])
ventas_test = ventas.merge(recetas,
                           on='Cod_Prod',
                           how='left')



