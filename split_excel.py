import os
import pandas as pd
from pathlib import Path

def split_multi_sheet_excel():
    excel_path = r"C:\Users\ACER\OneDrive\Desktop\combined_excel.xlsx"
    target_dir = Path(r"C:\Users\ACER\OneDrive\Desktop\nepse-ai-app\backend\data\raw")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    print("Opening Excel workbook wrapper...")
    # Using ExcelFile avoids loading all sheets into memory at once
    xl = pd.ExcelFile(excel_path)
    sheet_names = xl.sheet_names
    
    print(f"Found {len(sheet_names)} daily trading sheets to process.")
    
    processed_count = 0
    for sheet in sheet_names:
        # Normalize sheet name format from '2026_07_07' to '2026-07-07'
        normalized_date = sheet.replace('_', '-')
        
        # Verify the sheet name looks like a date before processing
        # (This avoids processing summary tabs or default Sheet1 tabs)
        parts = normalized_date.split('-')
        if len(parts) != 3 or not parts[0].isdigit():
            print(f"Skipping sheet '{sheet}': Does not match a YYYY_MM_DD date format.")
            continue
            
        print(f"Extracting trading day: {normalized_date}...")
        
        # Read just this single sheet
        df_sheet = pd.read_excel(xl, sheet_name=sheet)
        
        # Target path: backend/data/raw/YYYY-MM-DD.csv
        csv_filename = target_dir / f"{normalized_date}.csv"
        
        # Save to CSV without the index row
        df_sheet.to_csv(csv_filename, index=False)
        processed_count += 1
        
    print(f"\nExtraction complete! Generated {processed_count} CSV files in {target_dir}")

if __name__ == "__main__":
    split_multi_sheet_excel()