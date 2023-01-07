import json
import re
from functools import cache
from pathlib import Path
from typing import Set

from fedimapper.settings import settings

__repo_base = Path(settings.stop_words_directory)
__repo_settings = __repo_base / "languages.json"
__language_settings = {}

if __repo_settings.exists():
    with open(__repo_settings) as fp:
        __language_settings = json.load(fp)


def _get_file_name(language: str) -> str | None:
    if language in __language_settings:
        return f"{__language_settings[language]}.txt"
    if language in __language_settings.values():
        return f"{language}.txt"
    return None


@cache
def get_language_stop_words(language: str, suppress_error: bool = False) -> Set[str]:
    language_file = _get_file_name(language)

    if not language_file:
        if suppress_error:
            return Set([])
        raise ValueError(f"No registered language file for language file for {language}.")

    path_file = __repo_base / language_file
    if not path_file.exists():
        if suppress_error:
            return Set([])
        raise ValueError(f"Unable to find language file for {language}.")

    try:
        with open(path_file) as fp:
            results = set(fp.read().split("\n"))
    except:
        if suppress_error:
            return set([])
        raise

    return results


WORD_PATTERN = re.compile(r"[\w-]+", re.IGNORECASE)


def get_key_words(language, string) -> Set[str]:
    stop_words = get_language_stop_words(language, suppress_error=True)
    words = WORD_PATTERN.findall(string)
    words = [word.lower() for word in words if len(word) > 2]
    return set([word for word in words if word not in stop_words])
