import hmac
import math
import secrets
from abc import ABC, abstractmethod
from copy import deepcopy
from datetime import datetime
from typing import Any, Callable

from .constants import ALLOWED_CURRENCY
from .exceptions import CurrencyNotFoundError, InsufficientFundsError, ValidationError
from .hash import HasherProtocol, Pbkdf2Hasher
from .utils import convert


class Base(ABC):
    """Base class for objects stored in JSON files"""

    @abstractmethod
    def to_dict(self) -> dict[str, Any]: ...


class User(Base):
    """User account with a salted password hash"""

    MAX_USERNAME_LENGTH = 32

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
        hasher: HasherProtocol = Pbkdf2Hasher(),
    ):
        self._user_id = user_id
        self.username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date
        self._hasher = hasher

    def get_user_info(self) -> None:
        """Print user info"""
        user_info = (
            f"User id: {self._user_id}\n"
            f"Username: {self._username}\n"
            f"Registration date: {self._registration_date}\n"
        )
        print(user_info)

    def change_password(self, new_password: str) -> None:
        """Change user password"""
        self._hashed_password, self._salt = self._hash_password(
            new_password, self._hasher
        )

    def verify_password(self, password: str) -> bool:
        """Verify user password"""
        attempt = self._hasher.hash(password, self._salt)
        return hmac.compare_digest(attempt, self._hashed_password)

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    @property
    def hasher(self) -> HasherProtocol:
        return self._hasher

    @username.setter
    def username(self, value: str):
        value = value.strip()
        if not value:
            raise ValidationError("Имя не может быть пустым")
        if len(value) > self.MAX_USERNAME_LENGTH:
            raise ValidationError(
                f"Имя не может быть длиннее {self.MAX_USERNAME_LENGTH} символов"
            )

        self._username = value

    def to_dict(self) -> dict[str, Any]:
        """Convert the user to a users.json record"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "hashed_password": self.hashed_password,
            "salt": self.salt,
            "registration_date": self.registration_date.isoformat(timespec="seconds"),
        }

    @staticmethod
    def _hash_password(
        password: str, hasher: HasherProtocol = Pbkdf2Hasher()
    ) -> tuple[str, str]:
        salt = secrets.token_hex(16)
        if len(password) < 4:
            raise ValidationError("Пароль должен быть не короче 4 символов")
        return hasher.hash(password, salt), salt

    @classmethod
    def from_dict(
        cls, user_profile: dict[str, Any], hasher: HasherProtocol = Pbkdf2Hasher()
    ) -> "User":
        """Create a user from a users.json record"""
        date = datetime.fromisoformat(user_profile["registration_date"])
        profile: dict[str, Any] = user_profile | {"registration_date": date}
        return cls(**profile, hasher=hasher)

    @classmethod
    def register(
        cls,
        user_id: int,
        username: str,
        password: str,
        hasher: HasherProtocol = Pbkdf2Hasher(),
    ) -> "User":
        """Create a new user with a hashed password"""
        hashed_password, salt = cls._hash_password(password, hasher)
        return cls(user_id, username, hashed_password, salt, datetime.now(), hasher)


class Wallet(Base):
    """Balance in one currency"""

    def __init__(self, currency_code: str, balance: float = 0.0):
        self.currency_code = currency_code
        self.balance = balance

    def deposit(self, amount: float) -> None:
        """Add money to wallet"""
        self._validate_amount(amount)
        self.balance += amount

    def get_balance_info(self) -> None:
        """Print balance info of wallet"""
        print(f"Current balance: {self.balance} {self.currency_code}")

    def withdraw(self, amount: float) -> None:
        """Withdraw money from wallet"""
        self._validate_amount(amount)
        if amount > self.balance:
            raise InsufficientFundsError(self.balance, amount, self.currency_code)

        self.balance -= amount

    @staticmethod
    def _validate_amount(amount: float) -> None:
        if not math.isfinite(amount) or amount <= 0:
            raise ValidationError("'amount' должен быть положительным числом")

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"Balance must be a number, given {type(value).__name__}.")
        if value < 0:
            raise ValueError("Balance must be >= 0.")

        self._balance = float(value)

    def to_dict(self) -> dict[str, Any]:
        """Convert the wallet to a portfolios.json record"""
        return {
            "currency_code": self.currency_code,
            "balance": self.balance,
        }

    @classmethod
    def from_dict(cls, wallet_profile: dict[str, Any]) -> "Wallet":
        """Create a wallet from a portfolios.json record"""
        return cls(**wallet_profile)


class Portfolio(Base):
    """User's wallets, one per currency"""

    def __init__(self, user: User, wallets: dict[str, Wallet]):
        self._user = user
        self._user_id = user.user_id
        self._wallets = wallets

    def add_currency(self, currency_code) -> Wallet:
        """Add an empty wallet for a new currency"""
        if currency_code in self._wallets:
            raise KeyError(f"Currency code: {currency_code} is already in portfolio.")
        if currency_code not in ALLOWED_CURRENCY:
            raise CurrencyNotFoundError(f"Неизвестная валюта {currency_code!r}")

        self._wallets[currency_code] = Wallet(currency_code)
        return self._wallets[currency_code]

    def get_or_add_wallet(self, currency_code: str) -> Wallet:
        """Return the wallet, creating it if needed"""
        return self._wallets.get(currency_code) or self.add_currency(currency_code)

    def get_values(
        self, base_currency: str = "USD", *, get_price: Callable[[str, str], float]
    ) -> dict[str, float]:
        """Return the value of each wallet in the base currency"""
        if base_currency not in ALLOWED_CURRENCY:
            raise CurrencyNotFoundError(f"Неизвестная базовая валюта {base_currency!r}")
        return {
            currency: convert(wallet.balance, currency, base_currency, get_price)
            for currency, wallet in self._wallets.items()
        }

    def get_total_value(
        self, base_currency: str = "USD", *, get_price: Callable[[str, str], float]
    ) -> float:
        """Return the total value of all wallets in the base currency"""
        return sum(self.get_values(base_currency, get_price=get_price).values())

    def get_wallet(self, currency_code: str) -> Wallet:
        """Return the wallet of the currency"""
        if currency_code not in self._wallets:
            raise KeyError(f"Currency {currency_code} not in portfolio.")

        return self._wallets[currency_code]

    @property
    def user(self) -> User:
        return self._user

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def wallets(self) -> dict[str, Wallet]:
        return deepcopy(self._wallets)

    def to_dict(self) -> dict[str, Any]:
        """Convert the portfolio to a portfolios.json record"""
        wallets = self.wallets

        return {
            "user_id": self._user_id,
            "wallets": {
                currency: wallet.to_dict() for currency, wallet in wallets.items()
            },
        }

    @classmethod
    def from_dict(cls, portfolio_profile: dict[str, Any], user: User) -> "Portfolio":
        """Create a portfolio from a portfolios.json record"""
        wallets = {
            currency: Wallet.from_dict({"currency_code": currency, **wallet})
            for currency, wallet in portfolio_profile["wallets"].items()
        }
        return cls(user, wallets)
