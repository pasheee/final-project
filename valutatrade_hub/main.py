from valutatrade_hub.cli.context import AppContext
from valutatrade_hub.cli.interface import run
from valutatrade_hub.cli.session import Session
from valutatrade_hub.infra.constants import CONFIG, PROJECT_PATH
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.repository import (
    JsonCurrencyRepository,
    JsonPortfolioRepository,
    JsonUserRepository,
)
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.logging_config import setup_logging
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.scheduler import Scheduler
from valutatrade_hub.parser_service.updater import RatesUpdater


def main() -> None:
    """Initialize storage and start the scheduler and command loop"""
    settings = SettingsLoader(CONFIG)
    settings.load()
    db = DatabaseManager()
    for key, default in (
        ("USERS_PATH", []),
        ("PORTFOLIOS_PATH", []),
        ("RATES_PATH", {"pairs": {}, "last_refresh": None}),
        ("HISTORY_PATH", []),
    ):
        db.initialize(PROJECT_PATH / settings.get(key), default)
    setup_logging(settings.get("LOG_FORMAT"), settings.get("LOG_LEVEL"))
    parser_config = ParserConfig()
    updater = RatesUpdater(
        ExchangeRateApiClient(parser_config), CoinGeckoClient(parser_config)
    )
    ctx = AppContext(
        Session(),
        JsonUserRepository(PROJECT_PATH / settings.get("USERS_PATH")),
        JsonPortfolioRepository(PROJECT_PATH / settings.get("PORTFOLIOS_PATH")),
        JsonCurrencyRepository(
            PROJECT_PATH / settings.get("RATES_PATH"),
            PROJECT_PATH / settings.get("HISTORY_PATH"),
        ),
        settings.get("RATES_TTL_SECONDS"),
        updater,
    )
    Scheduler(updater, ctx.rates, ctx.rates_ttl).start()
    run(ctx)
