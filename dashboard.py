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
        .btn { background-color: #5865F2; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; }
        .btn:hover { background-color: #4752C4; }
        .avatar { width: 40px; height: 40px; border-radius: 50%; }
    </style>
</head>
<body>
    <div class="header">
        {% if session.get('user') %}
            <img class="avatar" src="https://cdn.discordapp.com/avatars/{{ session['user']['id'] }}/{{ session['user']['avatar'] }}.png" alt="Avatar">
            <span>Connecté en tant que <b>{{ session['user']['username'] }}</b></span>
            <a href="/logout" class="btn" style="background-color: #ED4245;">Se déconnecter</a>
        {% else %}
            <a href="/login" class="btn">Se connecter avec Discord</a>
        {% endif %}
    </div>

    <div class="nav">
        <a href="/">🏆 Niveaux</a>
        <a href="/economy">💰 Économie</a>
    </div>

    <h1>{{ title }}</h1>
    <table>
        <tr><th>Position</th><th>Membre</th>
            {% if page == 'levels' %}<th>Niveau</th><th>XP</th>{% else %}<th>Solde</th>{% endif %}
        </tr>
        {% for i, row in enumerate(leaderboard, 1) %}
        <tr><td>#{{ i }}</td><td>{{ row[3] or row[0] }}</td>
            {% if page == 'levels' %}<td>⭐ {{ row[2] }}</td><td>{{ row[1] }} XP</td>{% else %}<td>🪙 {{ row[1] }} pièces</td>{% endif %}
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

@app.route("/")
async def index():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("SELECT user_id, xp, level, username FROM users ORDER BY level DESC, xp DESC LIMIT 10")
    except sqlite3.OperationalError:
        c.execute("SELECT user_id, xp, level, user_id FROM users ORDER BY level DESC, xp DESC LIMIT 10")
    leaderboard = c.fetchall()
    conn.close()
    
    return await render_template_string(HTML_TEMPLATE, leaderboard=leaderboard, enumerate=enumerate, session=session, page="levels", title="🏆 Leaderboard - Top Niveaux")

@app.route("/economy")
async def economy():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("SELECT user_id, balance, 0, username FROM users ORDER BY balance DESC LIMIT 10")
    except sqlite3.OperationalError:
        c.execute("SELECT user_id, balance, 0, user_id FROM users ORDER BY balance DESC LIMIT 10")
    leaderboard = c.fetchall()
    conn.close()
    
    return await render_template_string(HTML_TEMPLATE, leaderboard=leaderboard, enumerate=enumerate, session=session, page="economy", title="💰 Leaderboard - Économie")

@app.route("/login")
async def login():
    redirect_uri = request.host_url.rstrip('/') + "/callback"
    # Force le HTTPS si on n'est pas en local (obligatoire pour Discord)
    if "127.0.0.1" not in redirect_uri and "localhost" not in redirect_uri:
        redirect_uri = redirect_uri.replace("http://", "https://")
        
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

    redirect_uri = request.host_url.rstrip('/') + "/callback"
    if "127.0.0.1" not in redirect_uri and "localhost" not in redirect_uri:
        redirect_uri = redirect_uri.replace("http://", "https://")

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

        # Sauvegarde le profil de l'utilisateur dans son navigateur
        session["user"] = {"id": user_info["id"], "username": user_info["username"], "avatar": user_info.get("avatar")}
        
    return redirect(url_for("index"))

if __name__ == "__main__":
    # Lance le panel web sur le port 5000 (accessible via http://127.0.0.1:5000)
    app.run(host="0.0.0.0", port=5000)