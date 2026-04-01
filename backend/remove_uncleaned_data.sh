#!/bin/bash

echo "=============================================================================="
echo "REMOVING UNCLEANED DATA FILES"
echo "=============================================================================="
echo ""

# Function to remove files
remove_files() {
    local pattern="$1"
    local description="$2"
    
    echo "Removing: $description"
    find Data -name "$pattern" -type f ! -name "cleaned_*" ! -name "*reduced*" -print -delete 2>/dev/null | while read file; do
        echo "  ✗ Deleted: $file"
    done
}

# Remove original CSV files that have cleaned versions
echo "=== COSA_Infrastructure folder ==="
cd Data/COSA_Infrastructure 2>/dev/null && {
    for file in *.csv; do
        if [ -f "cleaned_$file" ] && [[ "$file" != cleaned_* ]]; then
            echo "  ✗ Removing: $file"
            rm -f "$file"
        fi
    done
    cd ../..
}

echo ""
echo "=== Unclean folder ==="
cd Data/Unclean 2>/dev/null && {
    for file in *.xlsx *.xls *.xlsm; do
        [ -e "$file" ] || continue
        base="${file%.*}"
        if [ -f "cleaned_${base}.csv" ] || ls "cleaned_${base}_"*.csv 1> /dev/null 2>&1; then
            echo "  ✗ Removing: $file"
            rm -f "$file"
        fi
    done
    cd ../..
}

echo ""
echo "=== GIS folder ==="
cd Data/GIS 2>/dev/null && {
    # Remove CSV files with cleaned versions
    for file in *.csv; do
        if [ -f "cleaned_$file" ] && [[ "$file" != cleaned_* ]]; then
            echo "  ✗ Removing: $file"
            rm -f "$file"
        fi
    done
    
    # Remove Excel files with cleaned versions
    for file in *.xlsx *.xls *.xlsm; do
        [ -e "$file" ] || continue
        base="${file%.*}"
        if [ -f "cleaned_${base}.csv" ] || ls "cleaned_${base}_"*.csv 1> /dev/null 2>&1; then
            echo "  ✗ Removing: $file"
            rm -f "$file"
        fi
    done
    cd ../..
}

echo ""
echo "=== GIS Shapefiles (converted to CSV) ==="
# Remove shapefiles and associated files
find Data/GIS -name "*.shp" -o -name "*.shx" -o -name "*.dbf" -o -name "*.prj" -o -name "*.cpg" -o -name "*.sbn" -o -name "*.sbx" -o -name "*.shp.xml" -o -name "*.qmd" 2>/dev/null | while read file; do
    # Check if cleaned CSV version exists
    dir=$(dirname "$file")
    base=$(basename "$file" | sed 's/\.[^.]*$//')
    if [ -f "$dir/cleaned_${base}.csv" ]; then
        echo "  ✗ Removing: $file"
        rm -f "$file"
    fi
done

echo ""
echo "=== Large 311 file (keeping reduced version only) ==="
if [ -f "Data/ZIPCODE 78207/clean/311-reports-78207.csv" ] && [ -f "Data/ZIPCODE 78207/clean/311-reports-78207-reduced.csv" ]; then
    echo "  ✗ Removing: Data/ZIPCODE 78207/clean/311-reports-78207.csv (412 MB)"
    rm -f "Data/ZIPCODE 78207/clean/311-reports-78207.csv"
fi

echo ""
echo "=============================================================================="
echo "CLEANUP COMPLETE!"
echo "=============================================================================="
echo ""
echo "Remaining files:"
find Data -name "cleaned_*" -o -name "*reduced*" | grep -E "\.(csv|xlsx)$" | wc -l
echo "cleaned files retained"
