#!/bin/bash

# Paths to compare
PATH1="/media/gskourts/TOSHIBA EXT1/photos/"
PATH2="/media/gskourts/TOSHIBA EXT/photos/"

echo "Comparing folder sizes between:"
echo "EXT1: $PATH1"
echo "EXT:  $PATH2"
echo "=================================="

# Create temporary files
TMP1=$(mktemp)
TMP2=$(mktemp)

# Get directory sizes (excluding the total line)
du -h --max-depth=1 "$PATH1" | head -n -1 | sort > "$TMP1"
du -h --max-depth=1 "$PATH2" | head -n -1 | sort > "$TMP2"

# Extract just the folder names for comparison
cut -d'/' -f6- "$TMP1" | sort > "${TMP1}_names"
cut -d'/' -f6- "$TMP2" | sort > "${TMP2}_names"

echo -e "\n📁 FOLDERS ONLY IN EXT1:"
comm -23 "${TMP1}_names" "${TMP2}_names" | while read folder; do
    if [ -n "$folder" ]; then
        size=$(grep "$folder" "$TMP1" | cut -f1)
        echo "  $size - $folder"
    fi
done

echo -e "\n📁 FOLDERS ONLY IN EXT:"
comm -13 "${TMP1}_names" "${TMP2}_names" | while read folder; do
    if [ -n "$folder" ]; then
        size=$(grep "$folder" "$TMP2" | cut -f1)
        echo "  $size - $folder"
    fi
done

echo -e "\n🔄 SIZE MISMATCHES:"
# Compare folders that exist in both
comm -12 "${TMP1}_names" "${TMP2}_names" | while read folder; do
    if [ -n "$folder" ]; then
        size1=$(grep "$folder" "$TMP1" | cut -f1)
        size2=$(grep "$folder" "$TMP2" | cut -f1)
        
        if [ "$size1" != "$size2" ]; then
            echo "  $folder:"
            echo "    EXT1: $size1"
            echo "    EXT:  $size2"
        fi
    fi
done

echo -e "\n✅ FOLDERS WITH MATCHING SIZES:"
comm -12 "${TMP1}_names" "${TMP2}_names" | while read folder; do
    if [ -n "$folder" ]; then
        size1=$(grep "$folder" "$TMP1" | cut -f1)
        size2=$(grep "$folder" "$TMP2" | cut -f1)
        
        if [ "$size1" = "$size2" ]; then
            echo "  $size1 - $folder"
        fi
    fi
done

# Cleanup
rm "$TMP1" "$TMP2" "${TMP1}_names" "${TMP2}_names"