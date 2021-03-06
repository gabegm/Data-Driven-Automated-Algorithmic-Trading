"""
Module Docstring
"""

__author__ = "Gabriel Gauci Maistre"
__version__ = "0.1.0"
__license__ = "MIT"

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import quandl as qdl
import scipy.stats as stats
import statsmodels.api as sm
import statsmodels.tsa.api as smt
import talib as ta
from arch.unitroot import KPSS
from matplotlib import mlab
from mpl_finance import candlestick_ohlc
from pandas.tseries.holiday import USFederalHolidayCalendar
from scipy.stats import shapiro, kstest, anderson
from scipy.stats.mstats import normaltest
from sklearn import metrics
from sklearn.svm import SVC, LinearSVC
from sqlalchemy import create_engine
from statsmodels.tsa.arima_model import ARMA, ARIMA
from statsmodels.tsa.stattools import adfuller
from talib import MA_Type

import keys

pd.options.mode.chained_assignment = None  # default='warn'
plt.style.use('ggplot')


def get_time_series(ticker=None, start_date=None, end_date=None, file_location="data/WIKI_PRICES.csv"):
    """
    returns end-of-day data of the selected ticker in the format of a dataframe 
    if condition checks if one ticker or a list of tickers are being passed
    :param file_location: 
    :param ticker: 
    :param start_date:
    :param end_date:
    :return: 
    """
    df = pd.read_csv(file_location, index_col='date', parse_dates=True)
    df.index = df.index.tz_localize('UTC').tz_convert('UTC')

    if ticker is None:
        return df
    elif isinstance(ticker, list):
        df = df.loc[df['ticker'].isin(ticker)]
    else:
        df = df.loc[df['ticker'] == ticker]

    if start_date is not None:
        if start_date and end_date is not None:
            df = df.loc[(df.index > start_date) & (df.index <= end_date)]
        df = df.loc[(df.index > start_date)]

    df = df[np.isfinite(df['adj_close'])]

    return df


def get_correlated_time_series(df, save=False):
    """
    pivots the dataframe to return the correlations of the stocks in the dataframe
    :param df:
    :param save:
    :return: 
    """
    # pivoting the DataFrame to create a column for every ticker
    df = df.pivot(index=None, columns='ticker', values='adj_close')

    # creating a DataFrame with the correlation values of every column to every column
    df = df.corr()

    if save:
        df.to_csv("data/df_corr.csv")

    return df


def get_positively_correlated_stocks(df, correlation=0.5):
    """
    Returns a list of positively correlated stocks from a correlated dataframe
    :param df: 
    :param correlation:
    :return: 
    """
    indices = np.where(df > correlation)
    indices = [(df.index[x], df.columns[y]) for x, y in zip(*indices) if x != y and x < y]

    return indices


def get_negatively_correlated_stocks(df, correlation=-0.5):
    """
    Returns a list of negatively correlated stocks from a correlated dataframe
    :param df:
    :param correlation:
    :return: 
    """
    indices = np.where(df < correlation)
    indices = [(df.index[x], df.columns[y]) for x, y in zip(*indices) if x != y and x < y]

    return indices


def get_neutrally_correlated_stocks(df, correlation=0.5):
    """
    Returns a list of neutrally correlated stocks from a correlated dataframe
    :param df:
    :param correlation:
    :return: 
    """
    indices = np.where((df < correlation) & (df > -correlation))
    indices = [(df.index[x], df.columns[y]) for x, y in zip(*indices) if x != y and x < y]

    return indices


def get_stocks_from_list(stocks, ticker):
    """
    returns a list of matching stocks in a list
    :param stocks: 
    :param ticker: 
    :return: 
    """
    matching = [s for s in stocks if ticker in s]

    tickers = np.unique(matching)

    return tickers


def get_correlated_stocks_list(df_corr):
    """
    returns a string list from the tickers in the list
    :param df_corr:
    :return:
    """
    stocks = get_neutrally_correlated_stocks(df_corr, correlation=0.1)

    tickers = list(set(stocks))

    tickers = np.reshape(tickers, (-1, 1)).tolist()

    tickers = [item for sublist in tickers for item in sublist][:15]

    return tickers


def get_sma(close, days, window):
    """
    Calculates the simple moving average of the security
    :param close:
    :param days:
    :param window:
    :return:
    """
    sma = ta.SMA(np.array(close), days)[window - 1:]

    # drop nan values
    sma = sma[~np.isnan(sma)]

    return sma


def get_percentage_difference(first, last):
    """
    Calculates the percentage of the portfolio to allocate based on the percentage increase
    :param first:
    :param last:
    :return:
    """
    percent = ((last - first) / first) * 10

    percent = float(np.around(percent, 2))

    return percent


def flatten_list(l):
    """
    flattens a list of lists
    :param l:
    :return:
    """
    return [item for sublist in l for item in sublist]


def get_sharpe_ratio(returns, N=252):
    """
    Calculate the annualised Sharpe ratio of a returns stream
    based on a number of trading periods, N. N defaults to 252,
    which then assumes a stream of daily returns.

    The function assumes that the returns are the excess of
    those compared to a benchmark.
    """

    # Assume an average annual risk-free rate over the period of 5%
    excess_daily_ret = returns - 0.05 / 252

    return np.sqrt(N) * np.mean(excess_daily_ret) / np.std(excess_daily_ret)


def plot_end_of_day(df, stocks=None, title=None, xlabel=None, ylabel=None, legend=None, save=False):
    """
    plots the end-of-day close price for the specified ticker(s)
    :param df: 
    :param stocks: 
    :param title: 
    :param xlabel: 
    :param ylabel: 
    :param legend: 
    :param save: 
    :return: 
    """
    fig = plt.figure()
    ax = fig.add_subplot(111)

    if stocks is not None:
        for stock in stocks:
            ax.plot(df[stock])
            ax.legend(stocks)
    else:
        ax.plot(df)
        ax.legend([legend])

    ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
    fig.tight_layout()

    if save:
        fig.savefig("charts/{}.png".format(title))


def plot_ticker(df):
    fig = plt.figure()
    ax1 = plt.subplot2grid((6, 1), (0, 0), rowspan=5, colspan=1)
    ax1.plot(df['adj_close'])
    ax1.plot(df['adj_close'].rolling(window=100, min_periods=0).mean())
    ax1.set(title='Time Series Plot', xlabel='time', ylabel='$')
    ax1.legend(['Adjusted Close $', '100 day moving average'])
    ax2 = plt.subplot2grid((6, 1), (5, 0), rowspan=1, colspan=1, sharex=ax1)
    ax2.bar(df.index, df['adj_volume'])
    ax2.set(title='Time Series Plot', xlabel='time', ylabel='$')
    ax2.legend(['Volume'])
    fig.tight_layout()


def get_stationarity_statistics(df):
    """
    returns a list of stationary statistics for the dataframe being passed
    :param df: 
    :return: 
    """
    # verify stationarity
    adfstat, pvalue, critvalues, resstore = adfuller(df, regression="nc", store=True, regresults=True)

    # D’Agostino and Pearson normality test of returns
    dagostino_results = normaltest(df)

    # Shapiro-Wilk normality test
    shapiro_results = shapiro(df)

    # Kolmogorov-Smirnov normality test
    ks_results = kstest(df, cdf='norm')

    # Anderson-Darling normality test
    anderson_results = anderson(df)

    # Kwiatkowski-Phillips-Schmidt-Shin normality test
    kpss_results = KPSS(df)

    return adfstat, pvalue, critvalues, resstore, dagostino_results, shapiro_results, ks_results, anderson_results, kpss_results


def get_stock_statistics(df):
    """
    returns a series of statistics
    :param df: 
    :return: 
    """
    mean = df.mean(axis=0)
    median = df.median(axis=0)
    maximum = df.max(axis=0)
    minimum = df.min(axis=0)
    var = df.var(axis=0)
    std = df.std(axis=0)
    skewness = df.skew(axis=0)
    kurtosis = df.kurtosis(axis=0)

    return mean, median, maximum, minimum, var, std, skewness, kurtosis


def get_classifier_metrics(original, prediction):
    classification_report = metrics.classification_report(original, prediction)
    confusion_matrix = metrics.confusion_matrix(original, prediction)

    return classification_report, confusion_matrix


def get_regression_metrics(original, prediction):
    explained_variance_score = metrics.explained_variance_score(original, prediction)
    mean_absolute_error = metrics.mean_absolute_error(original, prediction)
    mean_squared_error = metrics.mean_squared_error(original, prediction)
    median_absolute_error = metrics.median_absolute_error(original, prediction)
    r2_score = metrics.r2_score(original, prediction)

    return explained_variance_score, mean_absolute_error, mean_squared_error, median_absolute_error, r2_score


def plot_histogram(y, ticker='', title=''):
    """
    plots a histogram of the stock returns
    :param title:
    :param ticker:
    :param y:
    :return:
    """
    fig = plt.figure()

    mu = np.mean(y)  # mean of distribution
    sigma = np.std(y)  # standard deviation of distribution
    x = mu + sigma * np.random.randn(10000)

    num_bins = 50
    # the histogram of the data
    n, bins, patches = plt.hist(x, num_bins, normed=1, facecolor='green', alpha=0.5)
    # add a 'best fit' line
    y = mlab.normpdf(bins, mu, sigma)
    plt.plot(bins, y, 'r--')
    plt.xlabel('returns')
    plt.ylabel('probability')
    plt.title('{} Histogram of returns \n $\mu={}$ \n $\sigma={}$'.format(ticker, mu, sigma))

    # Tweak spacing to prevent clipping of ylabel
    plt.subplots_adjust(left=0.15)
    fig.tight_layout()
    fig.savefig('charts/{}-{}-histogram.png'.format(ticker, title))


def plot_time_series(y, lags=None, ticker='', title=''):
    """
    plots the stock return, acf, pacf, and qq 
    :param ticker: 
    :param y: 
    :param lags: 
    :return: 
    """
    if not isinstance(y, pd.Series):
        y = pd.Series(y)

    fig = plt.figure()
    ax1 = plt.subplot2grid((3, 2), (0, 0), colspan=2)
    ax2 = plt.subplot2grid((3, 2), (1, 0))
    ax3 = plt.subplot2grid((3, 2), (1, 1))
    ax4 = plt.subplot2grid((3, 2), (2, 0))
    ax5 = plt.subplot2grid((3, 2), (2, 1))

    ax1.plot(y)
    smt.graphics.plot_acf(y, lags=lags, ax=ax2, alpha=0.5)
    smt.graphics.plot_pacf(y, lags=lags, ax=ax3, alpha=0.5)
    sm.qqplot(y, line='s', ax=ax4)
    stats.probplot(y, sparams=(y.mean(), y.std()), plot=ax5)

    ax1.set_title('{} Time Series Analysis Plots'.format(ticker))
    ax4.set_title('QQ Plot')

    fig.tight_layout()
    if title is not '':
        fig.savefig('charts/{}-{}-time-series.png'.format(ticker, title))
    else:
        fig.savefig('charts/{}-time-series.png'.format(ticker))


def plot_svm(X, Y, ylabel, xlabel):
    h = .02  # step size in the mesh

    # we create an instance of SVM and fit out data. We do not scale our
    # data since we want to plot the support vectors
    C = 1.0  # SVM regularization parameter
    svc = SVC(kernel='linear', C=C).fit(X, Y)
    rbf_svc = SVC(kernel='rbf', gamma=0.7, C=C).fit(X, Y)
    poly_svc = SVC(kernel='poly', degree=3, C=C).fit(X, Y)
    lin_svc = LinearSVC(C=C).fit(X, Y)

    # create a mesh to plot in
    x_min, x_max = X[:, 0].min() - 1, X[:, 0].max() + 1
    y_min, y_max = X[:, 1].min() - 1, X[:, 1].max() + 1
    xx, yy = np.meshgrid(np.arange(x_min, x_max, h),
                         np.arange(y_min, y_max, h))

    # title for the plots
    titles = ['SVC with linear kernel',
              'LinearSVC (linear kernel)',
              'SVC with RBF kernel',
              'SVC with polynomial (degree 3) kernel']

    for i, clf in enumerate((svc, lin_svc, rbf_svc, poly_svc)):
        # Plot the decision boundary. For that, we will assign a color to each
        # point in the mesh [x_min, x_max]x[y_min, y_max].
        plt.subplot(2, 2, i + 1)
        plt.subplots_adjust(wspace=0.4, hspace=0.4)

        Z = clf.predict(np.c_[xx.ravel(), yy.ravel()])

        # Put the result into a color plot
        Z = Z.reshape(xx.shape)
        plt.contourf(xx, yy, Z, cmap=plt.cm.coolwarm, alpha=0.8)

        # Plot also the training points
        plt.scatter(X[:, 0], X[:, 1], c=Y, cmap=plt.cm.coolwarm)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.xlim(xx.min(), xx.max())
        plt.ylim(yy.min(), yy.max())
        plt.xticks(())
        plt.yticks(())
        plt.title(titles[i])


def plot_svm_2(X, Y):
    # figure number
    fignum = 1

    # fit the model
    for name, penalty in (('unreg', 1), ('reg', 0.05)):
        clf = SVC(kernel='linear', C=penalty)
        clf.fit(X, Y)

        # get the separating hyperplane
        w = clf.coef_[0]
        a = -w[0] / w[1]
        xx = np.linspace(-5, 5)
        yy = a * xx - (clf.intercept_[0]) / w[1]

        # plot the parallels to the separating hyperplane that pass through the
        # support vectors
        margin = 1 / np.sqrt(np.sum(clf.coef_ ** 2))
        yy_down = yy + a * margin
        yy_up = yy - a * margin

        # plot the line, the points, and the nearest vectors to the plane
        plt.figure(fignum, figsize=(4, 3))
        plt.clf()
        plt.plot(xx, yy, 'k-')
        plt.plot(xx, yy_down, 'k--')
        plt.plot(xx, yy_up, 'k--')

        plt.scatter(clf.support_vectors_[:, 0], clf.support_vectors_[:, 1], s=80,
                    facecolors='none', zorder=10)
        plt.scatter(X[:, 0], X[:, 1], c=Y, zorder=10, cmap=plt.cm.Paired)

        plt.axis('tight')
        x_min = -4.8
        x_max = 4.2
        y_min = -6
        y_max = 6

        XX, YY = np.mgrid[x_min:x_max:200j, y_min:y_max:200j]
        Z = clf.predict(np.c_[XX.ravel(), YY.ravel()])

        # Put the result into a color plot
        Z = Z.reshape(XX.shape)
        plt.figure(fignum, figsize=(4, 3))
        plt.pcolormesh(XX, YY, Z, cmap=plt.cm.Paired)

        plt.xlim(x_min, x_max)
        plt.ylim(y_min, y_max)

        plt.xticks(())
        plt.yticks(())
        fignum = fignum + 1


def get_best_ma_model(df):
    """
    loops through all ma models and returns the best one based on the dataframe passed
    :param df: 
    :return: 
    """
    best_aic = np.inf
    best_order = None
    best_mdl = None

    rng = range(11)
    for j in rng:
        try:
            tmp_mdl = ARMA(df, order=(0, j)).fit(maxlag=30, method='mle', trend='nc', disp=-1)
            tmp_aic = tmp_mdl.aic
            if tmp_aic < best_aic:
                best_aic = tmp_aic
                best_order = (0, j)
                best_mdl = tmp_mdl
        except:
            continue

    print('aic: {:6.5f} | order: {}'.format(best_aic, best_order))
    return best_aic, best_order, best_mdl


def get_best_arma_model(df):
    """
    loops through all arma models and returns the best one based on the dataframe passed
    :param df: 
    :return: 
    """
    best_aic = np.inf
    best_order = None
    best_mdl = None

    rng = range(5)  # [0,1,2,3,4,5]
    for i in rng:
        for j in rng:
            try:
                tmp_mdl = ARMA(df, order=(i, j)).fit(method='mle', trend='nc', disp=-1)
                tmp_aic = tmp_mdl.aic
                if tmp_aic < best_aic:
                    best_aic = tmp_aic
                    best_order = (i, j)
                    best_mdl = tmp_mdl
            except:
                continue

    print('aic: {:6.5f} | order: {}'.format(best_aic, best_order))
    return best_aic, best_order, best_mdl


def get_best_arima_model(df):
    """
    loops through all arima models and returns the best one based on the dataframe passed
    :param df: 
    :return: 
    """
    # Fit ARIMA(p, d, q) model to SPY Returns
    # pick best order and final model based on aic

    best_aic = np.inf
    best_order = None
    best_mdl = None

    pq_rng = range(6)
    d_rng = range(3)
    for i in pq_rng:
        for d in d_rng:
            for j in pq_rng:
                try:
                    tmp_mdl = ARIMA(df, order=(i, d, j)).fit(method='mle', trend='nc', disp=-1)
                    tmp_aic = tmp_mdl.aic
                    if tmp_aic < best_aic:
                        best_aic = tmp_aic
                        best_order = (i, d, j)
                        best_mdl = tmp_mdl
                except:
                    continue

    print('aic: {:6.5f} | order: {}'.format(best_aic, best_order))
    return best_aic, best_order, best_mdl


def get_best_garch_model(df):
    """
    loops through all garch models and returns the best one based on the dataframe passed
    :param df: 
    :return: 
    """
    best_aic = np.inf
    best_order = None
    best_mdl = None

    pq_rng = range(5)  # [0,1,2,3,4]
    d_rng = range(2)  # [0,1]
    for i in pq_rng:
        for d in d_rng:
            for j in pq_rng:
                try:
                    tmp_mdl = smt.ARIMA(df, order=(i, d, j)).fit(method='mle', trend='nc')
                    tmp_aic = tmp_mdl.aic
                    if tmp_aic < best_aic:
                        best_aic = tmp_aic
                        best_order = (i, d, j)
                        best_mdl = tmp_mdl
                except:
                    continue
    print('aic: {:6.5f} | order: {}'.format(best_aic, best_order))
    return best_aic, best_order, best_mdl


def get_best_sarimax_model(df):
    """
    loops through all sarimax models and returns the best one based on the dataframe passed
    :param df: 
    :return: 
    """
    best_aic = np.inf
    best_order = None
    best_mdl = None

    pq_rng = range(5)  # [0,1,2,3,4]
    d_rng = range(2)  # [0,1]
    for i in pq_rng:
        for d in d_rng:
            for j in pq_rng:
                try:
                    tmp_mdl = sm.tsa.SARIMAX(df, order=(i, d, j)).fit(mle_regression=True, trend='nc')
                    tmp_aic = tmp_mdl.aic
                    if tmp_aic < best_aic:
                        best_aic = tmp_aic
                        best_order = (i, d, j)
                        best_mdl = tmp_mdl
                except:
                    continue
    print('aic: {:6.5f} | order: {}'.format(best_aic, best_order))
    return best_aic, best_order, best_mdl


def get_technical_analysis_features(df):
    """
    calculates a number of technical analyses to use as features 
    :param df: 
    :return: 
    """
    # calculate a simple moving average of the close prices
    df['sma_5'] = ta.SMA(np.array(df['adj_close']), 5)

    # 50 day simple moving average
    df['sma_50'] = ta.SMA(np.array(df['adj_close']), 20)

    # calculating bollinger bands, with triple exponential moving average
    df['upper'], df['middle'], df['lower'] = ta.BBANDS(np.array(df['adj_close']), matype=MA_Type.T3)

    # calculating momentum of the close prices, with a time period of 5
    df['mom_adj_close'] = ta.MOM(np.array(df['adj_close']), timeperiod=5)

    # AD - Chaikin A/D Line
    df['AD'] = ta.AD(np.array(df['adj_high']),
                     np.array(df['adj_low']),
                     np.array(df['adj_close']),
                     np.array(df['adj_volume']))

    # ADOSC - Chaikin A/D Oscillator
    df['ADOSC'] = ta.ADOSC(np.array(df['adj_high']),
                           np.array(df['adj_low']),
                           np.array(df['adj_close']),
                           np.array(df['adj_volume']), fastperiod=3, slowperiod=10)

    # OBV - On Balance Volume
    df['OBV'] = ta.OBV(np.array(df['adj_close']), np.array(df['adj_volume']))

    df['TRANGE'] = ta.TRANGE(np.array(df['adj_high']),
                             np.array(df['adj_low']),
                             np.array(df['adj_close']))

    return df


def get_lagged_features(df):
    """
    generates a lagged time series and returns the features for the classifier
    :param df: 
    :return: 
    """
    # generate lagged time series
    TS_1 = df.shift(1)
    TS_2 = df.shift(2)
    TS_3 = df.shift(3)
    TS_4 = df.shift(4)
    TS_5 = df.shift(5)

    df['feat1'] = df['adj_close'] > TS_1['adj_close']
    df['feat2'] = df['adj_close'] > TS_2['adj_close']
    df['feat3'] = df['adj_close'] > TS_3['adj_close']
    df['feat4'] = df['adj_close'] > TS_4['adj_close']
    df['feat5'] = df['adj_close'] > TS_5['adj_close']

    return df


def get_sma_regression_features(df):
    """
    calculates the 15 and 50 day simple moving average and returns the features for the regression
    :param df: 
    :return: 
    """
    # calculate a simple moving average of the close prices
    df['sma_15'] = ta.SMA(np.array(df['adj_close'].shift(1)), 15)

    # 50 day simple moving average
    df['sma_50'] = ta.SMA(np.array(df['adj_close'].shift(1)), 50)

    return df


def get_sma_classifier_features(df):
    """
    calculates the 2-6 day simple moving average and returns the features for the classifier
    :param df: 
    :return: 
    """
    df['sma_2'] = ta.SMA(np.array(df['adj_close'].shift(1)), 2)
    df['sma_3'] = ta.SMA(np.array(df['adj_close'].shift(1)), 3)
    df['sma_4'] = ta.SMA(np.array(df['adj_close'].shift(1)), 4)
    df['sma_5'] = ta.SMA(np.array(df['adj_close'].shift(1)), 5)
    df['sma_6'] = ta.SMA(np.array(df['adj_close'].shift(1)), 6)

    df['sma_2'] = df.apply(lambda x: 1 if x['adj_close'] > x['sma_2'] else 0, axis=1)
    df['sma_3'] = df.apply(lambda x: 1 if x['adj_close'] > x['sma_3'] else 0, axis=1)
    df['sma_4'] = df.apply(lambda x: 1 if x['adj_close'] > x['sma_4'] else 0, axis=1)
    df['sma_5'] = df.apply(lambda x: 1 if x['adj_close'] > x['sma_5'] else 0, axis=1)
    df['sma_6'] = df.apply(lambda x: 1 if x['adj_close'] > x['sma_6'] else 0, axis=1)

    return df


def generate_proj_returns(burn_in, trace, len_to_train):
    num_pred = 1000
    mod_returns = np.ones(shape=(num_pred, len_to_train))
    vol = np.ones(shape=(num_pred, len_to_train))
    for k in range(0, num_pred):
        nu = trace[burn_in + k]['nu']
        mu = trace[burn_in + k]['mu']
        sigma = trace[burn_in + k]['sigma']
        s = trace[burn_in + k]['logs'][-1]
        for j in range(0, len_to_train):
            cur_log_return, s = _generate_proj_returns(mu,
                                                       s,
                                                       nu,
                                                       sigma)
            mod_returns[k, j] = cur_log_return
            vol[k, j] = s
    return mod_returns, vol


def _generate_proj_returns(mu, volatility, nu, sig):
    next_vol = np.random.normal(volatility, scale=sig)  # sig is SD

    # Not 1/np.exp(-2*next_vol), scale treated differently in scipy than pymc3
    log_return = stats.t.rvs(nu, mu, scale=np.exp(-1 * next_vol))
    return log_return, next_vol


def get_log_prices(prices, df, test_set):
    """
    converts the end of day close prices to log and returns them
    :param prices: 
    :param df: 
    :param test_set: 
    :return: 
    """
    for k in range(0, len(prices)):
        cur = np.log(df.values[test_set[0]])
        for j in range(0, len(prices[k])):
            cur = cur + prices[k, j]
            prices[k, j] = cur

    return prices


def plot_correlation(df_corr):
    """
    plots a heatmap of the correlations between stocks
    red (negative correlations)
    yellow (no correlations)
    green (positive correlations)
    :param df_corr: 
    :return: 
    """
    # creating an array of the values of correlations in the DataFrame
    data1 = df_corr.values

    fig1 = plt.figure()
    ax1 = fig1.add_subplot(111)

    # changes the fontsize of the tick label
    ax1.tick_params(axis='both', labelsize=12)

    heatmap1 = ax1.pcolor(data1, cmap=plt.cm.RdYlGn)

    # creating a colour side bar as a scale for the heatmap
    fig1.colorbar(heatmap1)

    # setting the ticks of the x-axis
    ax1.set_xticks(np.arange(data1.shape[1]) + 0.5, minor=False)

    # setting the ticks of the y-axis
    ax1.set_yticks(np.arange(data1.shape[0]) + 0.5, minor=False)

    # inverts the scale of the y-axis
    ax1.invert_yaxis()

    # places the x-axis at the top of the graph
    ax1.xaxis.tick_top()

    # storing the ticker labels in an array
    column_labels = df_corr.columns

    # storing the dates in an array
    row_labels = df_corr.index

    # setting the x-axis labels to the dates
    ax1.set_xticklabels(column_labels)

    # setting the y-axis labels to the ticker labels
    ax1.set_yticklabels(row_labels)

    # rotates the x-axis labels vertically to fit the graph
    plt.xticks(rotation=90)

    # sets the range from -1 to 1
    heatmap1.set_clim(-1, 1)

    # automatically adjusts subplot paramaters to give specified padding
    plt.tight_layout()


def plot_candlestick(df):
    """
    Plots a candlestick chart of the time series
    :param df: 
    :return: 
    """
    # creating a new DataFrame based on the adjusted_close price resampled with a 10 day window
    tickers_ohlc = df['adj_close'].resample('10D').ohlc()

    # creating a new DataFrame based on the adjusted volume resampled with a 10 day window
    tickers_volume = df['adj_volume'].resample('10D').sum()

    # resetting the index of the DataFrame
    tickers_ohlc = tickers_ohlc.reset_index()

    # converting the date column to mdates
    tickers_ohlc['date'] = tickers_ohlc['date'].map(mdates.date2num)

    # creating a new figure
    fig = plt.figure()

    # creating a subplot with a 6x1 grid and starts at (0,0)
    ax1 = plt.subplot2grid((6, 1), (0, 0), rowspan=5, colspan=1)

    # creating a subplot with a 6x1 grid and starts at (5,0)
    ax2 = plt.subplot2grid((6, 1), (5, 0), rowspan=1, colspan=1, sharex=ax1)

    # converts the axis from raw mdate numbers to dates
    ax1.xaxis_date()

    # plotting the candlestick graph
    candlestick_ohlc(ax1, tickers_ohlc.values, width=2, colorup='g')

    # plotting the volume bar chart
    ax2.fill_between(tickers_volume.index.map(mdates.date2num), tickers_volume.values, 0)

    fig.tight_layout()


def forecast_classifier(model, sample, features, steps=1):
    """
    forecasts n steps ahead using a classifier
    :param model: 
    :param sample: 
    :param features: 
    :param steps: 
    :return: 
    """
    for k in range(1, steps):
        sample.index = sample.index + pd.DateOffset(1)
        sample['outcome'][-1:] = model.predict(sample[features][-2:][:1])
        sample = get_sma_classifier_features(sample)

    return sample


def forecast_regression(model, sample, features, steps=1):
    """
    forecasts n steps ahead using a regression
    skips public holidays and weekends
    :param model: 
    :param sample: 
    :param features: 
    :param steps: 
    :return: 
    """
    for k in range(1, steps):
        sample = sample.shift(periods=1, freq='D', axis=0)

        # if is_day_holiday(sample.index[-1:]):
        #   sample = sample.shift(periods=1, freq='B', axis=0)

        # while sample.index[-1:].weekday >= 5:
        #   sample = sample.shift(periods=1, freq='D', axis=0)

        sample['adj_close'][-1:] = model.predict(sample[features][-2:][:1])
        sample = get_sma_regression_features(sample)

    return sample


def is_day_holiday(date):
    """
    returns true if date passed is a holiday
    :param date: 
    :return: 
    """
    holiday = USFederalHolidayCalendar().holidays(start=date.strftime("%d-%m-%Y").item(),
                                                  end=date.strftime("%d-%m-%Y").item())

    if len(holiday) is 1:
        return True

    return False


def export_to_sql():
    DB_TYPE = 'postgresql'
    DB_DRIVER = 'psycopg2'
    DB_USER = 'admin'
    DB_PASS = 'password'
    DB_HOST = 'localhost'
    DB_PORT = '5432'
    DB_NAME = 'pandas_upsert'
    POOL_SIZE = 50
    TABLENAME = 'test_upsert'
    SQLALCHEMY_DATABASE_URI = '%s+%s://%s:%s@%s:%s/%s' % (DB_TYPE, DB_DRIVER, DB_USER,
                                                          DB_PASS, DB_HOST, DB_PORT, DB_NAME)

    ENGINE = create_engine(SQLALCHEMY_DATABASE_URI, pool_size=POOL_SIZE, max_overflow=0)

    pd.to_sql(TABLENAME, ENGINE, if_exists='append', index=False)


def download_data(dataset, start_date=None, end_date=None):
    """
    bulk download is currently not available to free access
    :param dataset: 
    :param start_date: 
    :param end_date: 
    :return: 
    """
    # quandl.get(":database_code/:dataset_code", returns = ":return_format")
    qdl.ApiConfig.api_key = keys.quandl_api

    # When returns is omitted, a pandas dataframe is returned
    data = qdl.get(dataset, start_date=start_date, end_date=end_date)

    return data


def zipline_fix():
    df = pd.read_csv('data/^GSPC.csv', index_col='Date', parse_dates=True)
    df.index = df.index.tz_localize('UTC').tz_convert('UTC')
    df = df.convert_objects(convert_numeric=True)
    df = df['Adj Close'].pct_change()
    df.to_csv('~/.zipline/data/^GSPC_benchmark.csv')
