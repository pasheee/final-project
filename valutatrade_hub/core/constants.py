from .currencies import CURRENCIES, CryptoCurrency

DEFAULT_BASE_CURRENCY = "USD"
ALLOWED_CURRENCY = list(CURRENCIES)
CORE_CRYPTO_CURRENCY = [
    c.code for c in CURRENCIES.values() if isinstance(c, CryptoCurrency)
]
CORE_FIAT_CURRENCY = [
    c.code for c in CURRENCIES.values() if not isinstance(c, CryptoCurrency)
]
