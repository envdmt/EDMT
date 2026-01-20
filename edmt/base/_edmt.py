import inspect
import pkgutil
import edmt

import inspect
import pkgutil
from types import ModuleType

def list_functions(module_name: str = "edmt") -> None:
    """
    Inspect and print all functions in the specified module and its submodules.

    Parameters
    ----------
    module_name : str, optional
        The name of the root module to inspect (default: "edmt").

    """
    try:
        root_module = __import__(module_name, fromlist=[''])
    except ImportError as e:
        print(f"Error: Could not import module '{module_name}': {e}")
        return

    edmt_functions = [
        name for name, obj in inspect.getmembers(root_module)
        if inspect.isfunction(obj) and obj.__module__ == root_module.__name__
    ]

    print(f"Functions directly in {module_name} module:")
    if edmt_functions:
        for func_name in sorted(edmt_functions):
            print(f"- {func_name}")
    else:
        print("  No functions found.")

    print(f"\n--- Submodules of {module_name} ---")
    if not hasattr(root_module, '__path__'):
        print("  Module has no submodules (not a package).")
        return

    for importer, modname, ispkg in pkgutil.walk_packages(root_module.__path__, prefix=f"{module_name}."):
        print(f"- {modname}")
        try:
            submodule = __import__(modname, fromlist=[''])

            # Only include functions defined in this submodule (not imported)
            submodule_functions = [
                name for name, obj in inspect.getmembers(submodule)
                if inspect.isfunction(obj) and getattr(obj, '__module__', None) == modname
            ]

            if submodule_functions:
                print(f"  Functions in {modname}:")
                for func_name in sorted(submodule_functions):
                    print(f"  - {func_name}")
            else:
                print(f"  No functions found directly in {modname}.")

        except Exception as e:
            print(f"  Could not inspect submodule {modname}: {e}")