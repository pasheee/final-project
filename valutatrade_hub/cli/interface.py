import shlex
from argparse import ArgumentParser, Namespace

from valutatrade_hub.core.constants import DEFAULT_BASE_CURRENCY
from valutatrade_hub.core.models import User
from valutatrade_hub.core.usecases import (
    buy,
    get_rate,
    login,
    register,
    sell,
    show_portfolio,
    show_rates,
    update_rates,
)

from .context import AppContext
from .decorators import handle_errors, require_login
from .exceptions import CliError
from .utils import fmt_rate, print_portfolio, print_trade


@handle_errors
def cmd_register(args: Namespace, ctx: AppContext) -> None:
    """Register a new user with an empty portfolio"""
    user, _ = register(args.username, args.password, ctx.users, ctx.portfolios)
    print(
        f"Пользователь {user.username!r} зарегистрирован (id={user.user_id}). "
        f"Войдите: login --username {user.username} --password **** "
    )


@handle_errors
def cmd_login(args: Namespace, ctx: AppContext) -> None:
    """Log in as an existing user"""
    user = login(args.username, args.password, ctx.users)
    ctx.session.login(user)
    print(f"Вы вошли как {user.username!r}")


@handle_errors
@require_login
def cmd_show_portfolio(args: Namespace, ctx: AppContext, user: User) -> None:
    """Show wallets and their value in the base currency"""
    portfolio, values, total = show_portfolio(
        user, args.base, ctx.portfolios, ctx.rates
    )
    print_portfolio(portfolio, values, total, args.base)


@handle_errors
@require_login
def cmd_buy(args: Namespace, ctx: AppContext, user: User) -> None:
    """Buy currency, paying from the USD wallet"""
    trade = buy(
        user, args.currency, args.amount, ctx.portfolios, ctx.rates, ctx.rates_ttl
    )
    print_trade("Покупка выполнена", "Оценочная стоимость покупки", trade)


@handle_errors
@require_login
def cmd_sell(args: Namespace, ctx: AppContext, user: User) -> None:
    """Sell currency, adding the proceeds to the USD wallet"""
    trade = sell(
        user, args.currency, args.amount, ctx.portfolios, ctx.rates, ctx.rates_ttl
    )
    print_trade("Продажа выполнена", "Оценочная выручка", trade)


@handle_errors
def cmd_get_rate(args: Namespace, ctx: AppContext) -> None:
    """Show the exchange rate and its inverse"""
    rate, inverted_rate, updated_at = get_rate(
        args.src, args.dst, ctx.rates, ctx.rates_ttl
    )
    updated_at = updated_at.replace("T", " ")
    print(f"Курс {args.src}→{args.dst}: {fmt_rate(rate)} (обновлено: {updated_at})")
    print(f"Обратный курс {args.dst}→{args.src}: {fmt_rate(inverted_rate)}")


@handle_errors
def cmd_update_rates(args: Namespace, ctx: AppContext) -> None:
    """Fetch fresh rates from ExchangeRate-API and CoinGecko"""
    rates_updated, last_refresh = update_rates(args.source, ctx.updater, ctx.rates)
    print(
        f"Update successful. Total rates updated: {rates_updated}. "
        f"Last refresh: {last_refresh}"
    )


@handle_errors
def cmd_show_rates(args: Namespace, ctx: AppContext) -> None:
    """Show cached rates: all, one currency or the top N cryptocurrencies"""
    rates, last_refresh = show_rates(args.currency, args.top, args.base, ctx.rates)
    print(f"Rates from cache (updated at {last_refresh}):")
    for pair, rate in rates:
        print(f"- {pair}: {fmt_rate(rate)}")


class Parser(ArgumentParser):
    """Argument parser that raises CliError instead of exiting"""

    def exit(self, status=0, message=None):
        """Raise CliError with the argparse message"""
        raise CliError((message or "").strip())


def build_parser() -> Parser:
    """Create the parser with all commands"""
    parser = Parser(prog="valutatrade")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=Parser)

    for name, func in (("register", cmd_register), ("login", cmd_login)):
        p = sub.add_parser(name)
        p.add_argument("--username", required=True)
        p.add_argument("--password", required=True)
        p.set_defaults(func=func)

    p = sub.add_parser("show-portfolio")
    p.add_argument("--base", default=DEFAULT_BASE_CURRENCY)
    p.set_defaults(func=cmd_show_portfolio)

    for name, func in (("buy", cmd_buy), ("sell", cmd_sell)):
        p = sub.add_parser(name)
        p.add_argument("--currency", required=True)
        p.add_argument("--amount", type=float, required=True)
        p.set_defaults(func=func)

    p = sub.add_parser("get-rate")
    p.add_argument("--from", dest="src", required=True)
    p.add_argument("--to", dest="dst", required=True)
    p.set_defaults(func=cmd_get_rate)

    p = sub.add_parser("update-rates")
    p.add_argument("--source", choices=["coingecko", "exchangerate"])
    p.set_defaults(func=cmd_update_rates)

    p = sub.add_parser("show-rates")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--currency")
    group.add_argument("--top", type=int)
    p.add_argument("--base", default=DEFAULT_BASE_CURRENCY)
    p.set_defaults(func=cmd_show_rates)

    return parser


def run(ctx: AppContext) -> None:
    """Read and run commands until exit"""
    parser = build_parser()
    while (line := input("> ")) != "exit":
        try:
            args = parser.parse_args(shlex.split(line))
        except (CliError, ValueError) as e:
            print(e)
            continue
        args.func(args, ctx)
