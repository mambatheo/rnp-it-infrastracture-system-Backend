"""
Management command to seed IT equipment with realistic records.
Ensures hierarchical consistency of locations and mutes signals during seeding.
"""
import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from equipment.models import (
    Region, DPU, Station, RegionOffice, DPUOffice,
    Unit, Directorate, Department, Office,
    EquipmentCategory, EquipmentStatus, Brand,
    Equipment, Stock, Deployment,
)
from equipment.signals import auto_classify_equipment

User = get_user_model()

# ─── Helpers ──────────────────────────────────────────────────────────────────

def rand_date(start_year=2018, end_year=2025):
    start = date(start_year, 1, 1)
    end   = date(end_year, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))

def rand_bool(prob=0.6):
    return random.random() < prob

# ─── People & text pools ──────────────────────────────────────────────────────

OFFICERS = [
    'Sgt. Jean Bosco Habimana', 'Insp. Alice Mutoni', 'Supt. David Nkusi',
    'Cst. Fatuma Uwase', 'Sgt. Eric Mugabo', 'IP Samuel Kamanzi',
    'AIP Theophile Mura', 'ASP Grace Nyirandagijimana', 'Sgt. Claude Bizimana',
    'Insp. Diane Umutesi', 'Cst. Patrick Niyonzima', 'Supt. Agnes Mukamana',
    'Sgt. Olivier Nizeyimana', 'Cst. Vestine Nyirahabimana', 'IP Emmanuel Uwimana',
    'AIP Josiane Mukandoli', 'ASP Pierre Ntaganda', 'Sgt. Anitha Kayitesi',
    'Insp. Frank Nzabonimpa', 'Cst. Solange Uwingabire', 'Supt. Robert Ruhinda',
    'Sgt. Clarisse Mukakabanda', 'IP Jean-Pierre Habimana', 'AIP Christine Iradukunda',
    'Cst. Sylvestre Niyomugabo', 'Sgt. Dorothee Nyirahabimana', 'Insp. Fabrice Ndayisaba',
]

PURPOSES = [
    'Standard workstation for ICT Dept.', 'Patrol operations management.',
    'Field supervisor laptop.', 'Tech support officer workstation.',
    'Administrative duties.', 'Intelligence data processing.',
]

STORAGE_LOCATIONS = [
    'IT Store Room — Shelf A1', 'IT Store Room — Shelf B1', 'Repair Bay',
    'Secure Storage Unit 1', 'Warehouse — Section D',
]

STOCK_COMMENTS = [
    'Ready for deployment.', 'Awaiting repair parts.', 'Sealed in original box.',
    'Needs testing before issue.', 'New arrival from procurement.',
]

STOCK_CONDITIONS = ['New', 'Good', 'Fair', 'Poor', 'Damaged', 'Under Repair']
STOCK_COND_WEIGHTS = [30, 30, 20, 10, 5, 5]
RETURN_CONDITIONS = ['Good', 'Fair', 'Poor', 'Damaged']

# ─── Device catalogue ────────────────────────────────────────────────────────

CATALOGUE = [
    ('Desktop', 'Dell', 'OptiPlex 7090', dict(CPU='Intel Core i7', ram_size='16GB', storage_size='512GB SSD')),
    ('Laptop', 'HP', 'EliteBook 840', dict(CPU='Intel Core i5', ram_size='8GB', storage_size='256GB SSD')),
    ('Server', 'Dell', 'PowerEdge R740', dict(CPU='Xeon Gold', ram_size='64GB', storage_size='2TB', ram_slots=16)),
    ('Printer', 'Canon', 'imageRUNNER 2625i', dict(printer_type='multipurpose')),
    ('UPS', 'APC', 'Smart-UPS 1500', dict()),
]

TYPE_PREFIXES = {
    'Desktop': 'DT', 'Laptop': 'LT', 'Server': 'SV', 'Printer': 'PR', 'UPS': 'UP',
}

class Command(BaseCommand):
    help = 'Seed IT equipment records with hierarchical consistency'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true')
        parser.add_argument('--count', type=int, default=1000)

    def handle(self, *args, **kwargs):
        total = kwargs['count']
        if kwargs['clear']:
            self.stdout.write("Clearing existing data...")
            Deployment.objects.all().delete()
            Stock.objects.all().delete()
            Equipment.objects.all().delete()

        admin = User.objects.filter(is_superuser=True).first() or User.objects.first()
        if not admin:
            self.stdout.write(self.style.ERROR('No users found.'))
            return

        # Prepare Hierarchies
        self.stdout.write("Mapping hierarchies...")
        regions = list(Region.objects.all())
        dpus = list(DPU.objects.all())
        stations = list(Station.objects.all())
        offices = list(Office.objects.all())

        # Maps for quick consistent lookups
        dpu_by_reg_id = {r.id: [d for d in dpus if d.region_id == r.id] for r in regions}
        st_by_dpu_id = {d.id: [s for s in stations if s.dpu_id == d.id] for d in dpus}
        off_by_dpu_id = {d.id: [o for o in offices if o.dpu_id == d.id] for d in dpus}

        # Categories & Statuses
        cats = {n: EquipmentCategory.objects.get_or_create(name=n)[0] for n in ['Computer', 'Server', 'Printer', 'Power']}
        statuses = {n: EquipmentStatus.objects.get_or_create(name=n)[0] for n in ['Active', 'New', 'Faulty', 'Under Repair']}
        brands = {} # Cache brands

        # Mute signals during Equipment creation
        post_save.disconnect(auto_classify_equipment, sender=Equipment)

        self.stdout.write(f"Generating {total} records...")
        for i in range(total):
            eq_type, b_name, m_name, extra = random.choice(CATALOGUE)
            if b_name not in brands:
                brands[b_name] = Brand.objects.get_or_create(
                    name=b_name, 
                    defaults={'category': cats.get(eq_type, cats['Computer'])}
                )[0]

            # Pick consistent location
            loc = {'region': None, 'dpu': None, 'station': None, 'office': None}
            if regions and rand_bool(0.9):
                reg = random.choice(regions)
                loc['region'] = reg
                possible_dpus = dpu_by_reg_id.get(reg.id, [])
                if possible_dpus and rand_bool(0.8):
                    dpu = random.choice(possible_dpus)
                    loc['dpu'] = dpu
                    
                    possible_stations = st_by_dpu_id.get(dpu.id, [])
                    if possible_stations and rand_bool(0.4):
                        loc['station'] = random.choice(possible_stations)
                        
                    possible_offices = off_by_dpu_id.get(dpu.id, [])
                    if possible_offices and rand_bool(0.3):
                        loc['office'] = random.choice(possible_offices)

            status = random.choice(list(statuses.values()))
            prefix = TYPE_PREFIXES.get(eq_type, 'EQ')
            
            eq = Equipment.objects.create(
                name=f"{b_name} {m_name}",
                equipment_type=eq_type,
                brand=brands[b_name],
                model=m_name,
                status=status,
                serial_number=f"{prefix}-{random.randint(10000, 99999)}-{i}",
                marking_code=f"RNP-{prefix}-{i+1000}-{random.randint(100,999)}",
                created_by=admin,
                updated_by=admin,
                deployment_date=rand_date() if status.name == 'Active' else None,
                **loc,
                **extra
            )

            # Create child records manually
            if status.name == 'Active':
                Deployment.objects.create(
                    equipment=eq,
                    issued_to_user=random.choice(OFFICERS),
                    issued_by=admin,
                    issued_date=eq.deployment_date or rand_date(),
                    purpose=random.choice(PURPOSES),
                    issued_to_region=eq.region,
                    issued_to_dpu=eq.dpu,
                    issued_to_station=eq.station,
                    issued_to_office=eq.office,
                )
            elif status.name in ['New', 'Faulty', 'Under Repair']:
                Stock.objects.create(
                    equipment=eq,
                    condition='New' if status.name == 'New' else 'Good',
                    storage_location=random.choice(STORAGE_LOCATIONS),
                    added_by=admin,
                )

        # Reconnect signals
        post_save.connect(auto_classify_equipment, sender=Equipment)
        self.stdout.write(self.style.SUCCESS(f"Seeded {total} records successfully."))