# Future
from __future__ import annotations

# My stuff
from utilities.utils.asset import *
from utilities.utils.datetime import *
from utilities.utils.embed import *
from utilities.utils.links import *
from utilities.utils.manager import *
from utilities.utils.missing import *
from utilities.utils.upload import *


def readable_bool(value: bool) -> str:
    return str(value).replace("True", "yes").replace("False", "no")


def codeblock(content: str, language: str = "py", max_characters: int | None = None) -> str:

    if max_characters and len(content) > max_characters:
        return content

    return f"```{language}\n" \
           f"{content}\n" \
           f"```"
