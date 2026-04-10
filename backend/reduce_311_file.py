#!/usr/bin/env python3
"""
Reduce the massive 311 reports CSV by keeping only essential columns
and filling null values with RAG-friendly placeholders
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Essential columns to keep
ESSENTIAL_COLUMNS = [
    # Core identifiers
    '_id',
    'folio',
    'organization_id',

    # Category/Type information
    'flag_category_id',
    'flag_category_name',
    'flag_subcategory_id',
    'flag_subcategory_name',
    'description',

    # Location data
    'location.type',
    'location.coordinates[0]',  # longitude
    'location.coordinates[1]',  # latitude
    'location_address',
    'location_geocode.formatted_address',

    # Status and priority
    'priority',
    'status',

    # Dates
    'date_created',
    'date_closed',

    # User information
    'user_added_id',
    'user_added_name',
    'user_added_lastname',
    'user_closed_id',
    'user_closed_name',
    'user_closed_lastname',
    'client_added_id',
    'client_added_name',
    'client_added_lastname',

    # Engagement metrics
    'like_user_count',
    'dislike_user_count',
    'like_client_count',
    'dislike_client_count',

    # File references (just the first few)
    'files_open[0]',
    'files_open[1]',
    'files_open[2]',

    # Labels (just the first few)
    'labels_text[0]',
    'labels_text[1]',
    'labels_text[2]',

    # Lagan details (non-array fields)
    'lagan_details.source_type',
    'lagan_details.priv',
    'lagan_details.anonymous',
]


def fill_311_null_values(df):
    """
    Fill null values with RAG-friendly placeholders specific to 311 data
    """
    print("Filling null values with appropriate placeholders...")

    # ID fields
    for col in ['_id', 'folio', 'organization_id', 'flag_category_id', 'flag_subcategory_id']:
        if col in df.columns:
            df[col] = df[col].fillna('Unknown')

    # Category/Name fields
    for col in ['flag_category_name', 'flag_subcategory_name']:
        if col in df.columns:
            df[col] = df[col].fillna('Unknown Category')

    # Description
    if 'description' in df.columns:
        df['description'] = df['description'].fillna('No description provided')

    # Location type
    if 'location.type' in df.columns:
        df['location.type'] = df['location.type'].fillna('Point')

    # Coordinates - fill with 0.0 (invalid coordinate that can be filtered)
    for col in ['location.coordinates[0]', 'location.coordinates[1]']:
        if col in df.columns:
            df[col] = df[col].fillna(0.0)

    # Addresses
    for col in ['location_address', 'location_geocode.formatted_address']:
        if col in df.columns:
            df[col] = df[col].fillna('Address Not Available')

    # Priority and Status
    if 'priority' in df.columns:
        df['priority'] = df['priority'].fillna('Normal')
    if 'status' in df.columns:
        df['status'] = df['status'].fillna('Unknown')

    # Dates
    for col in ['date_created', 'date_closed']:
        if col in df.columns:
            df[col] = df[col].fillna('Not Available')

    # User fields
    user_id_cols = ['user_added_id', 'user_closed_id', 'client_added_id']
    user_name_cols = ['user_added_name', 'user_closed_name', 'client_added_name']
    user_lastname_cols = ['user_added_lastname', 'user_closed_lastname', 'client_added_lastname']

    for col in user_id_cols:
        if col in df.columns:
            df[col] = df[col].fillna('Unknown')

    for col in user_name_cols:
        if col in df.columns:
            df[col] = df[col].fillna('Unknown')

    for col in user_lastname_cols:
        if col in df.columns:
            df[col] = df[col].fillna('Unknown')

    # Engagement counts
    count_cols = ['like_user_count', 'dislike_user_count', 'like_client_count', 'dislike_client_count']
    for col in count_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    # Files
    for i in range(3):
        col = f'files_open[{i}]'
        if col in df.columns:
            df[col] = df[col].fillna('No file')

    # Labels
    for i in range(3):
        col = f'labels_text[{i}]'
        if col in df.columns:
            df[col] = df[col].fillna('No label')

    # Lagan details
    if 'lagan_details.source_type' in df.columns:
        df['lagan_details.source_type'] = df['lagan_details.source_type'].fillna('Unknown')
    if 'lagan_details.priv' in df.columns:
        df['lagan_details.priv'] = df['lagan_details.priv'].fillna('Unknown')
    if 'lagan_details.anonymous' in df.columns:
        df['lagan_details.anonymous'] = df['lagan_details.anonymous'].fillna('Unknown')

    return df


def reduce_311_file(input_path, output_path):
    """
    Reduce 311 reports file by keeping only essential columns and filling nulls
    """
    print(f"Loading large CSV file (this may take a moment)...")
    print(f"Input: {input_path}")

    # Read the CSV
    df = pd.read_csv(input_path, low_memory=False)

    initial_size_mb = input_path.stat().st_size / (1024 * 1024)
    initial_rows = len(df)
    initial_cols = len(df.columns)

    print(f"\nOriginal file:")
    print(f"  Size: {initial_size_mb:.1f} MB")
    print(f"  Rows: {initial_rows:,}")
    print(f"  Columns: {initial_cols:,}")

    # Keep only columns that exist
    columns_to_keep = [col for col in ESSENTIAL_COLUMNS if col in df.columns]
    columns_not_found = [col for col in ESSENTIAL_COLUMNS if col not in df.columns]

    print(f"\nKeeping {len(columns_to_keep)} essential columns...")
    if columns_not_found:
        print(f"  Note: {len(columns_not_found)} columns not found in file (likely okay)")

    # Create reduced dataframe
    df_reduced = df[columns_to_keep].copy()

    # Clean the data
    print("Cleaning data...")

    # Standardize null representations
    df_reduced = df_reduced.replace(['NA', 'N/A', 'n/a', 'na', 'NaN', 'nan', '', ' ', 'null', 'NULL'], pd.NA)

    # Count nulls before filling
    nulls_before = df_reduced.isna().sum().sum()

    # Fill null values with RAG-friendly placeholders
    df_reduced = fill_311_null_values(df_reduced)

    # Count nulls after filling
    nulls_after = df_reduced.isna().sum().sum()
    nulls_filled = nulls_before - nulls_after

    # Remove rows where all values are null
    df_reduced = df_reduced.dropna(how='all')

    # Remove duplicate rows
    initial_reduced_rows = len(df_reduced)
    df_reduced = df_reduced.drop_duplicates()
    duplicates_removed = initial_reduced_rows - len(df_reduced)

    # Save reduced file
    print(f"Saving reduced file...")
    df_reduced.to_csv(output_path, index=False)

    final_size_mb = output_path.stat().st_size / (1024 * 1024)
    final_rows = len(df_reduced)
    final_cols = len(df_reduced.columns)

    print(f"\n{'='*80}")
    print(f"REDUCTION COMPLETE!")
    print(f"{'='*80}")
    print(f"\nReduced file:")
    print(f"  Size: {final_size_mb:.1f} MB ({initial_size_mb - final_size_mb:.1f} MB saved, {100 * (1 - final_size_mb/initial_size_mb):.1f}% reduction)")
    print(f"  Rows: {final_rows:,} ({initial_rows - final_rows:,} removed)")
    print(f"  Columns: {final_cols:,} ({initial_cols - final_cols:,} removed)")
    print(f"  Duplicates removed: {duplicates_removed:,}")
    print(f"  Null values filled: {nulls_filled:,}")
    print(f"  Remaining nulls: {nulls_after:,}")
    print(f"\nSaved to: {output_path.name}")
    print(f"{'='*80}\n")

    # Print column summary
    print("Columns kept:")
    for i, col in enumerate(columns_to_keep, 1):
        print(f"  {i:2d}. {col}")
    print()


def main():
    """Main function"""
    base_path = Path(__file__).parent
    input_file = base_path / "Data" / "ZIPCODE 78207" / "clean" / "311-reports-78207.csv"
    output_file = base_path / "Data" / "ZIPCODE 78207" / "clean" / "311-reports-78207-reduced.csv"

    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        return

    print("\n" + "="*80)
    print("311 REPORTS FILE SIZE REDUCTION - RAG-OPTIMIZED")
    print("="*80 + "\n")

    reduce_311_file(input_file, output_file)

    print("✓ All null values have been replaced with RAG-friendly placeholders!")
    print("✓ Use the reduced file for better performance and clearer data.\n")


if __name__ == "__main__":
    main()
