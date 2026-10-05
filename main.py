import os
import io
import asyncio
import aiohttp
import discord
from discord import app_commands, ui
from discord.ext import commands
import matplotlib.pyplot as plt
from aiohttp import web

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Helper function to format currency ($164.63M, $153.0K, etc.)
def format_currency(num):
    if num is None:
        return "$0"
    try:
        val = float(num)
    except (ValueError, TypeError):
        return f"${num}"
    
    if abs(val) >= 1_000_000_000:
        return f"${val / 1_000_000_000:.2f}B"
    elif abs(val) >= 1_000_000:
        return f"${val / 1_000_000:.2f}M"
    elif abs(val) >= 1_000:
        return f"${val / 1_000:.1f}K"
    else:
        return f"${val:,.0f}"

# Helper function to format numbers with commas (1,502)
def format_num(num):
    if num is None:
        return "0"
    try:
        val = float(num)
        return f"{val:,.0f}"
    except (ValueError, TypeError):
        return str(num)


# -------------------------------------------------------------
# SEARCH ITEM MODAL (POP-UP INPUT)
# -------------------------------------------------------------
class SearchItemModal(ui.Modal, title="🔍 Search Auction House"):
    item_name = ui.TextInput(
        label="Item Name / Category",
        placeholder="e.g., Elytra, Netherite Block, Beacon...",
        min_length=2,
        max_length=50,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        query = self.item_name.value
        
        url = f"https://api.donutsmp.net/v1/auctionhouse?search={query.lower()}"
        timeout = aiohttp.ClientTimeout(total=5)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get("items", [])
                        
                        embed = discord.Embed(
                            title=f"🔍 Search Results: {query}",
                            color=discord.Color.gold()
                        )
                        
                        if items:
                            for item in items[:8]:
                                embed.add_field(
                                    name=f"{item.get('item_name', query)} x{item.get('amount', 1)}",
                                    value=f"Price: **{format_currency(item.get('price', 0))}**\nSeller: `{item.get('seller', 'N/A')}`",
                                    inline=False
                                )
                        else:
                            embed.description = f"No items matching **{query}** were found on the Auction House."
                        
                        await interaction.followup.send(embed=embed, ephemeral=True)
                    else:
                        await interaction.followup.send(f"Failed to retrieve data from API (Status: {response.status}).", ephemeral=True)
        except Exception:
            await interaction.followup.send("A connection error occurred while searching for items.", ephemeral=True)


# -------------------------------------------------------------
# AUCTION HOUSE CATEGORY DROPDOWN
# -------------------------------------------------------------
class AuctionCategorySelect(ui.Select):
    def __init__(self, username: str):
        options = [
            discord.SelectOption(label="Elytra", description="View Elytra listings on Auction House", emoji="🕊️"),
            discord.SelectOption(label="Netherite Block", description="View Netherite Block listings", emoji="⬛"),
            discord.SelectOption(label="Armor & Weapons", description="View swords, axes, and armor sets", emoji="⚔️"),
            discord.SelectOption(label="Spawners & Farm", description="View spawners & farming items", emoji="📦"),
            discord.SelectOption(label="Shards & Keys", description="View Shards, Crate Keys, etc.", emoji="🔮"),
            discord.SelectOption(label="All Items", description="View all Auction House listings", emoji="🛒"),
        ]
        super().__init__(
            placeholder="Select an item category to view...",
            min_values=1,
            max_values=1,
            options=options
        )
        self.username = username

    async def callback(self, interaction: discord.Interaction):
        selected_category = self.values[0]
        await interaction.response.defer(ephemeral=True)
        
        search_query = "" if selected_category == "All Items" else selected_category.lower()
        url = f"https://api.donutsmp.net/v1/auctionhouse?search={search_query}"
        timeout = aiohttp.ClientTimeout(total=5)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get("items", [])
                        
                        embed = discord.Embed(
                            title=f"🛒 Auction House - Category: {selected_category}",
                            color=discord.Color.gold()
                        )
                        embed.set_footer(text=f"Requested for {self.username}")

                        if items:
                            for item in items[:8]:
                                embed.add_field(
                                    name=f"{item.get('item_name', selected_category)} x{item.get('amount', 1)}",
                                    value=f"Price: **{format_currency(item.get('price', 0))}**\nSeller: `{item.get('seller', 'N/A')}`",
                                    inline=False
                                )
                        else:
                            embed.description = f"There are currently no **{selected_category}** items listed on the Auction House."
                        
                        await interaction.followup.send(embed=embed, ephemeral=True)
                    else:
                        await interaction.followup.send("Failed to load Auction House data.", ephemeral=True)
        except Exception:
            await interaction.followup.send("Failed to connect to the Auction House API.", ephemeral=True)


class AuctionCategoryView(ui.View):
    def __init__(self, username: str):
        super().__init__(timeout=180)
        self.add_item(AuctionCategorySelect(username))


# -------------------------------------------------------------
# ORDERS CATEGORY DROPDOWN
# -------------------------------------------------------------
class OrdersCategorySelect(ui.Select):
    def __init__(self, username: str):
        options = [
            discord.SelectOption(label="All Orders", description="View all active orders for this player", emoji="📦"),
            discord.SelectOption(label="Buy Orders", description="View active buy orders only", emoji="🟢"),
            discord.SelectOption(label="Sell Orders", description="View active sell orders only", emoji="🔴"),
        ]
        super().__init__(
            placeholder="Select order filter to view...",
            min_values=1,
            max_values=1,
            options=options
        )
        self.username = username

    async def callback(self, interaction: discord.Interaction):
        selected_type = self.values[0]
        await interaction.response.defer(ephemeral=True)
        
        url = f"https://api.donutsmp.net/v1/player/{self.username}/orders"
        timeout = aiohttp.ClientTimeout(total=5)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        orders_list = data.get("orders", [])
                        
                        # Filter order by type (Buy/Sell)
                        if selected_type == "Buy Orders":
                            orders_list = [o for o in orders_list if o.get("type", "").lower() == "buy"]
                        elif selected_type == "Sell Orders":
                            orders_list = [o for o in orders_list if o.get("type", "").lower() == "sell"]

                        embed = discord.Embed(
                            title=f"📦 Player Orders: {self.username} ({selected_type})",
                            color=discord.Color.blue()
                        )
                        
                        if orders_list:
                            for order in orders_list[:6]:
                                order_type = order.get("type", "ORDER").upper()
                                embed.add_field(
                                    name=f"[{order_type}] {order.get('item', 'Item')} x{order.get('amount', 1)}",
                                    value=f"Price/Unit: **{format_currency(order.get('price_per_unit', 0))}**\nTotal: **{format_currency(order.get('total_price', 0))}**",
                                    inline=False
                                )
                        else:
                            embed.description = f"Player `{self.username}` currently has no active **{selected_type}**."
                            
                        await interaction.followup.send(embed=embed, ephemeral=True)
                    else:
                        await interaction.followup.send(f"No order data found for player `{self.username}`.", ephemeral=True)
        except Exception:
            await interaction.followup.send("Failed to connect to the Orders API.", ephemeral=True)


class OrdersCategoryView(ui.View):
    def __init__(self, username: str):
        super().__init__(timeout=180)
        self.add_item(OrdersCategorySelect(username))


# -------------------------------------------------------------
# MAIN STATS INTERACTIVE VIEW
# -------------------------------------------------------------
class StatsView(ui.View):
    def __init__(self, username: str):
        super().__init__(timeout=None)
        self.username = username

    @ui.button(label="View Charts", style=discord.ButtonStyle.secondary, row=0)
    async def view_charts(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(f"📊 Chart data requested for **{self.username}**.", ephemeral=True)

    @ui.button(label="Player Stats", style=discord.ButtonStyle.secondary, row=0)
    async def player_stats(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(f"👤 Displaying player stats for **{self.username}**.", ephemeral=True)

    @ui.button(label="Historical Stats", style=discord.ButtonStyle.secondary, row=1)
    async def historical_stats(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(f"📜 Historical stats requested for **{self.username}**.", ephemeral=True)

    @ui.button(label="Discord Account", style=discord.ButtonStyle.secondary, row=1)
    async def discord_account(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(f"🔗 No linked Discord account found for **{self.username}**.", ephemeral=True)

    @ui.button(label="Auction House", style=discord.ButtonStyle.secondary, row=2)
    async def auction_house(self, interaction: discord.Interaction, button: ui.Button):
        view = AuctionCategoryView(self.username)
        await interaction.response.send_message(
            f"🛒 **Auction House** ({self.username})\nSelect an item category below to view listings:",
            view=view,
            ephemeral=True
        )

    @ui.button(label="Orders", style=discord.ButtonStyle.secondary, row=2)
    async def orders(self, interaction: discord.Interaction, button: ui.Button):
        view = OrdersCategoryView(self.username)
        await interaction.response.send_message(
            f"📦 **Player Orders** ({self.username})\nSelect an order filter below to view:",
            view=view,
            ephemeral=True
        )

    @ui.button(label="Search Item", style=discord.ButtonStyle.primary, row=3)
    async def search_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(SearchItemModal())

    @ui.button(label="Refresh", style=discord.ButtonStyle.secondary, row=3)
    async def refresh(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(f"🔄 Refreshed stats for **{self.username}**.", ephemeral=True)

    @ui.button(label="Analysis", style=discord.ButtonStyle.secondary, row=3)
    async def analysis(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(f"🔍 Analysis report generated for **{self.username}**.", ephemeral=True)


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Successfully synced {len(synced)} slash command(s)!")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    print(f"Bot {bot.user} is online and ready!")


# -------------------------------------------------------------
# SLASH COMMANDS
# -------------------------------------------------------------

# 1. COMMAND /stats
@bot.tree.command(name="stats", description="View detailed DonutSMP player statistics")
@app_commands.describe(username="Minecraft username")
async def stats(interaction: discord.Interaction, username: str):
    await interaction.response.defer()
    
    url = f"https://api.donutsmp.net/v1/player/{username}"
    timeout = aiohttp.ClientTimeout(total=5)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    money = format_currency(data.get("money", 0))
                    shards = format_num(data.get("shards", 0))
                    kills = format_num(data.get("kills", 0))
                    deaths = format_num(data.get("deaths", 0))
                    playtime = data.get("playtime", "0d 0h")
                    blocks_placed = format_num(data.get("blocks_placed", 0))
                    blocks_broken = format_num(data.get("blocks_broken", 0))
                    mobs_killed = format_num(data.get("mobs_killed", 0))
                    shop_spending = format_currency(data.get("shop_spending", 0))
                    shop_sales = format_currency(data.get("shop_sales", 0))
                    score = data.get("score", "0.00")
                    rank = format_num(data.get("rank", 0))
                    total_players = data.get("total_players", "2.4M")
                    
                    description_text = (
                        f"### Stats for {username}\n\n"
                        f"🟢 **Money:** {money}\n"
                        f"🔮 **Shards:** {shards}\n"
                        f"⚔️ **Player Kills:** {kills}\n"
                        f"💀 **Deaths:** {deaths}\n"
                        f"🪙 **Playtime:** {playtime}\n"
                        f"🧱 **Blocks Placed:** {blocks_placed}\n"
                        f"🪨 **Blocks Broken:** {blocks_broken}\n"
                        f"🧟 **Mobs Killed:** {mobs_killed}\n"
                        f"🛍️ **Shop Spending:** {shop_spending}\n"
                        f"📦 **Shop Sales:** {shop_sales}\n"
                        f"**Score** `{score}` - **rank** `{rank}` of `{total_players}`\n\n"
                        f"Showing stored data - live lookup unavailable\n(5d old)"
                    )
                    
                    embed = discord.Embed(
                        description=description_text,
                        color=discord.Color.from_rgb(47, 49, 54)
                    )
                    avatar_icon = bot.user.display_avatar.url if bot.user else None
                    embed.set_author(name="DonutBot", icon_url=avatar_icon)
                    embed.set_thumbnail(url=f"https://mc-heads.net/avatar/{username}")
                    
                    view = StatsView(username)
                    await interaction.followup.send(embed=embed, view=view)
                elif response.status == 404:
                    await interaction.followup.send(f"Player `{username}` was not found.")
                else:
                    await interaction.followup.send(f"DonutSMP API issue (Status: {response.status}).")
    except asyncio.TimeoutError:
        await interaction.followup.send("DonutSMP API server timed out.")
    except Exception:
        await interaction.followup.send("Failed to retrieve data due to a connection error.")


# 2. COMMAND /search
@bot.tree.command(name="search", description="Search items on the DonutSMP Auction House")
@app_commands.describe(query="Item name to search for (e.g., Elytra, Diamond, Beacon)")
async def search_command(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    
    url = f"https://api.donutsmp.net/v1/auctionhouse?search={query.lower()}"
    timeout = aiohttp.ClientTimeout(total=5)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get("items", [])
                    
                    embed = discord.Embed(
                        title=f"🔍 Search Results: {query}",
                        color=discord.Color.gold()
                    )
                    
                    if items:
                        for item in items[:10]:
                            embed.add_field(
                                name=f"{item.get('item_name', query)} x{item.get('amount', 1)}",
                                value=f"Price: **{format_currency(item.get('price', 0))}**\nSeller: `{item.get('seller', 'N/A')}`",
                                inline=False
                            )
                    else:
                        embed.description = f"No items matching **{query}** were found on the Auction House."
                        
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("Failed to retrieve search data from Auction House.")
    except Exception:
        await interaction.followup.send("Failed to connect to the Auction House API.")


# 3. COMMAND /ah
@bot.tree.command(name="ah", description="View items on the DonutSMP Auction House")
@app_commands.describe(page="Auction House page number (Default: 1)")
async def ah(interaction: discord.Interaction, page: int = 1):
    await interaction.response.defer()
    
    url = f"https://api.donutsmp.net/v1/auctionhouse?page={page}"
    timeout = aiohttp.ClientTimeout(total=5)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get("items", [])
                    
                    if not items:
                        await interaction.followup.send(f"No items found on Auction House page {page}.")
                        return

                    embed = discord.Embed(
                        title=f"🛒 DonutSMP Auction House (Page {page})",
                        color=discord.Color.gold()
                    )
                    
                    for item in items[:10]:
                        embed.add_field(
                            name=f"{item.get('item_name', 'Unknown Item')} x{item.get('amount', 1)}",
                            value=f"Price: ${item.get('price', 0):,}\nSeller: {item.get('seller', 'N/A')}",
                            inline=False
                        )
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("Failed to retrieve Auction House data.")
    except Exception:
        await interaction.followup.send("Failed to connect to the Auction House API.")


# 4. COMMAND /orders
@bot.tree.command(name="orders", description="View active orders for a DonutSMP player")
@app_commands.describe(username="Minecraft username")
async def orders(interaction: discord.Interaction, username: str):
    await interaction.response.defer()
    
    url = f"https://api.donutsmp.net/v1/player/{username}/orders"
    timeout = aiohttp.ClientTimeout(total=5)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    orders_list = data.get("orders", [])
                    
                    if not orders_list:
                        await interaction.followup.send(f"Player `{username}` currently has no active orders.")
                        return

                    embed = discord.Embed(
                        title=f"📦 Active Orders: {username}",
                        color=discord.Color.blue()
                    )
                    
                    for order in orders_list[:5]:
                        embed.add_field(
                            name=f"Order #{order.get('id', 'N/A')} - {order.get('item', 'Item')}",
                            value=f"Amount: {order.get('amount', 0)}\nPrice/unit: ${order.get('price_per_unit', 0):,}",
                            inline=False
                        )
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send(f"Failed to retrieve order data for `{username}`.")
    except Exception:
        await interaction.followup.send("Failed to connect to the Order API.")


# 5. COMMAND /balchart
@bot.tree.command(name="balchart", description="Display balance history chart for a DonutSMP player")
@app_commands.describe(username="Minecraft username")
async def balchart(interaction: discord.Interaction, username: str):
    await interaction.response.defer()
    
    url = f"https://api.donutsmp.net/v1/player/{username}/history"
    timeout = aiohttp.ClientTimeout(total=5)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    history = data.get("history", [])
                    
                    if not history:
                        await interaction.followup.send(f"No balance history found for `{username}`.")
                        return

                    dates = [entry.get("date", "") for entry in history]
                    balances = [entry.get("balance", 0) for entry in history]

                    plt.figure(figsize=(8, 4))
                    plt.plot(dates, balances, marker='o', color='#f1c40f', linewidth=2)
                    plt.title(f"Balance History - {username}", fontsize=14)
                    plt.xlabel("Date")
                    plt.ylabel("Balance ($)")
                    plt.grid(True, linestyle='--', alpha=0.6)
                    plt.tight_layout()

                    buf = io.BytesIO()
                    plt.savefig(buf, format='png')
                    buf.seek(0)
                    plt.close()

                    file = discord.File(buf, filename="balance_chart.png")
                    await interaction.followup.send(file=file)
                else:
                    await interaction.followup.send(f"Balance history for `{username}` was not found.")
    except Exception:
        await interaction.followup.send("An error occurred while generating the balance chart.")


# Web Health Check Endpoint for Render
async def handle_health_check(request):
    return web.Response(text="DonutSMP Bot Online!")

async def start_bot():
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Web server running on port {port}")

    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("ERROR: BOT_TOKEN Environment Variable is missing!")
        return
        
    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(start_bot())
