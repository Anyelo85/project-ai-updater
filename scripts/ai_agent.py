import os
import subprocess
import requests
from openai import OpenAI

# Limpieza absoluta de variables
def clean(txt):
    if not txt: return ""
    return "".join(c for c in txt if c.isalnum() or c in (':', '/', '.', '-', '_')).strip()

# Obtener las variables
OLLAMA_URL = clean(os.environ.get("OLLAMA_NGROK_URL", ""))
REPO_URL = clean(os.environ.get("TARGET_REPO_URL", ""))
TOKEN = clean(os.environ.get("GH_TOKEN", ""))

def main():
    print("--- DIAGNÓSTICO DE AGENTE AI ---")
    print(f"¿OLLAMA_NGROK_URL configurado?: {'SÍ' if OLLAMA_URL else 'NO'}")
    print(f"¿TARGET_REPO_URL configurado?: {'SÍ' if REPO_URL else 'NO'}")
    print(f"¿GH_TOKEN configurado?: {'SÍ' if TOKEN else 'NO'}")

    if not REPO_URL or not OLLAMA_URL or not TOKEN:
        print("\nERROR: Faltan secretos en GitHub.")
        return

    folder = "repo_trabajo"
    if os.path.exists(folder):
        subprocess.run(["rm", "-rf", folder], check=False)

    print(f"\nClonando el repositorio objetivo...")
    try:
        subprocess.run(["git", "clone", REPO_URL, folder], check=True)
        os.chdir(folder)
    except Exception as e:
        print(f"Error al clonar: {e}")
        return

    # Buscar archivo
    files = [f for f in os.listdir('.') if os.path.isfile(f) and not f.startswith('.')]
    target = "index.html" if "index.html" in files else (files[0] if files else None)
    
    if not target:
        print("No se encontraron archivos editables.")
        return

    print(f"Archivo seleccionado: {target}")
    with open(target, "r", encoding='utf-8') as f:
        code = f.read()

    print(f"Conectando a Ollama en {OLLAMA_URL}...")
    try:
        # IMPORTANTE: Añadimos 'ngrok-skip-browser-warning' para evitar el error 403
        client = OpenAI(
            base_url=f"{OLLAMA_URL}/v1", 
            api_key="ollama", 
            timeout=300,
            default_headers={"ngrok-skip-browser-warning": "true"}
        )
        
        res = client.chat.completions.create(
            model="llama3",
            messages=[{"role": "user", "content": f"Mejora este código profesionalmente. Responde SOLO con el código completo:\n\n{code}"}]
        )
        new_code = res.choices[0].message.content.strip()
        
        if "```" in new_code:
            new_code = new_code.split("```")[1]
            if "\n" in new_code:
                new_code = "\n".join(new_code.split("\n")[1:])
        
        with open(target, "w", encoding='utf-8') as f:
            f.write(new_code.strip())

        print("Preparando Pull Request...")
        subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "checkout", "-b", "ai-upgrade"], check=True)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "IA: Mejoras automáticas"], check=True)
        
        push_url = REPO_URL.replace("https://", f"https://{TOKEN}@")
        subprocess.run(["git", "push", "-f", push_url, "ai-upgrade"], check=True)
        
        repo_path = REPO_URL.replace("https://github.com/", "").replace(".git", "")
        pr_res = requests.post(
            f"https://api.github.com/repos/{repo_path}/pulls",
            json={"title": "Mejora IA", "body": "Sugerencia de Ollama (Llama3)", "head": "ai-upgrade", "base": "main"},
            headers={"Authorization": f"token {TOKEN}"}
        )
        
        if pr_res.status_code == 201:
            print("¡ÉXITO TOTAL! Revisa tu portafolio.")
        else:
            print(f"Aviso sobre PR: {pr_res.text}")

    except Exception as e:
        print(f"Error en la conexión con la IA: {e}")

if __name__ == "__main__":
    main()
