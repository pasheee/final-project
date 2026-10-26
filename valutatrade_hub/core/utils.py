from datetime import datetime, timedelta, timezone
from typing import Callable

from .exceptions import CurrencyNotFoundError


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_expired(timestamp: str, ttl: int) -> bool:
    age = datetime.now(timezone.utc) - datetime.fromisoformat(timestamp)
    return age > timedelta(seconds=ttl)


def validate_currency_code(code: str) -> None:
    if not code.isupper():
        raise CurrencyNotFoundError(f"Code {code!r} must be uppercase.")
    if len(code) < 2 or len(code) > 5:
        raise CurrencyNotFoundError(f"Code {code!r} has invalid length.")
    if " " in code:
        raise CurrencyNotFoundError(f"Code {code!r} has space.")


def convert(
    amount: float, src: str, dst: str, get_price: Callable[[str, str], float]
) -> float:
    return amount * get_price(src, dst)
