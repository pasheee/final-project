from valutatrade_hub.core.exceptions import CoreError


class ConfigError(CoreError):
    pass


class DatabaseError(CoreError):
    pass


class UserDoesntExist(DatabaseError):
    pass


class UserAlreadyExist(DatabaseError):
    pass


class PortfolioDoesntExist(DatabaseError):
    pass


class RateNotFound(DatabaseError):
    pass
