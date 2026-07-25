"""Stands in for an expensive-to-import module. Records that its body ran."""
import builtins
builtins._lazypkg_heavy_loaded = True
DATA = [i * i for i in range(1000)]
