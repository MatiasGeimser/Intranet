import pandas as pd
import requests

data = {
    'Nombre Comercial': ['Empresa A', 'Empresa A', 'Empresa B', 'Empresa B'],
    'Telefono': ['12345678', '12345678', '12345678', '87654321']
}
df = pd.DataFrame(data)
df.to_excel('test_commercial.xlsx', index=False)

with open('test_commercial.xlsx', 'rb') as f:
    response = requests.post('http://localhost:8000/api/duplicate-phones/process-commercial', files={'file': f})

print(response.json())
