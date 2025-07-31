FROM python:3.11-slim
WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm

CMD python -c "import os, json; idx = os.getenv('BOT_INDEX', '0'); f = open('settings/settings.example.json'); cfg = json.load(f); f.close(); cfg['bot']['prefix'] = f'{idx}.'; cfg['name'] = f'bot{idx}'; cfg['disable_checks'] = True; json.dump(cfg, open('settings/settings.json', 'w'), indent=4)" && python bot.py
