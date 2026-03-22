"""
Management command to seed 10,000 equipment records per category.
Run AFTER seed_reference_data has been executed.

Usage:
    python manage.py seed_equipment
    python manage.py seed_equipment --count 100        # smaller batch for testing
    python manage.py seed_equipment --category Laptop  # single category only
"""
import random
import string
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from equipment.models import (
    Equipment, EquipmentCategory, EquipmentStatus, Brand,
    Region, DPU, Station, RegionOffice, DPUOffice,
    Unit, Directorate, Department, Office,
)

# ─── Realistic model names per category ───────────────────────────────────────

MODELS = {
    'Desktop': [
        'OptiPlex 3090', 'OptiPlex 5090', 'OptiPlex 7090',
        'ProDesk 400 G7', 'ProDesk 600 G6', 'EliteDesk 800 G6',
        'ThinkCentre M70q', 'ThinkCentre M90s', 'IdeaCentre 5',
        'Aspire TC-895', 'Veriton M4680G',
        'ROG Strix G15', 'ExpertCenter D7',
        'iMac 24-inch', 'Mac mini M2',
        'ESPRIMO P558', 'CELSIUS W5010',
    ],
    'Laptop': [
        'Latitude 5520', 'Latitude 7420', 'Latitude 9420',
        'XPS 13', 'XPS 15', 'Inspiron 15 3000',
        'EliteBook 840 G8', 'EliteBook 850 G8', 'ProBook 450 G8',
        'ThinkPad T14', 'ThinkPad X1 Carbon', 'ThinkPad E15',
        'IdeaPad 5', 'Legion 5 Pro',
        'VivoBook 15', 'ZenBook 14', 'ExpertBook B9',
        'MacBook Pro 14"', 'MacBook Air M2',
        'Swift 5', 'Aspire 5',
        'Galaxy Book Pro', 'Galaxy Book2 360',
        'MateBook D15', 'MateBook X Pro',
    ],
    'Server': [
        'PowerEdge R750', 'PowerEdge R650', 'PowerEdge T550',
        'ProLiant DL380 Gen10', 'ProLiant DL360 Gen10', 'ProLiant ML350 Gen10',
        'ThinkSystem SR650', 'ThinkSystem ST550',
        'System x3650 M5', 'System x3550 M5',
        'UCS C220 M6', 'UCS C240 M6',
        'FusionServer 2288H V6', 'FusionServer 5885H V6',
        'PRIMERGY RX2540 M6',
    ],
    'Workstation': [
        'Precision 3650', 'Precision 5820', 'Precision 7920',
        'Z2 G8', 'Z4 G4', 'Z6 G4', 'Z8 G4',
        'ThinkStation P340', 'ThinkStation P620',
        'ProArt Station PA90',
    ],
    'Tablet': [
        'iPad Pro 12.9"', 'iPad Air 5th Gen', 'iPad 10th Gen',
        'Galaxy Tab S8', 'Galaxy Tab S8+', 'Galaxy Tab A8',
        'Tab P12 Pro', 'Tab M10 Plus',
        'MatePad Pro 12.6',
        'Surface Pro 9', 'Surface Go 3',
        'Fire HD 10',
    ],
    'Smartphone': [
        'iPhone 14 Pro', 'iPhone 13', 'iPhone 12',
        'Galaxy S23', 'Galaxy A54', 'Galaxy A34',
        'P50 Pro', 'Nova 10 Pro',
        'Redmi Note 12', 'Xiaomi 13 Pro',
        'Nokia G60', 'Nokia XR20',
        'Reno 10 Pro', 'Oppo A78',
    ],
    'Printer': [
        'LaserJet Pro M404dn', 'LaserJet Pro MFP M428fdw',
        'Color LaserJet Pro M454dw',
        'PIXMA G6020', 'imageCLASS MF445dw',
        'EcoTank ET-4850', 'WorkForce Pro WF-4830',
        'HL-L2350DW', 'MFC-L2750DW',
        'Phaser 6510', 'VersaLink C405',
        'ECOSYS M2540dn', 'ECOSYS P2040dw',
        'SP 3600DN', 'IM 430F',
    ],
    'Scanner': [
        'imageFORMULA DR-C225 II', 'CanoScan LiDE 400',
        'ScanJet Pro 3600 f1', 'ScanJet Enterprise Flow 7000 s3',
        'Perfection V39', 'WorkForce ES-500W',
        'ADS-3600W', 'ADS-2700W',
        'fi-7300NX', 'fi-800R',
        'Alaris S2060w',
    ],
    'Photocopier': [
        'imageRUNNER ADVANCE DX 4935i', 'imageRUNNER 2630i',
        'AltaLink C8145', 'WorkCentre 7845',
        'MP 2555SP', 'IM 350F',
        'TASKalfa 2554ci', 'TASKalfa 3554ci',
        'bizhub C3350i', 'bizhub 4752',
        'MX-2651', 'MX-3571',
    ],
    'Plotter': [
        'DesignJet T650', 'DesignJet T830 MFP',
        'imagePROGRAF TX-3000', 'imagePROGRAF TM-300',
        'SureColor T3470', 'SureColor T5470',
        'VersaCAMM VS-540i',
    ],
    'Fax Machine': [
        'MFC-J995DW', 'FAX-2840', 'IntelliFax-4100e',
        'KX-MB2085', 'KX-FLB803',
        'LaserJet MFP M148dw',
        'FAX-L170',
    ],
    'Network Switch': [
        'Catalyst 9200L', 'Catalyst 9300', 'Catalyst 9500',
        'Aruba 2930F', 'Aruba 3810M', 'Aruba 6300M',
        'EX2300-24T', 'EX3400-48T',
        'CloudEngine S5731', 'CloudEngine S6730',
        'DGS-1210-28', 'DGS-3130-54TS',
        'GS728TPv2', 'XS708T',
        'UniFi USW-Pro-24',
    ],
    'Router': [
        'ISR 4321', 'ISR 4351', 'ASR 1001-X',
        'MX204', 'MX480',
        'CCR2004-1G-12S+2XS', 'RB4011iGS+',
        'NE40E-X3', 'AR6280',
        'EdgeRouter 12', 'UniFi Dream Machine Pro',
        'Archer AX6000', 'Archer AX90',
        'Nighthawk AX12', 'Orbi RBK863S',
        'RT-AX88U', 'GT-AX11000',
    ],
    'Firewall': [
        'ASA 5506-X', 'ASA 5508-X', 'Firepower 2110',
        'FortiGate 60F', 'FortiGate 100F', 'FortiGate 200F',
        'PA-820', 'PA-3220', 'PA-5220',
        'SRX300', 'SRX380',
        'TZ470', 'NSa 2700',
        'XG 125', 'XG 210',
    ],
    'Access Point': [
        'Catalyst 9115AX', 'Catalyst 9120AX',
        'AP-515', 'AP-635', 'AP-655',
        'R750', 'R850', 'T750',
        'EAP670', 'EAP660 HD',
        'WAX630', 'WAX640',
        'UniFi U6 Pro', 'UniFi U6 LR',
    ],
    'Modem': [
        'HG8245H5', 'HG8546M', 'EchoLife EG8145V5',
        'Archer VR900v', 'TD-W9970',
        'ISR 891W',
        'VMG3625-T50B', 'VMG8825-T50K',
        'Nighthawk C7800',
    ],
    'Hub': [
        'USB 3.0 Hub 7-Port', 'USB-C Hub 10-in-1',
        'Powered USB Hub 13-Port',
        'Hi-Speed USB 2.0 Hub',
    ],
    'Repeater': [
        'RE650', 'RE705X', 'RE900XD',
        'EX7500', 'EX8000',
        'AC2200 Tri-Band WiFi Extender',
    ],
    'Network Gateway': [
        'SonicWall TZ270', 'SonicWall NSa 2700',
        'Cisco 819 IoT GW',
        'Cradlepoint E3000',
        'Peplink Balance 310X',
    ],
    'Network Bridge': [
        'AirBridge NanoBeam 5AC',
        'LiteBeam 5AC Gen2',
        'PowerBeam 5AC ISO',
        'DLB-5-15ac',
    ],
    'IP Phone': [
        'CP-8841', 'CP-8851', 'CP-8861',
        'VVX 501', 'VVX 601',
        'T54W', 'T57W', 'T58A',
        'GXP2170', 'GXP2135',
        'D385', 'D735',
        '9608G', '9641G',
    ],
    'DECT Phone': [
        'KX-TGP600', 'KX-TPA60',
        'Gigaset S700H Pro', 'Gigaset R700H Pro',
        'CD490', 'CD785 Combo',
        'VTech DS6151',
    ],
    'PBX System': [
        'IP Office 500 V2', 'Aura Communication Manager',
        'Unified CM 12.5', 'Unified CM 14',
        'KX-NS700', 'KX-NS1000',
        '3CX Phone System v18',
        'Yeastar S100', 'Yeastar S300',
    ],
    'Video Conferencing': [
        'Webex Room Kit', 'Webex Board 55',
        'Group 500', 'Group 700', 'Studio X50',
        'Rally Bar', 'MeetUp', 'Rally Bar Mini',
        'Zoom Rooms Kit', 'Zoom Room Appliance',
        'IdeaHub S2', 'CloudLink 900',
    ],
    'TV Screen': [
        'QN85B 85"', 'UN75TU7000', 'The Frame 65"',
        'OLED C2 65"', 'QNED90 75"', 'NanoCell 86"',
        'BRAVIA XR A95K 65"', 'BRAVIA X90K 75"',
        'The One 55"', 'OLED 806 65"',
        'S546 55"', 'S75 65"',
        'QLed 75Q60B', 'Hisense U8H 65"',
        'LC-70UI9362K',
    ],
    'Projector': [
        'EB-L1505U', 'EB-PU2010B', 'EB-735Fi',
        'W2700i', 'TK850i', 'X3000i',
        'VPL-FHZ85', 'VPL-PHZ61',
        'EH416', 'EH470', 'EH505',
        'PX748-4K', 'PX728-4K',
        'LS831WU', 'PX701HD',
        'LC-WXL200A',
    ],
    'Interactive Whiteboard': [
        'SMART Board MX265', 'SMART Board 7075',
        'ActivPanel 9 75"', 'ActivPanel Elements 65"',
        'RP7502', 'RP6502',
        'The Wall 110"',
        'OLED Signage 65EW5G',
    ],
    'Display Panel': [
        'QM55B', 'QM75B', 'QM98B',
        'UH5F-E 55"', 'UH7F-E 75"',
        'MultiSync ME651', 'MultiSync ME861',
        'ST5502S', 'ST6502S',
        'BDL4650D', 'BDL5588XC',
    ],
    'UPS': [
        'Smart-UPS 1500VA', 'Smart-UPS 3000VA', 'Smart-UPS RT 5000VA',
        '9PX 1000i', '9PX 2200i', '9SX 3000i',
        'PR1000ELCD', 'PR2200ELCDRT2U', 'PR3000ELCDRTXL2U',
        'GXT5-1000MR230', 'GXT5-3000MR230',
        'NETYS PR 2200VA', 'ITYS-E 1200VA',
    ],
    'PDU': [
        'AP7900B', 'AP7901B', 'AP7968B',
        'ePDU G3 Metered', 'ePDU G3 Switched',
        'PX3-5190V', 'PX3-5590V',
        'MPH2', 'RSC-16-1P20A',
        'SRXPDU4L21TABA',
    ],
    'ATS': [
        'AP7721', 'AP7722', 'AP4450A',
        'ATS-16A-10S', 'ATS-32A-8S',
        'STS 16A', 'STS 32A',
    ],
    'Generator': [
        'QSB7-G7 150kVA', 'QSB5-G7 100kVA',
        'C175 D5B 175kVA', 'C250 D5 250kVA',
        '1106A-70TAG4 100kVA', '2206C-E13TAG3 275kVA',
        'KD200 200kVA', 'KD100 100kVA',
        'EF7200DE 6kVA', 'EF6600DE 5.5kVA',
    ],
    'External HDD': [
        'Backup Plus Portable 2TB', 'Expansion Portable 1TB',
        'My Passport Ultra 4TB', 'My Book Desktop 8TB',
        'Canvio Advance 2TB', 'Canvio Basics 1TB',
        'T7 Portable SSD 1TB',
        'Rugged Mini 1TB', 'Rugged RAID Pro 4TB',
    ],
    'Flash Drive': [
        'Ultra USB 3.0 128GB', 'Extreme Go USB 3.1 256GB',
        'DataTraveler 100 G3 64GB', 'DataTraveler Exodia 128GB',
        'Bar Plus 256GB', 'Fit Plus 128GB',
        'Turbo 3.1 128GB', 'JetFlash 790 64GB',
    ],
    'SSD': [
        '870 EVO 1TB', '970 EVO Plus 2TB', '980 Pro 1TB',
        'Blue SN570 1TB', 'Black SN850X 2TB',
        'BarraCuda 510 1TB', 'FireCuda 530 2TB',
        'A2000 1TB', 'KC3000 2TB',
        'MX500 2TB', 'P5 Plus 1TB',
    ],
    'NAS': [
        'DS923+', 'DS1522+', 'RS1221+',
        'TS-464', 'TS-873A', 'TVS-h1288X',
        'My Cloud EX2 Ultra', 'My Cloud PR4100',
        'ReadyNAS 626X', 'ReadyNAS 628X',
    ],
    'Tape Drive': [
        'StoreEver LTO-8', 'StoreEver MSL2024',
        'PowerVault LTO-8', 'ML3 Tape Library',
        'IBM TS2280', 'IBM TS4300',
        'Scalar i3', 'SuperLoader 3',
    ],
    'Memory Card': [
        'Extreme Pro SDXC 256GB', 'Ultra SDXC 128GB',
        'PRO Plus MicroSDXC 256GB', 'EVO Select MicroSDXC 512GB',
        'Canvas React Plus 128GB', 'Canvas Select Plus 256GB',
        'JetFlash Card 64GB', 'JetFlash Card 128GB',
        'Professional 1066x SDXC 256GB',
    ],
    'Mouse': [
        'MX Master 3S', 'MX Anywhere 3', 'M720 Triathlon',
        'Arc Mouse', 'Sculpt Ergonomic',
        'MS116', 'MS3220',
        'M100', 'M185',
        'Genius DX-120', 'Genius NetScroll 120',
    ],
    'Keyboard': [
        'MX Keys', 'K780 Multi-Device', 'K380',
        'Ergonomic Keyboard', 'All-in-One Media',
        'KB216', 'KB522',
        'SK-8845', 'SK-8820',
        'HP 125 Wired',
        'Genius SlimStar 126',
    ],
    'Monitor': [
        'UltraSharp U2722D', 'P2422H', 'S2722QC',
        'EliteDisplay E27q', 'Z27xs G3 QHD', 'E24i G4',
        '27UK850-W', '32UN880-B', '24MP88HV',
        'U32P2 4K', 'ThinkVision T27h',
        'ProArt PA278QV', 'VG279QM', 'ROG Swift PG279QM',
        'EW3270U', 'PD3220U',
        'VG1655', 'VP2768a', 'VP3268-4K',
        'Acer XV272U', 'Acer ET322QK',
    ],
    'Webcam': [
        'C920s Pro HD', 'C922x Pro Stream', 'StreamCam',
        'LifeCam Studio', 'Modern Webcam',
        'Kiyo Pro', 'Kiyo X',
        'FHD PC Camera AC925',
    ],
    'Headset': [
        'H390', 'H570e', 'Zone Wired',
        'Evolve2 30', 'Evolve2 65', 'Engage 75',
        'Blackwire 3225', 'Voyager Focus 2',
        'WH-1000XM5', 'WH-XB910N',
        'HD 450BT', 'MB Pro 2',
    ],
    'Decoder': [
        'GS8120', 'GS9120', 'GS7010',
        'Nagra 7', 'Nagra Kudelski',
        'Pace RNG200N', 'Pace Xi5',
        'DCX3220', 'DCX3400',
    ],
    'Digital Receiver': [
        'DSB-H470N', 'DSB-H510N',
        'Tiger T8 Ultra', 'Geant GN-DS 650HD',
        'Openbox S6 Pro+', 'Formuler Z8',
    ],
    'CCTV Camera': [
        'DS-2CD2143G2-I', 'DS-2CD2347G2-LU', 'DS-2DE4A425IWG',
        'IPC-HDW2831T-AS', 'IPC-HFW2831T-ZAS',
        'P3245-V', 'P3245-VE', 'Q6135-LE',
        'H5A 2MP', 'H4SL-BO6-IR',
        'FLEXIDOME 5100i', 'AUTODOME 7000i',
        'QNV-8080R', 'XNV-8080R',
    ],
    'DVR/NVR': [
        'iDS-7208HQHI-M1/S', 'iDS-7216HQHI-M2/S',
        'DS-7608NI-I2/8P', 'DS-7616NI-I2/16P',
        'XVR5108H-4KL-I3', 'XVR5116H-I3',
        'NVR308-32X', 'NVR608-64-4KS2',
        'Milestone XProtect', 'Genetec Security Center',
        'S9008', 'S9016',
    ],
    'Biometric Device': [
        'SpeedFace-V5L', 'SpeedFace-V4L', 'ProFace X',
        'BioStation 3', 'BioStation A2', 'FaceStation F2',
        'VF30', 'VF20',
        'MorphoWave Compact', 'MorphoWave Tower',
        'AC7000', 'AC2000',
    ],
    'Card Reader': [
        'SCR3310v2', 'ACR39U-I1',
        'OmniKey 3121', 'OmniKey 5427CK',
        'HID OMNIKEY 1021',
        'Gemalto IDBridge CT700',
    ],
    'Barcode Scanner': [
        'DS2208', 'DS8178', 'DS3678',
        'Xenon 1952g', 'Granit 1981i',
        'PowerScan PD9500', 'Gryphon I GD4590',
        'QuadraLux', '3310g',
    ],
    'Radio / Walkie-Talkie': [
        'APX 6000', 'APX 8000', 'SLR 8000',
        'TK-3402U16P', 'TK-2402U16P', 'NX-5200',
        'PD785G', 'PD985', 'PD365',
        'IC-F52D', 'IC-F62D',
        'BF-F8HP', 'UV-5R Pro',
    ],
    'GPS Device': [
        'GPSMAP 66i', 'Montana 700i', 'eTrex 32x',
        'R8s GNSS', 'R12i GNSS',
        'GR-i3', 'GR-i5',
        'Viva GS16', 'MS60',
    ],
    'Cable / Connector': [
        'Cat6 Patch Cable 1m', 'Cat6 Patch Cable 2m', 'Cat6 Patch Cable 5m',
        'Cat6A Patch Cable 1m', 'Cat6A Patch Cable 3m',
        'HDMI 2.1 Cable 2m', 'HDMI 2.0 Cable 5m',
        'DisplayPort 1.4 Cable', 'USB-C to USB-A Cable',
        'Fiber LC-LC Duplex 10m', 'Fiber SC-SC Duplex 5m',
        'SFP+ DAC Twinax 3m', 'SFP+ DAC Twinax 5m',
    ],
    'Rack / Cabinet': [
        '42U NetShelter SX', '24U NetShelter SX', '12U NetShelter WX',
        '42U RS Series', '22U RS Series',
        '42U TS IT', '26U TS IT',
        '42U VRA Series', '22U VRA Series',
        'WM015BPW1E', 'WM040BP1E',
    ],
    'KVM Switch': [
        'CS1768', 'CS1716i', 'KN8164V',
        'KVM-0831P', 'KVM-1631P',
        'NetDirector B064-008-01-IPG',
        'B020-U16-19KIT',
        'Dell KVM 2161DS', 'Dell KVM 1082DS',
    ],
}

# Fallback models for any category not in the map
_FALLBACK_MODELS = ['Model A', 'Model B', 'Model C', 'Model X', 'Model Pro', 'Model Plus']

# ─── Location pools (filled from DB at runtime) ───────────────────────────────

CONDITION_NOTES = [
    'Good condition', 'Minor scratches', 'Excellent condition',
    'Refurbished unit', 'Factory sealed', 'Previously used',
    'Battery replaced', 'Screen replaced', 'Keyboard replaced',
    'Fan cleaned', 'RAM upgraded', 'Storage upgraded',
]


def _random_serial():
    prefix = random.choice(['SN', 'SER', 'SRL', 'S'])
    digits = ''.join(random.choices(string.digits, k=10))
    return f"{prefix}-{digits}"


def _random_marking():
    dept = random.choice(['ICT', 'RNP', 'HQ', 'OPS', 'FIN', 'LOG', 'ADM'])
    year = random.randint(2018, 2025)
    num  = random.randint(1000, 9999)
    return f"{dept}/{year}/{num}"


def _random_date(start_year=2015, end_year=2024):
    start = date(start_year, 1, 1)
    end   = date(end_year, 12, 31)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def _random_location(regions, dpus, units, offices):
    """Pick a random location assignment (mutually exclusive FK fields)."""
    choice = random.choices(
        ['region', 'dpu', 'unit', 'office'],
        weights=[10, 30, 30, 30],
    )[0]

    kwargs = {}
    if choice == 'region' and regions:
        kwargs['region'] = random.choice(regions)
    elif choice == 'dpu' and dpus:
        kwargs['dpu'] = random.choice(dpus)
    elif choice == 'unit' and units:
        kwargs['unit'] = random.choice(units)
    elif choice == 'office' and offices:
        kwargs['office'] = random.choice(offices)
    else:
        # fallback
        if dpus:
            kwargs['dpu'] = random.choice(dpus)
    return kwargs


class Command(BaseCommand):
    help = 'Seed 10,000 equipment records per category (run after seed_reference_data)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count', type=int, default=10_000,
            help='Number of records per category (default: 10000)',
        )
        parser.add_argument(
            '--category', type=str, default=None,
            help='Seed only a specific category name (default: all)',
        )
        parser.add_argument(
            '--batch', type=int, default=500,
            help='Bulk-create batch size (default: 500)',
        )

    def handle(self, *args, **options):
        count_per_cat = options['count']
        only_category = options['category']
        batch_size    = options['batch']

        self.stdout.write('Loading reference data from DB...')

        statuses = list(EquipmentStatus.objects.all())
        regions  = list(Region.objects.all())
        dpus     = list(DPU.objects.all())
        units    = list(Unit.objects.all())
        offices  = list(Office.objects.all())

        if not statuses:
            self.stderr.write(self.style.ERROR(
                'No statuses found. Run seed_reference_data first.'
            ))
            return

        # Determine which categories to seed
        if only_category:
            categories = list(EquipmentCategory.objects.filter(name__iexact=only_category))
            if not categories:
                self.stderr.write(self.style.ERROR(f'Category "{only_category}" not found.'))
                return
        else:
            categories = list(EquipmentCategory.objects.all())

        # Pre-load brands per category name for fast lookup
        brand_map = {}
        for brand in Brand.objects.select_related('category').all():
            cat_name = brand.category.name if brand.category else '__none__'
            brand_map.setdefault(cat_name, []).append(brand)

        total_created = 0

        for category in categories:
            self.stdout.write(f'  Seeding {count_per_cat:,} × {category.name}...')

            cat_brands = brand_map.get(category.name, [])
            cat_models = MODELS.get(category.name, _FALLBACK_MODELS)

            batch = []
            for i in range(count_per_cat):
                brand  = random.choice(cat_brands) if cat_brands else None
                model  = random.choice(cat_models)
                status = random.choice(statuses)
                dep_date = _random_date()

                location_kwargs = _random_location(regions, dpus, units, offices)

                eq = Equipment(
                    equipment_type = EquipmentCategory.name,
                    brand          = brand,
                    model          = model,
                    serial_number  = _random_serial(),
                    marking_code   = _random_marking(),
                    status         = status,
                    date_deployed  = dep_date,
                    # Leave name blank — let model generate or leave null
                )
                for k, v in location_kwargs.items():
                    setattr(eq, k, v)

                batch.append(eq)

                # Flush batch
                if len(batch) >= batch_size:
                    with transaction.atomic():
                        Equipment.objects.bulk_create(batch, ignore_conflicts=True)
                    total_created += len(batch)
                    batch = []

            # Flush remainder
            if batch:
                with transaction.atomic():
                    Equipment.objects.bulk_create(batch, ignore_conflicts=True)
                total_created += len(batch)

            self.stdout.write(self.style.SUCCESS(
                f'    ✓ {category.name}: {count_per_cat:,} records inserted'
            ))

        self.stdout.write(self.style.SUCCESS(
            f'\nDONE. Total equipment records created: {total_created:,}'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Total equipment in DB: {Equipment.objects.count():,}'
        ))