dicte = {'a': 3,
         'b': 2,
         'c': 1}

for num, item in enumerate(dicte.items()):
    print('num:, ', num, 'key', item[0], 'value', item[1])

test = [range(0, 10)]

print(type(test[0]))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

data = pd.DataFrame(np.random.randint(10, size=(100,)))
data['Test'] = np.random.randint(10, size=(100,))
data['Test2'] = np.random.randint(10, size=(100,))
data['Test3'] = np.random.randint(10, size=(100,))
data = data.reset_index()

# create plot with index as X value, and demand as y value
ax = data.plot(x='index', y='Test', legend=False)
ax2 = ax.twinx()
data.plot(x='index', y='Test2', ax=ax, legend=False, color="r")
ax.figure.legend()
plt.show()
