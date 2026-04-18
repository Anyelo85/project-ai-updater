import os
import subprocess
import requests
import time
from openai import OpenAI

# Configuración con limpieza de espacios y barras finales
OLLAMA_NGROK_URL = os.environ.get("OLLAMA_NGROK_URL", "").strip().rstrip('/')
TARGET_REPO_URL = os.environ.get("TARGET_REPO_URL", "").strip()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()

def main():
    print(f"--- DEBUG: Iniciando Proceso ---")
    print(f"URL: {OLLAMA_NGROK_URL}")
    print(f"Repo: {TARGET_REPO_URL}")

    if not OLLAMA_NGROK_URL or not TARGET_REPO_URL:
        print("ERROR: Faltan Secrets en GitHub (OLLAMA_NGROK_URL o TARGET_REPO_URL).")
        return

    repo_name = TARGET_REPO_URL.split("/")[-1].replace(".git", "").strip()
    
    if os.path.exists(repo_name):
        print(f"Limpiando directorio antiguo: {repo_name}")
        subprocess.run(["rm", "-rf", repo_name], check=False)

    print(f"Clonando {TARGET_REPO_URL}...")
    try:
        subprocess.run(["git", "clone", TARGET_REPO_URL], check=True)
    except Exception as e:
        print(f"Error al clonar: {e}")
        return

    os.chdir(repo_name)
    print(f"Cambiado al directorio: {os.getcwd()}")

    # Buscar archivo para analizar (Prioridad index.html)
    archivos_posibles = ["index.html", "main.cpp", "app.js", "style.css"]
    file_to_analyze = None
    
    for f in archivos_posibles:
        if os.path.exists(f):
            file_to_analyze = f
            break
    
    if not file_to_analyze:
        todos = [f for f in os.listdir('.') if os.path.isfile(f)]
        if todos:
            file_to_analyze = todos[0]
    
    if not file_to_analyze:
        print("Error: No se encontró ningún archivo para analizar.")
        return

    print(f"Analizando archivo: {file_to_analyze}")
    with open(file_to_analyze, "r", encoding='utf-8') as f:
        original_code = f.read()

    print(f"Conectando con Ollama (esperando respuesta)...")
    try:
        client = OpenAI(
            base_url=f"{OLLAMA_NGROK_URL}/v1",
            api_key="ollama",
            timeout=300.0 # 5 minutos de espera
        )
        
        prompt = f"Mejora este código profesionalmente. Responde SOLO con el código:\n\n{original_code}"
        
        start = time.time()
        response = client.chat.completions.create(
            model="llama3", 
            messages=[{"role": "user", "content": prompt}]
        )
        print(f"Ollama respondió en {time.time() - start:.2f} segundos.")
        
        suggested_code = response.choices[0].message.content.strip()
        
        # Limpiar bloques de código markdown
        if "```" in suggested_code:
            suggested_code = suggested_code.split("```")[1]
            if "\n" in suggested_code:
                first_line = suggested_code.split("\n")[0]
                if first_line.lower() in ["html", "css", "js", "javascript", "cpp", "python"]:
                    suggested_code = "\n".join(suggested_code.split("\n")[1:])
            suggested_code = suggested_code.strip()

        with open(file_to_analyze, "w", encoding='utf-8') as f:
            f.write(suggested_code)
        
        print("Cambios guardados. Creando Rama y PR...")
        
        subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "checkout", "-b", "ai-improvements"], check=True)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "IA: Mejoras de código"], check=True)
        
        push_url = TARGET_REPO_URL.replace("https://", f"https://{GITHUB_TOKEN}@")
        subprocess.run(["git", "push", "-f", push_url, "ai-improvements"], check=True)
        
        api_url = TARGET_REPO_URL.replace("https://github.com/", "https://api.github.com/repos/").replace(".git", "")
        pr_payload = {
            "title": "IA: Sugerencia de mejora",
            "body": "Sugerencia automática de Ollama.",
            "head": "ai-improvements",
            "base": "main"
        }
        res = requests.post(f"{api_url}/pulls", json=pr_payload, headers={"Authorization": f"token {GITHUB_TOKEN}"})
        
        if res.status_code == 201:
            print("¡Pull Request creado con éxito!")
        else:
            print(f"Error al crear PR: {res.text}")

    except Exception as e:
        print(f"ERROR FATAL: {e}")

if __name__ == "__main__":
    main()
