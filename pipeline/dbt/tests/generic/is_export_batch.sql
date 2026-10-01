{% test is_export_batch(model, column_name) %}
select {{ column_name }}
from {{ model }}
where {{ column_name }} is null
   or {{ column_name }} not in (select export_batch_id from {{ ref('stg_erp__export_batch') }})
{% endtest %}
