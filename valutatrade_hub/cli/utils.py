from valutatrade_hub.core.constants import CORE_CRYPTO_CURRENCY, DEFAULT_BASE_CURRENCY
from valutatrade_hub.core.models import Portfolio
from valutatrade_hub.core.usecases import Trade


def fmt_amount(value: float, currency: str) -> str:
    return f"{value:,.4f}" if currency in CORE_CRYPTO_CURRENCY else f"{value:,.2f}"


def fmt_rate(rate: float) -> str:
    return f"{rate:.8f}" if rate < 1 else f"{rate:.2f}"


def print_portfolio(
    portfolio: Portfolio, values: dict[str, float], total: float, base: str
) -> None:
    print(f"Портфель пользователя {portfolio.user.username!r} (база: {base}):")
    if not values:
        print("Кошельков пока нет.")
        return

    for w_curr, w in portfolio.wallets.items():
        balance, value = fmt_amount(w.balance, w_curr), fmt_amount(values[w_curr], base)
        print(f"- {w_curr}: {balance}  → {value} {base}")

    print("-" * 33)
    print(f"ИТОГО: {fmt_amount(total, base)} {base}")


def print_trade(title: str, cost_label: str, trade: Trade) -> None:
    code, base = trade.currency_code, DEFAULT_BASE_CURRENCY
    amount, rate = fmt_amount(trade.amount, code), fmt_rate(trade.rate)
    print(f"{title}: {amount} {code} по курсу {rate} {base}/{code}")
    print("Изменения в портфеле:")

    old = fmt_amount(trade.old_balance, code)
    new = fmt_amount(trade.new_balance, code)
    print(f"- {code}: было {old} → стало {new}")

    if code != base:
        old = fmt_amount(trade.base_old_balance, base)
        new = fmt_amount(trade.base_new_balance, base)
        print(f"- {base}: было {old} → стало {new}")

    print(f"{cost_label}: {fmt_amount(trade.cost, base)} {base}")
