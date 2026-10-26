from valutatrade_hub.core.exceptions import CoreError


class ApiRequestError(CoreError):
    def __init__(self, reason: str):
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")
