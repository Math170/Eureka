import discord
from discord.ext import commands
import os
import json
import random
import asyncio

# --- CONFIGURATION DES FICHIERS ---
# Ce fichier stockera l'argent et les warns
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.json")

def load_data():
    """Charge les données depuis le fichier JSON au démarrage"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"economy": {}, "warns": {}}

def save_data():
    """Sauvegarde l'état actuel dans le fichier JSON"""
    data = {
        "economy": economy,
        "warns": warns
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Initialisation des données
data = load_data()
economy = data.get("economy", {})
warns = data.get("warns", {})

# Configuration du Bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True 
intents.reactions = True 

bot = commands.Bot(command_prefix='?', intents=intents, help_command=None)

# --- UTILITAIRES ÉCONOMIE ---

def get_balance(user_id):
    user_id = str(user_id) # JSON transforme les clés en string
    if user_id not in economy:
        economy[user_id] = 1000
    return economy[user_id]

def add_balance(user_id, amount):
    user_id = str(user_id)
    current = get_balance(user_id)
    economy[user_id] = current + amount
    save_data() # Sauvegarde automatique à chaque mouvement d'argent

# --- COMMANDES DE BOUTIQUE ---

@bot.command(extras={'category': '💰 Économie'})
async def shop(ctx):
    """Affiche les articles disponibles à l'achat"""
    embed = discord.Embed(title="🛒 Boutique Eureka", description="Achète des grades avec tes pièces !", color=discord.Color.blue())
    embed.add_field(name="✨ Rôle VIP", value="Prix : 5,000 pièces\nCommande : `?buy vip`", inline=False)
    embed.add_field(name="👑 Rôle Millionnaire", value="Prix : 50,000 pièces\nCommande : `?buy million`", inline=False)
    embed.set_footer(text="Assurez-vous que les rôles existent sur le serveur !")
    await ctx.send(embed=embed)

@bot.command(extras={'category': '💰 Économie'})
async def buy(ctx, item: str.lower):
    """Achète un objet de la boutique"""
    user_id = str(ctx.author.id)
    balance = get_balance(user_id)

    items = {
        "vip": {"price": 5000, "role_name": "VIP ✨"},
        "million": {"price": 50000, "role_name": "Millionnaire 👑"}
    }

    if item not in items:
        return await ctx.send("❌ Cet article n'existe pas dans le shop.")

    price = items[item]["price"]
    role_name = items[item]["role_name"]

    if balance < price:
        return await ctx.send(f"❌ Il te manque {price - balance} pièces pour acheter ce rôle.")

    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        return await ctx.send(f"❌ Erreur : Le rôle `{role_name}` n'a pas été créé par l'administrateur.")

    if role in ctx.author.roles:
        return await ctx.send("❌ Tu possèdes déjà ce rôle !")

    # Transaction
    add_balance(user_id, -price)
    await ctx.author.add_roles(role)
    await ctx.send(f"🎉 Félicitations {ctx.author.mention}, tu as acheté le rôle **{role_name}** !")

# --- JEUX DE CASINO ---

@bot.command(extras={'category': '🎰 Casino'})
async def slots(ctx, bet: int):
    """Machine à sous : tente de gagner le jackpot !"""
    if bet <= 0: return await ctx.send("Mise invalide.")
    if get_balance(ctx.author.id) < bet: return await ctx.send("❌ Solde insuffisant.")

    emojis = ["🍎", "🍊", "🍇", "💎", "🔔"]
    r1, r2, r3 = [random.choice(emojis) for _ in range(3)]
    
    add_balance(ctx.author.id, -bet) # On retire la mise
    
    res_msg = f"🎰 **[ {r1} | {r2} | {r3} ]** 🎰\n"
    
    if r1 == r2 == r3:
        win = bet * 10
        add_balance(ctx.author.id, win)
        await ctx.send(f"{res_msg}💰 **JACKPOT !** Tu gagnes **{win} pièces** !")
    elif r1 == r2 or r2 == r3 or r1 == r3:
        win = bet * 2
        add_balance(ctx.author.id, win)
        await ctx.send(f"{res_msg}✅ **Gagné !** Tu remportes **{win} pièces**.")
    else:
        await ctx.send(f"{res_msg}💀 **Perdu...**")

@bot.command(extras={'category': '💰 Économie'})
async def work(ctx):
    """Gagne un salaire aléatoire (toutes les 1h)"""
    # Ici tu peux ajouter un cooldown avec @commands.cooldown(1, 3600, commands.BucketType.user)
    gain = random.randint(50, 250)
    add_balance(ctx.author.id, gain)
    await ctx.send(f"👷 **{ctx.author.name}**, tu as travaillé dur et gagné **{gain} pièces** !")

@bot.command(extras={'category': '💰 Économie'})
async def leaderboard(ctx):
    """Affiche les plus riches"""
    if not economy: return await ctx.send("Le classement est vide.")
    
    sorted_eco = sorted(economy.items(), key=lambda x: x[1], reverse=True)[:5]
    embed = discord.Embed(title="🏆 Top 5 des Fortunes", color=discord.Color.gold())
    
    for i, (u_id, bal) in enumerate(sorted_eco, 1):
        user = bot.get_user(int(u_id))
        name = user.name if user else f"Membre {u_id}"
        embed.add_field(name=f"{i}. {name}", value=f"{bal} pièces", inline=False)
    
    await ctx.send(embed=embed)

# --- ADMINISTRATION ---

@bot.command(extras={'category': '🛠️ Administration'})
@commands.has_permissions(administrator=True)
async def addmoney(ctx, member: discord.Member, amount: int):
    """Donne de l'argent à un membre"""
    add_balance(member.id, amount)
    await ctx.send(f"👑 **{amount} pièces** ont été ajoutées à {member.display_name}.")

# N'oublie pas d'inclure tes autres commandes (setup, help, modération, etc.) ici

# --- LANCEMENT ---
chemin_token = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.txt")
with open(chemin_token, "r") as f:
    bot.run(f.read().strip())