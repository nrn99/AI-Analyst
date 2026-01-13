from openpyxl import Workbook
import os

wb = Workbook()
ws = wb.active
ws.append(["Date", "Description", "Amount", "Category"])
ws.append(["2024-01-01", "Browser Test", "-25.00", "Dining"])
wb.save("browser_test.xlsx")
print("Verified: browser_test.xlsx created")
