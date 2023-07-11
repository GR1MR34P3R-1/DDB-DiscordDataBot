import discord
from discord.ext import commands
import sqlite3
import datetime
import configparser
import multiprocessing

# Load the configuration from config.ini
config = configparser.ConfigParser()
config.read('config.ini')

bot_token = config.get('Bot', 'token')
base_directory = config.get('Bot', 'base_directory')
database_file = base_directory + '/LoggedData/data.db'
log_file = base_directory + '/LoggedData/data.log'

intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Connect to the SQLite database
conn = sqlite3.connect(database_file)
c = conn.cursor()

# Create a table for storing messages
c.execute('''CREATE TABLE IF NOT EXISTS messages
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              channel_id INTEGER,
              channel_name TEXT,
              guild_id INTEGER,
              guild_name TEXT,
              author_id INTEGER,
              author_name TEXT,
              content TEXT)''')

# Open the log file in append mode
log = open(log_file, 'a')

def log_message(message):
    # Log the message content, author, channel, and guild
    channel_id = message.channel.id
    channel_name = message.channel.name
    guild_id = message.guild.id if message.guild else None
    guild_name = message.guild.name if message.guild else None
    author_id = message.author.id
    author_name = message.author.name
    message_content = message.content

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f'[{timestamp}] [{guild_name}/{channel_name}] {author_name}: {message_content}'

    print(log_entry)

    # Save the message to the database
    c.execute("INSERT INTO messages (channel_id, channel_name, guild_id, guild_name, author_id, author_name, content) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (channel_id, channel_name, guild_id, guild_name, author_id, author_name, message_content))
    conn.commit()

    # Save the message to the log file
    log.write(log_entry + '\n')
    log.flush()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

    # Log old messages in text channels
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).read_message_history:
                async for message in channel.history(limit=None, oldest_first=True):
                    log_message(message)

    # Log old messages in private channels
    for channel in bot.private_channels:
        if isinstance(channel, discord.TextChannel):
            async for message in channel.history(limit=None, oldest_first=True):
                log_message(message)

@bot.event
async def on_message(message):
    p = multiprocessing.Process(target=log_message, args=(message,))
    p.start()

@bot.event
async def on_disconnect():
    # Close the database connection and log file
    conn.close()
    log.close()

bot.run(bot_token)
