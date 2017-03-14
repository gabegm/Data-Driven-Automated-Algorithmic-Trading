import functions as fc
import pandas as pd
import numpy as np
from sklearn.neighbors import KNeighborsRegressor
import matplotlib.pyplot as plt

AAPL = fc.return_ticker('AAPL')

fc.end_of_day_plot(AAPL['adj_close'], title='AAPL', xlabel='time', ylabel='$', legend='Adjusted Close $')

# add the outcome variable, 1 if the trading session was positive (close>open), 0 otherwise
AAPL['outcome'] = AAPL.apply(lambda x: 1 if x['adj_close'] > x['adj_open'] else -1, axis=1)

# distance between Highest and Opening price
AAPL['ho'] = AAPL['adj_high'] - AAPL['adj_open']

# distance between Lowest and Opening price
AAPL['lo'] = AAPL['adj_low'] - AAPL['adj_open']

# difference between Closing price - Opening price
AAPL['gain'] = AAPL['adj_close'] - AAPL['adj_open']

AAPL = fc.get_sma_features(AAPL).dropna()

training_set = AAPL[:-500]
test_set = AAPL[-500:]

# values of features
X = np.array(training_set[['sma_15', 'sma_50']].values)

# target values
Y = list(training_set['adj_close'])

# fit a k-nearest neighbor model to the data
mdl = KNeighborsRegressor().fit(X, Y)
print(mdl)

# make predictions
pred = mdl.predict(test_set[['sma_15', 'sma_50']].values)

results = pd.DataFrame(data=dict(original=test_set['outcome'], prediction=pred), index=test_set.index)

fig = plt.figure()
ax = fig.add_subplot(111)
ax.plot(results['original'])
ax.plot(results['prediction'])
ax.set(title='Time Series Plot', xlabel='time', ylabel='$')
ax.legend(['Original $', 'Forecast $'])
fig.tight_layout()