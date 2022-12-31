from hashlib import sha256


def sha256string(input: str) -> str:
    return sha256(input.encode("utf-8")).hexdigest()
