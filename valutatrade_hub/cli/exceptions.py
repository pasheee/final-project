from valutatrade_hub.core.exceptions import CoreError


class CliError(CoreError):
    pass


class NotLoggedError(CliError):
    pass
