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


class lab_strat_v2(IStrategy):

    INTERFACE_VERSION = 2

    buy_ema_period = IntParameter(10, 365, default=36, space="buy")
    buy_ema_test = IntParameter(10, 365, default=201, space="buy")

    sell_btc_ema_period = IntParameter(20, 300, default=164, space="sell")
    sell_rsi_enabled = BooleanParameter(default=True, space="sell")
    sell_btc_drop_enabled = BooleanParameter(default=True, space="sell")
    sell_macd_enabled = BooleanParameter(default=True, space="sell")
    sell_rsi = IntParameter(0, 99, default=78, space="sell")
    # Optimal timeframe for the strategy.
    timeframe = '4h'

    # ROI table:
    minimal_roi = {
        "0": 1,
#        "1809": 0.214,
#        "4455": 0.052,
#        "5813": -0.05
    }
    # Optimal stoploss designed for the strategy.
    # This attribute will be overridden if the config file contains "stoploss"
    stoploss = -0.35

    # Trailing stop:
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.12
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

        informative['ema'] = ta.EMA(informative, timeperiod=20)

        dataframe = merge_informative_pair(dataframe, informative, self.timeframe, '1d', ffill=True)

        for val in self.buy_ema_test.range:
            dataframe[f'ema_{val}'] = ta.EMA(dataframe, timeperiod=val)

        dataframe['rsi'] = ta.RSI(dataframe)
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        dataframe['cci'] = ta.CCI(dataframe)
        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                    (dataframe[f'buy_ema_{self.buy_ema_period.value}_1d'] < dataframe['close_1d']) |
                    (qtpylib.crossed_above(dataframe['close'], dataframe[f'ema_{self.buy_ema_test.value}']))
            ),
            'buy'] = 1
        return dataframe


    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = [ ]
        if self.sell_macd_enabled.value:
            conditions.append(qtpylib.crossed_below(dataframe['macd'], dataframe['macdsignal']))
        if self.sell_btc_drop_enabled.value:
            conditions.append(dataframe[f'sell_ema_{self.sell_btc_ema_period.value}_1d'] > dataframe['close_1d'])
        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'sell'] = 1
        return dataframe
