from abc import ABC, abstractmethod

from .exceptions import CurrencyNotFoundError
from .utils import validate_currency_code


class Currency(ABC):
    def __init__(self, name: str, code: str):
        self.name = name
        self.code = code

    @abstractmethod
    def get_display_info(self) -> str: ...

    @property
    def code(self):
        return self._code

    @code.setter
    def code(self, value: str):
        validate_currency_code(value)
        self._code = value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value: str):
        if not value.strip():
            raise CurrencyNotFoundError("Currency name can`t be empty.")
        self._name = value


class FiatCurrency(Currency):
    """Currency issued by a country"""

    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)
        self.issuing_country = issuing_country

    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    """Cryptocurrency with an algorithm and a market cap"""

    def __init__(self, name: str, code: str, algorithm: str, market_cap: float):
        super().__init__(name, code)
        self.algorithm = algorithm
        self.market_cap = market_cap

    def get_display_info(self) -> str:
        mcap = f"{self.market_cap:.2e}".replace("e+", "e")
        return (
            f"[CRYPTO] {self.code} — {self.name} (Algo: {self.algorithm}, MCAP: {mcap})"
        )


CURRENCIES: dict[str, Currency] = {
    currency.code: currency
    for currency in (
        FiatCurrency("US Dollar", "USD", "United States"),
        FiatCurrency("Euro", "EUR", "Eurozone"),
        CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
        FiatCurrency("Russian Ruble", "RUB", "Russia"),
        CryptoCurrency("Ethereum", "ETH", "Ethash", 4.5e11),
    )
}


def get_currency(code: str) -> Currency:
    validate_currency_code(code)
    if code not in CURRENCIES:
        raise CurrencyNotFoundError(f"Неизвестная валюта {code!r}")
    return CURRENCIES[code]
