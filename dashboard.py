from quart import Quart, render_template_string, session, redirect, request, url_for
import sqlite3
import os
import aiohttp
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv() # Charge les variables secrètes depuis le fichier .env

app = Quart(__name__)
app.secret_key = os.getenv("QUART_SECRET_KEY", "fallback_secret") # Nécessaire pour les sessions web
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

# --- CONFIGURATION DISCORD OAUTH2 ---
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Eureka Bot - Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #2c2f33; color: white; text-align: center; }
        .header { padding: 20px; background-color: #23272a; display: flex; justify-content: flex-end; align-items: center; gap: 15px; }
        .nav { display: flex; justify-content: center; gap: 15px; margin-top: 20px; }
        .nav a { background-color: #7289da; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; }
        .nav a:hover { background-color: #4752C4; }
        h1 { color: #7289da; margin-top: 30px; }
        table { margin: 0 auto; border-collapse: collapse; width: 60%; background-color: #23272a; border-radius: 8px; overflow: hidden;}
        th, td { padding: 15px; border-bottom: 1px solid #2c2f33; }
        th { background-color: #7289da; font-weight: bold;}
        .btn { background-color: #5865F2; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; border: none; cursor: pointer;}
        .btn:hover { background-color: #4752C4; }
        .avatar { width: 40px; height: 40px; border-radius: 50%; }
        .admin-box { background-color: #23272a; padding: 20px; border-radius: 8px; width: 50%; margin: 20px auto; border: 2px solid #7289da; }
        input, select { padding: 10px; border-radius: 5px; border: none; margin: 5px; }
    </style>
</head>
<body>
    <div class="header">
        {% if session.get('user') %}
            <img class="avatar" src="https://cdn.discordapp.com/avatars/{{ session['user']['id'] }}/{{ session['user']['avatar'] }}.png" alt="Avatar">
            <span>Connecté en tant que <b>{{ session['user']['username'] }}</b></span>
            <a href="/logout" class="btn" style="background-color: #ED4245;">Se déconnecter</a>
        {% endif %}
    </div>

    {% if not session.get('user') %}
        <div style="margin-top: 100px;">
            <h1>🔒 Accès Restreint</h1>
            <p>Ce panel est réservé à l'administration du bot.</p><br>
            <a href="/login" class="btn">Connexion Propriétaire</a>
        </div>
    {% else %}
        <div class="admin-box">
            <h2>🛠️ Actions Rapides</h2>
            <form action="/admin_action" method="post">
                <input type="text" name="target_id" placeholder="ID Discord du membre" required>
                <select name="action">
                    <option value="add_xp">➕ Ajouter XP</option>
                    <option value="remove_xp">➖ Retirer XP</option>
                    <option value="add_money">💰 Ajouter Pièces</option>
                    <option value="remove_money">💸 Retirer Pièces</option>
                </select>
                <input type="hidden" name="guild_id" value="{{ current_guild }}">
                <input type="number" name="amount" placeholder="Montant" required min="1">
                <button type="submit" class="btn" style="background-color: #43b581;">Exécuter</button>
            </form>
            {% if message %}
                <p style="color: #43b581; font-weight: bold; margin-top: 15px;">{{ message }}</p>
            {% endif %}
        </div>

        <div class="nav">
            <a href="/?guild_id={{ current_guild }}">🏆 Niveaux</a>
            <a href="/economy?guild_id={{ current_guild }}">💰 Économie</a>
        </div>

        <div style="margin: 20px auto; width: 50%; text-align: center;">
            <form action="{{ request.path }}" method="get">
                <label for="guild_select" style="font-weight: bold; color: white;">Serveur : </label>
                <select name="guild_id" id="guild_select" onchange="this.form.submit()" style="padding: 10px; border-radius: 5px; background: #2c2f33; color: white; border: 1px solid #7289da;">
                    {% for g in guilds %}
                        <option value="{{ g }}" {% if g == current_guild %}selected{% endif %}>Serveur ID : {{ g }}</option>
                    {% endfor %}
                </select>
            </form>
        </div>

        <h1>{{ title }}</h1>
        <table>
            <tr><th>Position</th><th>Membre</th><th>ID Copiable</th>
                {% if page == 'levels' %}<th>Niveau</th><th>XP</th>{% else %}<th>Solde</th>{% endif %}
            </tr>
            {% for i, row in enumerate(leaderboard, 1) %}
            <tr><td>#{{ i }}</td><td>{{ row[3] or 'Inconnu' }}</td><td><code>{{ row[0] }}</code></td>
                {% if page == 'levels' %}<td>⭐ {{ row[2] }}</td><td>{{ row[1] }} XP</td>{% else %}<td>🪙 {{ row[1] }} pièces</td>{% endif %}
            </tr>
            {% endfor %}
        </table>
    {% endif %}
</body>
</html>
"""

@app.route("/")
async def index():
    msg = request.args.get("msg")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute("SELECT DISTINCT guild_id FROM users WHERE guild_id IS NOT NULL")
    guilds = [row[0] for row in c.fetchall()]
    current_guild = request.args.get("guild_id")
    if not current_guild and guilds:
        current_guild = guilds[0]

    try:
        c.execute("SELECT user_id, xp, level, username FROM users WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT 10", (current_guild,))
    except sqlite3.OperationalError:
        c.execute("SELECT user_id, xp, level, user_id FROM users WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT 10", (current_guild,))
    leaderboard = c.fetchall()
    conn.close()
    
    return await render_template_string(HTML_TEMPLATE, leaderboard=leaderboard, enumerate=enumerate, session=session, page="levels", title="🏆 Leaderboard - Top Niveaux", message=msg, guilds=guilds, current_guild=current_guild, request=request)

@app.route("/economy")
async def economy():
    msg = request.args.get("msg")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute("SELECT DISTINCT guild_id FROM users WHERE guild_id IS NOT NULL")
    guilds = [row[0] for row in c.fetchall()]
    current_guild = request.args.get("guild_id")
    if not current_guild and guilds:
        current_guild = guilds[0]

    try:
        c.execute("SELECT user_id, balance, 0, username FROM users WHERE guild_id = ? ORDER BY balance DESC LIMIT 10", (current_guild,))
    except sqlite3.OperationalError:
        c.execute("SELECT user_id, balance, 0, user_id FROM users WHERE guild_id = ? ORDER BY balance DESC LIMIT 10", (current_guild,))
    leaderboard = c.fetchall()
    conn.close()
    
    return await render_template_string(HTML_TEMPLATE, leaderboard=leaderboard, enumerate=enumerate, session=session, page="economy", title="💰 Leaderboard - Économie", message=msg, guilds=guilds, current_guild=current_guild, request=request)

@app.route("/admin_action", methods=["POST"])
async def admin_action():
    owner_id = os.getenv("OWNER_ID")
    if not session.get("user") or str(session["user"]["id"]) != str(owner_id):
        return "Non autorisé", 403
    
    form = await request.form
    target_id = form.get("target_id", "").strip()
    action = form.get("action")
    current_guild = form.get("guild_id", "0")
    try:
        amount = int(form.get("amount", 0))
    except ValueError:
        amount = 0

    if amount <= 0 or not target_id:
        return redirect(url_for("index", msg="Erreur : Données invalides."))

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute("SELECT balance FROM users WHERE user_id = ? AND guild_id = ?", (target_id, current_guild))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id, guild_id) VALUES (?, ?)", (target_id, current_guild))

    if action == "add_money":
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ? AND guild_id = ?", (amount, target_id, current_guild))
        msg = f"✅ {amount} pièces ajoutées au membre {target_id}."
    elif action == "remove_money":
        c.execute("UPDATE users SET balance = MAX(0, balance - ?) WHERE user_id = ? AND guild_id = ?", (amount, target_id, current_guild))
        msg = f"✅ {amount} pièces retirées au membre {target_id}."
    elif action == "add_xp":
        c.execute("UPDATE users SET xp = xp + ? WHERE user_id = ? AND guild_id = ?", (amount, target_id, current_guild))
        msg = f"✅ {amount} XP ajouté au membre {target_id}."
    elif action == "remove_xp":
        c.execute("UPDATE users SET xp = MAX(0, xp - ?) WHERE user_id = ? AND guild_id = ?", (amount, target_id, current_guild))
        msg = f"✅ {amount} XP retiré au membre {target_id}."
    
    conn.commit()
    conn.close()

    referer = request.headers.get("Referer")
    if referer and "economy" in referer:
        return redirect(url_for("economy", msg=msg, guild_id=current_guild))
    return redirect(url_for("index", msg=msg, guild_id=current_guild))

@app.route("/login")
async def login():
    host = request.headers.get("X-Forwarded-Host", request.host)
    proto = request.headers.get("X-Forwarded-Proto", "http" if "127.0.0.1" in host or "localhost" in host else "https")
    redirect_uri = f"{proto}://{host}/callback"
        
    oauth_url = f"https://discord.com/oauth2/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri={quote(redirect_uri)}&scope=identify"
    return redirect(oauth_url)

@app.route("/logout")
async def logout():
    session.pop("user", None)
    return redirect(url_for("index"))

@app.route("/callback")
async def callback():
    code = request.args.get("code")
    if not code: return "Erreur : Aucun code fourni."

    host = request.headers.get("X-Forwarded-Host", request.host)
    proto = request.headers.get("X-Forwarded-Proto", "http" if "127.0.0.1" in host or "localhost" in host else "https")
    redirect_uri = f"{proto}://{host}/callback"

    data = {
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri
    }
    
    async with aiohttp.ClientSession() as http_session:
        async with http_session.post("https://discord.com/api/oauth2/token", data=data) as resp:
            token_info = await resp.json()
            if "access_token" not in token_info: return f"Erreur Discord : {token_info}"

        headers = {"Authorization": f"Bearer {token_info['access_token']}"}
        async with http_session.get("https://discord.com/api/users/@me", headers=headers) as user_resp:
            user_info = await user_resp.json()

        owner_id = os.getenv("OWNER_ID")
        if str(user_info["id"]) == str(owner_id):
            session["user"] = {"id": user_info["id"], "username": user_info["username"], "avatar": user_info.get("avatar")}
        else:
            return f"Accès refusé : Vous n'êtes pas le propriétaire de ce bot. (Votre ID : {user_info['id']})"
        
    return redirect(url_for("index"))

if __name__ == "__main__":
    # Lance le panel web sur le port 5000 (accessible via http://127.0.0.1:5000)
    app.run(host="0.0.0.0", port=5000)