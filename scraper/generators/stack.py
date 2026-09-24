import random
from typing import Any

from .common import Generator, distinct_ints, ints, size, valid_parens, wants_true

PAIRS = {"(": ")", "[": "]", "{": "}"}
INT_MAX = 2**31 - 1


def valid_parens_string(rng: random.Random, pairs: int) -> str:
    out: list[str] = []
    stack: list[str] = []
    opened = 0
    while opened < pairs or stack:
        if opened < pairs and (not stack or rng.random() < 0.5):
            opener = rng.choice("([{")
            out.append(opener)
            stack.append(PAIRS[opener])
            opened += 1
        else:
            out.append(stack.pop())
    return "".join(out)


def valid_parentheses(rng: random.Random, i: int) -> list[Any]:
    n = size(rng, i, 2000)
    if wants_true(i):
        return [valid_parens_string(rng, max(1, n // 2))]
    while True:
        if rng.random() < 0.7:
            s = list(valid_parens_string(rng, max(1, n // 2)))
            s[rng.randrange(len(s))] = rng.choice("()[]{}")
        else:
            s = [rng.choice("()[]{}") for _ in range(n)]
        if not valid_parens("".join(s)):
            return ["".join(s)]


def truncating_divide(a: int, b: int) -> int:
    quotient = abs(a) // abs(b)
    return quotient if (a >= 0) == (b > 0) else -quotient


def apply(op: str, a: int, b: int) -> int | None:
    if op == "+":
        result = a + b
    elif op == "-":
        result = a - b
    elif op == "*":
        result = a * b
    else:
        if b == 0:
            return None
        result = truncating_divide(a, b)
    return result if -INT_MAX - 1 <= result <= INT_MAX else None


def evaluate_rpn(rng: random.Random, i: int) -> list[Any]:
    operands = max(1, size(rng, i, 2000) // 2)
    tokens: list[str] = []
    stack: list[int] = []
    pushed = 0
    while pushed < operands or len(stack) > 1:
        if len(stack) < 2 or (pushed < operands and rng.random() < 0.5):
            value = rng.randint(-200, 200)
            tokens.append(str(value))
            stack.append(value)
            pushed += 1
            continue
        b, a = stack[-1], stack[-2]
        for op in rng.sample(["+", "-", "*", "/"], 4):
            result = apply(op, a, b)
            if result is not None:
                stack[-2:] = [result]
                tokens.append(op)
                break
        else:
            value = rng.randint(1, 200)
            tokens.append(str(value))
            stack.append(value)
            pushed += 1
    return [tokens]


def generate_parentheses(rng: random.Random, i: int) -> list[Any]:
    return [i % 8 + 1]


def daily_temperatures(rng: random.Random, i: int) -> list[Any]:
    n = size(rng, i, 5000)
    return [ints(rng, n, 30, 100)]


def car_fleet(rng: random.Random, i: int) -> list[Any]:
    n = size(rng, i, 3000)
    target = rng.randint(n + 1, rng.choice([n + 20, 10**6]))
    position = distinct_ints(rng, n, 0, target - 1)
    speed = ints(rng, n, 1, rng.choice([5, 10**6]))
    return [target, position, speed]


GENERATORS: dict[str, Generator] = {
    "valid-parentheses": valid_parentheses,
    "evaluate-reverse-polish-notation": evaluate_rpn,
    "generate-parentheses": generate_parentheses,
    "daily-temperatures": daily_temperatures,
    "car-fleet": car_fleet,
}
