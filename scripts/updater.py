import os
import subprocess
import requests
import time
import sys
from openai import OpenAI

# 1. Limpieza extrema de variables
OLLAMA_NGROK_URL = os.environ.get("OLLAMA_NGROK_URL", "").strip().replace('\n', '').replace('\r', '').rstrip('/')
TARGET_REPO_URL = os.environ.get("TARGET_REPO_URL", "").strip().replace('\n', '').replace('\r', '')
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip().replace('\n', '').replace('\r', '')

def main():
    print("--- INICIO DEL SCRIPT (V3) ---")
    
    if not TARGET_REPO_URL:
        print("ERROR: TARGET_REPO_URL no definida.")
        return

    # Extraer nombre del repo y limpiar CUALQUIER carácter invisible
    repo_name = TARGET_REPO_URL.split("/")[-1].replace(".git", "")
    repo_name = "".join(c for c in repo_name if c.isalnum() or c in ('-', '_')).strip()
    
    print(f"Variable Repo: '{repo_name}'")

    # Limpiar si ya existe
    if os.path.exists(repo_name):
        print(f"Borrando carpeta existente: {repo_name}")
        subprocess.run(["rm", "-rf", repo_name], check=False)

    print(f"Ejecutando: git clone {TARGET_REPO_URL}")
    try:
        # Clonar el repo
        result = subprocess.run(["git", "clone", TARGET_REPO_URL, repo_name], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error en git clone: {result.stderr}")
            return
    except Exception as e:
        print(f"Error fatal al clonar: {e}")
        return

    # Verificar si la carpeta existe realmente
    print(f"Directorios actuales: {os.listdir('.')}")
    if not os.path.isdir(repo_name):
        print(f"ERROR: La carpeta '{repo_name}' no existe tras el clonado.")
        return

    os.chdir(repo_name)
    print(f"Cambiado a: {os.getcwd()}")

    # Buscar archivo (index.html, app.js, o el primero que encuentre)
    archivos = [f for f in os.listdir('.') if os.path.isfile(f) and not f.startswith('.')]
    file_to_analyze = "index.html" if "index.html" in archivos else (archivos[0] if archivos else None)
    
    if not file_to_analyze:
        print("No se encontraron archivos para mejorar.")
        return

    print(f"Mejorando: {file_to_analyze}")
    with open(file_to_analyze, "r", encoding='utf-8') as f:
        original_code = f.read()

    print(f"Conectando a Ollama en {OLLAMA_NGROK_URL}...")
    try:
        client = OpenAI(
            base_url=f"{OLLAMA_NGROK_URL}/v1",
            api_key="ollama",
            timeout=600.0
        )
        
        prompt = f"Mejora este código profesionalmente. Responde SOLO con el código completo:\n\n{original_code}"
        
        response = client.chat.completions.create(
            model="llama3", 
            messages=[{"role": "user", "content": prompt}]
        )
        
        suggested_code = response.choices[0].message.content.strip()
        
        # Limpiar Markdown
        if "```" in suggested_code:
            suggested_code = suggested_code.split("```")[1]
            if "\n" in suggested_code:
                suggested_code = "\n".join(suggested_code.split("\n")[1:]).strip()

        with open(file_to_analyze, "w", encoding='utf-8') as f:
            f.write(suggested_code)
        
        print("Creando Pull Request en GitHub...")
        subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "checkout", "-b", "ai-fix"], check=True)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "IA: Mejoras automáticas"], check=True)
        
        push_url = TARGET_REPO_URL.replace("https://", f"https://{GITHUB_TOKEN}@")
        subprocess.run(["git", "push", "-f", push_url, "ai-fix"], check=True)
        
        # API de GitHub para PR
        repo_path = TARGET_REPO_URL.replace("https://github.com/", "").replace(".git", "")
        api_url = f"https://api.github.com/repos/{repo_path}/pulls"
        pr_data = {"title": "Mejora IA", "body": "Sugerencia de Ollama", "head": "ai-fix", "base": "main"}
        
        res = requests.post(api_url, json=pr_data, headers={"Authorization": f"token {GITHUB_TOKEN}"})
        if res.status_code == 201:
            print("¡TODO LISTO! Revisa tus Pull Requests.")
        else:
            print(f"Aviso PR: {res.text}")

    except Exception as e:
        print(f"Error en el proceso de IA: {e}")

if __name__ == "__main__":
    main()
