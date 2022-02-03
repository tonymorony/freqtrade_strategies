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

"""
Idea of strategy is to sit patiently in fiat when market is decreasing, wait for bull market, sell high and then repeat
|   Best |  147/1000 |      961 |    884    0   77 |        6.31% |  280380.525 USDT (28,038.05%) | 4 days 15:50:00 |    -5.59002 |    109503.421 USDT   (28.01%) |    

    # Buy hyperspace params:
    buy_params = {
        "buy_ema_period": 132,
        "buy_when_btc_rise": True,
    }

    # Sell hyperspace params:
    sell_params = {
        "sell_cci": 262,
        "sell_cci_enabled": True,
        "sell_ema_enabled": True,
        "sell_ema_period": 159,
        "sell_macd_enabled": False,
        "sell_rsi": 71,
        "sell_rsi_enabled": True,
        "sell_when_btc_drop": False,
    }

    # ROI table:  # value loaded from strategy
    minimal_roi = {
        "0": 10000
    }

    # Stoploss:
    stoploss = -0.35

    # Trailing stop:
    trailing_stop = True  # value loaded from strategy
    trailing_stop_positive = 0.01  # value loaded from strategy
    trailing_stop_positive_offset = 0.08  # value loaded from strategy
    trailing_only_offset_is_reached = True  # value loaded from strategy
"""


class tonyl_strategy_4(IStrategy):
    INTERFACE_VERSION = 2

    buy_when_btc_rise = CategoricalParameter([True, False], default=True, space="buy")
    sell_when_btc_drop = CategoricalParameter([True, False], default=False, space="sell")

    sell_rsi = IntParameter(70, 99, default=78, space="sell")
    sell_cci = IntParameter(100, 300, default=100, space="sell")

    sell_rsi_enabled = CategoricalParameter([True, False], default=True, space="sell")
    sell_cci_enabled = CategoricalParameter([True, False], default=True, space="sell")
    sell_macd_enabled = CategoricalParameter([True, False], default=True, space="sell")
    sell_ema_enabled = CategoricalParameter([True, False], default=True, space="sell")
    buy_ema_period = IntParameter(10, 365, default=299, space="buy")
    sell_ema_period = IntParameter(10, 777, default=124, space="sell")
    # Optimal timeframe for the strategy.
    timeframe = '4h'

    # ROI table:
    minimal_roi = {
        "0": 10000
    }

    # Optimal stoploss designed for the strategy.
    # This attribute will be overridden if the config file contains "stoploss".
    stoploss = -0.349

    # Trailing stop:
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.08
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

        for val in self.sell_ema_period.range:
            dataframe[f'sell_ema_{val}'] = ta.EMA(dataframe, timeperiod=val)
        informative['ema'] = ta.EMA(informative, timeperiod=20)

        dataframe = merge_informative_pair(dataframe, informative, self.timeframe, '1d', ffill=True)


        dataframe['rsi'] = ta.RSI(dataframe)
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        dataframe['cci'] = ta.CCI(dataframe)

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        conditions = []
        if self.buy_when_btc_rise.value:
            conditions.append(dataframe[f'buy_ema_{self.buy_ema_period.value}_1d'] < dataframe['close_1d'])

        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'buy'] = 1

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        conditions = []

        return dataframe
