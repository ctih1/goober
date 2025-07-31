with open("docker-compose.yml", "w") as f:
    f.write("version: '3'\nservices:\n")
    for i in range(1, 31):
        delay = (i - 1) * 30
        f.write(f"""  bot{i}:
    build: .
    environment:
      - DISCORD_BOT_TOKEN=${{TOKEN_{i}}}
      - BOT_INDEX={i}
    volumes:
      - ./data/bot{i}:/app/data
      - ./data/bot{i}/settings:/app/settings
    restart: unless-stopped
""")