#!/usr/bin/env python3
"""
Convert shapefiles to cleaned CSV format with RAG-friendly null filling
"""

import pandas as pd
import geopandas as gpd
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


def fill_null_values_spatial(gdf):
    """
    Fill null values in GeoDataFrame with RAG-friendly placeholders
    """
    if gdf.empty:
        return gdf

    gdf_filled = gdf.copy()

    for col in gdf_filled.columns:
        # Skip geometry column
        if col == 'geometry':
            continue

        col_lower = col.lower()
        dtype = gdf_filled[col].dtype

        # Check how many nulls in this column
        null_count = gdf_filled[col].isna().sum()
        if null_count == 0:
            continue

        # Numeric columns
        if pd.api.types.is_numeric_dtype(dtype):
            if any(keyword in col_lower for keyword in ['id', 'fid', 'objectid']):
                gdf_filled[col] = gdf_filled[col].fillna(0)
            elif any(keyword in col_lower for keyword in ['area', 'length', 'perimeter']):
                gdf_filled[col] = gdf_filled[col].fillna(0.0)
            else:
                gdf_filled[col] = gdf_filled[col].fillna(0)

        # String/Object columns
        elif pd.api.types.is_object_dtype(dtype):
            if any(keyword in col_lower for keyword in ['name', 'label', 'desc', 'type']):
                gdf_filled[col] = gdf_filled[col].fillna('Unknown')
            elif any(keyword in col_lower for keyword in ['district', 'zone', 'region']):
                gdf_filled[col] = gdf_filled[col].fillna('Unknown')
            else:
                gdf_filled[col] = gdf_filled[col].fillna('Unknown')

    return gdf_filled


def shapefile_to_csv(shp_path, output_path, include_geometry=True):
    """
    Convert shapefile to CSV with cleaned data
    """
    print(f"Converting: {shp_path.name}")
    try:
        # Read shapefile
        gdf = gpd.read_file(shp_path)

        initial_rows = len(gdf)
        initial_cols = len(gdf.columns)

        # Standardize null representations
        for col in gdf.columns:
            if col != 'geometry':
                gdf[col] = gdf[col].replace(['NA', 'N/A', 'n/a', 'na', '', ' ', 'null', 'NULL'], pd.NA)

        # Count nulls before filling
        nulls_before = gdf.drop(columns=['geometry']).isna().sum().sum() if 'geometry' in gdf.columns else gdf.isna().sum().sum()

        # Fill null values
        gdf = fill_null_values_spatial(gdf)

        # Count nulls after filling
        nulls_after = gdf.drop(columns=['geometry']).isna().sum().sum() if 'geometry' in gdf.columns else gdf.isna().sum().sum()
        nulls_filled = nulls_before - nulls_after

        # Remove duplicates
        initial_gdf_rows = len(gdf)
        gdf = gdf.drop_duplicates()
        duplicates_removed = initial_gdf_rows - len(gdf)

        # Convert to CSV-friendly format
        if include_geometry:
            # Add centroid coordinates for point reference
            gdf['centroid_lon'] = gdf.geometry.centroid.x
            gdf['centroid_lat'] = gdf.geometry.centroid.y
            # Add bounding box
            gdf['bbox_minx'] = gdf.geometry.bounds['minx']
            gdf['bbox_miny'] = gdf.geometry.bounds['miny']
            gdf['bbox_maxx'] = gdf.geometry.bounds['maxx']
            gdf['bbox_maxy'] = gdf.geometry.bounds['maxy']
            # Convert geometry to WKT for CSV storage
            gdf['geometry_wkt'] = gdf.geometry.to_wkt()

        # Drop the geometry column for CSV export
        df = gdf.drop(columns=['geometry'])

        # Save to CSV
        df.to_csv(output_path, index=False)

        final_rows = len(df)
        final_cols = len(df.columns)

        print(f"  ✓ Rows: {initial_rows} → {final_rows} (removed {initial_rows - final_rows})")
        print(f"  ✓ Cols: {initial_cols} → {final_cols} (geometry expanded to WKT + coordinates)")
        print(f"  ✓ Duplicates removed: {duplicates_removed}")
        print(f"  ✓ Null values filled: {nulls_filled}")
        print(f"  ✓ Saved to: {output_path.name}\n")

        return True

    except Exception as e:
        print(f"  ✗ Error: {str(e)}\n")
        return False


def clean_gis_shapefiles():
    """
    Find and clean all shapefiles in GIS subdirectories
    """
    base_path = Path(__file__).parent / "Data" / "GIS"

    # Directories to search
    search_dirs = [
        base_path / "bexar_county",
        base_path / "bexar_watersheds",
        base_path / "CouncilDistricts",
    ]

    # Also search for any other shapefiles in GIS root
    search_dirs.append(base_path)

    all_shapefiles = []
    for search_dir in search_dirs:
        if search_dir.exists():
            shapefiles = list(search_dir.glob("*.shp"))
            all_shapefiles.extend(shapefiles)

    # Remove duplicates
    all_shapefiles = list(set(all_shapefiles))

    if not all_shapefiles:
        print("No shapefiles found to clean.")
        return

    print(f"\n{'='*80}")
    print(f"SHAPEFILE CLEANING - RAG-OPTIMIZED")
    print(f"Found {len(all_shapefiles)} shapefiles to convert")
    print(f"{'='*80}\n")

    cleaned_count = 0

    for shp_file in sorted(all_shapefiles):
        # Create output filename in same directory
        output_name = f"cleaned_{shp_file.stem}.csv"
        output_path = shp_file.parent / output_name

        if shapefile_to_csv(shp_file, output_path):
            cleaned_count += 1

    print(f"{'='*80}")
    print(f"SUMMARY: Converted {cleaned_count}/{len(all_shapefiles)} shapefiles to CSV")
    print(f"{'='*80}\n")


def main():
    """Main function"""
    try:
        import geopandas
        print("\n" + "="*80)
        print("SHAPEFILE TO CSV CONVERTER - RAG-OPTIMIZED")
        print("="*80)

        clean_gis_shapefiles()

        print("✓ All shapefiles have been converted to CSV with null filling!")
        print("✓ Geometry data preserved as WKT + centroid coordinates + bounding boxes\n")

    except ImportError:
        print("\n" + "="*80)
        print("ERROR: geopandas not installed")
        print("="*80)
        print("\nInstalling geopandas...")
        import subprocess
        subprocess.run(['pip3', 'install', 'geopandas'], check=True)
        print("\n✓ geopandas installed. Please run this script again.\n")


if __name__ == "__main__":
    main()
