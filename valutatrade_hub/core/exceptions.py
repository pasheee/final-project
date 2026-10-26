class CoreError(Exception):
    pass


class InvalidPassword(CoreError):
    pass


class CurrencyNotFoundError(CoreError):
    pass


class WalletDoesntExist(CoreError):
    pass


class ValidationError(CoreError):
    pass


class InsufficientFundsError(CoreError):
    def __init__(self, available: float, required: float, code: str):
        super().__init__(
            f"Недостаточно средств: доступно {available:.4f} {code}, "
            f"требуется {required:.4f} {code}"
        )


class StaleRateError(CoreError):
    pass
