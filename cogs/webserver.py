import discord
from discord.ext import commands, tasks
import asyncio
from aiohttp import web
import psutil
import os
import json
from datetime import datetime
import time
import aiohttp
from aiohttp import WSMsgType

class GooberWeb(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application()
        self.runner = None
        self.site = None
        self.last_command = "No commands executed yet"
        self.last_command_time = "Never"
        self.start_time = time.time()
        self.websockets = set()
        
        self.app.add_routes([
            web.get('/', self.handle_index),
            web.get('/changesong', self.handle_changesong),
            web.get('/stats', self.handle_stats),
            web.get('/data', self.handle_json_data),
            web.get('/ws', self.handle_websocket),
            web.get('/styles.css', self.handle_css),
        ])

        self.bot.loop.create_task(self.start_web_server())
        self.update_clients.start()
        
    async def start_web_server(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '0.0.0.0', 8080)
        await self.site.start()
        print("Goober web server started on port 8080")
    
    async def stop_web_server(self):
        await self.site.stop()
        await self.runner.cleanup()
        print("Web server stopped")
    
    def cog_unload(self):
        self.update_clients.cancel()
        self.bot.loop.create_task(self.stop_web_server())
    
    @tasks.loop(seconds=5)
    async def update_clients(self):
        if not self.websockets:
            return
            
        stats = await self.get_bot_stats()
        message = json.dumps(stats)
        
        for ws in set(self.websockets):
            try:
                await ws.send_str(message)
            except ConnectionResetError:
                self.websockets.remove(ws)
            except Exception as e:
                print(f"Error sending to websocket: {e}")
                self.websockets.remove(ws)
    
    async def handle_websocket(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.websockets.add(ws)
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.ERROR:
                    print(f"WebSocket error: {ws.exception()}")
        finally:
            self.websockets.remove(ws)
            
        return ws
    
    async def handle_css(self, request):
        css_path = os.path.join(os.path.dirname(__file__), 'styles.css')
        if os.path.exists(css_path):
            return web.FileResponse(css_path)
        return web.Response(text="CSS file not found", status=404)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
            
        ctx = await self.bot.get_context(message)
        if ctx.valid and ctx.command:
            self._update_command_stats(ctx.command.name, ctx.author)
    
    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction, command):
        self._update_command_stats(command.name, interaction.user)
    
    def _update_command_stats(self, command_name, user):
        self.last_command = f"{command_name} (by {user.name}#{user.discriminator})"
        self.last_command_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.websockets:
            asyncio.create_task(self.update_clients())
    
    async def get_bot_stats(self):
        process = psutil.Process(os.getpid())
        mem_info = process.memory_full_info()
        cpu_percent = psutil.cpu_percent()
        process_cpu = process.cpu_percent()
        
        memory_json_size = "N/A"
        if os.path.exists("memory.json"):
            memory_json_size = f"{os.path.getsize('memory.json') / 1024:.2f} KB"
        
        guilds = sorted(self.bot.guilds, key=lambda g: g.member_count, reverse=True)
        guild_info = [f"{g.name} ({g.member_count} members)" for g in guilds]
        
        uptime_seconds = int(time.time() - self.start_time)
        uptime_str = f"{uptime_seconds // 86400}d {(uptime_seconds % 86400) // 3600}h {(uptime_seconds % 3600) // 60}m {uptime_seconds % 60}s"
        
        return {
            "ram_usage": f"{mem_info.rss / 1024 / 1024:.2f} MB",
            "cpu_usage": f"{process_cpu}%",
            "system_cpu": f"{cpu_percent}%",
            "memory_json_size": memory_json_size,
            "guild_count": len(guilds),
            "guilds": guild_info,
            "last_command": self.last_command,
            "last_command_time": self.last_command_time,
            "bot_uptime": uptime_str,
            "latency": f"{self.bot.latency * 1000:.2f} ms",
            "bot_name": self.bot.user.name,
            "bot_avatar_url": str(self.bot.user.avatar.url) if self.bot.user.avatar else "",
            "authenticated": os.getenv("gooberauthenticated"),
            "lastmsg": os.getenv("gooberlatestgen")
        }
    
    async def handle_update(self, request):
        if os.path.exists("goob/update.py"):
            return web.FileResponse("goob/update.py")
        return web.Response(text="Update file not found", status=404)

    async def handle_changesong(self, request):
        song = request.query.get('song', '')
        if song:
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=song))
            return web.Response(text=f"Changed song to: {song}")
        return web.Response(text="Please provide a song parameter", status=400)

    async def handle_changes(self, request):
        if os.path.exists("goob/changes.txt"):
            return web.FileResponse("goob/changes.txt")
        return web.Response(text="Changelog not found", status=404)
    
    async def handle_index(self, request):
        stats = await self.get_bot_stats()

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>goobs central</title>
            <link rel="stylesheet" href="/styles.css">
        </head>
        <body>
            <div class="topnav">
                <div class="stat-item" id="ram-usage">
                    <span class="stat-title">RAM:</span>
                    <span>{stats['ram_usage']}</span>
                </div>
                <div class="stat-item" id="cpu-usage">
                    <span class="stat-title">CPU:</span>
                    <span>{stats['cpu_usage']}</span>
                </div>
                <div class="stat-item" id="system-cpu">
                    <span class="stat-title">System CPU:</span>
                    <span>{stats['system_cpu']}</span>
                </div>
                <div class="stat-item" id="latency">
                    <span class="stat-title">Latency:</span>
                    <span>{stats['latency']}</span>
                </div>
                <div class="stat-item" id="json-size">
                    <span class="stat-title">JSON Size:</span>
                    <span>{stats['memory_json_size']}</span>
                </div>
                <div class="stat-item" id="uptime">
                    <span class="stat-title">Uptime:</span>
                    <span>{stats['bot_uptime']}</span>
                </div>
            </div>

            <div class="center">
                <h2>
                <div class="bot-info">
                    <img src="{stats['bot_avatar_url']}" alt="botvatar" class="bot-avatar" id="bot-avatar">
                    <span id="bot-name">{stats['bot_name']}</span>
                </div>
                </h2>
                <hr>
                <p>your stupid little goober that learns off other people's messages</p>
            </div>

            <div class="stat-container-row">
                <div>
                    <div class="stat-title">Last Command</div>
                    <div id="last-command">{stats['last_command']}</div>
                    <div style="font-size: 0.9em; color: #999;" id="last-command-time">at {stats['last_command_time']}</div>
                    <br>
                    <div class="stat-title">Logged into goober central</div>
                    <div id="last-command">{stats['authenticated']}</div>
                    <br>
                    <div class="stat-title">Last generated message</div>
                    <div id="last-command">{stats['lastmsg']}</div>
                    <br>
                    <div class="stat-title">Change song</div>
                    <form action="/changesong" method="get">
                        <input type="text" name="song" placeholder="Enter song name..." style="background-color:black; color:white; solid #ccc;">
                        <button type="submit">
                            change song
                        </button>
                    </form>
                </div>

                <div class="balls">
                    <div class="stat-title">Servers (<span id="guild-count">{stats['guild_count']}</span>)</div>
                    <div id="guild-list">
                        {"".join(f'<div class="guild-item">{guild}</div>' for guild in stats['guilds'])}
                    </div>
                </div>
            </div>
            <script>
                const ws = new WebSocket('ws://' + window.location.host + '/ws');
                
                ws.onmessage = function(event) {{
                    const data = JSON.parse(event.data);

                    document.getElementById('ram-usage').innerHTML = `<span class="stat-title">RAM:</span> <span>${{data.ram_usage}}</span>`;
                    document.getElementById('cpu-usage').innerHTML = `<span class="stat-title">CPU:</span> <span>${{data.cpu_usage}}</span>`;
                    document.getElementById('system-cpu').innerHTML = `<span class="stat-title">System CPU:</span> <span>${{data.system_cpu}}</span>`;
                    document.getElementById('latency').innerHTML = `<span class="stat-title">Latency:</span> <span>${{data.latency}}</span>`;
                    document.getElementById('json-size').innerHTML = `<span class="stat-title">JSON Size:</span> <span>${{data.memory_json_size}}</span>`;
                    document.getElementById('uptime').innerHTML = `<span class="stat-title">Uptime:</span> <span>${{data.bot_uptime}}</span>`;
                    
                    document.getElementById('bot-name').textContent = data.bot_name;
                    const botAvatar = document.getElementById('bot-avatar');
                    if (botAvatar.src !== data.bot_avatar_url) {{
                        botAvatar.src = data.bot_avatar_url;
                    }}
                    

                    document.getElementById('last-command').textContent = data.last_command;
                    document.getElementById('last-command-time').textContent = `at ${{data.last_command_time}}`;
                    
                    document.getElementById('guild-count').textContent = data.guild_count;
                    document.getElementById('guild-list').innerHTML = 
                        data.guilds.map(guild => `<div class="guild-item">${{guild}}</div>`).join('');
                }};
                
                ws.onclose = function() {{
                    console.log('WebSocket disconnected');
                }};
            </script>
        </body>
        </html>
        """
        
        return web.Response(text=html_content, content_type='text/html')
    
    async def handle_stats(self, request):
        return await self.handle_index(request)
    
    async def handle_json_data(self, request):
        stats = await self.get_bot_stats()
        return web.json_response(stats)

async def setup(bot):
    await bot.add_cog(GooberWeb(bot))