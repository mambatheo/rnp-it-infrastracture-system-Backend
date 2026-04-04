"""
Management command to seed equipment records.
Run AFTER seed_reference_data has been executed.

Default: 1,000,000 records per category  (~55 categories = 55 M+ total rows).
Use --count to override, --category to target one category, --batch to tune bulk size.
Use --clear to wipe existing equipment data (Lending, Deployment, Stock, Equipment)
before seeding (reference data is kept intact).

Usage:
    python manage.py seed_equipment                          # 1 M per category
    python manage.py seed_equipment --count 100             # quick smoke-test
    python manage.py seed_equipment --category Laptop       # single category only
    python manage.py seed_equipment --batch 2000            # larger bulk batches
    python manage.py seed_equipment --clear                 # wipe equipment then seed
    python manage.py seed_equipment --clear --count 50      # wipe then seed 50 per cat
"""
import random
import string
from contextlib import contextmanager
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models.signals import post_save

from equipment.models import (
    Equipment, EquipmentCategory, EquipmentStatus, Brand,
    Region, DPU, Station,
    Unit, Directorate, Department, Office,
    Stock, Deployment, Lending, TrainingSchool,
)

try:
    from equipment.signals import auto_classify_equipment
    _HAS_SIGNAL = True
except ImportError:
    _HAS_SIGNAL = False

User = get_user_model()

# ─────────────────────────────────────────────────────────────────────────────
# MODEL NAMES PER CATEGORY
# ─────────────────────────────────────────────────────────────────────────────

MODELS = {
    'Desktop': [
        'OptiPlex 3090', 'OptiPlex 5090', 'OptiPlex 7090',
        'ProDesk 400 G7', 'ProDesk 600 G6', 'EliteDesk 800 G6',
        'ThinkCentre M70q', 'ThinkCentre M90s', 'IdeaCentre 5',
        'Aspire TC-895', 'Veriton M4680G', 'ExpertCenter D7',
        'iMac 24-inch', 'Mac mini M2', 'ESPRIMO P558', 'CELSIUS W5010',
    ],
    'Laptop': [
        'Latitude 5520', 'Latitude 7420', 'Latitude 9420',
        'XPS 13', 'XPS 15', 'Inspiron 15 3000',
        'EliteBook 840 G8', 'EliteBook 850 G8', 'ProBook 450 G8',
        'ThinkPad T14', 'ThinkPad X1 Carbon', 'ThinkPad E15',
        'IdeaPad 5', 'Legion 5 Pro', 'VivoBook 15', 'ZenBook 14',
        'MacBook Pro 14', 'MacBook Air M2', 'Swift 5', 'Aspire 5',
        'Galaxy Book Pro', 'MateBook D15', 'MateBook X Pro',
    ],
    'Server': [
        'PowerEdge R750', 'PowerEdge R650', 'PowerEdge T550',
        'ProLiant DL380 Gen10', 'ProLiant DL360 Gen10', 'ProLiant ML350 Gen10',
        'ThinkSystem SR650', 'ThinkSystem ST550',
        'UCS C220 M6', 'UCS C240 M6',
        'FusionServer 2288H V6', 'PRIMERGY RX2540 M6',
    ],
    'Workstation': [
        'Precision 3650', 'Precision 5820', 'Precision 7920',
        'Z2 G8', 'Z4 G4', 'Z6 G4', 'Z8 G4',
        'ThinkStation P340', 'ThinkStation P620', 'ProArt Station PA90',
    ],
    'Tablet': [
        'iPad Pro 12.9', 'iPad Air 5th Gen', 'iPad 10th Gen',
        'Galaxy Tab S8', 'Galaxy Tab S8+', 'Galaxy Tab A8',
        'Tab P12 Pro', 'MatePad Pro 12.6', 'Surface Pro 9', 'Fire HD 10',
    ],
    'Smartphone': [
        'iPhone 14 Pro', 'iPhone 13', 'iPhone 12',
        'Galaxy S23', 'Galaxy A54', 'Galaxy A34',
        'P50 Pro', 'Nova 10 Pro', 'Redmi Note 12',
        'Nokia G60', 'Nokia XR20', 'Reno 10 Pro',
    ],
    'Printer': [
        'LaserJet Pro M404dn', 'LaserJet Pro MFP M428fdw',
        'Color LaserJet Pro M454dw', 'PIXMA G6020',
        'imageCLASS MF445dw', 'EcoTank ET-4850',
        'WorkForce Pro WF-4830', 'HL-L2350DW', 'MFC-L2750DW',
        'Phaser 6510', 'VersaLink C405', 'ECOSYS M2540dn',
    ],
    'Scanner': [
        'imageFORMULA DR-C225 II', 'CanoScan LiDE 400',
        'ScanJet Pro 3600 f1', 'Perfection V39', 'WorkForce ES-500W',
        'ADS-3600W', 'fi-7300NX', 'fi-800R', 'Alaris S2060w',
    ],
    'Photocopier': [
        'imageRUNNER ADVANCE DX 4935i', 'imageRUNNER 2630i',
        'AltaLink C8145', 'WorkCentre 7845', 'MP 2555SP', 'IM 350F',
        'TASKalfa 2554ci', 'bizhub C3350i', 'MX-2651',
    ],
    'Plotter': [
        'DesignJet T650', 'DesignJet T830 MFP',
        'imagePROGRAF TX-3000', 'SureColor T3470', 'VersaCAMM VS-540i',
    ],
    'Fax Machine': [
        'MFC-J995DW', 'FAX-2840', 'IntelliFax-4100e',
        'KX-MB2085', 'FAX-L170',
    ],
    'Network Switch': [
        'Catalyst 9200L', 'Catalyst 9300', 'Catalyst 9500',
        'Aruba 2930F', 'Aruba 3810M', 'Aruba 6300M',
        'EX2300-24T', 'CloudEngine S5731', 'DGS-1210-28',
        'GS728TPv2', 'UniFi USW-Pro-24',
    ],
    'Router': [
        'ISR 4321', 'ISR 4351', 'ASR 1001-X', 'MX204', 'MX480',
        'CCR2004-1G-12S+2XS', 'EdgeRouter 12', 'UniFi Dream Machine Pro',
        'Archer AX6000', 'Nighthawk AX12', 'RT-AX88U',
    ],
    'Firewall': [
        'ASA 5506-X', 'ASA 5508-X', 'Firepower 2110',
        'FortiGate 60F', 'FortiGate 100F', 'FortiGate 200F',
        'PA-820', 'PA-3220', 'SRX300', 'TZ470', 'XG 125',
    ],
    'Access Point': [
        'Catalyst 9115AX', 'Catalyst 9120AX',
        'AP-515', 'AP-635', 'R750', 'R850',
        'EAP670', 'WAX630', 'UniFi U6 Pro', 'UniFi U6 LR',
    ],
    'Modem': [
        'HG8245H5', 'HG8546M', 'EchoLife EG8145V5',
        'Archer VR900v', 'ISR 891W', 'VMG3625-T50B',
    ],
    'Hub': [
        'USB 3.0 Hub 7-Port', 'USB-C Hub 10-in-1',
        'Powered USB Hub 13-Port', 'Hi-Speed USB 2.0 Hub',
    ],
    'Repeater': [
        'RE650', 'RE705X', 'RE900XD', 'EX7500', 'EX8000',
    ],
    'Network Gateway': [
        'SonicWall TZ270', 'SonicWall NSa 2700',
        'Cisco 819 IoT GW', 'Cradlepoint E3000', 'Peplink Balance 310X',
    ],
    'Network Bridge': [
        'AirBridge NanoBeam 5AC', 'LiteBeam 5AC Gen2',
        'PowerBeam 5AC ISO', 'DLB-5-15ac',
    ],
    'IP Phone': [
        'CP-8841', 'CP-8851', 'CP-8861',
        'VVX 501', 'VVX 601', 'T54W', 'T57W', 'T58A',
        'GXP2170', 'GXP2135', 'D385', '9608G',
    ],
    'DECT Phone': [
        'KX-TGP600', 'KX-TPA60',
        'Gigaset S700H Pro', 'CD490', 'VTech DS6151',
    ],
    'PBX System': [
        'IP Office 500 V2', 'Unified CM 12.5', 'Unified CM 14',
        'KX-NS700', '3CX Phone System v18', 'Yeastar S100',
    ],
    'Video Conferencing': [
        'Webex Room Kit', 'Webex Board 55', 'Group 500', 'Studio X50',
        'Rally Bar', 'MeetUp', 'Zoom Rooms Kit', 'IdeaHub S2',
    ],
    'TV Screen': [
        'QN85B 85in', 'UN75TU7000', 'The Frame 65in',
        'OLED C2 65in', 'QNED90 75in', 'BRAVIA XR A95K 65in',
        'QLed 75Q60B', 'Hisense U8H 65in',
    ],
    'Projector': [
        'EB-L1505U', 'EB-PU2010B', 'EB-735Fi', 'W2700i', 'TK850i',
        'VPL-FHZ85', 'EH416', 'EH470', 'PX748-4K', 'LS831WU',
    ],
    'Interactive Whiteboard': [
        'SMART Board MX265', 'SMART Board 7075',
        'ActivPanel 9 75in', 'RP7502', 'RP6502',
    ],
    'Display Panel': [
        'QM55B', 'QM75B', 'QM98B', 'UH5F-E 55in',
        'MultiSync ME651', 'BDL4650D', 'BDL5588XC',
    ],
    'UPS': [
        'Smart-UPS 1500VA', 'Smart-UPS 3000VA', 'Smart-UPS RT 5000VA',
        '9PX 1000i', '9PX 2200i', 'PR1000ELCD', 'PR2200ELCDRT2U',
        'GXT5-1000MR230', 'NETYS PR 2200VA', 'ITYS-E 1200VA',
    ],
    'PDU': [
        'AP7900B', 'AP7901B', 'AP7968B',
        'ePDU G3 Metered', 'PX3-5190V', 'MPH2',
    ],
    'ATS': [
        'AP7721', 'AP7722', 'AP4450A', 'STS 16A', 'STS 32A',
    ],
    'Generator': [
        'QSB7-G7 150kVA', 'QSB5-G7 100kVA',
        'C175 D5B 175kVA', 'C250 D5 250kVA', 'KD200 200kVA', 'KD100 100kVA',
    ],
    'External HDD': [
        'Backup Plus Portable 2TB', 'Expansion Portable 1TB',
        'My Passport Ultra 4TB', 'Canvio Advance 2TB', 'T7 Portable SSD 1TB',
        'Rugged Mini 1TB',
    ],
    'Flash Drive': [
        'Ultra USB 3.0 128GB', 'Extreme Go USB 3.1 256GB',
        'DataTraveler 100 G3 64GB', 'Bar Plus 256GB', 'JetFlash 790 64GB',
    ],
    'SSD': [
        '870 EVO 1TB', '970 EVO Plus 2TB', '980 Pro 1TB',
        'Blue SN570 1TB', 'Black SN850X 2TB', 'BarraCuda 510 1TB',
        'MX500 2TB', 'P5 Plus 1TB',
    ],
    'NAS': [
        'DS923+', 'DS1522+', 'RS1221+', 'TS-464', 'TS-873A',
        'My Cloud EX2 Ultra', 'ReadyNAS 626X',
    ],
    'Tape Drive': [
        'StoreEver LTO-8', 'StoreEver MSL2024',
        'PowerVault LTO-8', 'IBM TS2280', 'Scalar i3',
    ],
    'Memory Card': [
        'Extreme Pro SDXC 256GB', 'Ultra SDXC 128GB',
        'PRO Plus MicroSDXC 256GB', 'EVO Select MicroSDXC 512GB',
        'Canvas React Plus 128GB',
    ],
    'Mouse': [
        'MX Master 3S', 'MX Anywhere 3', 'M720 Triathlon',
        'Arc Mouse', 'MS116', 'M100', 'M185', 'Genius DX-120',
    ],
    'Keyboard': [
        'MX Keys', 'K780 Multi-Device', 'K380',
        'KB216', 'KB522', 'HP 125 Wired', 'Genius SlimStar 126',
    ],
    'Monitor': [
        'UltraSharp U2722D', 'P2422H', 'S2722QC',
        'EliteDisplay E27q', 'Z27xs G3 QHD',
        '27UK850-W', '32UN880-B', 'U32P2 4K', 'ThinkVision T27h',
        'ProArt PA278QV', 'VG279QM', 'EW3270U', 'VP3268-4K', 'Acer XV272U',
    ],
    'Webcam': [
        'C920s Pro HD', 'C922x Pro Stream', 'StreamCam',
        'LifeCam Studio', 'Kiyo Pro', 'Kiyo X',
    ],
    'Headset': [
        'H390', 'H570e', 'Zone Wired',
        'Evolve2 30', 'Evolve2 65', 'Blackwire 3225',
        'WH-1000XM5', 'HD 450BT',
    ],
    'Decoder': [
        'GS8120', 'GS9120', 'GS7010',
        'Nagra 7', 'Pace RNG200N', 'DCX3220',
    ],
    'Digital Receiver': [
        'DSB-H470N', 'DSB-H510N', 'Tiger T8 Ultra',
        'Geant GN-DS 650HD', 'Openbox S6 Pro+',
    ],
    'CCTV Camera': [
        'DS-2CD2143G2-I', 'DS-2CD2347G2-LU', 'DS-2DE4A425IWG',
        'IPC-HDW2831T-AS', 'P3245-V', 'Q6135-LE',
        'H5A 2MP', 'FLEXIDOME 5100i', 'QNV-8080R',
    ],
    'DVR/NVR': [
        'DS-7208HQHI-M1', 'DS-7216HQHI-M2',
        'DS-7608NI-I2/8P', 'XVR5108H-4KL-I3',
        'NVR308-32X', 'S9008', 'S9016',
    ],
    'Biometric Device': [
        'SpeedFace-V5L', 'SpeedFace-V4L', 'ProFace X',
        'BioStation 3', 'BioStation A2', 'FaceStation F2',
        'MorphoWave Compact', 'AC7000',
    ],
    'Card Reader': [
        'SCR3310v2', 'ACR39U-I1', 'OmniKey 3121',
        'OmniKey 5427CK', 'Gemalto IDBridge CT700',
    ],
    'Barcode Scanner': [
        'DS2208', 'DS8178', 'DS3678',
        'Xenon 1952g', 'Granit 1981i', 'PowerScan PD9500', '3310g',
    ],
    'Radio / Walkie-Talkie': [
        'APX 6000', 'APX 8000', 'SLR 8000',
        'TK-3402U16P', 'NX-5200', 'PD785G', 'PD985',
        'IC-F52D', 'BF-F8HP', 'UV-5R Pro',
    ],
    'GPS Device': [
        'GPSMAP 66i', 'Montana 700i', 'eTrex 32x',
        'R8s GNSS', 'GR-i3', 'Viva GS16', 'MS60',
    ],
    'Cable / Connector': [
        'Cat6 Patch Cable 1m', 'Cat6 Patch Cable 2m', 'Cat6 Patch Cable 5m',
        'Cat6A Patch Cable 3m', 'HDMI 2.1 Cable 2m', 'HDMI 2.0 Cable 5m',
        'DisplayPort 1.4 Cable', 'Fiber LC-LC Duplex 10m',
        'SFP+ DAC Twinax 3m',
    ],
    'Rack / Cabinet': [
        '42U NetShelter SX', '24U NetShelter SX', '12U NetShelter WX',
        '42U RS Series', '22U RS Series', '42U TS IT', '26U TS IT',
    ],
    'KVM Switch': [
        'CS1768', 'CS1716i', 'KN8164V', 'KVM-0831P',
        'NetDirector B064-008-01-IPG', 'Dell KVM 2161DS',
    ],
    'Peripheral': [
        'USB Hub 4-Port', 'Wireless Presenter', 'Numeric Keypad',
        'Drawing Tablet', 'USB Sound Card', 'Generic Peripheral',
    ],
}

_FALLBACK_MODELS = ['Model A', 'Model B', 'Model C', 'Model X', 'Model Pro', 'Model Plus']

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

_DIGITS          = string.digits
_SERIAL_PREFIXES = ['SN', 'SER', 'SRL', 'EQ', 'RNP']


def _random_serial():
    prefix = random.choice(_SERIAL_PREFIXES)
    digits = ''.join(random.choices(_DIGITS, k=10))
    return f'{prefix}-{digits}'


def _random_marking(seq: int) -> str:
    return f'RNP/{seq:010d}'


_DATE_START = date(2015, 1, 1)
_DATE_RANGE = (date(2024, 12, 31) - _DATE_START).days


def _random_date() -> date:
    return _DATE_START + timedelta(days=random.randint(0, _DATE_RANGE))


@contextmanager
def _signal_muted(sender):
    if _HAS_SIGNAL:
        post_save.disconnect(auto_classify_equipment, sender=sender)
    try:
        yield
    finally:
        if _HAS_SIGNAL:
            post_save.connect(auto_classify_equipment, sender=sender)


def _build_location_pool(regions, dpus, stations, units, training_schools, offices):
    """
    Build a flat list of location-kwarg dicts for random.choice().

    Weights (approximate share of pool):
      Stations          40 %  – most equipment lives at a specific station
      DPUs              30 %
      Offices           10 %
      Units             10 %
      Regions            5 %  – HQ / unassigned
      Training Schools   5 %
    """
    dpu_region = {d.id: d.region for d in dpus}
    stn_dpu    = {s.id: s.dpu    for s in stations}

    pool = []

    for s in stations:
        entry = {'station': s}
        dpu = stn_dpu.get(s.id)
        if dpu:
            entry['dpu'] = dpu
            rgn = dpu_region.get(dpu.id)
            if rgn:
                entry['region'] = rgn
        pool.extend([entry] * 4)          # weight 4

    for d in dpus:
        entry = {'dpu': d}
        rgn = dpu_region.get(d.id)
        if rgn:
            entry['region'] = rgn
        pool.extend([entry] * 3)          # weight 3

    for o in offices:
        entry = {'office': o}
        try:
            if o.region: entry['region'] = o.region
            if o.dpu:    entry['dpu']    = o.dpu
        except Exception:
            pass
        pool.extend([entry] * 1)          # weight 1

    for u in units:
        pool.append({'unit': u})           # weight 1

    for r in regions:
        pool.extend([{'region': r}] * 1)  # weight 1

    for ts in training_schools:
        pool.extend([{'training_school': ts}] * 1)  # weight 1

    return pool


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND
# ─────────────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Seed equipment records — default 1,000,000 per category (run after seed_reference_data)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count', type=int, default=1_000_000,
            help='Records per category (default: 1 000 000)',
        )
        parser.add_argument(
            '--category', type=str, default=None,
            help='Only seed this category name (case-insensitive)',
        )
        parser.add_argument(
            '--batch', type=int, default=2_000,
            help='Bulk-create batch size (default: 2000).',
        )
        parser.add_argument(
            '--clear', action='store_true',
            help=(
                'Delete all existing equipment records (Lending, Deployment, '
                'Stock, Equipment) before seeding. Reference data is preserved.'
            ),
        )

    def handle(self, *args, **options):
        count_per_cat = options['count']
        only_category = options['category']
        batch_size    = options['batch']

        # ── Optional clear ──────────────────────────────────────────────────
        if options['clear']:
            self.stdout.write(self.style.WARNING(
                'Clearing existing equipment records (Lending → Deployment → Stock → Equipment)...'
            ))
            with transaction.atomic():
                lend_count = Lending.objects.count()
                Lending.objects.all().delete()
                self.stdout.write(f'  Deleted {lend_count:,} Lending record(s).')

                dep_count = Deployment.objects.count()
                Deployment.objects.all().delete()
                self.stdout.write(f'  Deleted {dep_count:,} Deployment record(s).')

                stock_count = Stock.objects.count()
                Stock.objects.all().delete()
                self.stdout.write(f'  Deleted {stock_count:,} Stock record(s).')

                eq_count = Equipment.objects.count()
                Equipment.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(
                    f'  Deleted {eq_count:,} Equipment record(s). Done.'
                ))

        # ── Load all reference objects once ────────────────────────────────
        self.stdout.write('Loading reference data from DB...')

        statuses         = list(EquipmentStatus.objects.all())
        regions          = list(Region.objects.all())
        dpus             = list(DPU.objects.select_related('region').all())
        stations         = list(Station.objects.select_related('dpu__region').all())
        units            = list(Unit.objects.all())
        offices          = list(Office.objects.select_related('region', 'dpu').all())
        training_schools = list(TrainingSchool.objects.all())
        admin            = (
            User.objects.filter(is_superuser=True).first()
            or User.objects.first()
        )

        if not statuses:
            self.stderr.write(self.style.ERROR(
                'No statuses found — run seed_reference_data first.'))
            return
        if not (regions or dpus or units):
            self.stderr.write(self.style.ERROR(
                'No location data found — run seed_reference_data first.'))
            return

        self.stdout.write('Building location pool...')
        loc_pool = _build_location_pool(
            regions, dpus, stations, units, training_schools, offices
        )
        self.stdout.write(
            f'  Pool size: {len(loc_pool):,} slots  '
            f'({len(stations):,} stations | {len(dpus):,} DPUs | '
            f'{len(units):,} units | {len(training_schools):,} training schools)'
        )

        if not loc_pool:
            self.stderr.write(self.style.ERROR(
                'Location pool is empty — no stations, DPUs, units, or regions found. '
                'Run seed_reference_data first.'
            ))
            return

        # ── Resolve categories ─────────────────────────────────────────────
        if only_category:
            categories = list(EquipmentCategory.objects.filter(name__iexact=only_category))
            if not categories:
                self.stderr.write(self.style.ERROR(f'Category "{only_category}" not found.'))
                return
        else:
            categories = list(EquipmentCategory.objects.all())

        # Brand lookup: category_id → [Brand, …]
        brand_map: dict[int, list] = {}
        for brand in Brand.objects.select_related('category').all():
            if brand.category_id:
                brand_map.setdefault(brand.category_id, []).append(brand)

        # ── Active status IDs (for deployment_date logic) ──────────────────
        active_status_ids = set(
            EquipmentStatus.objects.filter(name='Active').values_list('id', flat=True)
        )

        # ── Global sequence base (avoids duplicate marking codes) ──────────
        seq_base = Equipment.objects.count()

        total_created = 0

        with _signal_muted(Equipment):
            for category in categories:
                cat_brands = brand_map.get(category.id, [])
                cat_models = MODELS.get(category.name, _FALLBACK_MODELS)

                self.stdout.write(
                    f'  Seeding {count_per_cat:,} × {category.name}  '
                    f'({len(cat_brands)} brands, {len(cat_models)} models)...'
                )

                cat_created = 0
                batch: list[Equipment] = []

                with transaction.atomic():
                    for i in range(count_per_cat):
                        seq_base += 1

                        brand  = random.choice(cat_brands) if cat_brands else None
                        model  = random.choice(cat_models)
                        status = random.choice(statuses)
                        intent = random.choice(['Stock', 'Deployment'])

                        eq = Equipment(
                            name                = f'{category.name} {model}',
                            equipment_type      = category,
                            registration_intent = intent,
                            brand               = brand,
                            model               = model,
                            status              = status,
                            serial_number       = _random_serial(),
                            marking_code        = _random_marking(seq_base),
                            deployment_date     = (
                                _random_date() if status.id in active_status_ids else None
                            ),
                            created_by          = admin,
                            updated_by          = admin,
                        )

                        # Apply location FKs from pool
                        for field, value in random.choice(loc_pool).items():
                            setattr(eq, field, value)

                        batch.append(eq)

                        if len(batch) >= batch_size:
                            Equipment.objects.bulk_create(batch, ignore_conflicts=True)
                            cat_created += len(batch)
                            batch = []

                            if cat_created > 0 and cat_created % 100_000 == 0:
                                self.stdout.write(
                                    f'    … {cat_created:,} / {count_per_cat:,}'
                                )

                    # Flush remaining rows
                    if batch:
                        Equipment.objects.bulk_create(batch, ignore_conflicts=True)
                        cat_created += len(batch)

                total_created += cat_created
                self.stdout.write(self.style.SUCCESS(
                    f'    ✓ {category.name}: {cat_created:,} records inserted'
                ))

        self.stdout.write(self.style.SUCCESS(
            f'\nDONE.  This run: {total_created:,} records'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Grand total in DB: {Equipment.objects.count():,}'
        ))