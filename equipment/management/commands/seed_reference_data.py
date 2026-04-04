"""
Management command to seed all reference / lookup data.
Must be run BEFORE seed_equipment.

Creates:
  - EquipmentStatus
  - EquipmentCategory  (with matching Brand entries)
  - RegionOffice  →  Region  →  DPUOffice  →  DPU  →  Station
  - Unit  →  Directorate  →  Department  →  Office
  - TrainingSchool

Usage:
    python manage.py seed_reference_data
    python manage.py seed_reference_data --clear   # wipe and re-seed
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from equipment.models import (
    EquipmentStatus, EquipmentCategory, Brand,
    RegionOffice, Region,
    DPUOffice, DPU, Station,
    Unit, Directorate, Department, Office,
    Equipment, Stock, Deployment, Lending, TrainingSchool,
)


# ─────────────────────────────────────────────────────────────────────────────
# REFERENCE DATA
# ─────────────────────────────────────────────────────────────────────────────

STATUSES = [
    "Active",
    "Inactive",
    "Under Repair",
    "Retired",
    "Damaged",
    "Lost / Stolen",
    "Borrowed",
    "Decommissioned",
    "New",
    "In Transit",
]

# category_name -> [brand_name, ...]
CATEGORIES_AND_BRANDS = {
    "Desktop":              ["Dell", "HP", "Lenovo", "Acer", "Asus", "Apple", "Fujitsu"],
    "Laptop":               ["Dell", "HP", "Lenovo", "Asus", "Acer", "Apple", "Samsung", "Huawei"],
    "Server":               ["Dell", "HP", "Lenovo", "IBM", "Cisco", "Huawei", "Fujitsu"],
    "Workstation":          ["Dell", "HP", "Lenovo", "Asus"],
    "Tablet":               ["Apple", "Samsung", "Lenovo", "Huawei", "Microsoft", "Amazon"],
    "Smartphone":           ["Apple", "Samsung", "Huawei", "Xiaomi", "Nokia", "Oppo"],
    "Printer":              ["HP", "Canon", "Epson", "Brother", "Xerox", "Kyocera", "Ricoh"],
    "Scanner":              ["Canon", "HP", "Epson", "Brother", "Fujitsu", "Kodak"],
    "Photocopier":          ["Canon", "Xerox", "Ricoh", "Kyocera", "Konica Minolta", "Sharp"],
    "Plotter":              ["HP", "Canon", "Epson", "Roland"],
    "Fax Machine":          ["Brother", "Panasonic", "HP", "Canon"],
    "Network Switch":       ["Cisco", "Aruba", "Juniper", "Huawei", "D-Link", "Netgear", "Ubiquiti"],
    "Router":               ["Cisco", "Juniper", "MikroTik", "Huawei", "TP-Link", "Netgear", "Asus"],
    "Firewall":             ["Cisco", "Fortinet", "Palo Alto", "Juniper", "SonicWall", "Sophos"],
    "Access Point":         ["Cisco", "Aruba", "Ruckus", "TP-Link", "Netgear", "Ubiquiti"],
    "Modem":                ["Huawei", "TP-Link", "Cisco", "Zyxel", "Netgear"],
    "Hub":                  ["TP-Link", "Anker", "Belkin", "Ugreen"],
    "Repeater":             ["TP-Link", "Netgear", "Asus"],
    "Network Gateway":      ["SonicWall", "Cisco", "Cradlepoint", "Peplink"],
    "Network Bridge":       ["Ubiquiti", "Mikrotik", "DLB"],
    "IP Phone":             ["Cisco", "Polycom", "Yealink", "Grandstream", "Avaya"],
    "DECT Phone":           ["Panasonic", "Gigaset", "Philips", "VTech"],
    "PBX System":           ["Avaya", "Cisco", "Panasonic", "3CX", "Yeastar"],
    "Video Conferencing":   ["Cisco", "Polycom", "Logitech", "Zoom", "Huawei"],
    "TV Screen":            ["Samsung", "LG", "Sony", "Philips", "Hisense", "Sharp"],
    "Projector":            ["Epson", "BenQ", "Sony", "NEC", "Optoma", "Acer"],
    "Interactive Whiteboard": ["SMART", "Promethean", "Samsung", "LG"],
    "Display Panel":        ["Samsung", "NEC", "LG", "Philips", "ViewSonic"],
    "UPS":                  ["APC", "Eaton", "Riello", "Liebert"],
    "PDU":                  ["APC", "Eaton", "Raritan", "Vertiv"],
    "ATS":                  ["APC", "Eaton", "Vertiv"],
    "Generator":            ["Cummins", "Caterpillar", "Perkins", "Kohler", "Kipor"],
    "External HDD":         ["Seagate", "Western Digital", "Toshiba", "Samsung"],
    "Flash Drive":          ["SanDisk", "Kingston", "Samsung", "Transcend"],
    "SSD":                  ["Samsung", "Western Digital", "Seagate", "Kingston", "Crucial"],
    "NAS":                  ["Synology", "QNAP", "Western Digital", "Netgear"],
    "Tape Drive":           ["HP", "Dell", "IBM", "Quantum"],
    "Memory Card":          ["SanDisk", "Samsung", "Kingston", "Lexar"],
    "Mouse":                ["Logitech", "Microsoft", "HP", "Dell", "Genius"],
    "Keyboard":             ["Logitech", "Microsoft", "HP", "Dell", "Genius"],
    "Monitor":              ["Dell", "HP", "LG", "Samsung", "Asus", "Acer", "ViewSonic"],
    "Webcam":               ["Logitech", "Microsoft", "Razer"],
    "Headset":              ["Logitech", "Jabra", "Plantronics", "Sony", "Sennheiser"],
    "Decoder":              ["Nagra", "Pace", "Motorola"],
    "Digital Receiver":     ["Samsung", "Tiger", "Geant", "Openbox", "Formuler"],
    "CCTV Camera":          ["Hikvision", "Dahua", "Axis", "Bosch", "Hanwha"],
    "DVR/NVR":              ["Hikvision", "Dahua", "Uniview", "Milestone", "Genetec"],
    "Biometric Device":     ["ZKTeco", "Suprema", "IDEMIA", "HID", "Anviz"],
    "Card Reader":          ["SCM Microsystems", "ACS", "HID", "Gemalto"],
    "Barcode Scanner":      ["Zebra", "Honeywell", "Datalogic", "Symbol"],
    "Radio / Walkie-Talkie":["Motorola", "Kenwood", "Hytera", "Icom", "Baofeng"],
    "GPS Device":           ["Garmin", "Trimble", "Leica", "Topcon"],
    "Cable / Connector":    ["Belkin", "Ugreen", "Anker", "TP-Link"],
    "Rack / Cabinet":       ["APC", "Eaton", "Tripp Lite", "Vertiv"],
    "KVM Switch":           ["ATEN", "Tripp Lite", "Raritan", "Dell"],
    "Peripheral":           ["Logitech", "Microsoft", "HP", "Generic"],
}

# ── Geography ──────────────────────────────────────────────────────────────────

regions_dpus = {
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
}

STATIONS = [
    # Gasabo
    ("Rutunga","Gasabo"),("Rusororo","Gasabo"),("Remera","Gasabo"),("Nduba","Gasabo"),
    ("Ndera","Gasabo"),("Kinyinya","Gasabo"),("Kimironko","Gasabo"),("Kimihurura","Gasabo"),
    ("Kacyiru","Gasabo"),("Jali","Gasabo"),("Jabana","Gasabo"),("Gisozi","Gasabo"),
    ("Gikomero","Gasabo"),("Gatsata","Gasabo"),("Bumbogo","Gasabo"),
    # Nyarugenge
    ("Nyarugenge","Nyarugenge"),("Kigali","Nyarugenge"),("Rwezamenyo","Nyarugenge"),
    ("Muhima","Nyarugenge"),("Kimisagara","Nyarugenge"),("Kanyinya","Nyarugenge"),
    ("Mageragere","Nyarugenge"),
    # Kicukiro
    ("Gahanga","Kicukiro"),("Masaka","Kicukiro"),("Nyarugunga","Kicukiro"),
    ("Kanombe","Kicukiro"),("Kicukiro","Kicukiro"),("Gikondo","Kicukiro"),("Kigarama","Kicukiro"),
    # Rwamagana
    ("Kigabiro","Rwamagana"),("Nzige","Rwamagana"),("Musha","Rwamagana"),
    ("Muyumbu","Rwamagana"),("Karenge","Rwamagana"),("Gishari","Rwamagana"),
    ("Rubona","Rwamagana"),("Fumbwe","Rwamagana"),
    # Kayonza
    ("Rukara","Kayonza"),("Mukarange","Kayonza"),("Kabarondo","Kayonza"),
    ("Rwinkavu","Kayonza"),("Gahini","Kayonza"),("Nyamirama","Kayonza"),
    ("Mwiri","Kayonza"),("Murundi","Kayonza"),("Ndego","Kayonza"),
    # Gatsibo
    ("Kabarore","Gatsibo"),("Kiramuruzi","Gatsibo"),("Ngarama","Gatsibo"),
    ("Gatsibo","Gatsibo"),("Muhura","Gatsibo"),("Rwimbogo","Gatsibo"),
    ("Nyagihanga","Gatsibo"),("Rugarama","Gatsibo"),("Murambi","Gatsibo"),
    ("Gasange","Gatsibo"),("Remera","Gatsibo"),("Gitoki","Gatsibo"),
    # Bugesera
    ("Nyamata","Bugesera"),("Mayange","Bugesera"),("Ruhuha","Bugesera"),
    ("Kamabuye","Bugesera"),("Rweru","Bugesera"),("Rilima","Bugesera"),
    ("Ntarama","Bugesera"),("Gashora","Bugesera"),
    # Kirehe
    ("Kirehe","Kirehe"),("Nyamugari","Kirehe"),("Nyarubuye","Kirehe"),
    ("Gatore","Kirehe"),("Mpanga","Kirehe"),("Nasho","Kirehe"),
    ("Kigarama","Kirehe"),("Gahara","Kirehe"),
    # Ngoma
    ("Kibungo","Ngoma"),("Sake","Ngoma"),("Remera","Ngoma"),("Mutenderi","Ngoma"),
    ("Zaza","Ngoma"),("Rukira","Ngoma"),("Rukumberi","Ngoma"),("Mugesera","Ngoma"),
    ("Jarama","Ngoma"),("Karembo","Ngoma"),("Gashanda","Ngoma"),("Rurenge","Ngoma"),
    # Nyagatare
    ("Nyagatare","Nyagatare"),("Matimba","Nyagatare"),("Karangazi","Nyagatare"),
    ("Gatunda","Nyagatare"),("Rwimiyaga","Nyagatare"),("Katabagema","Nyagatare"),
    ("Rwempesha","Nyagatare"),("Karama","Nyagatare"),("Mimuri","Nyagatare"),
    ("Musheferi","Nyagatare"),("Kiyombe","Nyagatare"),("Tabagwe","Nyagatare"),
    ("Ntoma Mobile","Nyagatare"),
    # Ruhango
    ("Byimana","Ruhango"),("Kabagari","Ruhango"),("Kinazi","Ruhango"),
    ("Ntongwe","Ruhango"),("Mbuye","Ruhango"),("Ruhango","Ruhango"),
    # Huye
    ("Ngoma","Huye"),("Rusatira","Huye"),("Huye","Huye"),("Mbazi","Huye"),("Simbi","Huye"),
    # Nyaruguru
    ("Mata","Nyaruguru"),("Kibeho","Nyaruguru"),("Nyagisozi","Nyaruguru"),
    ("Busanze","Nyaruguru"),("Muganza","Nyaruguru"),("Ngera","Nyaruguru"),("Kivu","Nyaruguru"),
    # Gisagara
    ("Ndora","Gisagara"),("Gikonko","Gisagara"),("Nyanza","Gisagara"),("Save","Gisagara"),
    ("Mamba","Gisagara"),("Mukindo","Gisagara"),("Muganza","Gisagara"),
    # Nyamagabe
    ("Gasaka","Nyamagabe"),("Kaduha","Nyamagabe"),("Musebeya","Nyamagabe"),
    ("Tare","Nyamagabe"),("Kitabi","Nyamagabe"),("Musange","Nyamagabe"),
    # Muhanga
    ("Nyamabuye","Muhanga"),("Kiyumba","Muhanga"),("Muhanga","Muhanga"),("Mushingiro","Muhanga"),
    # Kamonyi
    ("Musambira","Kamonyi"),("Rukoma","Kamonyi"),("Mugina","Kamonyi"),
    ("Kanombe","Kamonyi"),("Gacurabwenge","Kamonyi"),("Kayenzi","Kamonyi"),("Runda","Kamonyi"),
    # Nyanza
    ("Busasamana","Nyanza"),("Muyira","Nyanza"),("Mukingo","Nyanza"),
    ("Ntyazo","Nyanza"),("Busoro","Nyanza"),
    # Rubavu
    ("Kanama","Rubavu"),("Gisenyi","Rubavu"),("Mudende","Rubavu"),
    ("Busasamana","Rubavu"),("Bugeshi","Rubavu"),("Rugerero","Rubavu"),
    # Nyabihu
    ("Mukamira","Nyabihu"),("Jomba","Nyabihu"),("Rugera","Nyabihu"),
    ("Jenda","Nyabihu"),("Kabatwa","Nyabihu"),("Karago","Nyabihu"),
    # Ngororero
    ("Kavumu","Ngororero"),("Gatumba","Ngororero"),("Nyange","Ngororero"),
    ("Kanombe","Ngororero"),("Ngororero","Ngororero"),("Kabaya","Ngororero"),
    # Rutsiro
    ("Gihango","Rutsiro"),("Murunda","Rutsiro"),("Ruhango","Rutsiro"),
    ("Rusebeya","Rutsiro"),("Kivumu","Rutsiro"),
    # Karongi
    ("Bwishyura","Karongi"),("Gashari","Karongi"),("Gishyita","Karongi"),
    ("Rwankuba","Karongi"),("Rugabano","Karongi"),("Twumba","Karongi"),("Rubengera","Karongi"),
    # Nyamasheke
    ("Kanjongo","Nyamasheke"),("Ruharambuga","Nyamasheke"),("Macuba","Nyamasheke"),
    ("Gihombo","Nyamasheke"),("Shangi","Nyamasheke"),("Karengera","Nyamasheke"),
    ("Kagano","Nyamasheke"),
    # Rusizi
    ("Bugarama","Rusizi"),("Kamembe","Rusizi"),("Nyakabuye","Rusizi"),("Nkanka","Rusizi"),
    ("Gashonga","Rusizi"),("Bweyeye","Rusizi"),("Nkombo","Rusizi"),("Muganza","Rusizi"),
    # Gicumbi
    ("Kaniga","Gicumbi"),("Bukure","Gicumbi"),("Byumba","Gicumbi"),
    ("Rutare","Gicumbi"),("Cyumba","Gicumbi"),("Rushaki","Gicumbi"),
    # Rulindo
    ("Shyorongi","Rulindo"),("Kinihira","Rulindo"),("Bushoki","Rulindo"),
    ("Murambi","Rulindo"),("Ntarabana","Rulindo"),("Buyoga","Rulindo"),
    # Gakenke
    ("Janja","Gakenke"),("Ruri","Gakenke"),("Rushashi","Gakenke"),
    ("Gakenke","Gakenke"),("Cyabingo","Gakenke"),("Gashenyi","Gakenke"),
    # Burera
    ("Butaro","Burera"),("Bungwe","Burera"),("Cyanika","Burera"),("Rusarabuye","Burera"),
    ("Rugendabari","Burera"),("Gahunga","Burera"),("Nemba","Burera"),
    # Musanze
    ("Muhoza","Musanze"),("Busogo","Musanze"),("Kinigi","Musanze"),
    ("Remera","Musanze"),("Cyuve","Musanze"),
]

# ── Organisational units ───────────────────────────────────────────────────────

UNITS = [
    "IGP Office",
    "DIGP AP Office",
    "DIGP OPNS Office",
    "IT",
    "OPO",
    "ISPSSP",
    "Crime Intelligence",
    "Counter Intelligence",
    "PSO",
    "Inspectorate",
    "Training",
    "Fire & Rescue",
    "Transport & Logistics",
    "Marine",
    "CCC",
    "Community Policing",
    "HRM",
    "ASOC",
    "TRS",
    "PRM",
    "AI",
    "Logistics",
    "TAF",
    "Cooperation & Protocol",
    "K9",
    "Police General Headquarters",
    "BSU",
    "PDU",
    "Finance & CBM",
    "SAPU",
    "Band",
]

# ── Training Schools ───────────────────────────────────────────────────────────
# (name, location)
TRAINING_SCHOOLS = [
    "NPC",          
    "PTS Gishari",  
    "Mayange CTTC", 
]


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND
# ─────────────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Seed all reference / lookup data (run before seed_equipment)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear", action="store_true",
            help="Delete all existing reference data before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write(self.style.WARNING("Clearing existing reference data..."))
            self._clear_all()

        with transaction.atomic():
            self._seed_statuses()
            self._seed_categories_and_brands()
            self._seed_geography()
            self._seed_org_structure()
            self._seed_training_schools()

        self.stdout.write(self.style.SUCCESS("\nDONE. All reference data seeded."))
        self._print_summary()

    # ── clear ─────────────────────────────────────────────────────────────────

    def _clear_all(self):
        """
        Delete all data in dependency order.
        Equipment (and its dependents: Lending, Deployment, Stock) must be
        removed BEFORE the reference/lookup tables because those FK columns
        use on_delete=PROTECT.
        """
        with transaction.atomic():
            # 1. Dependents of Equipment (child rows first)
            self.stdout.write("  → Deleting Lendings...")
            Lending.objects.all().delete()

            self.stdout.write("  → Deleting Deployments...")
            Deployment.objects.all().delete()

            self.stdout.write("  → Deleting Stock entries...")
            Stock.objects.all().delete()

            self.stdout.write("  → Deleting Equipment records...")
            Equipment.objects.all().delete()

            # 2. Now safe to delete the reference / lookup tables
            self.stdout.write("  → Deleting Training Schools...")
            TrainingSchool.objects.all().delete()

            Station.objects.all().delete()
            DPU.objects.all().delete()
            DPUOffice.objects.all().delete()
            Region.objects.all().delete()
            RegionOffice.objects.all().delete()
            Office.objects.all().delete()
            Department.objects.all().delete()
            Directorate.objects.all().delete()
            Unit.objects.all().delete()
            Brand.objects.all().delete()
            EquipmentCategory.objects.all().delete()
            EquipmentStatus.objects.all().delete()

        self.stdout.write("  Cleared.")

    # ── statuses ───────────────────────────────────────────────────────────────

    def _seed_statuses(self):
        self.stdout.write("Seeding equipment statuses...")
        created = 0
        for name in STATUSES:
            _, was_created = EquipmentStatus.objects.get_or_create(name=name)
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(
            f"  Statuses: {created} created, {len(STATUSES) - created} already existed"
        ))

    # ── categories & brands ────────────────────────────────────────────────────

    def _seed_categories_and_brands(self):
        self.stdout.write("Seeding equipment categories and brands...")
        cat_created   = 0
        brand_created = 0

        for cat_name, brand_names in CATEGORIES_AND_BRANDS.items():
            category, was_created = EquipmentCategory.objects.get_or_create(name=cat_name)
            if was_created:
                cat_created += 1

            for brand_name in brand_names:
                _, bc = Brand.objects.get_or_create(
                    name=brand_name,
                    category=category,
                )
                if bc:
                    brand_created += 1

        self.stdout.write(self.style.SUCCESS(
            f"  Categories: {cat_created} created  |  Brands: {brand_created} created"
        ))

    # ── geography ──────────────────────────────────────────────────────────────

    def _seed_geography(self):
        self.stdout.write("Seeding geography (regions → DPUs → stations)...")
        re_count = dp_count = st_count = 0

        # Step 1: seed Regions from the flat (dpu, region) set
        region_names = sorted({r for _, r in regions_dpus})
        region_map = {}
        for region_name in region_names:
            region, created = Region.objects.get_or_create(name=region_name)
            region_map[region_name] = region
            if created:
                re_count += 1

        # Step 2: seed DPUs
        dpu_map = {}
        for dpu_name, region_name in regions_dpus:
            region = region_map[region_name]
            dpu, created = DPU.objects.get_or_create(
                name=dpu_name,
                defaults={"region": region},
            )
            dpu_map[dpu_name] = dpu
            if created:
                dp_count += 1

        # Step 3: seed Stations
        missing_dpus = set()
        for station_name, dpu_name in STATIONS:
            dpu = dpu_map.get(dpu_name)
            if not dpu:
                missing_dpus.add(dpu_name)
                continue
            _, created = Station.objects.get_or_create(name=station_name, dpu=dpu)
            if created:
                st_count += 1

        if missing_dpus:
            self.stdout.write(self.style.WARNING(
                f"  WARNING — DPUs not found: {sorted(missing_dpus)}"
            ))

        self.stdout.write(self.style.SUCCESS(
            f"  Regions: {re_count}  |  DPUs: {dp_count}  |  Stations: {st_count}"
        ))

    # ── org structure ──────────────────────────────────────────────────────────

    def _seed_org_structure(self):
        self.stdout.write("Seeding organisational units...")
        u_count = 0

        for unit_name in UNITS:
            _, created = Unit.objects.get_or_create(name=unit_name)
            if created:
                u_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"  Units: {u_count} created, {len(UNITS) - u_count} already existed"
        ))

    # ── training schools ───────────────────────────────────────────────────────
    
    # ── training schools ───────────────────────────────────────────────────────

    def _seed_training_schools(self):
        self.stdout.write("Seeding training schools...")
        created = 0

        for name in TRAINING_SCHOOLS:
            _, was_created = TrainingSchool.objects.get_or_create(
                name=name,
                defaults={"location": ""},
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f"  Training Schools: {created} created, "
            f"{len(TRAINING_SCHOOLS) - created} already existed"
        ))


    # ── summary ────────────────────────────────────────────────────────────────

    def _print_summary(self):
        self.stdout.write("\n── Summary ──────────────────────────────────────")
        self.stdout.write(f"  EquipmentStatus    : {EquipmentStatus.objects.count()}")
        self.stdout.write(f"  EquipmentCategory  : {EquipmentCategory.objects.count()}")
        self.stdout.write(f"  Brand              : {Brand.objects.count()}")
        self.stdout.write(f"  RegionOffice       : {RegionOffice.objects.count()}")
        self.stdout.write(f"  Region             : {Region.objects.count()}")
        self.stdout.write(f"  DPUOffice          : {DPUOffice.objects.count()}")
        self.stdout.write(f"  DPU                : {DPU.objects.count()}")
        self.stdout.write(f"  Station            : {Station.objects.count()}")
        self.stdout.write(f"  Unit               : {Unit.objects.count()}")
        self.stdout.write(f"  Directorate        : {Directorate.objects.count()}")
        self.stdout.write(f"  Department         : {Department.objects.count()}")
        self.stdout.write(f"  Office             : {Office.objects.count()}")
        self.stdout.write(f"  TrainingSchool     : {TrainingSchool.objects.count()}")
        self.stdout.write("─────────────────────────────────────────────────")