import os
import subprocess
import requests
from openai import OpenAI

# Configuración
OPENAI_API_KEY = "ollama" # Ollama no requiere una key real
OLLAMA_NGROK_URL = os.environ.get("OLLAMA_NGROK_URL", "http://localhost:11434")
TARGET_REPO_URL = os.environ["TARGET_REPO_URL"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]

def main():
    print("Starting AI Updater with Ollama...")

    repo_name = TARGET_REPO_URL.split("/")[-1].replace(".git", "")
    
    # Limpiar si ya existe
    if os.path.exists(repo_name):
        # En Windows usamos rmdir para seguridad, en Linux rm -rf
        if os.name == 'nt':
            subprocess.run(f"rmdir /s /q {repo_name}", shell=True, check=False)
        else:
            subprocess.run(f"rm -rf {repo_name}", shell=True, check=False)

    print(f"Cloning {repo_name}...")
    subprocess.run(f"git clone {TARGET_REPO_URL}", shell=True, check=True)

    os.chdir(repo_name)
    branch_name = "ai-suggestion"
    
    # <--- ¡IMPORTANTE! CAMBIA ESTA LÍNEA AL ARCHIVO QUE QUIERAS ANALIZAR --->
    file_to_analyze = "src/main.cpp" 

    try:
        with open(file_to_analyze, "r") as f:
            original_code = f.read()
    except FileNotFoundError:
        print(f"Error: File {file_to_analyze} not found. Exiting.")
        os.chdir("..")
        return

    print(f"Analyzing {file_to_analyze} with AI (Ollama via {OLLAMA_NGROK_URL})...")
    client = OpenAI(
        base_url=f"{OLLAMA_NGROK_URL}/v1",
        api_key=OPENAI_API_KEY
    )
    
    prompt = f"Analyze the following C++ code and suggest improvements for performance and readability. Respond only with the full, updated code, no explanations.\n\n```cpp\n{original_code}\n```"
    
    try:
        response = client.chat.completions.create(
            model="llama3", 
            messages=[{"role": "user", "content": prompt}]
        )
        suggested_code = response.choices[0].message.content
        # Limpiar el código de bloques de markdown si la IA los incluye
        if "```" in suggested_code:
            suggested_code = suggested_code.split("```")[1]
            if suggested_code.startswith("cpp"):
                suggested_code = suggested_code[3:]
            suggested_code = suggested_code.strip()

    except Exception as e:
        print(f"Error calling AI API: {e}")
        os.chdir("..")
        return

    print(f"Creating branch {branch_name}...")
    subprocess.run(["git", "config", "user.name", "github-actions[bot]"])
    subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"])
    subprocess.run(f"git checkout -b {branch_name}", shell=True, check=True)
    
    print("Applying AI suggestions...")
    with open(file_to_analyze, "w") as f:
        f.write(suggested_code)
    
    subprocess.run(["git", "add", file_to_analyze])
    subprocess.run(["git", "commit", "-m", "AI: Suggest code improvements"])
    
    print(f"Pushing branch {branch_name}...")
    push_url = TARGET_REPO_URL.replace("https://", f"https://{GITHUB_TOKEN}@")
    subprocess.run(f"git push {push_url} {branch_name}", shell=True, check=True)
    
    print("Creating Pull Request...")
    pr_title = f"AI Suggestion: Improve {file_to_analyze}"
    pr_body = "This is an automated suggestion from an AI (Ollama). Please review the changes carefully before merging."
    
    api_url = TARGET_REPO_URL.replace("https://github.com/", "https://api.github.com/repos/").replace(".git", "")
    pr_data = {"title": pr_title, "body": pr_body, "head": branch_name, "base": "main"}
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    response = requests.post(f"{api_url}/pulls", json=pr_data, headers=headers)
    if response.status_code == 201:
        print("Pull Request created successfully!")
    else:
        print(f"Failed to create Pull Request: {response.status_code} - {response.text}")
    
    os.chdir("..")
    print("Process finished.")

if __name__ == "__main__":
    main()
