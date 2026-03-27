# =============================================================
# vaultmind — ai_backend.py
# =============================================================
# Shared AI caller used by all scripts.
# All Ollama communication goes through this file.
# =============================================================

from pathlib import Path
import sys
import requests
import time

from config import (
    OLLAMA_MODEL, OLLAMA_API_URL, TEMPERATURES, TIMEOUT, 
    KEEP_ALIVE, NUM_CTX, VAULT_PATH, NVIDIA_MODEL, 
    USE_NVIDIA_NIM, NVIDIA_API_KEY
) # noqa: E402

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

# terminal colors
R    = "\033[0m"
RED  = "\033[31m"
YELLOW = "\033[33m"
GREEN  = "\033[32m"
DIM    = "\033[2m"


def check_ollama() -> bool:
    base_url = OLLAMA_API_URL.replace("/api/generate", "")

    # check if Ollama is running
    try:
        r = requests.get(f"{base_url}/api/tags", timeout=5)
        r.raise_for_status()
    except requests.exceptions.ConnectionError:
        print(f"{RED}  Error: Ollama is not running.{R}")
        print(f"     Start it with: {YELLOW}ollama serve{R}")
        return False
    except Exception as e:
        print(f"{RED}  Error: Could not reach Ollama: {e}{R}")
        return False

    # check if the configured model is available
    models = [m["name"] for m in r.json().get("models", [])]
    if not any(OLLAMA_MODEL in m for m in models):
        print(f"{RED}  Error: Model '{OLLAMA_MODEL}' not found.{R}")
        print(f"     Available models: {', '.join(models) if models else 'none'}")
        return False

    return True


def check_vault() -> bool:
    """
    Check if the configured vault path exists.
    Prints a error if not found.

    Returns:
        True if vault exists, False otherwise.
    """
    vault = Path(VAULT_PATH).expanduser().resolve()
    if not vault.is_dir():
        print(f"{RED}  Error: Vault not found at: {vault}{R}")
        print("     Update VAULT_PATH in config.py")
        return False
    return True


def run_startup_checks() -> None:
    print(f"{DIM}  running startup checks...{R}")

    vault_ok  = check_vault()
    ollama_ok = check_ollama()

    if not vault_ok or not ollama_ok:
        print(f"\n{RED}  fix the issues above and try again.{R}\n")
        sys.exit(1)

    print(f"{GREEN}  all checks passed{R}\n")


def get_backend() -> str:
    return "nvidia" if USE_NVIDIA_NIM else "ollama"


def backend_label(backend: str) -> str:
    if backend == "ollama":
        return f"NVIDIA NIM ({NVIDIA_MODEL})"
    return f"Ollama ({OLLAMA_MODEL})"

def call_ai(prompt: str, backend: str = "ollama", timeout: int = None, temperature: float = None) -> str:
    """
    Send a prompt to the configured AI backend and return the response text.

    Args:
        prompt:  The full prompt string to send to the model.
        backend: Which backend to use. Currently only 'ollama' is supported.
        timeout: Override the default timeout from config.py (in seconds).
        temperature: Override the global temperature for this specific call.

    Returns:
        The model's response as a stripped string.
    """
    
    if USE_NVIDIA_NIM:
        return _call_nvidia(prompt, NVIDIA_API_KEY, temperature)
    else:
        return _call_ollama(prompt, timeout or TIMEOUT, temperature)

def _call_nvidia(prompt: str, api_key: str, temperature: float = None) -> str:
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    global_temp = TEMPERATURES.get("default", 0.2)
    raw_temp = temperature if temperature is not None else global_temp
    final_temp = max(0.0, min(1.0, float(raw_temp or 0.2)))

    payload = {

        "model": NVIDIA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": final_temp,
        "top_p": 0.7,
        "max_tokens": 4096,
    } 
    
    for attempt in range(3):
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=300
            )
            response.raise_for_status()

            result = response.json()
            return result["choices"][0]["message"]["content"].strip()

        except requests.exceptions.RequestException as e:
            print(f"\n\033[31m[NVIDIA API ERROR - attempt {attempt+1}/3] {e}\033[0m")

            if attempt == 2:
                raise

            time.sleep(2 ** attempt)

def _call_ollama(prompt: str, timeout: int, temperature: float = None) -> str:
    """
    Internal function that makes the actual HTTP request to the Ollama API.
    """

    global_temp = TEMPERATURES.get("default", 0.2)
    raw_temp = temperature if temperature is not None else global_temp

    try:
        final_temp = max(0.0, min(1.0, float(raw_temp)))
    except (ValueError, TypeError):
        print(f"\n[WARNING] Invalid temperature '{raw_temp}' in config. Defaulting to 0.2")
        final_temp = 0.2

    response = requests.post(
        OLLAMA_API_URL,
        json={
            "model":      OLLAMA_MODEL,
            "prompt":     prompt,
            "stream":     False,
            "keep_alive": KEEP_ALIVE,
            "options": {
                "temperature":    final_temp,
                "top_p":          0.9,
                "repeat_penalty": 1.1,
                "num_ctx":        NUM_CTX,
            }
        },
        timeout=timeout,
    )

    response.raise_for_status()
    data = response.json()

    if "response" not in data:
        raise ValueError(f"Unexpected Ollama response format: {data}")

    return data["response"].strip()