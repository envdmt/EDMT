edmt
====

.. py:module:: edmt


Submodules
----------

.. toctree::
   :maxdepth: 1

   /autoapi/edmt/analysis/index
   /autoapi/edmt/base/index
   /autoapi/edmt/contrib/index
   /autoapi/edmt/conversion/index
   /autoapi/edmt/mapping/index
   /autoapi/edmt/models/index
   /autoapi/edmt/plotting/index
   /autoapi/edmt/workflow/index




Package Contents
----------------

.. py:function:: list_functions(module_name: str = 'edmt') -> None

   Inspect and print all functions in the specified module and its submodules.

   :param module_name: The name of the root module to inspect (default: "edmt").
   :type module_name: str, optional


.. py:function:: init(silent=False, force=False)

   Initializes the environment with EDMT-specific customizations.

   Parameters:
   ------------
           silent : bool, optional
               Suppresses console output (default is False).
           force : bool, optional
               Forces re-initialization even if already initialized (default is False).


