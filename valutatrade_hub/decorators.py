import logging
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable

from valutatrade_hub.core.constants import DEFAULT_BASE_CURRENCY
from valutatrade_hub.core.models import User

if TYPE_CHECKING:
    from valutatrade_hub.core.usecases import Trade

TradeFunc = Callable[..., "Trade"]

logger = logging.getLogger(__name__)


def log_action(verbose: bool = False) -> Callable[[TradeFunc], TradeFunc]:
    """Log trades, errors and optional wallet balance changes"""

    def decorator(func: TradeFunc) -> TradeFunc:
        @wraps(func)
        def wrapper(
            user: User, currency_code: str, amount: float, *args: Any, **kwargs: Any
        ) -> "Trade":
            action = (
                f"{func.__name__.upper()} user={user.username!r} "
                f"currency={currency_code!r} amount={amount}"
            )
            try:
                trade = func(user, currency_code, amount, *args, **kwargs)
            except Exception as e:
                logger.info(
                    f"{action} result=ERROR error_type={type(e).__name__} "
                    f"error_message={str(e)!r}"
                )
                raise

            details = f"rate={trade.rate} base={DEFAULT_BASE_CURRENCY!r}"
            if verbose:
                details += f" balance={trade.old_balance}→{trade.new_balance}"
            logger.info(f"{action} {details} result=OK")
            return trade

        return wrapper

    return decorator
