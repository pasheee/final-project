from valutatrade_hub.core.models import User

from .exceptions import NotLoggedError


class Session:
    """Current user of the command line"""

    def __init__(self):
        self._user: User | None = None

    def requires_user(self) -> User:
        if not self._user:
            raise NotLoggedError("Сначала выполните login")

        return self._user

    def login(self, user: User) -> None:
        self._user = user
