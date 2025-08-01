FROM python:3.11-slim
WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm

CMD python -c "import os, json, pathlib; idx = os.getenv('BOT_INDEX', '0'); p = pathlib.Path('settings/settings.json'); \
    (not p.exists()) and (lambda: ( \
        p.parent.mkdir(parents=True, exist_ok=True), \
        json.dump( \
            dict(__import__('json').load(open('settings/settings.example.json'))) | \
            {'bot': {'prefix': f'{idx}.'}, 'name': f'bot{idx}', 'disable_checks': True}, \
            open(p, 'w'), indent=4 \
        ) \
    ))()" && python bot.py