import os
import subprocess
import requests
import time
from openai import OpenAI

# 1. Limpieza radical de variables de entorno
def clean_env(var_name):
    value = os.environ.get(var_name, "")
    if not value:
        return ""
    # Quitar saltos de línea, retornos de carro, espacios y comillas accidentales
    return value.strip().replace('\n', '').replace('\r', '').replace('"', '').replace("'", "")

OLLAMA_NGROK_URL = clean_env("OLLAMA_NGROK_URL").rstrip('/')
TARGET_REPO_URL = clean_env("TARGET_REPO_URL")
GITHUB_TOKEN = clean_env("GITHUB_TOKEN")

def main():
    print("--- INICIANDO AI UPDATER (LIMPIEZA PROFUNDA) ---")
    
    if not OLLAMA_NGROK_URL:
        print("ERROR: OLLAMA_NGROK_URL está vacío o no existe en Secrets.")
        # No salimos para ver qué más falla, pero esto es crítico
    
    if not TARGET_REPO_URL:
        print("ERROR: TARGET_REPO_URL está vacío.")
        return

    # Extraer nombre del repo limpiando cualquier basura
    raw_repo_name = TARGET_REPO_URL.split("/")[-1].replace(".git", "")
    repo_name = "".join(c for c in raw_repo_name if c.isalnum() or c in ('-', '_')).strip()
    
    print(f"Repo destino: '{repo_name}'")

    if os.path.exists(repo_name):
        subprocess.run(["rm", "-rf", repo_name], check=False)

    print(f"Clonando {TARGET_REPO_URL}...")
    try:
        # Forzamos el nombre de la carpeta para evitar el problema del \n
        subprocess.run(["git", "clone", TARGET_REPO_URL, repo_name], check=True)
    except Exception as e:
        print(f"Error al clonar: {e}")
        return

    if not os.path.isdir(repo_name):
        print(f"Error: La carpeta {repo_name} no se creó.")
        return

    os.chdir(repo_name)
    
    # Buscar archivo
    archivos = [f for f in os.listdir('.') if os.path.isfile(f) and not f.startswith('.')]
    file_to_analyze = "index.html" if "index.html" in archivos else (archivos[0] if archivos else None)
    
    if not file_to_analyze:
        print("No hay archivos para analizar.")
        return

    print(f"Archivo: {file_to_analyze}")
    with open(file_to_analyze, "r", encoding='utf-8') as f:
        original_code = f.read()

    print(f"Conectando a Ollama en: {OLLAMA_NGROK_URL}")
    try:
        client = OpenAI(
            base_url=f"{OLLAMA_NGROK_URL}/v1",
            api_key="ollama",
            timeout=300.0
        )
        
        prompt = f"Mejora este código profesionalmente. Responde SOLO con el código:\n\n{original_code}"
        
        response = client.chat.completions.create(
            model="llama3", 
            messages=[{"role": "user", "content": prompt}]
        )
        
        suggested_code = response.choices[0].message.content.strip()
        
        # Limpieza de Markdown
        if "```" in suggested_code:
            parts = suggested_code.split("```")
            suggested_code = parts[1]
            if "\n" in suggested_code:
                suggested_code = "\n".join(suggested_code.split("\n")[1:])
            suggested_code = suggested_code.strip()

        with open(file_to_analyze, "w", encoding='utf-8') as f:
            f.write(suggested_code)
        
        print("Subiendo cambios a GitHub...")
        subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "checkout", "-b", "ai-fix"], check=True)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "IA: Mejoras automáticas"], check=True)
        
        push_url = TARGET_REPO_URL.replace("https://", f"https://{GITHUB_TOKEN}@")
        subprocess.run(["git", "push", "-f", push_url, "ai-fix"], check=True)
        
        print("¡Proceso exitoso localmente! Revisa los Pull Requests en el repo objetivo.")

    except Exception as e:
        print(f"Error con la IA: {e}")

if __name__ == "__main__":
    main()
