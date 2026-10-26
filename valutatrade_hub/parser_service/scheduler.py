import threading
import time
from itertools import count

from valutatrade_hub.core.ports import CurrencyRepository

from .updater import RatesUpdater

UPDATES_PER_TTL = 3


class Scheduler:
    """Scheduler for updating users.json and exchange_rates.json"""

    def __init__(
        self, updater: RatesUpdater, currency_repo: CurrencyRepository, ttl: int
    ):
        self.updater = updater
        self.currency_repo = currency_repo
        self.ttl = ttl

    def start(self) -> None:
        """Start the updates in a background thread"""
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        for tick in count():
            self.updater.update_history(self.currency_repo)
            if tick % UPDATES_PER_TTL == 0:
                self.currency_repo.refresh()
            time.sleep(self.ttl / UPDATES_PER_TTL)
