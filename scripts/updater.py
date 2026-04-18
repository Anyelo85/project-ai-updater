import os
import subprocess
import requests
from openai import OpenAI

# Limpieza absoluta de variables
def clean(txt):
    return "".join(c for c in (txt or "") if c.isalnum() or c in (':', '/', '.', '-', '_')).strip()

OLLAMA_URL = clean(os.environ.get("OLLAMA_NGROK_URL", "")).rstrip('/')
REPO_URL = clean(os.environ.get("TARGET_REPO_URL", ""))
TOKEN = clean(os.environ.get("GITHUB_TOKEN", ""))

def main():
    print("--- INICIANDO VERSIÓN 5 (MODO SEGURO) ---")
    
    if not REPO_URL or not OLLAMA_URL:
        print(f"ERROR: Variables incompletas. URL: '{OLLAMA_URL}', Repo: '{REPO_URL}'")
        return

    # Usamos un nombre de carpeta FIJO para evitar errores de caracteres invisibles
    folder = "repo_trabajo"
    
    if os.path.exists(folder):
        subprocess.run(["rm", "-rf", folder], check=False)

    print(f"Clonando {REPO_URL} en {folder}...")
    try:
        # Forzamos el nombre de la carpeta al final del comando git clone
        subprocess.run(["git", "clone", REPO_URL, folder], check=True)
    except Exception as e:
        print(f"Error fatal al clonar: {e}")
        return

    os.chdir(folder)

    # Buscar archivo para mejorar
    files = [f for f in os.listdir('.') if os.path.isfile(f) and not f.startswith('.')]
    target = "index.html" if "index.html" in files else (files[0] if files else None)
    
    if not target:
        print("No se encontraron archivos en el repo.")
        return

    print(f"Archivo a mejorar: {target}")
    with open(target, "r", encoding='utf-8') as f:
        code = f.read()

    print(f"Conectando a Ollama en {OLLAMA_URL}...")
    try:
        client = OpenAI(base_url=f"{OLLAMA_URL}/v1", api_key="ollama", timeout=300)
        res = client.chat.completions.create(
            model="llama3",
            messages=[{"role": "user", "content": f"Mejora este código. Devuelve SOLO el código:\n\n{code}"}]
        )
        new_code = res.choices[0].message.content.strip()
        
        # Limpiar si la IA pone ```html ... ```
        if "```" in new_code:
            new_code = new_code.split("```")[1]
            if "\n" in new_code:
                new_code = "\n".join(new_code.split("\n")[1:])
        
        with open(target, "w", encoding='utf-8') as f:
            f.write(new_code.strip())

        print("Creando Pull Request...")
        subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "checkout", "-b", "ai-update"], check=True)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "IA: Mejoras automáticas"], check=True)
        
        push_url = REPO_URL.replace("https://", f"https://{TOKEN}@")
        subprocess.run(["git", "push", "-f", push_url, "ai-update"], check=True)
        
        repo_path = REPO_URL.replace("https://github.com/", "").replace(".git", "")
        requests.post(
            f"https://api.github.com/repos/{repo_path}/pulls",
            json={"title": "Mejora IA", "body": "Sugerencia de Ollama", "head": "ai-update", "base": "main"},
            headers={"Authorization": f"token {TOKEN}"}
        )
        print("¡PROCESO FINALIZADO CON ÉXITO!")

    except Exception as e:
        print(f"Error durante la conexión con la IA: {e}")

if __name__ == "__main__":
    main()
