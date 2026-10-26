from dataclasses import dataclass

from valutatrade_hub.core.ports import (
    CurrencyRepository,
    PortfolioRepository,
    Updater,
    UserRepository,
)

from .session import Session


@dataclass
class AppContext:
    """Dependencies shared by the commands"""

    session: Session
    users: UserRepository
    portfolios: PortfolioRepository
    rates: CurrencyRepository
    rates_ttl: int
    updater: Updater
