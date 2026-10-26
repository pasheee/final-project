from abc import ABC, abstractmethod

import requests

from valutatrade_hub.core.constants import CORE_FIAT_CURRENCY, DEFAULT_BASE_CURRENCY

from .config import ParserConfig
from .constants import HTTP_ERRORS
from .exceptions import ApiRequestError


class BaseApiClient(ABC):
    SOURCE: str = ""

    def __init__(self, config: ParserConfig):
        self.config = config

    @abstractmethod
    def fetch_rates(self) -> dict: ...

    def _get_json(self, url: str, **kwargs) -> dict:
        try:
            response = requests.get(url, timeout=self.config.REQUEST_TIMEOUT, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response is not None:
                code = e.response.status_code
            reason = HTTP_ERRORS.get(code, "неожиданный ответ сервера")
            raise ApiRequestError(f"{reason} (HTTP {code})") from e
        except requests.exceptions.Timeout as e:
            timeout = self.config.REQUEST_TIMEOUT
            raise ApiRequestError(f"сервер не ответил за {timeout} с") from e
        except requests.exceptions.RequestException as e:
            raise ApiRequestError("нет соединения с сервером") from e


class CoinGeckoClient(BaseApiClient):
    """Client of CoinGecko for cryptocurrency rates"""

    SOURCE: str = "CoinGecko"

    def fetch_rates(self) -> dict:
        """Return cryptocurrency rates to USD"""
        code_by_id = {coin: code for code, coin in self.config.CRYPTO_ID_MAP.items()}
        params = {"ids": ",".join(code_by_id), "vs_currencies": DEFAULT_BASE_CURRENCY}
        data = self._get_json(self.config.COINGECKO_URL, params=params)
        return {
            f"{code_by_id[coin]}_{DEFAULT_BASE_CURRENCY}": {
                "rate": price[DEFAULT_BASE_CURRENCY.lower()]
            }
            for coin, price in data.items()
        }


class ExchangeRateApiClient(BaseApiClient):
    """Client of ExchangeRate-API for fiat currency rates"""

    SOURCE: str = "ExchangeRate-API"

    def fetch_rates(self) -> dict:
        """Return fiat currency rates to USD"""
        url = f"{self.config.EXCHANGERATE_API_URL}/latest/{DEFAULT_BASE_CURRENCY}"
        headers = {"Authorization": f"Bearer {self.config.EXCHANGERATE_API_KEY}"}
        result = self._get_json(url, headers=headers)
        return {
            f"{code}_{DEFAULT_BASE_CURRENCY}": {"rate": 1 / rate}
            for code, rate in result["conversion_rates"].items()
            if code in CORE_FIAT_CURRENCY
        }
