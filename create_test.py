import openpyxl
from app.api.endpoints.duplicate_phones import TEMP_DIR
import os

wb = openpyxl.Workbook()
ws = wb.active
ws.append(['Nombre', 'Teléfono', 'Fecha'])
ws.append(['Juan', '12345678 / 87654321', '2023-01-01'])
ws.append(['Pedro', '12345678', '2023-01-02'])
ws.append(['Maria', '55555555', '2023-01-03'])

test_file = os.path.join(TEMP_DIR, 'test_file.xlsx')
wb.save(test_file)
print(f'Test file saved to {test_file}')
