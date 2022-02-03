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
 657/5000:    879 trades. 693/126/60 Wins/Draws/Losses. Avg profit   5.19%. Median profit   8.48%. Total profit 73484.08206883 USDT (7348.41%). Avg duration 3 days, 9:03:00 min. Objective: -6.75854
"""


class lab_strat(IStrategy):

    INTERFACE_VERSION = 2

    buy_ema_period = IntParameter(10, 365, default=33, space="buy")
    buy_ema_test = IntParameter(10, 365, default=26, space="buy")

    # Optimal timeframe for the strategy.
    timeframe = '4h'

    # ROI table:
    minimal_roi = {
        "0": 0.481,
        "1307": 0.183,
        "3414": 0.03,
        "7636": 0
    }
    # Optimal stoploss designed for the strategy.
    # This attribute will be overridden if the config file contains "stoploss"
    stoploss = -0.35

    # Trailing stop:
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.097
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

        informative['ema'] = ta.EMA(informative, timeperiod=20)
        for val in self.buy_ema_test.range:
            dataframe[f'ema_{val}'] = ta.EMA(dataframe, timeperiod=val)

        dataframe = merge_informative_pair(dataframe, informative, self.timeframe, '1d', ffill=True)

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

        conditions = []
        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'sell'] = 1

        return dataframe
