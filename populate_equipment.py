"""
Mass Equipment Seeder — 10 000+ records
========================================
Run with: py manage.py shell -c "exec(open('populate_equipment.py').read())"

What it does
------------
1. Ensures EquipmentCategory, Brand, and EquipmentStatus lookup rows exist.
2. Reads Regions, DPUs, Stations, and Units already in the DB.
3. Bulk-creates 10 000+ Equipment rows (Stock intent) distributed
   across all available locations and brand/category combos.

Notes
-----
* Equipment.save() calls full_clean() which validates FK consistency.
  We therefore use bulk_create() with ignore_conflicts=True to bypass
  the Django-level validation and write directly — this is intentional
  for seeding purposes.  The DB still enforces FK integrity.
* Serial numbers and marking codes are generated to be unique.
* We deliberately skip Deployment records so all seeded items land
  in a "Stock" state (no Stock record required for Stock intent).
"""

import uuid
import random
import string
from datetime import date, timedelta

# ─── Django ORM imports ───────────────────────────────────────────────────────
from equipment.models import (
    EquipmentCategory, Brand, EquipmentStatus,
    Region, DPU, Station, Unit,
    Equipment,
)

print("=" * 60)
print("  Equipment Mass Seeder")
print("=" * 60)

# ─────────────────────────────────────────────────────────────────────────────
# 1.  LOOKUP DATA  — categories, brands, statuses
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_BRANDS = {
    "Desktop": [
        "HP", "Dell", "Lenovo", "Acer", "ASUS",
        "Apple", "Samsung", "Fujitsu", "Toshiba",
    ],
    "Laptop": [
        "HP", "Dell", "Lenovo", "Apple", "ASUS",
        "Acer", "Microsoft", "Huawei", "Samsung",
    ],
    "Printer": [
        "HP", "Canon", "Epson", "Brother", "Xerox",
        "Ricoh", "Konica Minolta", "Samsung", "Kyocera",
    ],
    "UPS": [
        "APC", "Eaton", "CyberPower", "Vertiv", "Schneider Electric",
        "Numeric", "Microtek", "Luminous", "Socomec",
    ],
    "Phone": [
        "Cisco", "Polycom", "Yealink", "Avaya", "Panasonic",
        "Grandstream", "Samsung", "Nokia", "Alcatel-Lucent",
    ],
    "Server": [
        "Dell", "HP", "IBM", "Lenovo", "Cisco",
        "Huawei", "Fujitsu", "Oracle", "SuperMicro",
    ],
    "Network Device": [
        "Cisco", "Juniper", "Huawei", "MikroTik", "TP-Link",
        "Aruba", "Netgear", "Ubiquiti", "D-Link",
    ],
    "Monitor": [
        "HP", "Dell", "Samsung", "LG", "Acer",
        "ASUS", "ViewSonic", "BenQ", "AOC",
    ],
    "Scanner": [
        "HP", "Canon", "Epson", "Brother", "Fujitsu",
        "Kodak", "Xerox", "Panasonic",
    ],
    "External Storage": [
        "Seagate", "Western Digital", "Samsung", "SanDisk",
        "Toshiba", "Kingston", "Lacie", "Buffalo",
    ],
}

STATUSES = ["Active", "In Repair", "Decommissioned", "In Stock", "Faulty"]

EQUIPMENT_TYPES = {
    "Desktop":          "Desktop Computer",
    "Laptop":           "Laptop Computer",
    "Printer":          "Printer",
    "UPS":              "UPS",
    "Phone":            "IP Phone",
    "Server":           "Server",
    "Network Device":   "Network Device",
    "Monitor":          "Monitor/Display",
    "Scanner":          "Scanner",
    "External Storage": "External Storage",
}

# Realistic models per category
MODELS = {
    "Desktop": [
        "EliteDesk 800 G6", "OptiPlex 7090", "ThinkCentre M720", "Veriton X6670G",
        "ProDesk 600 G5", "Aspire TC-895", "All-in-One PC 2021", "ESPRIMO P558",
        "Vostro 3888", "IdeaCentre 5i",
    ],
    "Laptop": [
        "ProBook 450 G8", "Latitude 5420", "ThinkPad E14", "MacBook Pro 14",
        "EliteBook 840 G8", "Aspire 5", "Surface Pro 8", "MateBook D15",
        "ZenBook 15", "Vostro 15 3510",
    ],
    "Printer": [
        "LaserJet Pro M404n", "PIXMA MG3650", "EcoTank L3150", "HL-L2350DW",
        "WorkCentre 6515", "SP C261SFNw", "bizhub C3350i", "ECOSYS P2040dn",
        "LaserJet MFP M430f", "LaserJet Pro M118dw",
    ],
    "UPS": [
        "Back-UPS 1500", "5PX 1500", "CP1500PFCLCD", "GXT4-1500RT120",
        "Smart-UPS 1500", "NMC3 1000", "VFI 1000 RMG PF1", "Numeric UP 800",
        "Socomec NETYS RT", "PowerKit 1000",
    ],
    "Phone": [
        "IP Phone 8841", "VVX 411", "T46U", "1140E", "KX-TGE474",
        "GXP2170", "J179", "Lumia 730", "OmniPCX Enterprise", "IP30",
    ],
    "Server": [
        "PowerEdge R740", "ProLiant DL380 Gen10", "System x3650 M5",
        "ThinkSystem SR650", "UCS C220 M5", "FusionServer 2288H",
        "PRIMERGY RX2540 M5", "SPARC T8-2", "SuperServer 6019P-MT",
        "ProLiant ML350 Gen10",
    ],
    "Network Device": [
        "Catalyst 9300", "EX2300-48T", "AR6140H", "CCR1036-8G",
        "T2600G-52TS", "Aruba 5412R", "S3300-28SFP", "UniFi Switch 48",
        "DGS-3630-52TC", "NetVoyant SRX320",
    ],
    "Monitor": [
        "EliteDisplay E243", "P2419H", "27F Monitor", "UltraSharp U2722D",
        "Aspire KG241Q", "ProArt PA279CV", "VP2768", "PD3200Q",
        "S2721DS", "24E1N3300A",
    ],
    "Scanner": [
        "ScanJet Pro 3000 s4", "imageFORMULA DR-C230", "WorkForce ES-400",
        "ADS-2700W", "fi-7160", "i1150", "DocuMate 3125",
        "KV-S1037", "ScanJet Pro 4500 fn1",
    ],
    "External Storage": [
        "Backup Plus 4TB", "My Passport 2TB", "T7 SSD 1TB", "Ultra Dual Drive Go",
        "Canvio Advance 2TB", "DataTraveler Exodia 64GB", "Rugged 2TB",
        "DriveStation 4TB", "P30 Elite 512GB", "SV35S 1TB",
    ],
}

# Dates spread over past 5 years
def rand_date(years_back=5):
    start = date.today() - timedelta(days=years_back * 365)
    return start + timedelta(days=random.randint(0, years_back * 365))

def rand_serial():
    return "SN-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))

def rand_marking():
    return "MC-" + "".join(random.choices(string.digits, k=7))

# ── Ensure categories exist ───────────────────────────────────────────────────
print("\n[1] Ensuring categories …")
cat_map = {}
for cat_name in CATEGORY_BRANDS:
    obj, created = EquipmentCategory.objects.get_or_create(name=cat_name)
    cat_map[cat_name] = obj
    print(f"    {'[NEW]' if created else '[OK]'} {cat_name}")

# ── Ensure brands exist per category ─────────────────────────────────────────
print("\n[2] Ensuring brands …")
brand_map = {}  # (cat_name, brand_name) → Brand obj
for cat_name, brand_names in CATEGORY_BRANDS.items():
    cat_obj = cat_map[cat_name]
    for brand_name in brand_names:
        obj, created = Brand.objects.get_or_create(name=brand_name, category=cat_obj)
        brand_map[(cat_name, brand_name)] = obj
        if created:
            print(f"    [NEW] {brand_name} ({cat_name})")

print(f"    Total brands: {len(brand_map)}")

# ── Ensure statuses exist ─────────────────────────────────────────────────────
print("\n[3] Ensuring statuses …")
status_map = {}
for s in STATUSES:
    obj, created = EquipmentStatus.objects.get_or_create(name=s)
    status_map[s] = obj
    print(f"    {'[NEW]' if created else '[OK]'} {s}")

# ─────────────────────────────────────────────────────────────────────────────
# 2.  READ LOCATIONS
# ─────────────────────────────────────────────────────────────────────────────
print("\n[4] Loading locations from DB …")
regions  = list(Region.objects.all())
dpus     = list(DPU.objects.all())
stations = list(Station.objects.all())
units    = list(Unit.objects.all())

# build DPU→Region lookup for consistency
dpu_region = {d.id: d.region_id for d in dpus}
# build Station→DPU lookup
station_dpu = {s.id: s.dpu_id for s in stations}

print(f"    Regions:  {len(regions)}")
print(f"    DPUs:     {len(dpus)}")
print(f"    Stations: {len(stations)}")
print(f"    Units:    {len(units)}")

if not dpus:
    raise RuntimeError("No DPUs found in DB.  Run populate_regions_dpus.py first.")

# ─────────────────────────────────────────────────────────────────────────────
# 3.  BUILD RECORDS
# ─────────────────────────────────────────────────────────────────────────────
TARGET = 10_500   # generate slightly above 10 000 to account for any skips
BATCH  = 500      # bulk_create batch size

print(f"\n[5] Generating {TARGET:,} equipment rows …")

# Pre-flatten brand/category combos for fast random choice
combos = []   # (cat_name, Brand obj, EquipmentType str)
for cat_name, brand_names in CATEGORY_BRANDS.items():
    equip_type = EQUIPMENT_TYPES[cat_name]
    for bn in brand_names:
        combos.append((cat_name, brand_map[(cat_name, bn)], equip_type))

status_objs  = list(status_map.values())
active_status = status_map.get("Active", status_objs[0])

serials  = set()
markings = set()

def unique_serial():
    while True:
        s = rand_serial()
        if s not in serials:
            serials.add(s)
            return s

def unique_marking():
    while True:
        m = rand_marking()
        if m not in markings:
            markings.add(m)
            return m

def pick_location():
    """Return (region, dpu, station) with a consistent hierarchy."""
    if stations and random.random() < 0.75:
        st   = random.choice(stations)
        dpu  = next(d for d in dpus if d.id == station_dpu[st.id])
        reg  = next(r for r in regions if r.id == dpu_region[dpu.id])
        return reg, dpu, st
    elif dpus:
        dpu = random.choice(dpus)
        reg = next(r for r in regions if r.id == dpu_region[dpu.id])
        return reg, dpu, None
    else:
        reg = random.choice(regions)
        return reg, None, None

records = []
created_total = 0
batch_num = 0

for i in range(TARGET):
    cat_name, brand_obj, equip_type = random.choice(combos)
    model_name = random.choice(MODELS.get(cat_name, ["Standard Model"]))
    status_obj = random.choice(status_objs)
    reg, dpu, station = pick_location()
    unit = random.choice(units) if units and random.random() < 0.4 else None

    deploy_date = rand_date(5) if random.random() < 0.6 else None
    warranty    = rand_date(3) if random.random() < 0.5 else None

    # Optional specs
    cpu = ram = storage = os_val = None
    if cat_name in ("Desktop", "Laptop", "Server"):
        cpu_choices = ["Intel Core i5-11400", "Intel Core i7-11700", "AMD Ryzen 5 5600",
                       "AMD Ryzen 7 5800", "Intel Xeon E-2300", "Intel Core i3-10100"]
        ram_choices = ["4GB", "8GB", "16GB", "32GB", "64GB", "128GB"]
        storage_choices = ["256GB SSD", "512GB SSD", "1TB HDD", "2TB HDD", "500GB SSD"]
        os_choices = ["Windows 10 Pro", "Windows 11 Pro", "Ubuntu 22.04", "RHEL 8", "Windows Server 2019"]
        cpu = random.choice(cpu_choices)
        ram = random.choice(ram_choices)
        storage = random.choice(storage_choices)
        os_val  = random.choice(os_choices)

    screen = None
    if cat_name in ("Desktop", "Laptop", "Monitor"):
        screen = random.choice(["14\"", "15.6\"", "21.5\"", "24\"", "27\"", "13.3\""])

    printer_t = None
    if cat_name == "Printer":
        printer_t = random.choice(["Laser", "Inkjet", "Multi-Function", "Dot Matrix", "Thermal"])

    network_t = None
    if cat_name == "Network Device":
        network_t = random.choice(["Switch", "Router", "Firewall", "Access Point", "Hub", "Modem"])

    telephone_t = None
    if cat_name == "Phone":
        telephone_t = random.choice(["VoIP", "Analog", "SIP", "DECT", "Softphone"])

    exstorage_t = None
    if cat_name == "External Storage":
        exstorage_t = random.choice(["HDD", "SSD", "Flash Drive", "NAS", "Tape"])

    ups_val = None
    if cat_name == "UPS":
        ups_val = random.choice(["500VA", "1000VA", "1500VA", "2000VA", "3000VA"])

    records.append(Equipment(
        id                  = uuid.uuid4(),
        name                = f"{brand_obj.name} {model_name}",
        equipment_type      = equip_type,
        registration_intent = Equipment.RegistrationIntent.STOCK,
        region              = reg,
        dpu                 = dpu,
        station             = station,
        unit                = unit,
        brand               = brand_obj,
        model               = model_name,
        status              = status_obj,
        serial_number       = unique_serial(),
        marking_code        = unique_marking(),
        deployment_date     = deploy_date,
        warranty_expiration = warranty,
        CPU                 = cpu,
        ram_size            = ram,
        storage_size        = storage,
        operating_system    = os_val,
        screen_size         = screen,
        printer_type        = printer_t,
        network_type        = network_t,
        telephone_type      = telephone_t,
        exstorage_type      = exstorage_t,
        ups                 = ups_val,
        # No created_by/updated_by — left NULL for seeder
    ))

    # Flush in batches
    if len(records) >= BATCH:
        batch_num += 1
        Equipment.objects.bulk_create(records, ignore_conflicts=True)
        created_total += len(records)
        print(f"    Batch {batch_num:>3}: inserted up to {created_total:>6,} rows …")
        records = []

# Final flush
if records:
    batch_num += 1
    Equipment.objects.bulk_create(records, ignore_conflicts=True)
    created_total += len(records)
    print(f"    Batch {batch_num:>3}: inserted up to {created_total:>6,} rows …")

# ─────────────────────────────────────────────────────────────────────────────
# 4.  SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
total_in_db = Equipment.objects.count()
print("\n" + "=" * 60)
print("  DONE!")
print(f"  Rows attempted : {TARGET:>8,}")
print(f"  Total in DB    : {total_in_db:>8,}")
print("=" * 60)
