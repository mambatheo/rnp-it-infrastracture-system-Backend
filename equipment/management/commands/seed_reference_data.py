"""
Management command to seed all reference / lookup data.
Must be run BEFORE seed_equipment.

Creates:
  - EquipmentStatus
  - EquipmentCategory  (with matching Brand entries)
  - RegionOffice  →  Region  →  DPUOffice  →  DPU  →  Station
  - Unit  →  Directorate  →  Department  →  Office

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
# Rwanda-realistic structure: region offices → regions → DPU offices → DPUs → stations

GEOGRAPHY = {
    "Kigali City Regional Office": {
        "regions": {
            "Nyarugenge": {
                "dpu_office": "Nyarugenge DPU Office",
                "dpus": {
                    "Nyarugenge DPU": ["Gitega Station", "Nyamirambo Station", "Kimisagara Station"],
                    "Kiyovu DPU":     ["Kiyovu Station", "Biryogo Station"],
                },
            },
            "Gasabo": {
                "dpu_office": "Gasabo DPU Office",
                "dpus": {
                    "Gasabo DPU":    ["Kimironko Station", "Remera Station", "Gisozi Station"],
                    "Kacyiru DPU":   ["Kacyiru Station", "Kibagabaga Station"],
                },
            },
            "Kicukiro": {
                "dpu_office": "Kicukiro DPU Office",
                "dpus": {
                    "Kicukiro DPU":  ["Gatenga Station", "Niboye Station", "Kagarama Station"],
                    "Gikondo DPU":   ["Gikondo Station", "Masaka Station"],
                },
            },
        }
    },
    "Northern Regional Office": {
        "regions": {
            "Musanze": {
                "dpu_office": "Musanze DPU Office",
                "dpus": {
                    "Musanze DPU":   ["Muhoza Station", "Kinigi Station"],
                    "Cyuve DPU":     ["Cyuve Station"],
                },
            },
            "Rulindo": {
                "dpu_office": "Rulindo DPU Office",
                "dpus": {
                    "Rulindo DPU":   ["Base Station", "Buyoga Station"],
                },
            },
            "Gakenke": {
                "dpu_office": "Gakenke DPU Office",
                "dpus": {
                    "Gakenke DPU":   ["Gakenke Station", "Coko Station"],
                },
            },
        }
    },
    "Southern Regional Office": {
        "regions": {
            "Huye": {
                "dpu_office": "Huye DPU Office",
                "dpus": {
                    "Huye DPU":      ["Ngoma Station", "Tumba Station"],
                    "Mbazi DPU":     ["Mbazi Station"],
                },
            },
            "Nyanza": {
                "dpu_office": "Nyanza DPU Office",
                "dpus": {
                    "Nyanza DPU":    ["Nyanza Station", "Busasamana Station"],
                },
            },
            "Muhanga": {
                "dpu_office": "Muhanga DPU Office",
                "dpus": {
                    "Muhanga DPU":   ["Shyogwe Station", "Rongi Station"],
                },
            },
        }
    },
    "Eastern Regional Office": {
        "regions": {
            "Rwamagana": {
                "dpu_office": "Rwamagana DPU Office",
                "dpus": {
                    "Rwamagana DPU": ["Rwamagana Station", "Fumbwe Station"],
                },
            },
            "Kayonza": {
                "dpu_office": "Kayonza DPU Office",
                "dpus": {
                    "Kayonza DPU":   ["Kabarondo Station", "Mukarange Station"],
                },
            },
            "Kirehe": {
                "dpu_office": "Kirehe DPU Office",
                "dpus": {
                    "Kirehe DPU":    ["Kirehe Station", "Nasho Station"],
                },
            },
        }
    },
    "Western Regional Office": {
        "regions": {
            "Rubavu": {
                "dpu_office": "Rubavu DPU Office",
                "dpus": {
                    "Rubavu DPU":    ["Gisenyi Station", "Nyundo Station"],
                    "Rugerero DPU":  ["Rugerero Station"],
                },
            },
            "Karongi": {
                "dpu_office": "Karongi DPU Office",
                "dpus": {
                    "Karongi DPU":   ["Bwishyura Station", "Rugabano Station"],
                },
            },
            "Rusizi": {
                "dpu_office": "Rusizi DPU Office",
                "dpus": {
                    "Rusizi DPU":    ["Bugarama Station", "Gihundwe Station"],
                },
            },
        }
    },
}

# ── Organisational units ───────────────────────────────────────────────────────

ORG_STRUCTURE = {
    "ICT Unit": {
        "directorates": {
            "ICT Infrastructure Directorate": {
                "departments": ["Networks Department", "Systems Department", "Data Centre Department"],
            },
            "ICT Services Directorate": {
                "departments": ["Helpdesk Department", "Software Department", "Security Department"],
            },
        }
    },
    "Finance Unit": {
        "directorates": {
            "Budget Directorate": {
                "departments": ["Planning Department", "Execution Department"],
            },
            "Accounting Directorate": {
                "departments": ["Payroll Department", "Reporting Department"],
            },
        }
    },
    "Administration Unit": {
        "directorates": {
            "Human Resources Directorate": {
                "departments": ["Recruitment Department", "Training Department"],
            },
            "Logistics Directorate": {
                "departments": ["Procurement Department", "Assets Department"],
            },
        }
    },
    "Operations Unit": {
        "directorates": {
            "Field Operations Directorate": {
                "departments": ["Deployment Department", "Monitoring Department"],
            },
            "Intelligence Directorate": {
                "departments": ["Analysis Department", "Investigations Department"],
            },
        }
    },
    "Legal Unit": {
        "directorates": {
            "Legal Affairs Directorate": {
                "departments": ["Contracts Department", "Compliance Department"],
            },
        }
    },
    "Communications Unit": {
        "directorates": {
            "Public Affairs Directorate": {
                "departments": ["Media Department", "Publications Department"],
            },
        }
    },
}


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

        self.stdout.write(self.style.SUCCESS("\nDONE. All reference data seeded."))
        self._print_summary()

    # ── clear ─────────────────────────────────────────────────────────────────

    def _clear_all(self):
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
        self.stdout.write("Seeding geography (region offices → regions → DPUs → stations)...")
        ro_count = re_count = do_count = dp_count = st_count = 0

        for ro_name, ro_data in GEOGRAPHY.items():
            region_office, created = RegionOffice.objects.get_or_create(name=ro_name)
            if created:
                ro_count += 1

            for region_name, region_data in ro_data["regions"].items():
                region, created = Region.objects.get_or_create(
                    name=region_name,
                    defaults={"region_office": region_office},
                )
                if created:
                    re_count += 1

                dpu_office_name = region_data.get("dpu_office")
                dpu_office = None
                if dpu_office_name:
                    dpu_office, created = DPUOffice.objects.get_or_create(name=dpu_office_name)
                    if created:
                        do_count += 1

                for dpu_name, station_names in region_data["dpus"].items():
                    dpu, created = DPU.objects.get_or_create(
                        name=dpu_name,
                        region=region,          # part of unique_dpu_per_region
                        defaults={
                            "dpu_office": dpu_office,
                        },
                    )
                    if created:
                        dp_count += 1

                    for station_name in station_names:
                        _, created = Station.objects.get_or_create(
                            name=station_name,
                            dpu=dpu,            # part of unique_station_per_dpu
                        )
                        if created:
                            st_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"  RegionOffices: {ro_count}  |  Regions: {re_count}  |  "
            f"DPUOffices: {do_count}  |  DPUs: {dp_count}  |  Stations: {st_count}"
        ))

    # ── org structure ──────────────────────────────────────────────────────────

    def _seed_org_structure(self):
        self.stdout.write("Seeding organisational structure (units → directorates → departments → offices)...")
        u_count = d_count = dept_count = o_count = 0

        # Office requires both region AND dpu (non-nullable), and clean() validates
        # that dpu.region == region. Pre-load a list of valid (region, dpu) pairs.
        dpu_pairs = list(
            DPU.objects.select_related("region").all()
        )
        if not dpu_pairs:
            self.stdout.write(self.style.WARNING(
                "  No DPUs found — skipping Office creation. "
                "Run seed_reference_data again after geography is seeded."
            ))
            dpu_pairs = []

        import itertools
        dpu_cycle = itertools.cycle(dpu_pairs) if dpu_pairs else None

        for unit_name, unit_data in ORG_STRUCTURE.items():
            unit, created = Unit.objects.get_or_create(name=unit_name)
            if created:
                u_count += 1

            for dir_name, dir_data in unit_data["directorates"].items():
                directorate, created = Directorate.objects.get_or_create(
                    name=dir_name,
                    defaults={"unit": unit},
                )
                if created:
                    d_count += 1

                for dept_name in dir_data["departments"]:
                    department, created = Department.objects.get_or_create(
                        name=dept_name,
                        defaults={"directorate": directorate},
                    )
                    if created:
                        dept_count += 1

                    if dpu_cycle is None:
                        continue

                    # Pick the next dpu+region pair — guaranteed consistent
                    dpu    = next(dpu_cycle)
                    region = dpu.region

                    office_name = f"{dept_name} Office"
                    _, created = Office.objects.get_or_create(
                        name=office_name,
                        defaults={
                            "department": department,
                            "region":     region,
                            "dpu":        dpu,
                        },
                    )
                    if created:
                        o_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"  Units: {u_count}  |  Directorates: {d_count}  |  "
            f"Departments: {dept_count}  |  Offices: {o_count}"
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
        self.stdout.write("─────────────────────────────────────────────────")