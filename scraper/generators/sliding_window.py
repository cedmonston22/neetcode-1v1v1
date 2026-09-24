import random
import string
from typing import Any

from .common import Generator, ints, lowercase, size

PRINTABLE = string.ascii_letters + string.digits + " !#$%&()*+,-./:;<=>?@[]^_{|}~"


def best_time_to_buy_and_sell(rng: random.Random, i: int) -> list[Any]:
    n = size(rng, i, 5000)
    return [ints(rng, n, 0, rng.choice([10, 10**4]))]


def longest_substring_no_repeat(rng: random.Random, i: int) -> list[Any]:
    n = size(rng, i, 5000, low=0)
    alphabet = rng.choice(["ab", "abcdef", string.ascii_lowercase, PRINTABLE])
    return [lowercase(rng, n, alphabet)]


def character_replacement(rng: random.Random, i: int) -> list[Any]:
    n = size(rng, i, 5000)
    alphabet = rng.choice(["AB", "ABCD", string.ascii_uppercase])
    return [lowercase(rng, n, alphabet), rng.randint(0, n)]


def permutation_in_string(rng: random.Random, i: int) -> list[Any]:
    alphabet = rng.choice(["abc", "abcdef", string.ascii_lowercase])
    s1 = lowercase(rng, size(rng, i, 50), alphabet)
    s2 = lowercase(rng, size(rng, i, 5000), alphabet)
    if rng.random() < 0.5:
        letters = list(s1)
        rng.shuffle(letters)
        at = rng.randint(0, len(s2))
        s2 = s2[:at] + "".join(letters) + s2[at:]
    return [s1, s2]


GENERATORS: dict[str, Generator] = {
    "best-time-to-buy-and-sell-stock": best_time_to_buy_and_sell,
    "longest-substring-without-repeating-characters": longest_substring_no_repeat,
    "longest-repeating-character-replacement": character_replacement,
    "permutation-in-string": permutation_in_string,
}
