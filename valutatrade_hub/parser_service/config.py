import os
from dataclasses import dataclass

from dotenv import load_dotenv
from frozendict import frozendict

load_dotenv()


@dataclass
class ParserConfig:
    """Settings of the external APIs"""

    EXCHANGERATE_API_KEY: str = os.getenv("EXCHANGERATE_API_KEY", "")
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    CRYPTO_ID_MAP: frozendict = frozendict(
        {
            "BTC": "bitcoin",
            "ETH": "ethereum",
        }
    )

    RATES_FILE_PATH: str = "data/rates.json"
    HISTORY_FILE_PATH: str = "data/exchange_rates.json"

    REQUEST_TIMEOUT: int = 10
