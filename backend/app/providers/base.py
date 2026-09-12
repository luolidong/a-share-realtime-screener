from abc import ABC, abstractmethod
import pandas as pd


class StockDataProvider(ABC):
    @abstractmethod
    def get_realtime_quotes(self) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def get_realtime_money_flow(self) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def get_financial_growth(self) -> pd.DataFrame:
        raise NotImplementedError
