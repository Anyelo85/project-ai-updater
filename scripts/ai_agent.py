import os
import subprocess
import requests
from openai import OpenAI

# Obtener las variables de manera segura
OLLAMA_URL = os.environ.get("OLLAMA_NGROK_URL", "").strip()
REPO_URL = os.environ.get("TARGET_REPO_URL", "").strip()
TOKEN = os.environ.get("GH_TOKEN", "").strip()

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
    except Exception as e:
        print(f"Error al clonar: {e}")
        return

    # Usar context manager para manejar el cambio de directorio de forma segura
    original_dir = os.getcwd()
    try:
        os.chdir(folder)
        
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
            # IMPORTANTE: Configuración correcta de autenticación para ngrok
            client = OpenAI(
                base_url=f"{OLLAMA_URL}/v1", 
                api_key="ollama", 
                timeout=300,
                default_headers={
                    "ngrok-skip-browser-warning": "true",
                    "User-Agent": "OpenAI/Python"
                }
            )
            
            res = client.chat.completions.create(
                model="llama3",
                messages=[{"role": "user", "content": f"Mejora este código profesionalmente. Responde SOLO con el código completo sin explicaciones:\n\n{code}"}]
            )
            new_code = res.choices[0].message.content.strip()
            
            # Extracción robusta de código entre backticks
            if "```" in new_code:
                parts = new_code.split("```")
                if len(parts) >= 2:
                    # Obtener el código entre los backticks
                    code_block = parts[1]
                    # Saltar la primera línea si contiene identificador de lenguaje (html, python, etc)
                    lines = code_block.split("\n")
                    if lines and not lines[0].strip().startswith(" "):
                        code_block = "\n".join(lines[1:] if len(lines) > 1 else [])
                    new_code = code_block.strip()
            
            # Validar que el código no esté vacío
            if not new_code:
                print("⚠️ Advertencia: La IA no devolvió código válido, usando original")
                new_code = code
            
            with open(target, "w", encoding='utf-8') as f:
                f.write(new_code.strip())

            print("Preparando Pull Request...")
            subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
            subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
            subprocess.run(["git", "checkout", "-b", "ai-upgrade"], check=True)
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", "IA: Mejoras automáticas"], check=True)
            
            # Usar variable de entorno GH_TOKEN de forma segura para git
            env = os.environ.copy()
            env["GH_TOKEN"] = TOKEN
            subprocess.run(["git", "push", "-f", REPO_URL, "ai-upgrade"], check=True, env=env)
            
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
    finally:
        # Asegurar que volvamos al directorio original
        os.chdir(original_dir)

if __name__ == "__main__":
    main()
