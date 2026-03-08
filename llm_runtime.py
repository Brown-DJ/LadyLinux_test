import subprocess
import threading

MODEL_NAME = "mistral"
model_loaded = False
model_load_attempted = False
lock = threading.Lock()


def ensure_model() -> None:
    global model_loaded, model_load_attempted

    if model_loaded or model_load_attempted:
        return

    with lock:
        if model_loaded or model_load_attempted:
            return

        model_load_attempted = True
        result = subprocess.run(
            ["ollama", "run", MODEL_NAME],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode == 0:
            model_loaded = True
