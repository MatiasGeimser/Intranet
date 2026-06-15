import requests
import pandas as pd

df1 = pd.DataFrame({'Telefono': ['11111111', '22222222', '33333333']})
df2 = pd.DataFrame({'Telefono': ['22222222', '44444444']})

df1.to_excel('test_b1.xlsx', index=False)
df2.to_excel('test_b2.xlsx', index=False)

with open('test_b1.xlsx', 'rb') as f1, open('test_b2.xlsx', 'rb') as f2:
    response = requests.post('http://localhost:8000/api/duplicate-phones/process', files={'file': f1, 'file2': f2})

print(response.json())
