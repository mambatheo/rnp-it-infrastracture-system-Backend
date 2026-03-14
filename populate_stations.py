"""
One-time data population script for Stations.
Run with: py manage.py shell -c "exec(open('populate_stations.py').read())"
"""
from equipment.models import DPU, Station

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

# Build DPU lookup (name → object)
dpu_map = {d.name: d for d in DPU.objects.all()}
missing_dpus = set()
created = skipped = 0

for station_name, dpu_name in STATIONS:
    dpu = dpu_map.get(dpu_name)
    if not dpu:
        missing_dpus.add(dpu_name)
        continue
    obj, was_created = Station.objects.get_or_create(name=station_name, dpu=dpu)
    if was_created:
        created += 1
    else:
        skipped += 1

if missing_dpus:
    print(f"WARNING — DPUs not found in DB: {sorted(missing_dpus)}")

print(f"\nDone. Stations created: {created}, already existed: {skipped}")
print(f"Total stations in DB: {Station.objects.count()}")
