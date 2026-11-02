# Выгрузка на eBay — пошагово

Всё через официальный API eBay (Sell Inventory API). По умолчанию работает **sandbox** (тестовый eBay, ничего не публикуется по-настоящему).

## 0. Что такое ключи и где они живут
| Что | Похоже на | Секрет? | Где хранится |
|---|---|---|---|
| App ID (Client ID) | `Asiia-vinted-SBX-1a2b…` | нет, это «логин» приложения | `config/ebay.json` |
| Dev ID | `a1b2c3d4-…` | нет, нашему коду не нужен | нигде |
| RuName | `Asiia_Elebeso-Asiia-vin-abcde` | нет | `config/ebay.json` |
| **Cert ID (Client Secret)** | `SBX-xxxxxxxx-…` (пример) | **ДА, как пароль** | Диспетчер учётных данных Windows (через `ebay_secrets.py`) |
| **Refresh token** (после входа) | `v^1.1#…` (пример) | **ДА**, даёт доступ к аккаунту ~18 мес. | Диспетчер учётных данных Windows (сам) |

Правила: секреты не вставлять в чат (в т.ч. сюда), в код, в Excel, в скриншоты, в GitHub. Утёк — сразу Application Keys → сброс Cert ID и `python ebay_secrets.py forget`.

## 1. Ключи разработчика (один раз, ~15 минут)
1. Включи двухфакторную защиту на eBay-аккаунте (Konto → Sicherheit), developer.ebay.com входит через него же.
2. **Application Keys** → создай Keyset для **Sandbox**. Скопируй **App ID** в `config/ebay.json`. Cert ID пока не трогай.
3. https://developer.ebay.com/sandbox → **Register a new Sandbox user** (выдуманные данные, свой пароль, не тот же, что от настоящего eBay).
4. **User Tokens** (рядом с Sandbox keyset) → **Get a Token from eBay via Your Application** → **Add eBay Redirect URL** → заполни название и Privacy Policy URL (можно ссылку на свой профиль), остальное по умолчанию → Save. Скопируй **RuName** в `config/ebay.json`.
5. `config/ebay.json` делается копией `config/ebay.example.json`. Поле client_secret там специально нет.
6. Установи безопасное хранилище и положи туда Cert ID:
```
pip install keyring
cd src\ebay
python ebay_secrets.py set      # вставь Cert ID (Ctrl+V или правый клик), ввод не видно, Enter
python ebay_secrets.py status   # должно быть: Cert ID: stored
```

## 2. Подключить аккаунт
```
python ebay_login.py
```
Откроется браузер (адрес должен начинаться с `https://auth.sandbox.ebay.com`) → войди **тестовым sandbox-пользователем** → «I agree» → скопируй адрес страницы, куда тебя перекинуло, и вставь в терминал. Скрипт проверит, что это ответ на именно этот вход. Токен сохраняется в Диспетчере учётных данных, файла с токеном больше нет.

## 3. Место отправки и правила (доставка, оплата, возврат)
```
python ebay_setup.py
```
Скрипт создаст место отправки (Нюрнберг) и покажет ID правил. Если их нет — создай в Seller Hub (Konto → Rahmenbedingungen) и запусти ещё раз. Вставь по одному ID каждого типа в `config/ebay.json` → `policies`.

## 4. Подготовить объявления
```
cd ..\..
python src\ebay\make_ebay_ready.py
```
Получишь `outputs/ebay_ready.csv`. Открой в Excel, проверь тексты и цены (на eBay цены часто чуть выше, чем на Vinted). Убери всё с `[BITTE ERGÄNZEN]` — такие объявления скрипт не выложит.
Фото: папка `photos/<id>/` → 1–12 jpg, первое — главное.

## 5. Выгрузить
```
python src\ebay\ebay_publish.py --only 3,7          # черновики (не видны покупателям)
python src\ebay\ebay_publish.py --only 3,7 --publish # опубликовать
```
В production перед публикацией каждой вещи скрипт покажет название и цену и попросит ввести `JA`. Без `--only` публиковать на настоящем eBay нельзя.
Категорию eBay подбирает сам. Если нужны обязательные характеристики (например «Abteilung»), добавь в csv колонку `aspect_Abteilung` со значением «Damen». Итог — в `outputs/ebay_report.csv`.

## 6. Настоящий eBay
Когда в sandbox всё прошло: создай Production keyset, в `config/ebay.json` поставь `"environment": "production"`, новые ключи и повтори шаги 2–3. Начни с 1–2 вещей.

## 7. Перед загрузкой на GitHub
```
python tools\check_secrets.py
```
Должно быть `OK: no secrets found.` Иначе не загружать.

## Отключить всё
`python src\ebay\ebay_secrets.py forget` — удалит Cert ID и вход из Windows. На стороне eBay: сброс Cert ID в Application Keys.

Важно: если вещь продалась на Vinted, сними её с eBay вручную, иначе продашь дважды.
