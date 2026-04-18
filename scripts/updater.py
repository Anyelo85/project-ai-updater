import os
import subprocess
import requests
from openai import OpenAI

# Configuración
OPENAI_API_KEY = "ollama" # Ollama no requiere una key real
OLLAMA_NGROK_URL = os.environ.get("OLLAMA_NGROK_URL", "").strip()
TARGET_REPO_URL = os.environ.get("TARGET_REPO_URL", "").strip()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()

def main():
    if not TARGET_REPO_URL:
        print("Error: TARGET_REPO_URL no está configurada.")
        return

    print("Starting AI Updater with Ollama...")

    # Limpiar el nombre del repo de posibles saltos de línea o espacios
    repo_name = TARGET_REPO_URL.split("/")[-1].replace(".git", "").strip()
    
    # Limpiar si ya existe la carpeta
    if os.path.exists(repo_name):
        print(f"Limpiando directorio existente: {repo_name}")
        if os.name == 'nt':
            subprocess.run(f"rmdir /s /q {repo_name}", shell=True, check=False)
        else:
            subprocess.run(["rm", "-rf", repo_name], check=False)

    print(f"Cloning {repo_name} desde {TARGET_REPO_URL}...")
    subprocess.run(["git", "clone", TARGET_REPO_URL], check=True)

    if not os.path.exists(repo_name):
        print(f"Error: No se pudo encontrar la carpeta clonada {repo_name}")
        return

    os.chdir(repo_name)
    branch_name = "ai-suggestion"
    
    # <--- AJUSTA ESTO: ¿Qué archivo quieres que la IA mejore? --->
    # Si tu portafolio es HTML/JS, cambia esto por "index.html" o similar.
    file_to_analyze = "index.html" 

    if not os.path.exists(file_to_analyze):
        # Si no existe index.html, intentamos buscar cualquier archivo .html o .js
        print(f"Aviso: {file_to_analyze} no encontrado. Buscando alternativa...")
        archivos = [f for f in os.listdir('.') if f.endswith(('.html', '.js', '.cpp', '.py'))]
        if archivos:
            file_to_analyze = archivos[0]
            print(f"Usando archivo encontrado: {file_to_analyze}")
        else:
            print("Error: No se encontraron archivos para analizar.")
            os.chdir("..")
            return

    try:
        with open(file_to_analyze, "r", encoding='utf-8') as f:
            original_code = f.read()
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        os.chdir("..")
        return

    print(f"Analyzing {file_to_analyze} with AI (Ollama via {OLLAMA_NGROK_URL})...")
    client = OpenAI(
        base_url=f"{OLLAMA_NGROK_URL}/v1",
        api_key=OPENAI_API_KEY
    )
    
    prompt = f"Mejora el siguiente código para que sea más profesional y eficiente. Responde ÚNICAMENTE con el código completo actualizado, sin explicaciones ni bloques de markdown:\n\n{original_code}"
    
    try:
        response = client.chat.completions.create(
            model="llama3", 
            messages=[{"role": "user", "content": prompt}]
        )
        suggested_code = response.choices[0].message.content
        
        # Limpieza básica por si la IA añade markdown
        if "```" in suggested_code:
            parts = suggested_code.split("```")
            suggested_code = parts[1]
            # Quitar el nombre del lenguaje si existe (ej: ```html)
            if suggested_code.startswith(("html", "javascript", "js", "cpp", "python", "py")):
                suggested_code = "\n".join(suggested_code.split("\n")[1:])
            suggested_code = suggested_code.strip()

    except Exception as e:
        print(f"Error llamando a la IA: {e}")
        os.chdir("..")
        return

    print(f"Creating branch {branch_name}...")
    subprocess.run(["git", "config", "user.name", "github-actions[bot]"])
    subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"])
    subprocess.run(["git", "checkout", "-b", branch_name], check=True)
    
    print("Applying AI suggestions...")
    with open(file_to_analyze, "w", encoding='utf-8') as f:
        f.write(suggested_code)
    
    subprocess.run(["git", "add", file_to_analyze])
    subprocess.run(["git", "commit", "-m", f"AI: Sugerencia de mejora para {file_to_analyze}"])
    
    print(f"Pushing branch {branch_name}...")
    push_url = TARGET_REPO_URL.replace("https://", f"https://{GITHUB_TOKEN}@")
    subprocess.run(["git", "push", "-f", push_url, branch_name], check=True)
    
    print("Creating Pull Request...")
    pr_title = f"IA Sugerencia: Mejorar {file_to_analyze}"
    pr_body = "Esta es una sugerencia automática generada por Ollama (Llama3). Por favor, revisa los cambios antes de fusionar."
    
    api_url = TARGET_REPO_URL.replace("https://github.com/", "https://api.github.com/repos/").replace(".git", "")
    pr_data = {"title": pr_title, "body": pr_body, "head": branch_name, "base": "main"}
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    response = requests.post(f"{api_url}/pulls", json=pr_data, headers=headers)
    if response.status_code == 201:
        print("¡Pull Request creado con éxito!")
    else:
        print(f"Error al crear PR: {response.status_code} - {response.text}")
    
    os.chdir("..")
    print("Proceso finalizado.")

if __name__ == "__main__":
    main()
