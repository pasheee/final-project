from dataclasses import dataclass

from valutatrade_hub.core.exceptions import (
    CurrencyNotFoundError,
    InvalidPassword,
    StaleRateError,
    WalletDoesntExist,
)
from valutatrade_hub.core.hash import HasherProtocol, Pbkdf2Hasher
from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.decorators import log_action

from .constants import ALLOWED_CURRENCY, CORE_CRYPTO_CURRENCY, DEFAULT_BASE_CURRENCY
from .currencies import get_currency
from .ports import CurrencyRepository, PortfolioRepository, Updater, UserRepository
from .utils import is_expired


@dataclass(frozen=True)
class Trade:
    """Result of a buy or sell: rate, cost and balances before and after"""

    currency_code: str
    amount: float
    rate: float
    cost: float
    old_balance: float
    new_balance: float
    base_old_balance: float
    base_new_balance: float


def register(
    username: str,
    password: str,
    user_repo: UserRepository,
    portfolio_repo: PortfolioRepository,
    hasher: HasherProtocol = Pbkdf2Hasher(),
) -> tuple[User, Portfolio]:
    """Register a user and create an empty portfolio"""
    user = User.register(user_repo.get_current_id(), username, password, hasher)
    user_repo.save(user)
    portfolio = portfolio_repo.create_portfolio(user)

    return user, portfolio


def login(username: str, password: str, user_repo: UserRepository) -> User:
    """Return the user if the password is correct"""
    user = user_repo.get_user_by_username(username)
    if not user.verify_password(password):
        raise InvalidPassword("Неверный пароль")

    return user


def show_portfolio(
    user: User,
    base: str,
    portfolio_repo: PortfolioRepository,
    currency_repo: CurrencyRepository,
) -> tuple[Portfolio, dict[str, float], float]:
    """Return the portfolio, wallet values and their total in the base currency"""
    portfolio = portfolio_repo.get_portfolio(user)
    values = portfolio.get_values(base, get_price=currency_repo.get_price)
    total = portfolio.get_total_value(base, get_price=currency_repo.get_price)

    return portfolio, values, total


def get_rate(
    src: str, dst: str, currency_repo: CurrencyRepository, rates_ttl: int
) -> tuple[float, float, str]:
    """Return the rate, the inverse rate and the update time, checking the TTL"""
    src, dst = get_currency(src).code, get_currency(dst).code
    if is_expired(currency_repo.get_updated_at(src, dst), rates_ttl):
        currency_repo.refresh()

    updated_at = currency_repo.get_updated_at(src, dst)
    if is_expired(updated_at, rates_ttl):
        raise StaleRateError(
            f"Курс {src}→{dst} устарел (обновлён {updated_at}). "
            "Выполните 'update-rates', чтобы загрузить свежие данные."
        )

    return (
        currency_repo.get_price(src, dst),
        currency_repo.get_price(dst, src),
        updated_at,
    )


@log_action(verbose=True)
def buy(
    user: User,
    currency_code: str,
    amount: float,
    portfolio_repo: PortfolioRepository,
    currency_repo: CurrencyRepository,
) -> Trade:
    """Buy currency, paying from the USD wallet"""
    currency_code = get_currency(currency_code).code
    portfolio = portfolio_repo.get_portfolio(user)
    wallet = portfolio.get_or_add_wallet(currency_code)
    base_wallet = portfolio.get_or_add_wallet(DEFAULT_BASE_CURRENCY)
    old_balance, base_old_balance = wallet.balance, base_wallet.balance
    rate = currency_repo.get_price(currency_code, DEFAULT_BASE_CURRENCY)
    cost = amount * rate

    if currency_code != DEFAULT_BASE_CURRENCY:
        base_wallet.withdraw(cost)
    wallet.deposit(amount)
    portfolio_repo.save(portfolio)

    return Trade(
        currency_code,
        amount,
        rate,
        cost,
        old_balance,
        wallet.balance,
        base_old_balance,
        base_wallet.balance,
    )


@log_action(verbose=True)
def sell(
    user: User,
    currency_code: str,
    amount: float,
    portfolio_repo: PortfolioRepository,
    currency_repo: CurrencyRepository,
) -> Trade:
    """Sell currency, adding the proceeds to the USD wallet"""
    currency_code = get_currency(currency_code).code
    portfolio = portfolio_repo.get_portfolio(user)
    if currency_code not in portfolio.wallets:
        raise WalletDoesntExist(
            f"У вас нет кошелька {currency_code!r}. "
            "Добавьте валюту: она создаётся автоматически при первой покупке."
        )

    wallet = portfolio.get_wallet(currency_code)
    base_wallet = portfolio.get_or_add_wallet(DEFAULT_BASE_CURRENCY)
    old_balance, base_old_balance = wallet.balance, base_wallet.balance
    rate = currency_repo.get_price(currency_code, DEFAULT_BASE_CURRENCY)
    cost = amount * rate

    wallet.withdraw(amount)
    if currency_code != DEFAULT_BASE_CURRENCY:
        base_wallet.deposit(cost)
    portfolio_repo.save(portfolio)

    return Trade(
        currency_code,
        amount,
        rate,
        cost,
        old_balance,
        wallet.balance,
        base_old_balance,
        base_wallet.balance,
    )


def update_rates(
    source: str | None, updater: Updater, currency_repo: CurrencyRepository
) -> tuple[int, str]:
    """Fetch fresh rates from the sources and refresh the cache"""
    num_updates, time_now = updater.run_update(currency_repo, source)

    return (num_updates, time_now)


def show_rates(
    currency: str | None, top: int | None, base: str, currency_repo: CurrencyRepository
) -> tuple[list[tuple[str, float]], str]:
    """Return cached rates: all, one currency or the top N cryptocurrencies"""
    last_refresh = currency_repo.get_last_refresh()
    base = get_currency(base).code
    if currency and currency not in ALLOWED_CURRENCY:
        raise CurrencyNotFoundError(f"Курс для {currency!r} не найден в кеше.")

    if currency:
        codes = [currency]
    elif top:
        codes = CORE_CRYPTO_CURRENCY
    else:
        codes = [code for code in ALLOWED_CURRENCY if code != base]
    rates = [(f"{code}_{base}", currency_repo.get_price(code, base)) for code in codes]

    if top:
        return sorted(rates, key=lambda r: r[1], reverse=True)[:top], last_refresh
    return sorted(rates), last_refresh
