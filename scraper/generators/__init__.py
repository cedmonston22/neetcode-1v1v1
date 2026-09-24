from .arrays_hashing import GENERATORS as ARRAYS_HASHING
from .binary_search import GENERATORS as BINARY_SEARCH
from .common import Generator
from .linked_list import GENERATORS as LINKED_LIST
from .sliding_window import GENERATORS as SLIDING_WINDOW
from .stack import GENERATORS as STACK
from .trees import GENERATORS as TREES
from .two_pointers import GENERATORS as TWO_POINTERS

GENERATORS: dict[str, Generator] = {
    **ARRAYS_HASHING,
    **TWO_POINTERS,
    **SLIDING_WINDOW,
    **STACK,
    **BINARY_SEARCH,
    **LINKED_LIST,
    **TREES,
}
