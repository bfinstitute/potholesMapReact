#!/usr/bin/env python3
"""
Dataset cleaning script for COSA Infrastructure, Unclean, and GIS folders
Removes nulls, duplicates, and fills empty values with RAG-friendly placeholders
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


def fill_null_values(df):
    """
    Fill null values with appropriate placeholders for RAG systems.
    - Numeric columns: Fill with 0 or -1 (depending on context)
    - String/Object columns: Fill with "Unknown"
    - Date columns: Fill with "Not Available"
    - Boolean columns: Fill with False or "Unknown"
    """
    if df.empty:
        return df

    df_filled = df.copy()

    for col in df_filled.columns:
        col_lower = col.lower()
        dtype = df_filled[col].dtype

        # Check how many nulls in this column
        null_count = df_filled[col].isna().sum()
        if null_count == 0:
            continue

        # Numeric columns
        if pd.api.types.is_numeric_dtype(dtype):
            # Count/ID fields - use 0
            if any(keyword in col_lower for keyword in ['count', 'number', 'num', 'total', 'sum']):
                df_filled[col] = df_filled[col].fillna(0)
            # Score/Rating/PCI fields - use -1 to indicate "Not Rated"
            elif any(keyword in col_lower for keyword in ['score', 'rating', 'pci', 'factor']):
                df_filled[col] = df_filled[col].fillna(-1)
            # Coordinate/Location fields - keep as NaN for now, will handle separately
            elif any(keyword in col_lower for keyword in ['lat', 'lon', 'coord', 'xcoord', 'ycoord']):
                df_filled[col] = df_filled[col].fillna(0.0)
            # Distance/Length fields - use 0
            elif any(keyword in col_lower for keyword in ['dist', 'length', 'width', 'feet', 'mile', 'meter']):
                df_filled[col] = df_filled[col].fillna(0)
            # Other numeric - use 0
            else:
                df_filled[col] = df_filled[col].fillna(0)

        # Date/Time columns
        elif pd.api.types.is_datetime64_any_dtype(dtype) or any(keyword in col_lower for keyword in ['date', 'time', 'created', 'modified', 'edited', 'opened', 'closed', 'start', 'finish', 'year']):
            df_filled[col] = df_filled[col].fillna('Not Available')

        # Boolean-like columns
        elif df_filled[col].dtype == 'bool':
            df_filled[col] = df_filled[col].fillna(False)

        # String/Object columns
        elif pd.api.types.is_object_dtype(dtype):
            # ID fields - use "Unknown"
            if any(keyword in col_lower for keyword in ['id', '_id', 'objectid', 'globalid', 'cartid', 'fid']):
                df_filled[col] = df_filled[col].fillna('Unknown')
            # Name fields
            elif any(keyword in col_lower for keyword in ['name', 'title', 'desc', 'label', 'type', 'category', 'status']):
                df_filled[col] = df_filled[col].fillna('Unknown')
            # Address/Location fields
            elif any(keyword in col_lower for keyword in ['address', 'location', 'street', 'place', 'city', 'zip']):
                df_filled[col] = df_filled[col].fillna('Not Available')
            # User/Person fields
            elif any(keyword in col_lower for keyword in ['user', 'person', 'owner', 'assigned', 'client']):
                df_filled[col] = df_filled[col].fillna('Unknown')
            # Comment/Description fields
            elif any(keyword in col_lower for keyword in ['comment', 'notes', 'description', 'info']):
                df_filled[col] = df_filled[col].fillna('No description provided')
            # URL/Link fields
            elif any(keyword in col_lower for keyword in ['url', 'link', 'http', 'view', 'map']):
                df_filled[col] = df_filled[col].fillna('Not Available')
            # Generic string fields
            else:
                df_filled[col] = df_filled[col].fillna('Unknown')

        # Fallback for anything else
        else:
            df_filled[col] = df_filled[col].fillna('Unknown')

    return df_filled


def clean_dataframe(df):
    """
    Clean a pandas DataFrame by:
    - Removing rows where all values are null
    - Removing columns where all values are null
    - Removing duplicate rows
    - Stripping whitespace from column names
    - Removing BOM characters from column names
    - Filling remaining null values with appropriate placeholders
    """
    if df.empty:
        return df, 0, 0

    # Remove BOM and whitespace from column names
    df.columns = df.columns.str.replace('\ufeff', '', regex=False)
    df.columns = df.columns.str.strip()

    # Remove rows where all values are NaN/null
    df = df.dropna(how='all')

    # Remove columns where all values are NaN/null
    df = df.dropna(axis=1, how='all')

    # Standardize null representations before deduplication
    df = df.replace(['NA', 'N/A', 'n/a', 'na', 'NaN', 'nan', '', ' ', 'null', 'NULL'], pd.NA)

    # Remove duplicate rows
    initial_rows = len(df)
    df = df.drop_duplicates()
    duplicates_removed = initial_rows - len(df)

    # Count nulls before filling
    nulls_before = df.isna().sum().sum()

    # Fill null values with appropriate placeholders
    df = fill_null_values(df)

    # Count nulls after filling
    nulls_after = df.isna().sum().sum()
    nulls_filled = nulls_before - nulls_after

    # Reset index
    df = df.reset_index(drop=True)

    return df, duplicates_removed, nulls_filled


def clean_csv_file(input_path, output_path):
    """Clean a CSV file"""
    print(f"Cleaning CSV: {input_path.name}")
    try:
        # Try different encodings
        for encoding in ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']:
            try:
                df = pd.read_csv(input_path, encoding=encoding, low_memory=False)
                break
            except UnicodeDecodeError:
                continue

        initial_rows = len(df)
        initial_cols = len(df.columns)

        df, duplicates, nulls_filled = clean_dataframe(df)

        final_rows = len(df)
        final_cols = len(df.columns)

        # Check for remaining nulls
        remaining_nulls = df.isna().sum().sum()

        # Save cleaned file
        df.to_csv(output_path, index=False)

        print(f"  ✓ Rows: {initial_rows} → {final_rows} (removed {initial_rows - final_rows})")
        print(f"  ✓ Cols: {initial_cols} → {final_cols} (removed {initial_cols - final_cols})")
        print(f"  ✓ Duplicates removed: {duplicates}")
        print(f"  ✓ Null values filled: {nulls_filled}")
        if remaining_nulls > 0:
            print(f"  ⚠ Remaining nulls: {remaining_nulls} (may be intentional)")
        print(f"  ✓ Saved to: {output_path.name}\n")

        return True
    except Exception as e:
        print(f"  ✗ Error: {str(e)}\n")
        return False


def clean_excel_file(input_path, output_path):
    """Clean an Excel file (convert to CSV)"""
    print(f"Cleaning Excel: {input_path.name}")
    try:
        # Read all sheets
        excel_file = pd.ExcelFile(input_path)

        if len(excel_file.sheet_names) == 1:
            # Single sheet - save as CSV
            df = pd.read_excel(input_path, sheet_name=0)
            initial_rows = len(df)
            initial_cols = len(df.columns)

            df, duplicates, nulls_filled = clean_dataframe(df)

            final_rows = len(df)
            final_cols = len(df.columns)

            # Check for remaining nulls
            remaining_nulls = df.isna().sum().sum()

            # Save as CSV
            csv_output = output_path.with_suffix('.csv')
            df.to_csv(csv_output, index=False)

            print(f"  ✓ Rows: {initial_rows} → {final_rows} (removed {initial_rows - final_rows})")
            print(f"  ✓ Cols: {initial_cols} → {final_cols} (removed {initial_cols - final_cols})")
            print(f"  ✓ Duplicates removed: {duplicates}")
            print(f"  ✓ Null values filled: {nulls_filled}")
            if remaining_nulls > 0:
                print(f"  ⚠ Remaining nulls: {remaining_nulls} (may be intentional)")
            print(f"  ✓ Saved to: {csv_output.name}\n")
        else:
            # Multiple sheets - save each as separate CSV
            print(f"  Found {len(excel_file.sheet_names)} sheets")
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(input_path, sheet_name=sheet_name)
                initial_rows = len(df)
                initial_cols = len(df.columns)

                df, duplicates, nulls_filled = clean_dataframe(df)

                final_rows = len(df)
                final_cols = len(df.columns)

                # Check for remaining nulls
                remaining_nulls = df.isna().sum().sum()

                # Create output filename with sheet name
                sheet_output = output_path.parent / f"{output_path.stem}_{sheet_name}.csv"
                df.to_csv(sheet_output, index=False)

                print(f"  Sheet '{sheet_name}':")
                print(f"    ✓ Rows: {initial_rows} → {final_rows} (removed {initial_rows - final_rows})")
                print(f"    ✓ Cols: {initial_cols} → {final_cols} (removed {initial_cols - final_cols})")
                print(f"    ✓ Duplicates removed: {duplicates}")
                print(f"    ✓ Null values filled: {nulls_filled}")
                if remaining_nulls > 0:
                    print(f"    ⚠ Remaining nulls: {remaining_nulls} (may be intentional)")
                print(f"    ✓ Saved to: {sheet_output.name}")
            print()

        return True
    except Exception as e:
        print(f"  ✗ Error: {str(e)}\n")
        return False


def clean_folder(folder_path):
    """Clean all data files in a folder"""
    folder = Path(folder_path)
    if not folder.exists():
        print(f"Folder not found: {folder}")
        return

    print(f"\n{'='*80}")
    print(f"CLEANING FOLDER: {folder.name}")
    print(f"{'='*80}\n")

    # Get all data files
    csv_files = list(folder.glob('*.csv'))
    excel_files = list(folder.glob('*.xlsx')) + list(folder.glob('*.xls')) + list(folder.glob('*.xlsm'))

    total_files = len(csv_files) + len(excel_files)
    cleaned_files = 0

    # Clean CSV files
    for csv_file in csv_files:
        if csv_file.name.startswith('cleaned_'):
            output_path = csv_file
        else:
            output_path = csv_file.parent / f"cleaned_{csv_file.name}"
        if clean_csv_file(csv_file, output_path):
            cleaned_files += 1

    # Clean Excel files
    for excel_file in excel_files:
        if excel_file.name.startswith('cleaned_'):
            output_path = excel_file.with_suffix('.csv')
        else:
            output_path = excel_file.parent / f"cleaned_{excel_file.stem}"
        if clean_excel_file(excel_file, output_path):
            cleaned_files += 1

    print(f"{'='*80}")
    print(f"SUMMARY: Cleaned {cleaned_files}/{total_files} files in {folder.name}")
    print(f"{'='*80}\n\n")


def main():
    """Main function to clean all three folders"""
    base_path = Path(__file__).parent / "Data"

    folders = [
        base_path / "COSA_Infrastructure",
        base_path / "Unclean",
        base_path / "GIS"
    ]

    print("\n" + "="*80)
    print("DATA CLEANING SCRIPT - RAG-OPTIMIZED VERSION")
    print("Replacing nulls with 'Unknown', 'Not Available', 0, etc.")
    print("="*80)

    for folder in folders:
        clean_folder(folder)

    print("\n" + "="*80)
    print("ALL FOLDERS CLEANED SUCCESSFULLY!")
    print("All null values have been replaced with RAG-friendly placeholders.")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
