import sqlite3
import json
import urllib.request
import os
from shapely.geometry import Point, shape

# Download Sri Lanka GeoJSON
geojson_url = "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson"
print("Downloading GeoJSON...")
with urllib.request.urlopen(geojson_url) as url:
    data = json.loads(url.read().decode())
    
# Find Sri Lanka
sl_feature = next(f for f in data["features"] if f["properties"]["ISO_A3"] == "LKA")
sl_polygon = shape(sl_feature["geometry"])

db_path = os.path.join(os.path.dirname(__file__), "..", "data", "outlets.db")
print(f"Connecting to {db_path}...")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Ensure the column exists
try:
    cursor.execute("ALTER TABLE outlets ADD COLUMN in_sea INTEGER DEFAULT 0")
except sqlite3.OperationalError:
    pass # Column already exists

cursor.execute("SELECT outlet_id, longitude, latitude FROM outlets")
outlets = cursor.fetchall()

in_sea_ids = []
print("Checking outlets against coastline...")
for outlet_id, lon, lat in outlets:
    pt = Point(lon, lat)
    # contains() returns True if the point is strictly inside
    if not sl_polygon.contains(pt):
        in_sea_ids.append((outlet_id,))

print(f"Found {len(in_sea_ids)} outlets in the sea.")

if in_sea_ids:
    cursor.executemany("UPDATE outlets SET in_sea = 1 WHERE outlet_id = ?", in_sea_ids)
    conn.commit()
    print("Database updated!")
else:
    print("No outlets in sea found.")

conn.close()
