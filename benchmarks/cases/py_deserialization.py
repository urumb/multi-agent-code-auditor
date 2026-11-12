import pickle

import yaml


def load_session(blob: bytes):
    return pickle.loads(blob)  # EXPECT: security


def load_config(text: str):
    return yaml.load(text, Loader=yaml.Loader)  # EXPECT: security


def load_safe_config(text: str):
    # Safe: SafeLoader cannot construct arbitrary objects.
    return yaml.safe_load(text)


def run_formula(expression: str):
    return eval(expression)  # EXPECT: security
