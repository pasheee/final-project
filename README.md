# ValutaTrade Hub

Консольное приложение для виртуального портфеля фиатных и криптовалют: регистрация, вход, покупка и продажа валюты, просмотр портфеля и курсов.

## Установка

```bash
uv sync
```

## Запуск

```bash
uv run finalproject
```

Или `python main.py`. Запускать нужно из корня проекта: `config.json`, `data/` и `logs/` ищутся в текущей папке. Выход из программы — команда `exit`.

## Команды

| Команда | Что делает |
|---|---|
| `register --username alice --password 1234` | регистрирует пользователя и создаёт ему пустой портфель |
| `login --username alice --password 1234` | входит в систему |
| `show-portfolio [--base USD]` | показывает кошельки и их стоимость в базовой валюте |
| `buy --currency BTC --amount 0.05` | покупает валюту, стоимость списывается с USD-кошелька |
| `sell --currency BTC --amount 0.01` | продаёт валюту, выручка зачисляется на USD-кошелёк |
| `get-rate --from USD --to BTC` | показывает курс и обратный курс |
| `update-rates [--source coingecko]` | загружает свежие курсы из ExchangeRate-API и CoinGecko, с `--source` — только из одного |
| `show-rates [--currency BTC \| --top 2] [--base EUR]` | показывает курсы из кеша: все, одной валюты или N самых дорогих криптовалют |

`show-portfolio`, `buy` и `sell` доступны только после `login`.

Поддерживаемые валюты: USD, EUR, BTC, RUB, ETH. Коды пишутся заглавными буквами: `usd` программа не примет.

## Ошибки

| Исключение | Где возникает | Команды | Что выводится |
|---|---|---|---|
| `CurrencyNotFoundError` | `get_currency()` и проверка кода валюты; базовая валюта в `Portfolio.get_values()` | `buy`, `sell`, `get-rate`, `show-portfolio`, `show-rates` | `Неизвестная валюта 'XYZ'`, `Курс для 'ABC' не найден в кеше.` или причина вроде `Code 'usd' must be uppercase.`, затем список валют и подсказка `get-rate -h` |
| `InsufficientFundsError` | `Wallet.withdraw()` | `buy` (не хватает USD), `sell` | `Недостаточно средств: доступно 0.0050 BTC, требуется 1.0000 BTC` |
| `WalletDoesntExist` | `sell()` | `sell` | `У вас нет кошелька 'ETH'. …` |
| `ApiRequestError` | клиенты внешних API в `parser_service/api_clients.py` | `update-rates` | `Ошибка при обращении к внешнему API: …` и совет повторить позже или проверить сеть |
| `StaleRateError` | `get_rate()`, `buy()`, `sell()` | `get-rate`, `buy`, `sell` | `Курс BTC→USD устарел (обновлён …). Выполните 'update-rates', чтобы загрузить свежие данные.` |

## Как пополнить счёт

Покупка USD ничего не списывает, поэтому так пополняется счёт:

```
> buy --currency USD --amount 1000
```

## Пример

```
> register --username alice --password 1234
Пользователь 'alice' зарегистрирован (id=0). Войдите: login --username alice --password ****
> login --username alice --password 1234
Вы вошли как 'alice'
> buy --currency USD --amount 1000
Покупка выполнена: 1,000.00 USD по курсу 1.00 USD/USD
Изменения в портфеле:
- USD: было 0.00 → стало 1,000.00
Оценочная стоимость покупки: 1,000.00 USD
> buy --currency BTC --amount 0.01
Покупка выполнена: 0.0100 BTC по курсу 59337.21 USD/BTC
Изменения в портфеле:
- BTC: было 0.0000 → стало 0.0100
- USD: было 1,000.00 → стало 406.63
Оценочная стоимость покупки: 593.37 USD
> show-portfolio
Портфель пользователя 'alice' (база: USD):
- USD: 406.63  → 406.63 USD
- BTC: 0.0100  → 593.37 USD
---------------------------------
ИТОГО: 1,000.00 USD
```

## Данные

| Файл | Что хранит |
|---|---|
| `data/users.json` | пользователи: id, имя, хеш пароля, соль, дата регистрации |
| `data/portfolios.json` | портфели: id пользователя и его кошельки |
| `data/rates.json` | снимок последних курсов к USD: курс, время обновления и источник |
| `data/exchange_rates.json` | журнал всех полученных курсов, по одной записи на пару и момент времени |

Core читает курсы из `data/rates.json`. Там лежат только курсы к USD, а курс любой другой пары считается через доллар. Сервис парсинга сначала дописывает полученные курсы в журнал `data/exchange_rates.json`, а затем переносит в снимок те, что свежее текущих. Записи с уже известным `id` и с некорректными кодами или курсом в журнал не попадают. Курс в снимке считается свежим `RATES_TTL_SECONDS` секунд (300). Если курс старше, команды `get-rate`, `buy` и `sell` сначала переносят в снимок свежие записи из журнала, а если свежих нет, просят выполнить `update-rates`.

## Parser Service

Курсы загружаются из двух API: фиатные валюты из ExchangeRate-API, криптовалюты из CoinGecko. CoinGecko работает без ключа, а для ExchangeRate-API нужен свой ключ: скопируй `.env.example` в `.env` и впиши ключ в `EXCHANGERATE_API_KEY`.

Отдельно запускать ничего не нужно: вместе с программой в фоне стартует планировщик из `parser_service/scheduler.py`. Раз в `RATES_TTL_SECONDS / 3` секунд он дописывает свежие курсы в журнал, а раз в `RATES_TTL_SECONDS` переносит их в снимок `rates.json`. Обновить курсы сразу можно командой `update-rates`, посмотреть снимок — командой `show-rates`.

## Валюты

Валюты описаны в `core/currencies.py`. Абстрактный класс `Currency` хранит `name` и `code` и требует метод `get_display_info()`. При создании валюты код проверяется: заглавные буквы, от 2 до 5 символов, без пробелов. Имя не может быть пустым.

| Класс | Дополнительные атрибуты | `get_display_info()` |
|---|---|---|
| `FiatCurrency` | `issuing_country` | `[FIAT] USD — US Dollar (Issuing: United States)` |
| `CryptoCurrency` | `algorithm`, `market_cap` | `[CRYPTO] BTC — Bitcoin (Algo: SHA-256, MCAP: 1.12e12)` |

Все валюты лежат в реестре `CURRENCIES`. `get_currency(code)` проверяет код и возвращает валюту из реестра, а на неизвестный код бросает `CurrencyNotFoundError`. Через неё коды проверяют `buy`, `sell` и `get-rate`.

## Настройки

Настройки лежат в `config.json` и читаются классом `SettingsLoader` из `infra/settings.py`.

| Ключ | Что задаёт |
|---|---|
| `USERS_PATH`, `PORTFOLIOS_PATH`, `RATES_PATH`, `HISTORY_PATH` | пути к JSON-файлам от корня проекта |
| `RATES_TTL_SECONDS` | сколько секунд курс считается свежим |
| `LOG_FORMAT` | формат строки лога |
| `LOG_LEVEL` | уровень логирования: `INFO`, для отладки `DEBUG` |

`SettingsLoader` и `DatabaseManager` из `infra/database.py` — синглтоны через `__new__`. У `SettingsLoader` два публичных метода: `load()` читает `config.json`, а `get(key, default=...)` возвращает значение по ключу. Если ключа нет и `default` не передан, бросается `ConfigError`. `DatabaseManager` читает и записывает JSON-файлы. Запись идёт через временный файл, чтобы при сбое файл не остался записанным наполовину.

**Где используются синглтоны.** usecases не обращаются к ним напрямую: core не зависит от инфры и получает всё нужное параметрами. `main` загружает настройки, по путям из них создаёт репозитории поверх `DatabaseManager` и кладёт их вместе с TTL в `AppContext`. Из него usecases получают репозитории, а `buy`, `sell` и `get_rate` — ещё и `RATES_TTL_SECONDS`. По той же причине `buy` и `sell` принимают пользователя из сессии, а не `user_id`, а `Portfolio.get_total_value()` получает курсы функцией `get_price`.

## Логи

`buy` и `sell` логируются декоратором `@log_action(verbose=True)` из `decorators.py` в файл `logs/actions.log`. Формат строковый, задаётся ключом `LOG_FORMAT`:

```
INFO 2026-10-26T00:47:53 BUY user='alice' currency='BTC' amount=0.01 rate=59337.21 base='USD' balance=0.0→0.01 result=OK
INFO 2026-10-26T00:47:53 SELL user='alice' currency='BTC' amount=1.0 result=ERROR error_type=InsufficientFundsError error_message='Недостаточно средств: доступно 0.0100 BTC, требуется 1.0000 BTC'
```

В строке: время, действие, пользователь, валюта и сумма. При успехе добавляются курс и базовая валюта, а `verbose=True` дописывает баланс кошелька «было→стало». В конце результат: `OK` или `ERROR` с типом и текстом ошибки. Ошибку декоратор записывает в лог и пробрасывает дальше. Файл ротируется при размере 1 МБ, хранятся 3 старых файла. Уровень по умолчанию `INFO`, для отладки поставь `LOG_LEVEL` в `DEBUG`. В тот же файл сервис парсинга пишет шаги обновления курсов и ошибки запросов к API.

## Структура

```
valutatrade_hub/
├── core/              модели, валюты, сценарии (usecases), порты, ошибки, утилиты, хеширование паролей
├── infra/             JSON-репозитории, DatabaseManager, SettingsLoader и ошибки хранилища
├── parser_service/    клиенты API, обновление курсов, фоновый планировщик, настройки и ошибки API
├── cli/               команды, разбор аргументов, сессия, форматирование вывода
├── decorators.py      @log_action
├── logging_config.py  настройка логов
└── main.py            сборка приложения и запуск
```

## Проверка кода

```bash
uv run ruff check .
```

```bash
uv run ruff format .
```


## Демонстрация

[![asciicast](https://asciinema.org/a/d8VlvASAGr5J7vu8.svg)](https://asciinema.org/a/d8VlvASAGr5J7vu8)

[Локальная запись Asciinema](docs/valutatrade-demo.cast) показывает регистрацию и вход,
обновление курсов через API, пополнение USD-кошелька, покупку и продажу валют,
оценку портфеля в USD и EUR, обработку ошибок и содержимое `logs/actions.log`.
Запись сделана с демонстрационным пользователем на отдельной копии данных.

Просмотр из корня проекта:

```bash
uvx asciinema play docs/valutatrade-demo.cast
```
