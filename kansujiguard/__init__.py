"""JP Kansuji Guard: convert kanji numerals in Japanese text to digits without breaking names, places and idioms."""
__version__ = "0.1.0"
from .guard import convert, parse_number, naive_convert  # noqa: F401
