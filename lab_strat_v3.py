# --- Do not remove these libs ---
import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame

from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter,
                                IStrategy, IntParameter, merge_informative_pair)

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
import pandas_ta as pta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from functools import reduce
from astral import moon
import datetime
"""
Idea of strategy is to sit patiently in fiat when market is decreasing, wait for bull market, sell high and then repeat
"""

def ssl_atr(dataframe, length = 7):
    df = dataframe.copy()
    df['smaHigh'] = df['high'].rolling(length).mean() + df['atr']
    df['smaLow'] = df['low'].rolling(length).mean() - df['atr']
    df['hlv'] = np.where(df['close'] > df['smaHigh'], 1, np.where(df['close'] < df['smaLow'], -1, np.NAN))
    df['hlv'] = df['hlv'].ffill()
    df['sslDown'] = np.where(df['hlv'] < 0, df['smaHigh'], df['smaLow'])
    df['sslUp'] = np.where(df['hlv'] < 0, df['smaLow'], df['smaHigh'])
    return df['sslDown'], df['sslUp']

class lab_strat_v3(IStrategy):

    INTERFACE_VERSION = 2

    buy_ema_period = IntParameter(10, 365, default=18, space="buy")
    buy_ema_test = IntParameter(10, 365, default=132, space="buy")
    sell_btc_ema_period = IntParameter(20, 300, default=37, space="sell")
    sell_ema_period = IntParameter(20, 300, default=74, space="sell")
    # Optimal timeframe for the strategy.
    timeframe = '4h'

    # ROI table:
    minimal_roi = {
      "0": 1
    }
    # Optimal stoploss designed for the strategy.
    # This attribute will be overridden if the config file contains "stoploss"
    stoploss = -0.99

    # Trailing stop:
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.079
    trailing_only_offset_is_reached = True
    # Run "populate_indicators()" only for new candle.
    process_only_new_candles = False

    # These values can be overridden in the "ask_strategy" section in the config.
    use_sell_signal = True
    sell_profit_only = False
    ignore_roi_if_buy_signal = False

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 30

    # Optional order type mapping.
    order_types = {
        'buy': 'limit',
        'sell': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    # Optional order time in force.
    order_time_in_force = {
        'buy': 'gtc',
        'sell': 'gtc'
    }

    def informative_pairs(self):
        # TODO: maybe it's better to use shorter timeframe on one of the sides? e.g. sell-off faster
        return [(f'BTC/USDT', '1d')]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        informative = self.dp.get_pair_dataframe(pair=f'BTC/USDT', timeframe='1d')

        for val in self.buy_ema_period.range:
            informative[f'buy_ema_{val}'] = ta.EMA(informative, timeperiod=val)

        for val in self.sell_btc_ema_period.range:
            informative[f'sell_ema_{val}'] = ta.EMA(informative, timeperiod=val)

        dataframe = merge_informative_pair(dataframe, informative, self.timeframe, '1d', ffill=True)

        for val in self.buy_ema_test.range:
            dataframe[f'ema_{val}'] = ta.EMA(dataframe, timeperiod=val)

        for val in self.sell_ema_period.range:
            dataframe[f'sell_ema_{val}'] = ta.EMA(dataframe, timeperiod=val)

        dataframe['efi_base'] = ((dataframe['close'] - dataframe['close'].shift()) * dataframe['volume'])
        dataframe['efi'] = ta.EMA(dataframe['efi_base'], 13)
        dataframe['efi_ok'] = (dataframe['efi'] > 0).astype('int')

        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        dataframe['ema_ok'] = (
                (dataframe['close'] > dataframe['ema50'])
                & (dataframe['ema50'] > dataframe['ema200'])
            ).astype('int') * 2

        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        ssl_down, ssl_up = ssl_atr(dataframe, 10)
        dataframe['ssl_down'] = ssl_down
        dataframe['ssl_up'] = ssl_up
        dataframe['ssl_ok'] = (
                (ssl_up > ssl_down) 
            ).astype('int') * 3

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                    ((dataframe[f'buy_ema_{self.buy_ema_period.value}_1d'] < dataframe['close_1d']) & (dataframe['ema_ok'] > 0)) |
                    (qtpylib.crossed_above(dataframe['close'], dataframe[f'ema_{self.buy_ema_test.value}'])) | 
                    ((dataframe['efi_ok'] > 0) & (dataframe['ssl_ok'] > 0))
#                    ((dataframe['efi_ok'] > 0) & (dataframe['ssl_ok'] > 0))
            ),
            'buy'] = 1
        return dataframe


    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                ((qtpylib.crossed_below(dataframe['close'], dataframe[f'sell_ema_{self.sell_ema_period.value}'])) &
                (dataframe[f'sell_ema_{self.sell_btc_ema_period.value}_1d'] > dataframe['close_1d']))
            ),
            'sell'] = 1
        return dataframe
