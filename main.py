import aiosqlite
import discord
from discord.ext import commands
from get_stock_info import get_stock_info

intents = discord.Intents.all()

bot = commands.Bot(command_prefix=">", intents=intents)

DATABASE_FN = "traders.db"

# Function to create database tables if they don't exist
async def create_tables():
    async with aiosqlite.connect(DATABASE_FN) as db:
        cursor = await db.cursor()
        
        # Create the 'users' table
        await cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER
            );
        ''')
        
        # Create the 'user_stocks' table
        await cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_stocks (
                user_id INTEGER,
                stock_symbol TEXT,
                amount INTEGER,
                PRIMARY KEY (user_id, stock_symbol),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
        ''')
        
        await db.commit()

# Function to check if a user is in the database
async def user_in_db(user_id):
    async with aiosqlite.connect(DATABASE_FN) as db:
        cursor = await db.cursor()
        await cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        
        user = await cursor.fetchone()
        
        return user

# Event handler for when the bot is ready
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await create_tables()

# Command to let a user join and initialize their balance
@bot.command()
async def join(ctx):
    user_id = ctx.author.id
    
    async with aiosqlite.connect(DATABASE_FN) as db:
        user = await user_in_db(user_id)
        
        if user:
            await ctx.send("ERROR: User has already joined.")
            return
        
        cursor = await db.cursor()
        
        await cursor.execute('INSERT INTO users (user_id, balance) VALUES (?, 5000)', (user_id,))
        
        await db.commit()
        
        await ctx.send(f"Welcome {ctx.author.name}! You have been granted an initial balance of $5000!")

# Command to allow a user to buy stocks
@bot.command()
async def buy(ctx, stock_symbol: str, amount: int):
    stock_price = get_stock_info(stock_symbol)
    
    if not stock_price:
        await ctx.send("ERROR: Invalid symbol.")
        return
    
    user_id = ctx.author.id
    
    async with aiosqlite.connect(DATABASE_FN) as db:
        cursor = await db.cursor()
        
        await cursor.execute('SELECT balance FROM users WHERE user_id=?', (user_id,))
        balance = await cursor.fetchone()
        
        if not balance:
            await ctx.send("ERROR: User has not joined.")
            return
        
        balance = balance[0]
        cost = int(amount * stock_price)
        
        if cost > balance:
            await ctx.send("ERROR: Insufficient balance.")
            return
        
        new_balance = balance - cost
        await cursor.execute('UPDATE users SET balance=? WHERE user_id=?', (new_balance, user_id))
        
        await cursor.execute('SELECT amount FROM user_stocks WHERE user_id=? AND stock_symbol=?', (user_id, stock_symbol))
        users_stocks = await cursor.fetchone()
        
        if users_stocks:
            new_amount = users_stocks[0] + amount
            await cursor.execute('UPDATE user_stocks SET amount=? WHERE user_id=? AND stock_symbol=?', (new_amount, user_id, stock_symbol))
        else:
            await cursor.execute('INSERT INTO user_stocks (user_id, stock_symbol, amount) VALUES (?, ?, ?)', (user_id, stock_symbol, amount))
        
        await ctx.send(f"Purchase successful: {amount} {stock_symbol} stocks.")
        await db.commit()

# Command to allow a user to sell stocks
@bot.command()
async def sell(ctx, stock_symbol: str, amount: int):
    stock_price = get_stock_info(stock_symbol)
    
    if not stock_price:
        await ctx.send("ERROR: Invalid symbol.")
        return
    
    user_id = ctx.author.id
    
    async with aiosqlite.connect(DATABASE_FN) as db:
        cursor = await db.cursor()
        
        await cursor.execute('SELECT balance FROM users WHERE user_id=?', (user_id,))
        balance = await cursor.fetchone()
        
        if not balance:
            await ctx.send("ERROR: User has not joined.")
            return
        
        balance = balance[0]
        
        await cursor.execute('SELECT amount FROM user_stocks WHERE user_id=? AND stock_symbol=?', (user_id, stock_symbol))
        users_stocks = await cursor.fetchone()
        
        if users_stocks and users_stocks[0] >= amount:
            new_amount = users_stocks[0] - amount
            
            await cursor.execute('UPDATE user_stocks SET amount=? WHERE user_id=? AND stock_symbol=?', (new_amount, user_id, stock_symbol))
            await cursor.execute('DELETE FROM user_stocks WHERE amount=0')
            
            new_balance = int(balance + (amount * stock_price))
            await cursor.execute('UPDATE users SET balance=? WHERE user_id=?', (new_balance, user_id))
            await ctx.send(f"Sale successful: {amount} {stock_symbol} stocks.")
        else:
            await ctx.send("ERROR: Invalid amount.")
        
        await db.commit()

# Command to display user's portfolio
@bot.command()
async def portfolio(ctx):
    user_id = ctx.author.id
    
    async with aiosqlite.connect(DATABASE_FN) as db:
        user = await user_in_db(user_id)
        
        if not user:
            await ctx.send("ERROR: User has not joined.")
            return
        
        cursor = await db.cursor()
        await cursor.execute("SELECT stock_symbol, amount FROM user_stocks WHERE user_id=?", (user_id,))
        
        stocks = "\n".join(f"{row[0]}: {row[1]}" for row in await cursor.fetchall())
        
        await cursor.execute('SELECT balance FROM users WHERE user_id=?', (user_id,))
        balance = await cursor.fetchone()
        balance = balance[0]
        
        embed = discord.Embed(title=ctx.author.name, description=f"Balance: {balance}", color=discord.Colour.blue())
        embed.add_field(name="Assets:", value=stocks)
        embed.set_thumbnail(url=ctx.author.avatar)
        await ctx.send(embed=embed)


bot.run("")