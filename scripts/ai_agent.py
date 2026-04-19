import os
import subprocess
import requests
from openai import OpenAI

# Limpieza absoluta de variables
def clean(txt):
    if not txt: return ""
    return "".join(c for c in txt if c.isalnum() or c in (':', '/', '.', '-', '_')).strip()

OLLAMA_URL = clean(os.environ.get("OLLAMA_NGROK_URL", "")).rstrip('/')
REPO_URL = clean(os.environ.get("TARGET_REPO_URL", ""))
TOKEN = clean(os.environ.get("GITHUB_TOKEN", ""))

def main():
    print("--- INICIANDO AGENTE AI V5 ---")
    
    if not REPO_URL or not OLLAMA_URL:
        print(f"ERROR: Variables incompletas.")
        print(f"OLLAMA_URL: '{OLLAMA_URL}'")
        print(f"REPO_URL: '{REPO_URL}'")
        return

    # Carpeta FIJA para evitar el error del \n
    folder = "temp_work_dir"
    
    if os.path.exists(folder):
        subprocess.run(["rm", "-rf", folder], check=False)

    print(f"Clonando {REPO_URL}...")
    try:
        subprocess.run(["git", "clone", REPO_URL, folder], check=True)
    except Exception as e:
        print(f"Error al clonar: {e}")
        return

    os.chdir(folder)

    # Buscar archivo para mejorar
    files = [f for f in os.listdir('.') if os.path.isfile(f) and not f.startswith('.')]
    target = "index.html" if "index.html" in files else (files[0] if files else None)
    
    if not target:
        print("No se encontraron archivos en el repositorio.")
        return

    print(f"Archivo objetivo: {target}")
    with open(target, "r", encoding='utf-8') as f:
        code = f.read()

    print(f"Llamando a Ollama en {OLLAMA_URL}...")
    try:
        client = OpenAI(base_url=f"{OLLAMA_URL}/v1", api_key="ollama", timeout=300)
        res = client.chat.completions.create(
            model="llama3",
            messages=[{"role": "user", "content": f"Mejora este código. Devuelve SOLO el código:\n\n{code}"}]
        )
        new_code = res.choices[0].message.content.strip()
        
        # Limpiar Markdown
        if "```" in new_code:
            new_code = new_code.split("```")[1]
            if "\n" in new_code:
                new_code = "\n".join(new_code.split("\n")[1:])
        
        with open(target, "w", encoding='utf-8') as f:
            f.write(new_code.strip())

        print("Creando Pull Request...")
        subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "checkout", "-b", "ai-update-branch"], check=True)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "IA: Mejoras automáticas"], check=True)
        
        push_url = REPO_URL.replace("https://", f"https://{TOKEN}@")
        subprocess.run(["git", "push", "-f", push_url, "ai-update-branch"], check=True)
        
        repo_path = REPO_URL.replace("https://github.com/", "").replace(".git", "")
        pr_res = requests.post(
            f"https://api.github.com/repos/{repo_path}/pulls",
            json={"title": "Mejora IA", "body": "Sugerencia de Ollama", "head": "ai-update-branch", "base": "main"},
            headers={"Authorization": f"token {TOKEN}"}
        )
        if pr_res.status_code == 201:
            print("¡ÉXITO TOTAL! Pull Request creado.")
        else:
            print(f"Aviso sobre PR: {pr_res.text}")

    except Exception as e:
        print(f"Error con la IA o Conexión: {e}")

if __name__ == "__main__":
    main()
