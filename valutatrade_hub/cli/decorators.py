from argparse import Namespace
from functools import wraps
from typing import Callable, TypeVar

from valutatrade_hub.core.constants import ALLOWED_CURRENCY
from valutatrade_hub.core.exceptions import (
    CoreError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.models import User
from valutatrade_hub.parser_service.exceptions import ApiRequestError

from .context import AppContext

R = TypeVar("R")


def require_login(
    func: Callable[[Namespace, AppContext, User], R],
) -> Callable[[Namespace, AppContext], R]:
    @wraps(func)
    def wrapper(args: Namespace, ctx: AppContext) -> R:
        user = ctx.session.requires_user()
        return func(args, ctx, user)

    return wrapper


def handle_errors(
    func: Callable[[Namespace, AppContext], None],
) -> Callable[[Namespace, AppContext], None]:
    @wraps(func)
    def wrapper(args: Namespace, ctx: AppContext) -> None:
        try:
            func(args, ctx)
        except InsufficientFundsError as e:
            print(e)
        except CurrencyNotFoundError as e:
            print(e)
            print(f"Поддерживаемые валюты: {', '.join(ALLOWED_CURRENCY)}")
            print("Справка: get-rate -h")
        except ApiRequestError as e:
            print(e)
            print("Повторите попытку позже или проверьте подключение к сети.")
        except CoreError as e:
            print(e)

    return wrapper
