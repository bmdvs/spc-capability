{% test in_range(model, column_name, min_value=none, max_value=none) %}
select {{ column_name }}
from {{ model }}
where {{ column_name }} is not null
  and (
    {% if min_value is not none %}{{ column_name }} < {{ min_value }}{% else %}false{% endif %}
    or {% if max_value is not none %}{{ column_name }} > {{ max_value }}{% else %}false{% endif %}
  )
{% endtest %}
