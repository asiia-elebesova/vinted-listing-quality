# Как пользоваться (для себя)

1. Открой папку проекта, правый клик по пустому месту → «Открыть в терминале».
2. Вставь ключ: `$env:ANTHROPIC_API_KEY="твой_ключ"`
3. Проверка всех объявлений: `python src/llm_review.py`
4. Отчёт «было/стало»: `python src/report.py` → открой `outputs/review_report.md`
   (или `outputs/rewrites.csv` в Excel).
5. Новые вещи перед выкладкой: заполни `data/new_listings_template.csv` и запусти
   `python src/llm_review.py --input data/new_listings_template.csv`.
6. Свои правила меняй в `config/checklist.json`, свои данные и фразы — в `config/seller_profile.json`.

Тексты всегда проверяй сама перед загрузкой: [BITTE ERGÄNZEN: ...] — это то, что нужно дописать.
