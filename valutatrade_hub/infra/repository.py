from pathlib import Path
from typing import Any

from valutatrade_hub.core.constants import DEFAULT_BASE_CURRENCY
from valutatrade_hub.core.exceptions import CurrencyNotFoundError
from valutatrade_hub.core.models import Base, Portfolio, User
from valutatrade_hub.core.utils import utc_now, validate_currency_code

from .database import DatabaseManager
from .exceptions import (
    PortfolioDoesntExist,
    RateNotFound,
    UserAlreadyExist,
    UserDoesntExist,
)


class JsonListRepository:
    """Base repository over a JSON file with a list"""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.db = DatabaseManager()

    def load_json_list(self) -> list[dict[str, Any]]:
        """Read the list from the file, or an empty list if there is no file"""
        try:
            return self.db.load(self.filepath)
        except FileNotFoundError:
            return []

    def save_json_list(self, json_list: list[dict[str, Any]]) -> None:
        """Write the list to the file"""
        self.db.save(self.filepath, json_list)

    def save_obj_to_list(self, obj: Base) -> None:
        """Append the object to the list in the file"""
        curr_list = self.load_json_list()
        curr_list.append(obj.to_dict())
        self.save_json_list(curr_list)


class JsonUserRepository(JsonListRepository):
    """Users in users.json"""

    def get_current_id(self):
        """Return the id for a new user"""
        users = self.load_json_list()
        return max((User.from_dict(user).user_id for user in users), default=-1) + 1

    def get_user_by_username(self, username: str) -> User:
        """Return the user by username"""
        user_profiles = self.load_json_list()
        for user in user_profiles:
            u = User.from_dict(user)
            if u.username == username:
                return u
        raise UserDoesntExist(f"Пользователь {username!r} не найден")

    def save(self, user: User) -> None:
        """Save the user, replacing the old record"""
        taken = any(
            u["username"] == user.username and u["user_id"] != user.user_id
            for u in self.load_json_list()
        )
        if taken:
            raise UserAlreadyExist(f"Имя пользователя {user.username!r} уже занято")

        self.save_obj_to_list(user)
        users = self.load_json_list()

        for i in range(len(users) - 1):
            user_dict = users[i]
            candidate = User.from_dict(user_dict)

            if candidate.user_id == user.user_id:
                users[i], users[len(users) - 1] = users[len(users) - 1], users[i]
                users.pop()
                self.save_json_list(users)
                return

        self.save_json_list(users)


class JsonPortfolioRepository(JsonListRepository):
    """Portfolios in portfolios.json"""

    def get_portfolio(self, user: User) -> Portfolio:
        """Return the user's portfolio"""
        portfolios = self.load_json_list()
        for portfolio in portfolios:
            if portfolio["user_id"] == user.user_id:
                return Portfolio.from_dict(portfolio, user)

        raise PortfolioDoesntExist(f"Портфель пользователя {user.username!r} не найден")

    def create_portfolio(self, user: User) -> Portfolio:
        """Create and save an empty portfolio for the user"""
        portfolio = Portfolio(user, {})
        self.save_obj_to_list(portfolio)
        return portfolio

    def save(self, portfolio: Portfolio) -> None:
        """Save the portfolio, replacing the old record"""
        self.save_obj_to_list(portfolio)
        portfolios = self.load_json_list()

        for i in range(len(portfolios) - 1):
            portfolio_dict = portfolios[i]

            if portfolio_dict["user_id"] == portfolio.user_id:
                portfolios[i], portfolios[len(portfolios) - 1] = (
                    portfolios[len(portfolios) - 1],
                    portfolios[i],
                )
                portfolios.pop()
                self.save_json_list(portfolios)
                return

        self.save_json_list(portfolios)


class JsonCurrencyRepository:
    """Rates cache in rates.json and their history in exchange_rates.json"""

    def __init__(self, rates_path: Path, history_path: Path):
        self.rates_path = rates_path
        self.history_path = history_path
        self.db = DatabaseManager()

    def get_price(self, src: str, dst: str) -> float:
        """Return the price of src in dst through rates to USD"""
        return self._usd_rate(src) / self._usd_rate(dst)

    def get_updated_at(self, src: str, dst: str) -> str:
        """Return the update time of the older rate in the pair"""
        if src == dst:
            return utc_now()
        legs = {src, dst} - {DEFAULT_BASE_CURRENCY}
        return min(self._pair(code)["updated_at"] for code in legs)

    def get_last_refresh(self) -> str:
        """Return the time of the last cache refresh"""
        snapshot = self._load_snapshot()
        if not snapshot["pairs"]:
            raise RateNotFound(
                "Локальный кеш курсов пуст. "
                "Выполните 'update-rates', чтобы загрузить данные."
            )
        return snapshot["last_refresh"]

    def refresh_history(self, records: list[dict[str, Any]]) -> None:
        """Append new valid records to the history"""
        history = self._load_history()
        known = {record["id"] for record in history}
        history += [r for r in records if r["id"] not in known and _is_valid(r)]
        self.db.save(self.history_path, history)

    def refresh(self) -> int:
        """Copy rates fresher than the cached ones from the history"""
        snapshot = self._load_snapshot()
        pairs = snapshot["pairs"]
        history = sorted(self._load_history(), key=lambda r: r["timestamp"])
        latest = {f"{r['from_currency']}_{r['to_currency']}": r for r in history}
        fresh = {
            pair: r
            for pair, r in latest.items()
            if pair not in pairs or r["timestamp"] > pairs[pair]["updated_at"]
        }
        pairs |= {
            pair: {
                "rate": r["rate"],
                "updated_at": r["timestamp"],
                "source": r["source"],
            }
            for pair, r in fresh.items()
        }
        snapshot["last_refresh"] = utc_now()
        self.db.save(self.rates_path, snapshot)
        return len(fresh)

    def _usd_rate(self, code: str) -> float:
        return 1.0 if code == DEFAULT_BASE_CURRENCY else self._pair(code)["rate"]

    def _pair(self, code: str) -> dict[str, Any]:
        pairs = self._load_snapshot()["pairs"]
        pair = f"{code}_{DEFAULT_BASE_CURRENCY}"
        if pair not in pairs:
            raise RateNotFound(
                f"Не удалось получить курс для {code}→{DEFAULT_BASE_CURRENCY}"
            )
        return pairs[pair]

    def _load_snapshot(self) -> dict[str, Any]:
        try:
            snapshot = self.db.load(self.rates_path)
        except FileNotFoundError:
            snapshot = {}
        snapshot.setdefault("pairs", {})
        return snapshot

    def _load_history(self) -> list[dict[str, Any]]:
        try:
            return self.db.load(self.history_path)
        except FileNotFoundError:
            return []


def _is_valid(record: dict[str, Any]) -> bool:
    try:
        validate_currency_code(record["from_currency"])
        validate_currency_code(record["to_currency"])
    except CurrencyNotFoundError:
        return False
    return isinstance(record["rate"], (int, float)) and record["rate"] > 0
