# eBay: как это работает и как пользоваться

Программы в `src/ebay/` выставляют вещи на eBay.de через официальный API eBay (Sell APIs). Всё запускается **у тебя на компьютере**, из папки `src\ebay`:

```
cd "C:\Users\Ася\Desktop\портфолио\github\vinted-listing-quality\src\ebay"
```

Python всегда так: `C:\PythonSD\python.exe` (обычный `python` не работает из-за кириллицы в пути).

## 0. Ключи и где они живут

| Что | Похоже на | Секрет? | Где хранится |
|---|---|---|---|
| App ID (Client ID) | `Name-vinted-PRD-xxxx…` | нет, это «логин» приложения | `config/ebay.json` |
| RuName | `Name-Name-vinted-abcde` | нет | `config/ebay.json` |
| **Cert ID (Client Secret)** | `PRD-xxxxxxxx-…` (пример) | **ДА, как пароль** | Диспетчер учётных данных Windows |
| **Refresh token** (после входа) | `v^1.1#…` (пример) | **ДА**, доступ к аккаунту ~18 мес. | Диспетчер учётных данных Windows |

- `config/ebay.json` на GitHub не попадает (`.gitignore`); образец — `config/ebay.example.json`.
- Секреты не вставлять в чат, код, Excel, скриншоты и GitHub.
- Утёк ключ → developer.ebay.com → Application Keys → сбросить Cert ID, потом `ebay_secrets.py forget`.

## 1. Первая настройка (уже сделана, на случай нового компьютера)

1. developer.ebay.com → **Application Keys** → Production keyset. App ID и RuName → `config/ebay.json`.
2. Для Production eBay требует ответ про удаление данных (Marketplace Account Deletion): мы выбрали исключение «I do not persist eBay data».
3. Положить Cert ID в хранилище Windows:
   ```
   C:\PythonSD\python.exe -m pip install keyring
   C:\PythonSD\python.exe ebay_secrets.py set      # вставить Cert ID, ввод не видно, Enter
   C:\PythonSD\python.exe ebay_secrets.py status   # Cert ID: stored
   ```
4. Войти в свой eBay:
   ```
   C:\PythonSD\python.exe ebay_login.py
   ```
   Откроется браузер (адрес должен начинаться с `https://auth.ebay.com`) → войти → «I agree» → скопировать адрес страницы, куда перекинуло, и вставить **в терминал** (не в чат: в нём одноразовый код).
5. Правила доставки, оплаты и возврата:
   ```
   C:\PythonSD\python.exe ebay_setup.py
   ```
   Создаёт (или находит) правила по имени и записывает их ID в `config/ebay.json`:
   - «Versand Kleidung klein» — GLS 4,59 / DPD 5,15 / Hermes Päckchen 5,19 / DHL Paket 6,19;
   - «Versand groß (Schuhe, Stiefel)» — GLS 6,89 / DPD 6,95 / Hermes 6,99 / DHL 7,69;
   - «Zahlung Standard», «Keine Rücknahme» (частный продавец, без возврата).

Переключить тестовый/настоящий eBay: `ebay_env.py sandbox` / `ebay_env.py production` (сейчас production).

## 2. Как выставлять вещи

**Таблица** `outputs/ebay_ready_<партия>.csv` — одна строка на вещь:

| Колонка | Что писать |
|---|---|
| `id` | любое короткое имя, например `A107`; на eBay станет SKU `VA107` |
| `new_title` | до 80 символов |
| `new_description` | текст объявления (эмодзи удаляются сами — eBay их не принимает) |
| `brand`, `size`, `color`, `material` | заполняют характеристики Marke, Größe, Farbe, Material |
| `condition` | `Neu mit Etikett`, `Neu, ohne Etikett`, `Sehr gut`, `Gut`, `Zufriedenstellend` |
| `price` | цена в евро (= цена на Kleinanzeigen), торг включён везде |
| `category_id` | пусто = eBay подберёт сам; можно указать номер категории |
| `versand` | пусто = маленькая посылка, `gross` = обувь, пальто, тяжёлое |
| `photos` | пусто = все фото из папки; или список `01.jpg,02.jpg` |
| `aspect_<Название>` | любая характеристика eBay, например `aspect_Abteilung` = `Damen`; несколько значений через `;` |

**Фото**: `photos/<id>/01.jpg, 02.jpg …` (до 12, от 500 px). Первое — настоящее фото вещи; фото с ИИ-манекеном — только вторым.

**Проверка** (ничего не создаёт и не загружает):
```
C:\PythonSD\python.exe ebay_publish.py --input ..\..\outputs\ebay_ready_batch3.csv --check
```
Для каждой вещи: категория, «check OK» или чего не хватает (`missing: …`) с примерами допустимых значений.

**Публикация** (перед каждой вещью нужно ввести `JA`):
```
C:\PythonSD\python.exe ebay_publish.py --input ..\..\outputs\ebay_ready_batch3.csv --publish --only N039,N049
```
Повторный запуск для уже выставленной вещи **обновляет** объявление, второе не создаётся. Ошибка одной вещи не останавливает остальные. Итог — в `outputs/ebay_report.csv`.

## 3. Уже выставленные вещи

```
C:\PythonSD\python.exe ebay_manage.py list            # все вещи: статус, цена, ссылка
C:\PythonSD\python.exe ebay_manage.py end A107        # снять с продажи (несколько: A107,A110)
```
`end` ничего не удаляет: объявление останавливается, черновик остаётся. Вернуть: `ebay_publish.py --only A107 --publish`.

**Продалось на Vinted или Kleinanzeigen → сразу `end` на eBay**, иначе продашь дважды.

## 4. Подводные камни (наш опыт)

- **Состояние «Gut»** в одежде и гимнастике eBay не принимает → ставить `Sehr gut` (в одежде показывается как «Gebraucht – gut»).
- **Обязательные характеристики** зависят от категории: джинсы — Schrittlänge (в дюймах: `30 in`, `30,5 in`); куртки и пальто — Produktart, Stil, Außenmaterial; кроссовки и бельё — Abteilung и Stil; книги — Autor, Buchtitel, Sprache; накладные ногти — Produktart `Press-On Nägel`.
- **Abteilung лучше указывать всегда**, иначе eBay может сам поставить «Kinder».
- **Бельё**: ношеные трусики запрещены; в названии не писать «nie getragen» (eBay отклоняет), писать «neu ungetragen».
- **Чужие бренды и имена** (K-Pop-айдолы и т.п.) в названии не использовать.
- **Категорию eBay иногда угадывает неверно** (колонка → фигурки Star Wars) — тогда указать `category_id` вручную.

## 5. Перед загрузкой на GitHub
```
C:\PythonSD\python.exe tools\check_secrets.py
```
(из корня проекта). Должно быть `OK: no secrets found.` Иначе не загружать.

## Отключить всё
`C:\PythonSD\python.exe ebay_secrets.py forget` — удалит Cert ID и вход из Windows. На стороне eBay: сброс Cert ID в Application Keys.
