import pandas as pd

try:
    df = pd.read_excel("Book1.xlsx", header=None)
    print("Row 0:", df.iloc[0].tolist())
    print("Row 1:", df.iloc[1].tolist())
    print("Row 2:", df.iloc[2].tolist())
except Exception as e:
    print("Error:", e)
