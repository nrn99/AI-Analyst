from openpyxl import Workbook
from pathlib import Path

wb = Workbook()
ws = wb.active
ws.append(["Date", "Description", "Amount", "Category"])
ws.append(["2024-01-01", "Browser Test", -25.00, "Dining"])  # Amount as number

# Save in same directory as script
output_path = Path(__file__).parent / "browser_test.xlsx"
wb.save(output_path)
print(f"Verified: {output_path} created")
