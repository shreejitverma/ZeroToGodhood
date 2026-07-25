"""Listing 31.2 - __init_subclass__ and __set_name__ (PEP 487): most of what
metaclasses were used for, without a metaclass.

Metaclasses are powerful but heavy: they change a class's type, they do not
compose (two metaclasses conflict), and they are hard to read. PEP 487 added two
hooks that cover the common cases without a metaclass. __init_subclass__ runs on
the BASE class each time it is subclassed (subclass registration, validation).
__set_name__ tells a descriptor its attribute name at class creation (Chapter 4).
"""


# --- __init_subclass__: the base is notified of each subclass ---
class Plugin:
    registry = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        Plugin.registry.append(cls.__name__)


class AudioPlugin(Plugin):
    pass


class VideoPlugin(Plugin):
    pass


print("--- __init_subclass__ registers subclasses, no metaclass needed ---")
print("  Plugin.registry:", Plugin.registry)


# --- __init_subclass__ can also take keyword arguments from the class line ---
class Validated:
    def __init_subclass__(cls, *, required, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.required_field = required


class Config(Validated, required="api_key"):
    pass


print()
print("--- __init_subclass__ accepts keywords from the class definition ---")
print("  Config.required_field:", Config.required_field)


# --- __set_name__: a descriptor learns its own name ---
class Named:
    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, owner=None):
        return f"I am '{self.name}'"


class Host:
    first = Named()
    second = Named()


print()
print("--- __set_name__ gives a descriptor its attribute name at class creation ---")
print("  Host().first :", Host().first)
print("  Host().second:", Host().second)
print()
print("Reach for __init_subclass__ and __set_name__ first; they compose (unlike")
print("metaclasses), they are far more readable, and they cover subclass")
print("registration, validation, and descriptor naming, the bulk of what")
print("metaclasses were historically used for.")
