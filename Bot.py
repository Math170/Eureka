import json
import discord
from discord.ext import commands
import os
import random
import asyncio
import datetime

# --- CONFIGURATION DES FICHIERS ---
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.json")

def load_data():
    """Charge les données depuis le fichier JSON au démarrage"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"economy": {}, "warns": {}, "levels": {}, "last_daily": {}}

def save_data():
    """Sauvegarde l'état actuel dans le fichier JSON"""
    data = {
        "economy": economy,
        "warns": warns,
        "levels": levels,
        "last_daily": last_daily
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# SYSTÈME DE SÉLECTION DE ROLE AVEC SELECT MENU
class CouleurMenu(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Rouge", emoji="🔴",description="Passer mon pseudo en rouge", value="Rouge 🔴"),
            discord.SelectOption(label="Jaune", emoji="🟡",description="Passer mon pseudo en jaune", value="Jaune 🟡"),
            discord.SelectOption(label="Vert", emoji="🟢",description="Passer mon pseudo en vert", value="Vert 🟢"),
            discord.SelectOption(label="Rose", emoji="🌸",description="Passer mon pseudo en rose", value="Rose 🌸"),
            discord.SelectOption(label="Retirer ma couleur", emoji="❌", value="remove")
        ]
        super().__init__(placeholder="Choisis ta couleur de pseudo...", options=options, custom_id="couleur_select")

    async def callback(self, interaction: discord.Interaction):
        # Liste des noms pour le nettoyage
        noms_couleurs = ["Rouge 🔴", "Jaune 🟡", "Vert 🟢", "Rose 🌸"]
        
        # On récupère les objets rôles sur le serveur
        roles_a_nettoyer = [discord.utils.get(interaction.guild.roles, name=n) for n in noms_couleurs]
        roles_a_nettoyer = [r for r in roles_a_nettoyer if r is not None]

        # 1. On retire toutes les couleurs existantes
        await interaction.user.remove_roles(*roles_a_nettoyer)

        if self.values[0] == "remove":
            await interaction.response.send_message("✅ Ta couleur a été retirée.", ephemeral=True)
        else:
            # 2. On ajoute la nouvelle couleur choisie
            choix = self.values[0]
            nouveau_role = discord.utils.get(interaction.guild.roles, name=choix)
            
            if nouveau_role:
                await interaction.user.add_roles(nouveau_role)
                await interaction.response.send_message(f"✅ Ton pseudo est maintenant en **{choix}** !", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Erreur : Le rôle n'a pas été trouvé. Refais un `?setup`.", ephemeral=True)
class CouleurView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Pour que le menu reste actif indéfiniment
        self.add_item(CouleurMenu())

# --- SYSTÈME DE RÔLES PAR CATÉGORIE (CHOIX MULTIPLES) ---
class RoleMenu(discord.ui.Select):
    def __init__(self, placeholder, role_options, custom_id):
        options = [
            discord.SelectOption(label=name, emoji=emoji, value=name)
            for name, emoji in role_options
        ]
        super().__init__(
            placeholder=placeholder,
            options=options,
            min_values=0, # 0 permet à l'utilisateur de tout décocher
            max_values=len(options), # Permet de sélectionner plusieurs rôles
            custom_id=custom_id
        )
        self.role_names = [name for name, _ in role_options]

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user_roles = interaction.user.roles
        
        managed_roles = [discord.utils.get(guild.roles, name=n) for n in self.role_names]
        managed_roles = [r for r in managed_roles if r is not None]
        
        selected_roles = [discord.utils.get(guild.roles, name=v) for v in self.values]
        selected_roles = [r for r in selected_roles if r is not None]
        
        # On trie ce qu'on doit ajouter et ce qu'on doit retirer
        roles_to_add = [r for r in selected_roles if r not in user_roles]
        roles_to_remove = [r for r in managed_roles if r not in selected_roles and r in user_roles]
        
        if roles_to_add: await interaction.user.add_roles(*roles_to_add)
        if roles_to_remove: await interaction.user.remove_roles(*roles_to_remove)
            
        await interaction.response.send_message("✅ Tes rôles ont été mis à jour !", ephemeral=True)

# --- SYSTÈME DE PRONOMS ET CRÉATION SUR MESURE ---
class PronounModal(discord.ui.Modal, title="Création de Pronom Personnalisé"):
    pronom_input = discord.ui.TextInput(
        label="Quel est ton pronom ?",
        placeholder="Ex: Al, Ul, ...",
        max_length=20, # On limite la longueur pour éviter les abus
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        pronom_name = f"Pronom: {self.pronom_input.value}"
        guild = interaction.guild
        
        # Nettoyer les anciens pronoms personnalisés du membre pour éviter l'accumulation
        old_customs = [r for r in interaction.user.roles if r.name.startswith("Pronom: ")]
        if old_customs:
            await interaction.user.remove_roles(*old_customs)

        # Création ou récupération du rôle s'il a déjà été créé par un autre membre
        role = discord.utils.get(guild.roles, name=pronom_name)
        if not role:
            role = await guild.create_role(name=pronom_name, colour=discord.Colour.light_grey())
        
        await interaction.user.add_roles(role)
        await interaction.response.send_message(f"✅ Ton pronom personnalisé **{self.pronom_input.value}** a été attribué !", ephemeral=True)

class PronounMenu(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Homme (Il/Lui)", emoji="👨", value="Il / Lui 👨"),
            discord.SelectOption(label="Femme (Elle/Elle)", emoji="👩", value="Elle / Elle 👩"),
            discord.SelectOption(label="Iel / Ael", emoji="💛", value="Iel / Ael 💛"),
            discord.SelectOption(label="Autre (Personnalisé)", emoji="✍️", value="autre")
        ]
        super().__init__(placeholder="👤 Choisis tes pronoms...", options=options, min_values=0, max_values=4, custom_id="select_pronoun")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user_roles = interaction.user.roles
        
        managed_names = ["Il / Lui 👨", "Elle / Elle 👩", "Iel / Ael 💛"]
        managed_roles = [discord.utils.get(guild.roles, name=n) for n in managed_names if discord.utils.get(guild.roles, name=n)]
        
        selected_names = [v for v in self.values if v != "autre"]
        selected_roles = [discord.utils.get(guild.roles, name=n) for n in selected_names if discord.utils.get(guild.roles, name=n)]
        
        roles_to_add = [r for r in selected_roles if r not in user_roles]
        roles_to_remove = [r for r in managed_roles if r not in selected_roles and r in user_roles]
        
        if roles_to_add: await interaction.user.add_roles(*roles_to_add)
        if roles_to_remove: await interaction.user.remove_roles(*roles_to_remove)
        
        if "autre" in self.values:
            await interaction.response.send_modal(PronounModal())
        else:
            # Si on ne coche pas "Autre", on retire les anciens rôles personnalisés
            old_customs = [r for r in user_roles if r.name.startswith("Pronom: ")]
            if old_customs: await interaction.user.remove_roles(*old_customs)
            await interaction.response.send_message("✅ Tes pronoms ont été mis à jour !", ephemeral=True)

class RoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(PronounMenu())
        self.add_item(RoleMenu("🎮 Choisis tes jeux...", [("Gamer 🎮", "🎮"), ("FPS 🔫", "🔫"), ("RPG 🗡️", "🗡️")], "select_jeux"))
        self.add_item(RoleMenu("📚 Choisis tes loisirs...", [("Littéraire 📚", "📚"), ("Cinéphile 🎬", "🎬"), ("Artiste 🎨", "🎨")], "select_loisirs"))
        self.add_item(RoleMenu("✨ Choisis ton style...", [("Chill ☕", "☕"), ("Noctambule 🦉", "🦉"), ("Actif ⚡", "⚡")], "select_vibe"))

data = load_data()
economy = data.get("economy", {})
warns = data.get("warns", {})
levels = data.get("levels", {}) 
last_daily = data.get("last_daily", {})

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True 
intents.reactions = True 

bot = commands.Bot(command_prefix='?', intents=intents, help_command=None)

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
        
    # Nettoyage des pronoms personnalisés vides si le membre qui part en était le dernier possesseur
    for r in member.guild.roles:
        if r.name.startswith("Pronom: ") and len(r.members) == 0:
            try:
                await r.delete(reason="Pronom inutilisé (membre parti)")
            except discord.HTTPException:
                pass

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

LEVEL_ROLES = {
    5: "Initié 🔰",
    10: "Habitué 🌟",
    20: "Vétéran 💫",
    30: "Maître 👑",
    50: "Légende 🐉"
}

async def add_xp_to_user(member: discord.Member, amount: int, channel: discord.TextChannel):
    global levels
    user_id = str(member.id)
    if user_id not in levels:
        levels[user_id] = {"xp": 0, "level": 1}
    
    old_level = levels[user_id]["level"]
    levels[user_id]["xp"] += amount
    leveled_up = False
    
    # Une boucle permet de passer plusieurs niveaux d'un coup si on donne beaucoup d'XP avec une commande
    while True:
        lvl_actuel = levels[user_id]["level"]
        xp_requis = 5 * (lvl_actuel ** 2) + (50 * lvl_actuel) + 100
        if levels[user_id]["xp"] >= xp_requis:
            levels[user_id]["level"] += 1
            levels[user_id]["xp"] -= xp_requis # Conserve l'XP en surplus au lieu de remettre à 0 !
            leveled_up = True
        else:
            break
            
    if leveled_up:
        new_level = levels[user_id]["level"]
        save_data()
        
        # Recherche du salon d'annonce ou utilise le salon actuel par défaut
        niv_ch = discord.utils.get(member.guild.text_channels, name="niveaux-📈")
        dest_ch = niv_ch if niv_ch else channel
        
        embed = discord.Embed(title="Niveau Supérieur ! 🎉", description=f"Bravo {member.mention} ! Tu as atteint le **Niveau {new_level}** ! 🚀", color=discord.Color.green())
        await dest_ch.send(content=member.mention, embed=embed)
        
        # Vérification et ajout des rôles de paliers
        for milestone, role_name in LEVEL_ROLES.items():
            if old_level < milestone <= new_level:
                role = discord.utils.get(member.guild.roles, name=role_name)
                if role and role not in member.roles:
                    await member.add_roles(role)
                    await dest_ch.send(f"🎖️ Félicitations, tu obtiens le grade **{role_name}** !")
    else:
        save_data()

xp_cooldown = {} # Pour l'anti-spam
@bot.event
async def on_message(message):
    global levels, xp_cooldown
    if message.author.bot or message.content.startswith('?'):
        await bot.process_commands(message)
        return

    user_id = str(message.author.id)
    now = datetime.datetime.utcnow().timestamp()

    # Anti-spam : 15 secondes entre chaque gain d'XP
    if user_id not in xp_cooldown or now - xp_cooldown[user_id] > 15:
        xp_gagne = random.randint(15, 25)
        await add_xp_to_user(message.author, xp_gagne, message.channel)
        xp_cooldown[user_id] = now

    await bot.process_commands(message)

# --- COMMANDES D'AIDE ET STATS ---

class HelpMenu(discord.ui.Select):
    def __init__(self, categories_dict):
        self.categories_dict = categories_dict
        options = [discord.SelectOption(label=cat, value=cat) for cat in categories_dict.keys()]
        super().__init__(placeholder="Choisis une catégorie...", options=options)

    async def callback(self, interaction: discord.Interaction):
        cat_name = self.values[0]
        cmd_list = self.categories_dict[cat_name]
        
        embed = discord.Embed(title=f"📚 Aide - {cat_name}", color=discord.Color.blue())
        value = ""
        for c in sorted(cmd_list, key=lambda x: x.name):
            value += f"**?{c.name}** : *{c.help or 'Aucune description'}*\n"
        
        embed.description = value
        # Le paramètre ephemeral=True fait en sorte que seul l'utilisateur voit ce message !
        await interaction.response.send_message(embed=embed, ephemeral=True)

class HelpView(discord.ui.View):
    def __init__(self, categories_dict, author_id):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.add_item(HelpMenu(categories_dict))
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # On vérifie que seul l'auteur de la commande puisse utiliser le menu
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Utilise ta propre commande `?help` pour naviguer !", ephemeral=True)
            return False
        return True

@bot.command()
async def help(ctx):
    """Affiche le menu d'aide interactif"""
    categories = {}
    for cmd in bot.commands:
        if cmd.hidden: continue
        cat = cmd.extras.get('category', '📁 Autres')
        if cat not in categories: categories[cat] = []
        categories[cat].append(cmd)

    embed = discord.Embed(
        title="📚 Aide - Eureka Bot", 
        description="Sélectionne une catégorie dans le menu déroulant ci-dessous pour voir ses commandes !",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    await ctx.send(embed=embed, view=HelpView(categories, ctx.author.id))

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

    # Fonction pour créer ou mettre à jour un rôle (permissions, couleur, etc.)
    async def init_role(role_name, **kwargs):
        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            try:
                await role.edit(**kwargs)
            except discord.Forbidden:
                pass
            return role
        return await guild.create_role(name=role_name, **kwargs)

    # ROLES
    color_red_r = await init_role("Rouge 🔴", colour=discord.Colour.from_rgb(231, 76, 60), hoist=False)
    color_yellow_r = await init_role("Jaune 🟡", colour=discord.Colour.from_rgb(241, 196, 15), hoist=False)
    color_green_r = await init_role("Vert 🟢", colour=discord.Colour.from_rgb(46, 204, 113), hoist=False)
    color_pink_r = await init_role("Rose 🌸", colour=discord.Colour.from_rgb(255, 105, 180), hoist=False)
    owner_r = await init_role("Fondateur 👑", colour=discord.Colour.from_rgb(241, 196, 15), hoist=True, permissions=discord.Permissions(
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
    admin_r = await init_role("Administrateur 🛡️", colour=discord.Colour.from_rgb(231, 76, 60), hoist=True, permissions=discord.Permissions(
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
    mod_r = await init_role("Modérateur ⚔️", colour=discord.Colour.from_rgb(46, 204, 113), hoist=True, permissions=discord.Permissions(
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
    member_r = await init_role("Membre 👤", colour=discord.Colour.from_rgb(84, 160, 255), hoist=True, permissions=discord.Permissions(
        add_reactions=True,
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
        embed_links=True,
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
        read_message_history=True,
        read_messages=True,
        request_to_speak=True,
        send_messages=True,
        send_messages_in_threads=True,
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
    booster_r = await init_role("Booster 🚀", colour=discord.Colour.from_rgb(244, 127, 255), hoist=True)
    mayor_r = await init_role("Maire 🏛️", colour=discord.Colour.from_rgb(230, 126, 34), hoist=True)
    
    # CREATION DE RÔLES DE BOUTIQUE
    # Ces rôles n'ont pas de permissions spéciales, ils sont esthétiques
    vip_role = await init_role(
        "VIP ✨", 
        colour=discord.Colour.from_rgb(255, 215, 0),
        hoist=True # Pour qu'ils apparaissent séparément dans la liste des membres
    )
    million_role = await init_role(
        "Millionnaire 👑", 
        colour=discord.Colour.from_rgb(192, 192, 192),
        hoist=True
    )

    # NOUVEAUX RÔLES CENTRES D'INTÉRÊT ET PRONOMS
    for nr in ["Gamer 🎮", "FPS 🔫", "RPG 🗡️", "Littéraire 📚", "Cinéphile 🎬", "Artiste 🎨", "Chill ☕", "Noctambule 🦉", "Actif ⚡", "Il / Lui 👨", "Elle / Elle 👩", "Iel / Ael 💛"]:
        await init_role(nr, colour=discord.Colour.light_grey(), hoist=False)

    # NOUVEAUX RÔLES DE NIVEAUX
    roles_niveaux = []
    for lvl_role in LEVEL_ROLES.values():
        r = await init_role(lvl_role, colour=discord.Colour.teal(), hoist=True)
        roles_niveaux.append(r)

    # --- HIÉRARCHIE DES RÔLES ---
    # On définit l'ordre. Plus le chiffre est grand, plus le rôle est haut.
    try:
        # On définit notre liste de hiérarchie de haut en bas
        hierarchie = [
            color_red_r, color_yellow_r, color_green_r, color_pink_r,
            owner_r, admin_r, mod_r,
            million_role, vip_role, mayor_r, booster_r
        ] + roles_niveaux + [
            member_r
        ]
        
        # Calcul dynamique des positions pour éviter les erreurs !
        pos_dict = {}
        base_pos = 2
        for role in reversed(hierarchie):
            if role:
                pos_dict[role] = base_pos
                base_pos += 1
                
        await guild.edit_role_positions(pos_dict)
    except discord.HTTPException:
        pass # On ignore l'erreur silencieusement, car l'ordre de création naturel des rôles fait déjà le tri !

    # PERMISSIONS
    perms_hide = {guild.default_role: discord.PermissionOverwrite(view_channel=False), member_r: discord.PermissionOverwrite(view_channel=True), mod_r: discord.PermissionOverwrite(view_channel=True)}
    perms_rules = {guild.default_role: discord.PermissionOverwrite(view_channel=True, send_messages=False, add_reactions=False), member_r: discord.PermissionOverwrite(send_messages=False, add_reactions=False)}
    perms_annonces = {guild.default_role: discord.PermissionOverwrite(view_channel=False), member_r: discord.PermissionOverwrite(view_channel=True, send_messages=False), mod_r: discord.PermissionOverwrite(send_messages=True)}

    # CREATION DES SALONS

    # --- INFORMATIONS ---
    c_info = await guild.create_category("📢--INFORMATIONS--📢")
    await guild.create_text_channel("arrivées-🛬", category=c_info, overwrites=perms_rules)
    await guild.create_text_channel("départs-🛫", category=c_info, overwrites=perms_rules)
    rules_ch = await guild.create_text_channel("règles-📋", category=c_info, overwrites=perms_rules)
    await guild.create_text_channel("annonces-📢", category=c_info, overwrites=perms_annonces)
    roles_ch=await guild.create_text_channel("rôles-🎭", category=c_info, overwrites=perms_annonces)
    await guild.create_text_channel("partenariats-🤝", category=c_info, overwrites=perms_annonces)

    # --- COMMUNAUTÉ (TEXTUEL) ---
    c_commu = await guild.create_category("💬--COMMUNAUTÉ--💬", overwrites=perms_hide)
    gen = await guild.create_text_channel("discussion-🌐", category=c_commu)
    await guild.create_text_channel("médias-📸", category=c_commu) # Pour photos et vidéos
    await guild.create_text_channel("recherche-de-groupe-🎮", category=c_commu)
    await guild.create_text_channel("commandes-bot-🤖", category=c_commu)

    # --- SALON NIVEAUX (Lecture Seule) ---
    perms_niveaux = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False), 
        member_r: discord.PermissionOverwrite(view_channel=True, send_messages=False), 
        mod_r: discord.PermissionOverwrite(view_channel=True, send_messages=True)
    }
    await guild.create_text_channel("niveaux-📈", category=c_commu, overwrites=perms_niveaux)

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
    
    await ctx.channel.delete()

    # --- ENVOI DU MENU DES COULEURS ---
    embed_couleur = discord.Embed(
        title="🎨 Ta couleur de pseudo",
        description="Choisis une couleur ci-dessous pour personnaliser ton nom !",
        color=discord.Color.gold()
    )
    await roles_ch.send(embed=embed_couleur, view=CouleurView())

    # --- ENVOI DU MENU DES CENTRES D'INTÉRÊT ---
    embed_roles = discord.Embed(
        title="🎭 Tes Centres d'Intérêt",
        description="Utilise les menus déroulants ci-dessous pour choisir les rôles qui te correspondent le plus ! Tu peux en sélectionner plusieurs par catégorie.",
        color=discord.Color.purple()
    )
    await roles_ch.send(embed=embed_roles, view=RoleView())

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

# --- SYSTÈME DE NIVEAUX ---

@bot.command(extras={'category': '🛠️ Administration'})
@commands.has_permissions(administrator=True)
async def addxp(ctx, member: discord.Member, amount: int):
    """Donne de l'XP à un membre"""
    if amount <= 0:
        return await ctx.send("❌ Le montant doit être positif.")
    await add_xp_to_user(member, amount, ctx.channel)
    await ctx.send(f"✅ **{amount} XP** ont été donnés à {member.mention}.")

@bot.command(extras={'category': '🛠️ Administration'})
@commands.has_permissions(administrator=True)
async def removexp(ctx, member: discord.Member, amount: int):
    """Retire de l'XP à un membre"""
    user_id = str(member.id)
    if user_id not in levels or amount <= 0:
        return await ctx.send("❌ Impossible de retirer cette XP.")
    
    levels[user_id]["xp"] -= amount
    if levels[user_id]["xp"] < 0:
        levels[user_id]["xp"] = 0
    save_data()
    await ctx.send(f"✅ **{amount} XP** ont été retirés à {member.mention}.")

@bot.command(extras={'category': '🛠️ Administration'})
@commands.has_permissions(administrator=True)
async def setlevel(ctx, member: discord.Member, level: int):
    """Définit le niveau d'un membre manuellement"""
    if level <= 0:
        return await ctx.send("❌ Le niveau doit être supérieur à 0.")
        
    user_id = str(member.id)
    if user_id not in levels:
        levels[user_id] = {"xp": 0, "level": 1}
        
    levels[user_id]["level"] = level
    levels[user_id]["xp"] = 0
    save_data()
    await ctx.send(f"✅ Le niveau de {member.mention} a été défini sur **{level}**.")

@bot.command(extras={'category': '📈 Niveaux'})
async def rank(ctx, member: discord.Member = None):
    """Affiche ton niveau et ton XP actuelle"""
    member = member or ctx.author
    user_id = str(member.id)

    if user_id not in levels:
        return await ctx.send(f"✨ {member.display_name} n'a pas encore envoyé de messages.")

    xp = levels[user_id]["xp"]
    lvl = levels[user_id]["level"]
    xp_requis = 5 * (lvl ** 2) + (50 * lvl) + 100

    embed = discord.Embed(title=f"📊 Rang de {member.display_name}", color=discord.Color.blue())
    embed.add_field(name="Niveau", value=f"⭐ {lvl}", inline=True)
    embed.add_field(name="XP", value=f"🧪 {xp}/{xp_requis}", inline=True)
    
    # Barre de progression simple
    progres = int((xp / xp_requis) * 10)
    barre = "🟦" * progres + "⬜" * (10 - progres)
    embed.add_field(name="Progression", value=barre, inline=False)
    
    await ctx.send(embed=embed)

@bot.command(extras={'category': '📈 Niveaux'})
async def leaderboard_xp(ctx):
    """Affiche les 5 membres ayant le plus haut niveau"""
    if not levels:
        return await ctx.send("Le classement est vide.")

    # Tri par niveau, puis par XP
    sorted_levels = sorted(levels.items(), key=lambda x: (x[1]['level'], x[1]['xp']), reverse=True)[:5]
    
    embed = discord.Embed(title="🏆 Top 5 - Eureka Levels", color=discord.Color.purple())
    for i, (u_id, stats) in enumerate(sorted_levels, 1):
        user = bot.get_user(int(u_id))
        name = user.name if user else f"Membre {u_id}"
        embed.add_field(name=f"{i}. {name}", value=f"Niveau {stats['level']} ({stats['xp']} XP)", inline=False)
    
    await ctx.send(embed=embed)

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
    
    add_balance(ctx.author.id, -bet)
    
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

@bot.command(extras={'category': '🎰 Casino'})
async def roulette(ctx, color: str, bet: int):
    """Roulette : mise sur 'rouge', 'noir' ou 'vert'"""
    color = color.lower()
    if color not in ['rouge', 'noir', 'vert']:
        return await ctx.send("❌ Choisis une couleur valide : `rouge`, `noir` ou `vert`.")
    if bet <= 0: return await ctx.send("❌ Mise invalide.")
    if get_balance(ctx.author.id) < bet: return await ctx.send("❌ Solde insuffisant.")

    add_balance(ctx.author.id, -bet)
    result_num = random.randint(0, 36)
    
    if result_num == 0: result_color = 'vert'
    elif result_num % 2 == 0: result_color = 'noir'
    else: result_color = 'rouge'
    
    if color == result_color:
        multiplier = 14 if result_color == 'vert' else 2
        win = bet * multiplier
        add_balance(ctx.author.id, win)
        await ctx.send(f"🎰 La bille s'arrête sur le **{result_num} {result_color.capitalize()}** !\n🎉 **Gagné !** Tu remportes **{win} pièces** !")
    else:
        await ctx.send(f"🎰 La bille s'arrête sur le **{result_num} {result_color.capitalize()}**...\n💀 **Perdu !** Tu perds ta mise.")

@bot.command(extras={'category': '🎰 Casino'})
async def roll(ctx, bet: int):
    """Lance les dés (1-100). Fais plus de 50 pour doubler !"""
    if bet <= 0: return await ctx.send("❌ Mise invalide.")
    if get_balance(ctx.author.id) < bet: return await ctx.send("❌ Solde insuffisant.")

    add_balance(ctx.author.id, -bet)
    result = random.randint(1, 100)

    if result > 50:
        win = bet * 2
        add_balance(ctx.author.id, win)
        await ctx.send(f"🎲 Tu as fait **{result}** !\n✅ **Gagné !** Tu remportes **{win} pièces**.")
    else:
        await ctx.send(f"🎲 Tu as fait **{result}**...\n❌ **Perdu !**")

@bot.command(extras={'category': '🎰 Casino'})
async def coinflip(ctx, face: str, bet: int):
    """Pile ou Face avec mise ! Choisis 'pile' ou 'face'"""
    face = face.lower()
    if face not in ['pile', 'face']:
        return await ctx.send("❌ Choisis `pile` ou `face`.")
    if bet <= 0: return await ctx.send("❌ Mise invalide.")
    if get_balance(ctx.author.id) < bet: return await ctx.send("❌ Solde insuffisant.")

    add_balance(ctx.author.id, -bet)
    result = random.choice(['pile', 'face'])

    if face == result:
        win = bet * 2
        add_balance(ctx.author.id, win)
        await ctx.send(f"🪙 La pièce tombe sur **{result.capitalize()}** !\n🎉 **Gagné !** Tu remportes **{win} pièces**.")
    else:
        await ctx.send(f"🪙 La pièce tombe sur **{result.capitalize()}**...\n💀 **Perdu !** Tu perds ta mise.")

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