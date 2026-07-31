"""Listing 295.1 - The frontier, and the constant beneath it: the data model endures.

Nineteen volumes of releases - from ABC's inheritance to the no-GIL build - and
through all of it one thing barely moved: the DATA MODEL. 'Everything is an
object' (Chapter 216) and 'behaviour is defined by protocols (dunder methods),
not by type' (the duck-typing thesis) are as true in 3.14 as they were in 1991.
A class that implements __len__, __iter__, __getitem__, __eq__, and __bool__
plugs into len(), for, in, [], ==, and truthiness EXACTLY like a builtin - because
those operators dispatch to the protocol, not to a fixed set of types. That
stability is why decades-old idioms still run unchanged, and why learning the
model once pays off across every release. This closing listing demonstrates the
constant core on today's interpreter. Verified on current interpreters.
"""


class Deck:
    """A custom type that participates in the core protocols - like a builtin."""
    def __init__(self, cards):
        self._cards = list(cards)

    def __len__(self):                           # -> len(deck)
        return len(self._cards)

    def __getitem__(self, i):                    # -> deck[i], and slicing, and `in`
        return self._cards[i]

    def __iter__(self):                          # -> for card in deck
        return iter(self._cards)

    def __eq__(self, other):                     # -> deck == other
        return isinstance(other, Deck) and self._cards == other._cards

    def __bool__(self):                          # -> truthiness of the deck
        return len(self._cards) > 0

    def __repr__(self):
        return f"Deck({self._cards})"


def main() -> None:
    deck = Deck(["A", "K", "Q", "J"])

    print("--- everything is an object, with a type (Chapter 216) ---")
    print(f"  the deck is an object : {isinstance(deck, object)}")
    print(f"  functions are objects too : {isinstance(len, object)}")
    print(f"  even a class is an object : {isinstance(Deck, object)}")
    print("  the oldest thesis in the language - EVERYTHING is a first-class")
    print("  object with a type - is unchanged after 19 volumes of releases")

    print("--- len() dispatches to __len__: protocol, not type ---")
    print(f"  len(deck) : {len(deck)}")
    print("  len() does not check 'is this a list?' - it calls __len__. any object")
    print("  that defines it has a length. this is duck typing at the operator")
    print("  level, and it has worked this way since the beginning")

    print("--- for/in/[] all come from __iter__ and __getitem__ ---")
    print(f"  list(deck)       : {list(deck)}   (for uses __iter__)")
    print(f"  deck[0], deck[-1]: {deck[0]}, {deck[-1]}   (__getitem__)")
    print(f"  deck[1:3]        : {deck[1:3]}   (slicing, same protocol)")
    print(f"  'Q' in deck      : {'Q' in deck}   (membership via iteration)")
    print("  iteration, indexing, slicing, and membership - the whole sequence")
    print("  experience - fall out of two dunder methods. the custom Deck behaves")
    print("  like a builtin because the operators target the PROTOCOL")

    print("--- == and truthiness come from __eq__ and __bool__ (Chapter 229) ---")
    print(f"  deck == Deck(['A','K','Q','J']) : {deck == Deck(['A', 'K', 'Q', 'J'])}")
    print(f"  bool(deck)        : {bool(deck)}   (non-empty -> truthy)")
    print(f"  bool(Deck([]))    : {bool(Deck([]))}   (empty -> falsy)")
    print(f"  `if deck:` takes the branch : {'yes' if deck else 'no'}")
    print("  equality and truthiness are protocols too. `if deck:` asks the")
    print("  object, exactly as `if some_list:` does - one model, every type")

    print("--- the payoff: learn the model once, use it forever ---")
    print("  the protocols shown here predate almost everything in this book and")
    print("  will outlast the frontier chapters. f-strings, pattern matching, and")
    print("  free-threading are all built ON this model; none of them changed it.")
    print("  that is why a Python program from 20 years ago still reads clearly")

    print("--- the constraint answered ---")
    print("  the whole timeline - 19 volumes of change - rests on a data model")
    print("  that barely moved: everything is an object, and behaviour comes from")
    print("  protocols any type can implement. a custom class plugs into len, for,")
    print("  in, [], ==, and truthiness like a builtin because operators dispatch")
    print("  to dunder methods, not to fixed types. the frontier moves; the core holds")


if __name__ == "__main__":
    main()
