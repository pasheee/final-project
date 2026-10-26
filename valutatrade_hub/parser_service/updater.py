import logging

from valutatrade_hub.core.ports import CurrencyRepository
from valutatrade_hub.core.utils import utc_now

from .api_clients import CoinGeckoClient, ExchangeRateApiClient
from .exceptions import ApiRequestError

logger = logging.getLogger(__name__)


class RatesUpdater:
    """Updater of rates from ExchangeRate-API and CoinGecko"""

    def __init__(
        self, fiat_api_client: ExchangeRateApiClient, crypto_api_client: CoinGeckoClient
    ):
        self.clients = {"exchangerate": fiat_api_client, "coingecko": crypto_api_client}

    def run_update(
        self, currency_repo: CurrencyRepository, source: str | None
    ) -> tuple[int, str]:
        """Fetch rates, add them to the history and refresh the cache"""
        updated_at, failed = self.update_history(currency_repo, source)
        num_refreshed = currency_repo.refresh()
        logger.info(f"Rates update finished: {num_refreshed} rates updated")
        if failed:
            raise ApiRequestError(
                f"не удалось получить курсы из {', '.join(failed)}, "
                "подробности в logs/actions.log"
            )
        return num_refreshed, updated_at

    def update_history(
        self, currency_repo: CurrencyRepository, source: str | None = None
    ) -> tuple[str, list[str]]:
        """Fetch rates and add them to the history"""
        logger.info("Starting rates update...")
        clients = [self.clients[source]] if source else self.clients.values()
        updated_at = utc_now()
        records, failed = [], []
        for client in clients:
            try:
                result = client.fetch_rates()
            except ApiRequestError as e:
                logger.error(f"Failed to fetch from {client.SOURCE}: {e}")
                failed.append(client.SOURCE)
                continue
            logger.info(f"Fetching from {client.SOURCE}... OK ({len(result)} rates)")
            records += [
                {
                    "id": f"{name}_{updated_at}",
                    "from_currency": name.split("_")[0],
                    "to_currency": name.split("_")[1],
                    "rate": payload["rate"],
                    "timestamp": updated_at,
                    "source": client.SOURCE,
                }
                for name, payload in result.items()
            ]

        currency_repo.refresh_history(records)
        return updated_at, failed
