{{ fullname | escape | underline }}

.. currentmodule:: {{ fullname }}

{% block body %}

{% if classes %}
Classes
-------

.. autosummary::
   :toctree:
   :template: class.rst

   {% for class in classes %}
   {{ class }}
   {% endfor %}

{% endif %}

{% if functions %}
Functions
---------

.. autosummary::
   :toctree:
   :template: function.rst

   {% for function in functions %}
   {{ function }}
   {% endfor %}

{% endif %}

{% if attributes %}
Attributes
----------

.. autosummary::
   :toctree:
   :template: attribute.rst

   {% for attribute in attributes %}
   {{ attribute }}
   {% endfor %}

{% endif %}

{% endblock %}

.. toctree::
   :hidden:

   ../index
   ../installation
   ../autoapi/index