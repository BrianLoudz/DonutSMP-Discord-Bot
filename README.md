# 🍩 DonutSMP Discord Bot

A feature-packed Discord Bot for tracking player statistics, auction house listings, order history, and balance charts for the **DonutSMP** Minecraft server. Built with Python using `discord.py` (v2.0+) and hosted seamlessly on **Render**.

---

## ✨ Features

- **`/stats <username>`**: Displays real-time player stats including money, kills, deaths, and playtime with player head avatar thumbnails.
- **`/ah [page]`**: Views current items available in the DonutSMP Auction House with price and seller details.
- **`/orders <username>`**: Checks active market orders for a specific player.
- **`/balchart <username>`**: Generates and uploads a visual chart of a player's balance history over time using `matplotlib`.

---

## 🛠️ Tech Stack

- **Python 3.10+**
- **[discord.py](https://github.com/Rapptz/discord.py)** (v2.0+) - Discord API Wrapper with Slash Commands support.
- **[aiohttp](https://github.com/aio-libs/aiohttp)** - Asynchronous HTTP client & lightweight web server for Render health checks.
- **[matplotlib](https://matplotlib.org/)** - Data visualization for player balance history.

---

## 📁 Repository Structure

```text
.
├── main.py            # Main bot logic, slash commands, and internal web server
├── requirements.txt   # Required Python package dependencies
└── README.md          # Project documentation
