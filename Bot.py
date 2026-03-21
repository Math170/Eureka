import json
import discord
from discord.ext import commands
import os
import sys
import io
import random
import asyncio
import datetime

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

# --- SYSTÈME DE VÉRIFICATION (REACTION ROLE) ---

@bot.event
async def on_raw_reaction_add(payload):
    """Donne le rôle membre lors du clic sur ✅ dans le salon règles"""
    if payload.user_id == bot.user.id:
        return

    if str(payload.emoji) == "✅":
        guild = bot.get_guild(payload.guild_id)
        channel = bot.get_channel(payload.channel_id)
        
        # On vérifie si le salon contient "règles" dans son nom
        if "règles" in channel.name.lower():
            member = guild.get_member(payload.user_id)
            role = discord.utils.get(guild.roles, name="Membre 👤")
            
            if role and member:
                await member.add_roles(role)
                # On retire la réaction pour garder le salon propre
                try:
                    message = await channel.fetch_message(payload.message_id)
                    await message.remove_reaction(payload.emoji, member)
                except:
                    pass

# --- ÉVÉNEMENTS DE BASE ---

@bot.event
async def on_member_join(member):
    """Message de bienvenue quand un membre arrive"""
    channel = discord.utils.get(member.guild.text_channels, name="arrivées-🛫") or \
              discord.utils.get(member.guild.text_channels, name="arrivée")
    
    if channel:
        regles_ch = discord.utils.get(member.guild.text_channels, name="règles-📋")
        mention = regles_ch.mention if regles_ch else "les règles"
        embed = discord.Embed(
            title=f"Bienvenue chez Eureka, {member.name} ! 💡",
            description=f"Ravi de te voir parmi nous ! Passe voir {mention} pour débloquer le serveur.",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(content=member.mention, embed=embed)

@bot.event
async def on_member_remove(member):
    """Message quand un membre quitte"""
    channel = discord.utils.get(member.guild.text_channels, name="départs-🛬")
    if channel:
        embed = discord.Embed(title=f"Au revoir {member.name} ! 🛫", color=discord.Color.red())
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)

# --- LOGS DE MESSAGES ---

@bot.event
async def on_message_delete(message):
    if message.author.bot: return
    log_ch = discord.utils.get(message.guild.text_channels, name="logs")
    if log_ch:
        embed = discord.Embed(title="🗑️ Message supprimé", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Auteur", value=message.author.mention)
        embed.add_field(name="Contenu", value=message.content or "*(Fichier/Image)*")
        await log_ch.send(embed=embed)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content: return
    log_ch = discord.utils.get(before.guild.text_channels, name="logs")
    if log_ch:
        embed = discord.Embed(title="📝 Message modifié", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Ancien", value=before.content, inline=False)
        embed.add_field(name="Nouveau", value=after.content, inline=False)
        await log_ch.send(embed=embed)

# --- COMMANDES D'AIDE ET STATS ---

@bot.command()
async def help(ctx):
    """Affiche les commandes triées par catégories"""
    embed = discord.Embed(title="📚 Aide - Eureka Bot", color=discord.Color.blue())
    categories = {}
    for cmd in bot.commands:
        if cmd.hidden: continue
        cat = cmd.extras.get('category', '📁 Autres')
        if cat not in categories: categories[cat] = []
        categories[cat].append(cmd)

    for cat_name, cmd_list in categories.items():
        value = ""
        for c in sorted(cmd_list, key=lambda x: x.name):
            value += f"**?{c.name}** : *{c.help}*\n"
        embed.add_field(name=cat_name, value=value, inline=False)
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(extras={'category': '✨ Utilitaires'})
async def stats(ctx):
    """Affiche les statistiques du serveur"""
    guild = ctx.guild
    embed = discord.Embed(title=f"📊 Stats : {guild.name}", color=discord.Color.purple())
    embed.add_field(name="Membres", value=str(guild.member_count))
    embed.add_field(name="Salons", value=str(len(guild.channels)))
    await ctx.send(embed=embed)

# --- ADMINISTRATION ---

@bot.command(extras={'category': '🛠️ Administration'})
@commands.has_permissions(administrator=True)
async def setup(ctx):
    """Reconstruction totale sécurisée avec Reaction Role"""
    guild = ctx.guild
    await ctx.send("🏗️ **Lancement de la reconstruction...**")
    for ch in guild.channels:
        try: 
            if ch.id != ctx.channel.id: await ch.delete()
        except: pass

    # ROLES
    owner_r = discord.utils.get(guild.roles, name="Fondateur 👑") or await guild.create_role(name="Fondateur 👑", colour=discord.Colour.from_rgb(241, 196, 15), hoist=True, permissions=discord.Permissions(
        add_reactions=False,
        administrator=True,
        attach_files=False,
        ban_members=False,
        bypass_slowmode=False,
        change_nickname=False,
        connect=False,
        create_events=False,
        create_expressions=False,
        create_instant_invite=False,
        create_polls=False,
        create_private_threads=False,
        create_public_threads=False,
        deafen_members=False,
        embed_links=False,
        external_emojis=False,
        external_stickers=False,
        kick_members=False,
        manage_channels=False,
        manage_emojis=False,
        manage_emojis_and_stickers=False,
        manage_events=False,
        manage_expressions=False,
        manage_guild=False,
        manage_messages=False,
        manage_nicknames=False,
        manage_permissions=False,
        manage_roles=False,
        manage_threads=False,
        manage_webhooks=False,
        mention_everyone=False,
        moderate_members=False,
        move_members=False,
        mute_members=False,
        pin_messages=False,
        priority_speaker=True,
        read_message_history=False,
        read_messages=False,
        request_to_speak=False,
        send_messages=False,
        send_messages_in_threads=False,
        send_polls=False,
        send_tts_messages=False,
        send_voice_messages=False,
        set_voice_channel_status=False,
        speak=False,
        stream=False,
        use_application_commands=False,
        use_embedded_activities=False,
        use_external_apps=False,
        use_external_emojis=False,
        use_external_sounds=False,
        use_external_stickers=False,
        use_soundboard=False,
        use_voice_activation=False,
        view_audit_log=False,
        view_channel=False,
        view_creator_monetization_analytics=False,
        view_guild_insights=False
    ))
    admin_r = discord.utils.get(guild.roles, name="Administrateur 🛡️") or await guild.create_role(name="Administrateur 🛡️", colour=discord.Colour.from_rgb(231, 76, 60), hoist=True, permissions=discord.Permissions(
        add_reactions=False,
        administrator=True,
        attach_files=False,
        ban_members=False,
        bypass_slowmode=False,
        change_nickname=False,
        connect=False,
        create_events=False,
        create_expressions=False,
        create_instant_invite=False,
        create_polls=False,
        create_private_threads=False,
        create_public_threads=False,
        deafen_members=False,
        embed_links=False,
        external_emojis=False,
        external_stickers=False,
        kick_members=False,
        manage_channels=False,
        manage_emojis=False,
        manage_emojis_and_stickers=False,
        manage_events=False,
        manage_expressions=False,
        manage_guild=False,
        manage_messages=False,
        manage_nicknames=False,
        manage_permissions=False,
        manage_roles=False,
        manage_threads=False,
        manage_webhooks=False,
        mention_everyone=False,
        moderate_members=False,
        move_members=False,
        mute_members=False,
        pin_messages=False,
        priority_speaker=True,
        read_message_history=False,
        read_messages=False,
        request_to_speak=False,
        send_messages=False,
        send_messages_in_threads=False,
        send_polls=False,
        send_tts_messages=False,
        send_voice_messages=False,
        set_voice_channel_status=False,
        speak=False,
        stream=False,
        use_application_commands=False,
        use_embedded_activities=False,
        use_external_apps=False,
        use_external_emojis=False,
        use_external_sounds=False,
        use_external_stickers=False,
        use_soundboard=False,
        use_voice_activation=False,
        view_audit_log=False,
        view_channel=False,
        view_creator_monetization_analytics=False,
        view_guild_insights=False
    ))
    mod_r = discord.utils.get(guild.roles, name="Modérateur ⚔️") or await guild.create_role(name="Modérateur ⚔️", colour=discord.Colour.from_rgb(46, 204, 113), hoist=True, permissions=discord.Permissions(
        add_reactions=False,
        administrator=False,
        attach_files=False,
        ban_members=False,
        bypass_slowmode=False,
        change_nickname=False,
        connect=False,
        create_events=False,
        create_expressions=False,
        create_instant_invite=False,
        create_polls=False,
        create_private_threads=False,
        create_public_threads=False,
        deafen_members=False,
        embed_links=False,
        external_emojis=False,
        external_stickers=False,
        kick_members=False,
        manage_channels=False,
        manage_emojis=False,
        manage_emojis_and_stickers=False,
        manage_events=False,
        manage_expressions=False,
        manage_guild=False,
        manage_messages=False,
        manage_nicknames=False,
        manage_permissions=False,
        manage_roles=False,
        manage_threads=False,
        manage_webhooks=False,
        mention_everyone=False,
        moderate_members=True,
        move_members=False,
        mute_members=False,
        pin_messages=False,
        priority_speaker=True,
        read_message_history=False,
        read_messages=False,
        request_to_speak=False,
        send_messages=False,
        send_messages_in_threads=False,
        send_polls=False,
        send_tts_messages=False,
        send_voice_messages=False,
        set_voice_channel_status=False,
        speak=False,
        stream=False,
        use_application_commands=False,
        use_embedded_activities=False,
        use_external_apps=False,
        use_external_emojis=False,
        use_external_sounds=False,
        use_external_stickers=False,
        use_soundboard=False,
        use_voice_activation=False,
        view_audit_log=False,
        view_channel=False,
        view_creator_monetization_analytics=False,
        view_guild_insights=False
    ))
    member_r = discord.utils.get(guild.roles, name="Membre 👤") or await guild.create_role(name="Membre 👤", colour=discord.Colour.from_rgb(84, 160, 255), hoist=True, permissions=discord.Permissions(
        add_reactions=True,
        administrator=True,
        attach_files=True,
        ban_members=False,
        bypass_slowmode=False,
        change_nickname=True,
        connect=True,
        create_events=False,
        create_expressions=False,
        create_instant_invite=True,
        create_polls=False,
        create_private_threads=False,
        create_public_threads=False,
        deafen_members=False,
        embed_links=False,
        external_emojis=True,
        external_stickers=True,
        kick_members=False,
        manage_channels=False,
        manage_emojis=False,
        manage_emojis_and_stickers=False,
        manage_events=False,
        manage_expressions=False,
        manage_guild=False,
        manage_messages=False,
        manage_nicknames=False,
        manage_permissions=False,
        manage_roles=False,
        manage_threads=False,
        manage_webhooks=False,
        mention_everyone=False,
        moderate_members=False,
        move_members=False,
        mute_members=False,
        pin_messages=False,
        priority_speaker=False,
        read_message_history=False,
        read_messages=True,
        request_to_speak=True,
        send_messages=True,
        send_messages_in_threads=False,
        send_polls=False,
        send_tts_messages=False,
        send_voice_messages=False,
        set_voice_channel_status=True,
        speak=True,
        stream=True,
        use_application_commands=True,
        use_embedded_activities=True,
        use_external_apps=True,
        use_external_emojis=True,
        use_external_sounds=True,
        use_external_stickers=True,
        use_soundboard=True,
        use_voice_activation=True,
        view_audit_log=False,
        view_channel=True,
        view_creator_monetization_analytics=False,
        view_guild_insights=False
    ))
    booster_r = discord.utils.get(guild.roles, name="Booster 🚀") or await guild.create_role(name="Booster 🚀", colour=discord.Colour.from_rgb(244, 127, 255), hoist=True)
    mayor_r = discord.utils.get(guild.roles, name="Maire 🏛️") or await guild.create_role(name="Maire 🏛️", colour=discord.Colour.from_rgb(230, 126, 34), hoist=True)
    color_red_r = discord.utils.get(guild.roles, name="Rouge 🔴") or await guild.create_role(name="Rouge 🔴", colour=discord.Colour.from_rgb(231, 76, 60), hoist=True)
    color_yellow_r = discord.utils.get(guild.roles, name="Jaune 🟡") or await guild.create_role(name="Jaune 🟡", colour=discord.Colour.from_rgb(241, 196, 15), hoist=True)
    color_green_r = discord.utils.get(guild.roles, name="Vert 🟢") or await guild.create_role(name="Vert 🟢", colour=discord.Colour.from_rgb(46, 204, 113), hoist=True)
    color_pink_r = discord.utils.get(guild.roles, name="Rose 🌸") or await guild.create_role(name="Rose 🌸", colour=discord.Colour.from_rgb(255, 105, 180), hoist=True)
    
    # CREATION DE RÔLES DE BOUTIQUE
    # Ces rôles n'ont pas de permissions spéciales, ils sont esthétiques
    vip_role = discord.utils.get(guild.roles, name="VIP ✨") or await guild.create_role(
        name="VIP ✨", 
        colour=discord.Colour.from_rgb(255, 215, 0), # Couleur dorée
        hoist=True # Pour qu'ils apparaissent séparément dans la liste des membres
    )

    million_role = discord.utils.get(guild.roles, name="Millionnaire 👑") or await guild.create_role(
        name="Millionnaire 👑", 
        colour=discord.Colour.from_rgb(192, 192, 192), # Couleur argent
        hoist=True
    )

    # PERMISSIONS
    perms_hide = {guild.default_role: discord.PermissionOverwrite(view_channel=False), member_r: discord.PermissionOverwrite(view_channel=True), mod_r: discord.PermissionOverwrite(view_channel=True)}
    perms_rules = {guild.default_role: discord.PermissionOverwrite(view_channel=True, send_messages=False, add_reactions=False), member_r: discord.PermissionOverwrite(send_messages=False, add_reactions=False)}
    perms_annonces = {guild.default_role: discord.PermissionOverwrite(view_channel=False), member_r: discord.PermissionOverwrite(view_channel=True, send_messages=False), mod_r: discord.PermissionOverwrite(send_messages=True)}

    # CREATION DES SALONS

    # --- INFORMATIONS ---
    c_info = await guild.create_category("📢--INFORMATIONS--📢")
    rules_ch = await guild.create_text_channel("règles-📋", category=c_info, overwrites=perms_rules)
    await guild.create_text_channel("annonces-📢", category=c_info, overwrites=perms_annonces)
    await guild.create_text_channel("partenariats-🤝", category=c_info, overwrites=perms_annonces)
    await guild.create_text_channel("arrivées-🛫", category=c_info, overwrites=perms_rules)

    # --- COMMUNAUTÉ (TEXTUEL) ---
    c_commu = await guild.create_category("💬--COMMUNAUTÉ--💬", overwrites=perms_hide)
    gen = await guild.create_text_channel("discussion-🌐", category=c_commu)
    await guild.create_text_channel("médias-📸", category=c_commu) # Pour photos et vidéos
    await guild.create_text_channel("recherche-de-groupe-🎮", category=c_commu)
    await guild.create_text_channel("commandes-bot-🤖", category=c_commu)

    # --- STAFF ---
    c_staff = await guild.create_category("🔐--STAFF--🔐", overwrites={guild.default_role: discord.PermissionOverwrite(view_channel=False), mod_r: discord.PermissionOverwrite(view_channel=True)})
    await guild.create_text_channel("sanctions-🚫", category=c_staff)
    await guild.create_text_channel("logs", category=c_staff)
    await guild.create_text_channel("réunion-staff", category=c_staff)

    # --- VOCAL ---
    c_vocal = await guild.create_category("🔊--SALONS VOCAUX--🔊", overwrites=perms_hide)
    await guild.create_voice_channel("Général 🔊", category=c_vocal)
    await guild.create_voice_channel("Duo #1 👥", category=c_vocal, user_limit=2)
    await guild.create_voice_channel("Trio #1 ☘️", category=c_vocal, user_limit=3)
    await guild.create_voice_channel("Musique 🎵", category=c_vocal)

    # --- AFK ---
    c_afk = await guild.create_category("💤--ABSENCE--💤", overwrites=perms_hide)
    afk_ch = await guild.create_voice_channel("AFK 💤", category=c_afk)
    await guild.edit(afk_channel=afk_ch, afk_timeout=300)

    # ENVOIEMENT DU MESSAGE DE RÈGLES AVEC REACTION ROLE
    embed = discord.Embed(
        title="📜 Règlement de Eureka",
        description="Bienvenue ! Pour débloquer l'accès aux autres salons (Médias, Jeux, Vocal), clique sur ✅.\n\n"
                    "1️⃣ Respectez les autres membres.\n"
                    "2️⃣ Utilisez les salons appropriés (Bots dans #commandes-bot).\n"
                    "3️⃣ Pas de contenu inapproprié dans #médias.\n\n"
                    "**Cliquez ci-dessous pour valider !**",
        color=discord.Color.blue()
    )
    msg = await rules_ch.send(embed=embed)
    await msg.add_reaction("✅")

    await gen.send(f"✅ **Eureka !** Serveur prêt. Système actif dans {rules_ch.mention}")
    await ctx.channel.delete()

@bot.command(extras={'category': '🛠️ Administration'})
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    """Supprime un nombre de messages : ?clear 10"""
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 **{amount}** messages supprimés.")
    await asyncio.sleep(3)
    await msg.delete()

# --- MODÉRATION ---

async def send_log(ctx, action, member, reason):
    log_ch = discord.utils.get(ctx.guild.text_channels, name="sanctions-🚫")
    if log_ch:
        embed = discord.Embed(title=f"Sanction : {action}", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Membre", value=member.mention)
        embed.add_field(name="Raison", value=reason)
        await log_ch.send(embed=embed)

@bot.command(extras={'category': '🛡️ Modération'})
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="Aucune raison"):
    """Expulse un membre du serveur"""
    await member.kick(reason=reason)
    await send_log(ctx, "Expulsion 👢", member, reason)
    await ctx.send(f"✅ {member.name} expulsé.")

@bot.command(extras={'category': '🛡️ Modération'})
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="Aucune raison"):
    """Bannit définitivement un membre"""
    await member.ban(reason=reason)
    await send_log(ctx, "Bannissement 🚫", member, reason)
    await ctx.send(f"✅ {member.name} banni.")

@bot.command(extras={'category': '🛡️ Modération'})
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason="Aucune raison"):
    """Donne un warn et prévient en MP"""
    if member.id not in warns: warns[member.id] = []
    warns[member.id].append(reason)
    nb = len(warns[member.id])
    try:
        await member.send(f"⚠️ Tu as reçu un warn sur {ctx.guild.name} pour : {reason} (Total : {nb}/3)")
    except: pass
    await send_log(ctx, f"Avertissement #{nb} ⚠️", member, reason)
    await ctx.send(f"⚠️ {member.mention} averti ({nb}/3).")
    if nb >= 3: await member.kick(reason="3 avertissements.")

# --- MINI-JEUX ---

@bot.command(extras={'category': '🎮 Mini-Jeux'})
async def pof(ctx):
    """Lance une pièce (Pile ou Face)"""
    await ctx.send(f"🪙 Résultat : **{random.choice(['Pile', 'Face'])}**")

@bot.command(extras={'category': '🎮 Mini-Jeux'})
async def game(ctx):
    """Jeu du Juste Prix (1-100)"""
    nb = random.randint(1, 100)
    await ctx.send(f"🎮 {ctx.author.mention}, devine le nombre !")
    def check(m): return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
    try:
        for i in range(7):
            msg = await bot.wait_for('message', check=check, timeout=30.0)
            if int(msg.content) < nb: await ctx.send("Plus haut !")
            elif int(msg.content) > nb: await ctx.send("Plus bas !")
            else:
                await ctx.send(f"🎉 GAGNÉ en {i+1} essais !")
                return
        await ctx.send(f"⌛ Perdu ! C'était {nb}.")
    except: await ctx.send("⏰ Temps écoulé.")

# --- SYSTÈME D'ÉCONOMIE ---
economy = {} # {user_id: solde}

def get_balance(user_id):
    """Récupère le solde ou initialise à 1000 si nouveau"""
    if user_id not in economy:
        economy[user_id] = 1000
    return economy[user_id]

def add_balance(user_id, amount):
    """Ajoute ou retire (si montant négatif) de l'argent"""
    current = get_balance(user_id)
    economy[user_id] = current + amount

# --- COMMANDES ÉCONOMIE ---

@bot.command(extras={'category': '💰 Économie'})
async def balance(ctx, member: discord.Member = None):
    """Affiche ton solde ou celui d'un membre"""
    member = member or ctx.author
    bal = get_balance(member.id)
    await ctx.send(f"🪙 **{member.display_name}** possède **{bal} pièces**.")

@bot.command(extras={'category': '💰 Économie'})
async def pay(ctx, member: discord.Member, amount: int):
    """Transfère de l'argent à un autre joueur"""
    if amount <= 0:
        return await ctx.send("❌ Le montant doit être positif.")
    
    if get_balance(ctx.author.id) < amount:
        return await ctx.send("❌ Tu n'as pas assez d'argent !")
    
    add_balance(ctx.author.id, -amount)
    add_balance(member.id, amount)
    await ctx.send(f"💸 {ctx.author.mention} a envoyé **{amount} pièces** à {member.mention} !")

@bot.command(extras={'category': '🛠️ Administration'})
@commands.has_permissions(administrator=True)
async def addmoney(ctx, member: discord.Member, amount: int):
    """Donne de l'argent à un membre"""
    add_balance(member.id, amount)
    await ctx.send(f"👑 **{amount} pièces** ont été ajoutées à {member.display_name}.")

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

# --- MINI-JEUX CASINO ---

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


# --- LANCEMENT ---
chemin_token = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.txt")
with open(chemin_token, "r") as f:
    bot.run(f.read().strip())