Admin import zip (demo)
=======================

offers-demo.xlsx          пример каталога (листы offers + items)
import-offers-from-xlsx.py  Excel → offers.yaml + vehicle_profiles.yaml

1. Редактировать offers-demo.xlsx
2. python import-offers-from-xlsx.py --input offers-demo.xlsx --offers-out offers.yaml --profiles-out vehicle_profiles.yaml
3. Скопировать YAML в Bridge catalog/ или tenants/demo/

См. catalog/import/README.md
