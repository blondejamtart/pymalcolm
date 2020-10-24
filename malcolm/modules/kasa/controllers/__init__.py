# Expose a nice namespace
from malcolm.core import submodule_all

from .KasaController import KasaController

__all__ = submodule_all(globals())
