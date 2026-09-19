"""patches loader plugin"""

import importlib
from functools import wraps
from inspect import signature
from pathlib import Path
from typing import Any


def patch_method(module, func_name: str, initial: bool = False):
    """Decorator to patch a function in a module/class by name."""
    if not hasattr(module, func_name):
        raise AttributeError(
            f"Module '{module.__name__}' has no attribute '{func_name}'"
        )
    original_func = getattr(module, func_name)

    if not callable(original_func):
        raise TypeError(
            f"Attribute '{func_name}' in '{module.__name__}' is not callable"
        )

    def decorator(new_func):
        @wraps(original_func)
        def wrapper(*args, **kwargs) -> Any:
            if initial:
                # if this is true, we'll call the original function initially.
                wrapper.result = original_func(*args, **kwargs)
            return new_func(*args, **kwargs)

        # incase we need the original function
        wrapper.original = original_func

        # patch it into the module
        setattr(module, func_name, wrapper)

        return wrapper  # just to be safe.

    return decorator


def load():
    """automatically imports patch files in the directory."""
    package_dir = Path(__file__).parent
    for file in package_dir.glob("*.py"):
        if file.stem == "__init__":
            continue
        module_name = f"{__package__}.{file.stem}"
        try:
            importlib.import_module(module_name)
        except ImportError:
            print(f"⚠️ Failed to load patch file {file.stem}")
