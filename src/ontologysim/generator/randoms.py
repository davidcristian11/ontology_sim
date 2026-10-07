import hashlib
import random


def derive_seed(base_seed: int, namespace: str) -> int:
    payload = f"{base_seed}:{namespace}".encode()
    digest = hashlib.sha256(payload).digest()

    return int.from_bytes(digest[:8], byteorder="big", signed=False)


def random_for(base_seed: int, namespace: str) -> random.Random:
    return random.Random(derive_seed(base_seed, namespace))
