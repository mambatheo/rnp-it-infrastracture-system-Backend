"""
One-time data population script for Regions and DPUs.
Run with: python manage.py shell < populate_regions_dpus.py
"""
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'itinfra.settings')

from equipment.models import Region, DPU

DATA = [
    # (DPU name, Region name)
    ("Gasabo",      "Central Region"),
    ("Nyarugenge",  "Central Region"),
    ("Kicukiro",    "Central Region"),

    ("Rwamagana",   "Eastern Region"),
    ("Kayonza",     "Eastern Region"),
    ("Gatsibo",     "Eastern Region"),
    ("Bugesera",    "Eastern Region"),
    ("Kirehe",      "Eastern Region"),
    ("Ngoma",       "Eastern Region"),
    ("Nyagatare",   "Eastern Region"),

    ("Ruhango",     "Southern Region"),
    ("Huye",        "Southern Region"),
    ("Nyaruguru",   "Southern Region"),
    ("Gisagara",    "Southern Region"),
    ("Nyamagabe",   "Southern Region"),
    ("Muhanga",     "Southern Region"),
    ("Kamonyi",     "Southern Region"),
    ("Nyanza",      "Southern Region"),

    ("Rubavu",      "Western Region"),
    ("Nyabihu",     "Western Region"),
    ("Ngororero",   "Western Region"),
    ("Rutsiro",     "Western Region"),
    ("Karongi",     "Western Region"),
    ("Nyamasheke",  "Western Region"),
    ("Rusizi",      "Western Region"),

    ("Gicumbi",     "Northern Region"),
    ("Rulindo",     "Northern Region"),
    ("Gakenke",     "Northern Region"),
    ("Burera",      "Northern Region"),
    ("Musanze",     "Northern Region"),
]

# Collect unique region names
region_names = sorted({r for _, r in DATA})

# Create regions (get_or_create to be safe)
region_map = {}
for name in region_names:
    obj, created = Region.objects.get_or_create(name=name)
    region_map[name] = obj
    print(f"  Region {'[NEW]' if created else '[EXISTS]'}: {name}")

print(f"\nRegions: {len(region_map)} total\n")

# Create DPUs
created_count = 0
skipped_count = 0
for dpu_name, region_name in DATA:
    region = region_map[region_name]
    obj, created = DPU.objects.get_or_create(name=dpu_name, defaults={'region': region})
    if created:
        created_count += 1
        print(f"  DPU [NEW]:    {dpu_name} → {region_name}")
    else:
        skipped_count += 1
        print(f"  DPU [EXISTS]: {dpu_name}")

print(f"\nDone. DPUs created: {created_count}, already existed: {skipped_count}")
