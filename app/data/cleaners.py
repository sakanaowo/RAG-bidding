import re
from typing import Callable

WS = re.compile(r"[\t\f\r]+")


def basic_clean(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = text.replace("\r", "\n").replace("\t", " ")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = WS.sub(" ", text)
    text = text.strip()
    return text


Cleaner = Callable[[str], str]
