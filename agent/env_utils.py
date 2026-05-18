"""
Environment loader utility for Haoner.

Loads configuration from .env file into os.environ.
"""

import os


def load_env():
    """Load .env file into os.environ."""
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()


def get_provider() -> str:
    """Get the LLM provider from environment."""
    load_env()
    return os.environ.get('LLM_PROVIDER', 'openai').lower()
