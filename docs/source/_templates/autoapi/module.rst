{{ fullname | replace("edmt.", "EDMT.") | capitalize }}
{{ "=" * (fullname | replace("edmt.", "EDMT.") | capitalize | length) }}

.. automodule:: {{ fullname }}
   :no-members:

{% block attributes %}
{% if attributes %}
Attributes
----------

.. autosummary::
   :toctree:
   {% for item in attributes %}
   {{ fullname }}.{{ item }}
   {% endfor %}
{% endif %}
{% endblock %}



{% block functions %}
{% if functions %}
Functions
---------

.. autosummary::
   :toctree:
   {% for item in functions %}
   {{ fullname }}.{{ item }}
   {% endfor %}
{% endif %}
{% endblock %}

{% block classes %}
{% if classes %}
Classes
-------

.. autosummary::
   :toctree:
   {% for item in classes %}
   {{ fullname }}.{{ item }}
   {% endfor %}
{% endif %}
{% endblock %}