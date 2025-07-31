with open("docker-compose.yml", "w") as f:
    f.write("version: '3'\nservices:\n")
    for i in range(1, 21):
        f.write(f"""  bot{i}:
    build: .
    environment:
      - DISCORD_BOT_TOKEN=${{TOKEN_{i}}}
      - BOT_INDEX={i}
    restart: unless-stopped
""")