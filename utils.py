import config

def strip_signature(text: str) -> str:
    if text.endswith(config.SIGNATURE):
        return text[:-len(config.SIGNATURE)]
    return text