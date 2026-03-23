import subprocess
import sys
import time

def main():
    print("🚀 Lancement de Eureka Bot et du Dashboard...")
    
    # sys.executable correspond au chemin du Python actuel (pratique si tu utilises un environnement virtuel venv)
    bot_process = subprocess.Popen([sys.executable, "bot.py"])
    print("✅ Bot Discord démarré.")
    
    dashboard_process = subprocess.Popen([sys.executable, "dashboard.py"])
    print("✅ Dashboard Web démarré.")
    
    try:
        # On fait tourner ce script principal à l'infini pour garder les sous-processus actifs
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Si on fait Ctrl+C dans le terminal, on arrête proprement les deux processus
        print("\n🛑 Arrêt en cours...")
        bot_process.terminate()
        dashboard_process.terminate()
        bot_process.wait()
        dashboard_process.wait()
        print("👋 Tous les services ont été arrêtés avec succès.")

if __name__ == "__main__":
    main()