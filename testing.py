dicte = {'a':3,
         'b':2,
         'c':1}

for num, item in enumerate(dicte.items()):
    print('num:, ', num, 'key', item[0], 'value', item[1])


test = [range(0, 10)]

print(type(test[0]))
