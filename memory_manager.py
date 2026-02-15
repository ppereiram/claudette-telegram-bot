import json
import os
import logging

logger = logging.getLogger(__name__)
MEMORY_FILE = 'user_memory.json'

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando memoria: {e}")
    return {}

def save_memory(data):
    try:
        with open(MEMORY_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error guardando memoria: {e}")

# --- API PÚBLICA (La que usa brain.py) ---

def get_all_facts():
    """Devuelve todo lo que el bot recuerda como un diccionario."""
    return load_memory()

def save_fact(key, value):
    """Guarda un dato nuevo."""
    data = load_memory()
    data[key] = value
    save_memory(data)
    return True

def get_fact(key):
    """Recupera un dato específico."""
    data = load_memory()
    return data.get(key)
