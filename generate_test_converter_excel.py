from openpyxl import Workbook

wb = Workbook()
ws = wb.active
ws.title = "Contactos"
headers = ["Nombre", "Apellido", "Correo", "Telefono", "Ciudad"]
ws.append(headers)

data = [
    ["Juan", "Perez", "juan@example.com", "123456", "Bogota"],
    ["Maria", "Gomez", "maria@example.com", "789101", "Medellin"],
    ["Carlos", "Rodriguez", "carlos@example.com", "112131", "Cali"],
    ["Ana", "Martinez", "ana@example.com", "415161", "Barranquilla"],
]

for row in data:
    ws.append(row)

wb.save("c:\\Intranet\\test_converter.xlsx")
print("test_converter.xlsx generado con éxito.")
