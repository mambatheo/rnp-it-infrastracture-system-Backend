import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import { equipmentApi, brandsApi, statusesApi, regionOfficesApi, regionsApi, dpuOfficesApi, dpusApi, stationsApi, unitsApi, directoratesApi, departmentsApi, officesApi, usersApi } from '../services/api';

const inputCls = "w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#003580]/30";

// ─── Equipment type choices (matches backend equipment_type field) ──────────────
const EQUIPMENT_TYPES = [
  'Desktop', 'Laptop', 'Server',
  'TV Screen', 'Projector', 'Decoder',
  'Printer', 'Network Device', 'Telephone',
  'External Storage', 'Peripheral', 'UPS',
];

const PRINTER_TYPES    = ['printer', 'scanner', 'multipurpose'];
const NETWORK_TYPES    = ['Switch', 'Router', 'Firewall', 'Access_point', 'Repeater', 'Hub', 'Modem', 'Gateway', 'Bridge'];
const TELEPHONE_TYPES  = ['Smartphone', 'Tablet', 'iPad', 'hht'];
const EXSTORAGE_TYPES  = ['flash', 'hdd', 'ssd'];
const PERIPHERAL_TYPES = ['Mouse', 'Keyboard', 'Monitor'];

function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[92vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h3 className="font-bold text-slate-800 text-lg">{title}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-xl leading-none">✕</button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

function Toast({ msg, type }) {
  if (!msg) return null;
  return (
    <div className={`fixed bottom-6 right-6 z-[100] px-5 py-3 rounded-xl shadow-lg text-sm font-medium text-white
      ${type === 'error' ? 'bg-red-500' : 'bg-green-500'}`}>
      {msg}
    </div>
  );
}

// ─── Intent Picker Modal ──────────────────────────────────────────────────────
function IntentPickerModal({ onPick, onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-[#003366] to-[#003580] px-6 py-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white/70 text-xs font-semibold uppercase tracking-widest mb-0.5">New Equipment</p>
             
            </div>
            <button onClick={onClose}
              className="text-white/60 hover:text-white text-2xl leading-none transition-colors">
              ✕
            </button>
          </div>
        </div>

        {/* Picker cards */}
        <div className="p-6 grid grid-cols-2 gap-4">
            <button
            onClick={() => onPick('Stock')}
            className="group flex flex-col items-center gap-3 p-6 rounded-2xl border-2 border-slate-100
              hover:border-[#003580] hover:bg-[#003580]/5 transition-all text-left">
            <div className="w-14 h-14 rounded-2xl bg-[#003580]/10 group-hover:bg-[#003580]/20
              flex items-center justify-center transition-colors">
            </div>
            <div>
              <p className="font-bold text-slate-800 text-sm">Stock It</p>
              
            </div>
          </button>

          {/* Deploy It */}
          <button
            onClick={() => onPick('Deployment')}
            className="group flex flex-col items-center gap-3 p-6 rounded-2xl border-2 border-slate-100
              hover:border-[#003580] hover:bg-[#003580]/5 transition-all text-left">
            <div className="w-14 h-14 rounded-2xl bg-[#003580]/10 group-hover:bg-[#003580]/20
              flex items-center justify-center transition-colors">
            </div>
            <div>
              <p className="font-bold text-slate-800 text-sm">Deploy It</p>
              
            </div>
          </button>
        </div>

    
      </div>
    </div>
  );
}

// ─── Field wrapper ────────────────────────────────────────────────────────────
const F = ({ label, children }) => (
  <div>
    <label className="block text-xs font-semibold text-slate-500 mb-1">{label}</label>
    {children}
  </div>
);

// ─── Equipment form ────────────────────────────────────────────────────────────
function SectionHead({ label }) {
  return (
    <div className="col-span-2 mt-2">
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide border-b border-slate-100 pb-2">{label}</p>
    </div>
  );
}

function EquipmentForm({ form, onChange, refs }) {
  const { brands, statuses, regionOffices, regions, dpuOffices, dpus, stations, units, directorates, departments, offices, users } = refs;
  const eqType = form.equipment_type || '';
  const intent = form.registration_intent;

  const showComputer   = ['Desktop', 'Laptop'].includes(eqType);
  const showServer     = eqType === 'Server';
  const showDisplay    = eqType === 'TV Screen';
  const showPrinter    = eqType === 'Printer';
  const showNetwork    = eqType === 'Network Device';
  const showTelephone  = eqType === 'Telephone';
  const showExstorage  = eqType === 'External Storage';
  const showPeripheral = eqType === 'Peripheral';
  const isDeployment   = intent === 'Deployment';
  const hasSpecs = showComputer || showServer || showDisplay || showPrinter || showNetwork || showTelephone || showExstorage || showPeripheral;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

      {/* ── Intent badge ── */}
      {intent && (
        <div className="col-span-2 -mt-1 mb-1">
          <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold
            ${isDeployment
              ? 'bg-green-100 text-green-700 border border-green-200'
              : 'bg-[#003580]/10 text-[#003580] border border-[#003580]/20'}`}>
            {isDeployment ? 'Deploying Immediately' : 'Adding to Stock'}
          </div>
        </div>
      )}

      {/* ══ Equipment Information ══════════════════════════════════════════════ */}
      <SectionHead label="Device Specifications" />

      <F label="Equipment Type *">
        <select className={inputCls} name="equipment_type" value={eqType} onChange={onChange}>
          <option value="">— Select Type —</option>
          {EQUIPMENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
      </F>

      <F label="Device Name *">
        <input className={inputCls} name="name" value={form.name || ''} onChange={onChange} placeholder="e.g. Dell OptiPlex 7090" />
      </F>

      <F label="Brand">
        <select className={inputCls} name="brand" value={form.brand || ''} onChange={onChange}>
          <option value="">— Select Brand —</option>
          {brands.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
        </select>
      </F>

      <F label="Status *">
        <select className={inputCls} name="status" value={form.status || ''} onChange={onChange}>
          <option value="">— Select Status —</option>
          {statuses.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
      </F>

      <F label="Model">
        <input className={inputCls} name="model" value={form.model || ''} onChange={onChange} />
      </F>

      <F label="Serial Number">
        <input className={inputCls} name="serial_number" value={form.serial_number || ''} onChange={onChange} />
      </F>

      <F label="Marking Code">
        <input className={inputCls} name="marking_code" value={form.marking_code || ''} onChange={onChange} />
      </F>

      {/* ══ Device Specifications (type-specific) ═════════════════════════ */}
      {hasSpecs && <SectionHead label="Device Specifications" />}

      {(showComputer || showServer || showTelephone) && (<>
        <F label="CPU"><input className={inputCls} name="CPU" value={form.CPU || ''} onChange={onChange} /></F>
        <F label="RAM (GB)"><input className={inputCls} name="ram_size" value={form.ram_size || ''} onChange={onChange} /></F>
        <F label="Storage"><input className={inputCls} name="storage_size" value={form.storage_size || ''} onChange={onChange} /></F>
      </>)}
      {(showComputer || showServer) && (
        <F label="GPU"><input className={inputCls} name="GPU" value={form.GPU || ''} onChange={onChange} /></F>
      )}
      {(showComputer || showServer || showTelephone) && (
        <F label="Operating System"><input className={inputCls} name="operating_system" value={form.operating_system || ''} onChange={onChange} /></F>
      )}
      {showServer && (<>
        <F label="RAM Slots"><input className={inputCls} type="number" name="ram_slots" value={form.ram_slots || ''} onChange={onChange} /></F>
        <F label="Storage Slots"><input className={inputCls} type="number" name="storage_slots" value={form.storage_slots || ''} onChange={onChange} /></F>
        <F label="Storage Type"><input className={inputCls} name="storage_type" value={form.storage_type || ''} onChange={onChange} /></F>
      </>)}
      {showDisplay && (
        <F label="Screen Size"><input className={inputCls} name="screen_size" value={form.screen_size || ''} onChange={onChange} /></F>
      )}
      {showPrinter && (
        <F label="Printer Type">
          <select className={inputCls} name="printer_type" value={form.printer_type || ''} onChange={onChange}>
            <option value="">— Select —</option>
            {PRINTER_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </F>
      )}
      {showNetwork && (
        <F label="Network Type">
          <select className={inputCls} name="network_type" value={form.network_type || ''} onChange={onChange}>
            <option value="">— Select —</option>
            {NETWORK_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </F>
      )}
      {showTelephone && (
        <F label="Telephone Type">
          <select className={inputCls} name="telephone_type" value={form.telephone_type || ''} onChange={onChange}>
            <option value="">— Select —</option>
            {TELEPHONE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </F>
      )}
      {showExstorage && (<>
        <F label="Storage Type">
          <select className={inputCls} name="exstorage_type" value={form.exstorage_type || ''} onChange={onChange}>
            <option value="">— Select —</option>
            {EXSTORAGE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </F>
        <F label="Storage Size"><input className={inputCls} name="storage_size" value={form.storage_size || ''} onChange={onChange} /></F>
      </>)}
      {showPeripheral && (
        <F label="Peripheral Type">
          <select className={inputCls} name="peripheral_type" value={form.peripheral_type || ''} onChange={onChange}>
            <option value="">— Select —</option>
            {PERIPHERAL_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </F>
      )}
       {/* IT Staff (Issuer) */}
        <SectionHead label="IT Staff " />
        <div className="col-span-2">
          <F label="Added By *">
            <select className={inputCls} name="issued_by" value={form.issued_by || ''} onChange={onChange}>
              <option value="">— Select Staff —</option>
              {(users || []).map(u => (
                <option key={u.id} value={u.id}>{u.first_name} {u.last_name} ({u.email})</option>
              ))}
            </select>
          </F>
        </div>

      {/* ══ Deployment-only fields (hidden for Stock) ══════════════════════ */}
      {isDeployment && (<>

       

        {/* Individual Recipient */}
        <SectionHead label="Individual Recipient (Police Officer)" />
        <div className="col-span-2">
          <F label="Issued To (Person Name)">
            <input className={inputCls} name="issued_to_user" value={form.issued_to_user || ''} onChange={onChange} placeholder="e.g. AIP T MURA" />
          </F>
        </div>

        {/* Territorial Location */}
        <SectionHead label="Territorial Location" />
        <div className="col-span-2">
          <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
            Fill at least one location field or the person name above.
          </p>
        </div>

        <F label="Region Office (HQ)">
          <select className={inputCls} name="issued_to_region_office" value={form.issued_to_region_office || ''} onChange={onChange}>
            <option value="">— None —</option>
            {regionOffices.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
        </F>
        <F label="Region">
          <select className={inputCls} name="issued_to_region" value={form.issued_to_region || ''} onChange={onChange}>
            <option value="">— None —</option>
            {regions.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
        </F>
        <F label="DPU Office (HQ)">
          <select className={inputCls} name="issued_to_dpu_office" value={form.issued_to_dpu_office || ''} onChange={onChange}>
            <option value="">— None —</option>
            {dpuOffices.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </F>
        <F label="DPU">
          <select className={inputCls} name="issued_to_dpu" value={form.issued_to_dpu || ''} onChange={onChange}>
            <option value="">— None —</option>
            {dpus.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </F>
        <F label="Station">
          <select className={inputCls} name="issued_to_station" value={form.issued_to_station || ''} onChange={onChange}>
            <option value="">— None —</option>
            {stations.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </F>

        {/* Units & Departments */}
        <SectionHead label="Units & Departments" />
        <F label="Unit">
          <select className={inputCls} name="issued_to_unit" value={form.issued_to_unit || ''} onChange={onChange}>
            <option value="">— None —</option>
            {units.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
          </select>
        </F>
        <F label="Directorate">
          <select className={inputCls} name="issued_to_directorate" value={form.issued_to_directorate || ''} onChange={onChange}>
            <option value="">— None —</option>
            {directorates.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </F>
        <F label="Department">
          <select className={inputCls} name="issued_to_department" value={form.issued_to_department || ''} onChange={onChange}>
            <option value="">— None —</option>
            {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </F>
        <F label="Office">
          <select className={inputCls} name="issued_to_office" value={form.issued_to_office || ''} onChange={onChange}>
            <option value="">— None —</option>
            {offices.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
          </select>
        </F>
        {/* ══ Dates ══════════════════════════════════════════════════════════ */}
      <SectionHead label="Dates" />

      <F label="Deployment Date">
        <input className={inputCls} type="date" name="deployment_date" value={form.deployment_date || ''} onChange={onChange} />
      </F>

      <F label="Warranty Expiry">
        <input className={inputCls} type="date" name="warranty_expiration" value={form.warranty_expiration || ''} onChange={onChange} />
      </F>

      </>)}

      

      {/* ══ Comments ═══════════════════════════════════════════════════════ */}
      <SectionHead label="Comments" />

      <div className="col-span-2">
        <textarea className={inputCls + ' resize-none'} name="comments" rows={3} value={form.comments || ''} onChange={onChange} />
      </div>

    </div>
  );
}

// ─── Main Equipment page ──────────────────────────────────────────────────────
const PAGE_SIZE = 15;

const READONLY_FIELDS = [
  'brand_name', 'status_name',
  'region_name', 'dpu_name', 'station_name', 'unit_name',
  'directorate_name', 'department_name', 'office_name',
  'created_by_name', 'updated_by_name',
  'age_since_deployed', 'is_in_stock',
  'created_at', 'updated_at',
];

export default function Equipment() {
  const navigate = useNavigate();

  const [items, setItems]       = useState([]);
  const [total, setTotal]       = useState(0);
  const [page, setPage]         = useState(1);
  const [search, setSearch]     = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [loading, setLoading]   = useState(false);
  const [modal, setModal]       = useState(null);
  const [selected, setSelected] = useState(null);
  const [form, setForm]         = useState({});
  const [submitting, setSub]    = useState(false);
  const [deleteId, setDeleteId] = useState(null);
  const [toast, setToast]       = useState({ msg: '', type: 'success' });

  const [refs, setRefs] = useState({ brands: [], statuses: [], regionOffices: [], regions: [], dpuOffices: [], dpus: [], stations: [], units: [], directorates: [], departments: [], offices: [], users: [] });

  const showToast = (msg, type = 'success') => { setToast({ msg, type }); setTimeout(() => setToast({ msg: '', type }), 3000); };

  // Load reference data
  useEffect(() => {
    const p = { page_size: 500 };
    Promise.allSettled([
      brandsApi.list(p),
      statusesApi.list(p),
      regionOfficesApi.list(p),
      regionsApi.list(p),
      dpuOfficesApi.list(p),
      dpusApi.list(p),
      stationsApi.list(p),
      unitsApi.list(p),
      directoratesApi.list(p),
      departmentsApi.list(p),
      officesApi.list(p),
      usersApi.list(p),
    ]).then(([brands, statuses, regionOffices, regions, dpuOffices, dpus, stations, units, directorates, departments, offices, users]) => {
      setRefs({
        brands:        brands.value?.results        || brands.value        || [],
        statuses:      statuses.value?.results      || statuses.value      || [],
        regionOffices: regionOffices.value?.results || regionOffices.value || [],
        regions:       regions.value?.results       || regions.value       || [],
        dpuOffices:    dpuOffices.value?.results    || dpuOffices.value    || [],
        dpus:          dpus.value?.results          || dpus.value          || [],
        stations:      stations.value?.results      || stations.value      || [],
        units:         units.value?.results         || units.value         || [],
        directorates:  directorates.value?.results  || directorates.value  || [],
        departments:   departments.value?.results   || departments.value   || [],
        offices:       offices.value?.results       || offices.value       || [],
        users:         users.value?.results         || users.value         || [],
      });
    });
  }, []);

  const fetchItems = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, page_size: PAGE_SIZE };
      if (search) params.search = search;
      if (typeFilter) params.equipment_type = typeFilter;
      const d = await equipmentApi.list(params);
      setItems(d.results || []);
      setTotal(d.count || 0);
    } catch { showToast('Failed to load equipment', 'error'); }
    finally { setLoading(false); }
  }, [page, search, typeFilter]);

  useEffect(() => { fetchItems(); }, [fetchItems]);

  const handleChange = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }));

  const openCreate = () => { setForm({}); setSelected(null); setModal('intent'); };
  const openEdit   = item => { setForm({ ...item }); setSelected(item); setModal('form'); };

  const pickIntent = (intent) => {
    setForm({ registration_intent: intent });
    setModal('form');
  };

  const handleSubmit = async () => {
    setSub(true);
    try {
      const payload = Object.fromEntries(Object.entries(form).filter(([k]) => !READONLY_FIELDS.includes(k)));
      // Nullify empty FK strings
      ['brand', 'status', 'region', 'dpu', 'station', 'unit', 'directorate', 'department', 'office'].forEach(k => {
        if (payload[k] === '' || payload[k] === undefined) payload[k] = null;
      });

      if (selected) { await equipmentApi.update(selected.id, payload); showToast('Equipment updated'); }
      else          { await equipmentApi.create(payload); showToast('Equipment created'); }
      setModal(null); fetchItems();
    } catch (err) {
      const msg = typeof err === 'object' ? JSON.stringify(err) : 'Failed to save';
      showToast(msg, 'error');
    } finally { setSub(false); }
  };

  const handleDelete = async () => {
    try { await equipmentApi.delete(deleteId); showToast('Equipment deleted'); setDeleteId(null); fetchItems(); }
    catch { showToast('Failed to delete', 'error'); }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);


  return (
    <Layout>
      <div className="p-6 max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-800">Equipment</h1>
          <p className="text-slate-500 text-sm mt-0.5">Manage IT equipment inventory — {total} total records</p>
        </div>

        {/* Search + Filter bar */}
        <div className="flex flex-wrap items-center gap-3 mb-5">
          <input
            className="border border-slate-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#003580]/30 max-w-xs w-full"
            placeholder="Search serial, name, model…"
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }} />
          <select
            className="border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#003580]/30"
            value={typeFilter}
            onChange={e => { setTypeFilter(e.target.value); setPage(1); }}>
            <option value="">All Types</option>
            {EQUIPMENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <button onClick={openCreate}
            className="ml-auto flex-shrink-0 inline-flex items-center gap-1.5 bg-[#003580] text-white px-4 py-2.5 rounded-xl text-sm font-medium hover:bg-[#002060]">
            <span className="text-lg leading-none">+</span> Add Equipment
          </button>
        </div>

        {/* Table */}
        <div className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-100">
                  {['Type', 'Device Name', 'Serial Number', 'Marking Code', 'Brand', 'Model', 'Status', 'Location', 'Equipment Age', 'Actions'].map(h => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={10} className="text-center py-12 text-slate-400">Loading…</td></tr>
                ) : items.length === 0 ? (
                  <tr><td colSpan={10} className="text-center py-12 text-slate-400">No equipment found.</td></tr>
                ) : items.map(item => (
                  <tr key={item.id}
                    className="border-b border-slate-50 hover:bg-[#003580]/5 cursor-pointer"
                    onClick={() => navigate(`/equipment/${item.id}`)}>
                    <td className="px-4 py-3 text-slate-600 whitespace-nowrap">                     
                      <span className="text-xs font-medium text-slate-500">{item.equipment_type || '—'}</span>
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-800">{item.name || '—'}</td>
                    <td className="px-4 py-3 text-slate-600 font-mono text-xs">{item.serial_number || '—'}</td>
                    <td className="px-4 py-3 text-slate-600 font-mono text-xs">{item.marking_code || '—'}</td>
                    <td className="px-4 py-3 text-slate-600">{item.brand_name || '—'}</td>
                    <td className="px-4 py-3 text-slate-600">{item.model || '—'}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
                        {item.status_name || '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-xs">
                      {[item.region_name, item.dpu_name, item.station_name].filter(Boolean).join(' › ') || '—'}
                    </td>
                    <td className="px-4 py-3 text-xs">
                      {item.age_since_deployed
                        ? <span className="px-2 py-0.5 rounded-full font-medium bg-blue-50 text-blue-600">{item.age_since_deployed}</span>
                        : <span className="text-slate-300">—</span>}
                    </td>
                    <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                      <div className="flex gap-2">
                        <button onClick={() => navigate(`/equipment/${item.id}`)}
                          className="px-3 py-1.5 rounded-lg bg-[#003580]/10 hover:bg-[#003580]/20 text-[#003580] text-xs font-medium">View</button>
                        <button onClick={() => openEdit(item)}
                          className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs">Edit</button>
                        <button onClick={() => setDeleteId(item.id)}
                          className="px-3 py-1.5 rounded-lg bg-red-100 hover:bg-red-200 text-red-600 text-xs">Delete</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100">
              <p className="text-xs text-slate-400">Page {page} of {totalPages} · {total} total</p>
              <div className="flex gap-2">
                <button disabled={page === 1} onClick={() => setPage(p => p - 1)}
                  className="px-3 py-1.5 text-xs border rounded-lg disabled:opacity-40">← Prev</button>
                <button disabled={page === totalPages} onClick={() => setPage(p => p + 1)}
                  className="px-3 py-1.5 text-xs border rounded-lg disabled:opacity-40">Next →</button>
              </div>
            </div>
          )}
        </div>

        {/* Intent Picker — shown before the form on Add */}
        {modal === 'intent' && (
          <IntentPickerModal
            onPick={pickIntent}
            onClose={() => setModal(null)}
          />
        )}

        {/* Add/Edit Modal */}
        {modal === 'form' && (
          <Modal
            title={selected
              ? 'Edit Equipment'
              : form.registration_intent === 'Deployment'
                ? 'Add Equipment — Deploy'
                : 'Add Equipment — Stock'}
            onClose={() => setModal(null)}>
            <EquipmentForm form={form} onChange={handleChange} refs={refs} />
            <div className="flex gap-3 justify-end mt-6">
              {!selected && (
                <button onClick={() => setModal('intent')}
                  className="px-4 py-2 rounded-lg border text-sm text-slate-600 hover:bg-slate-50">
                  ← Back
                </button>
              )}
              <button onClick={() => setModal(null)} className="px-4 py-2 rounded-lg border text-sm">Cancel</button>
              <button onClick={handleSubmit} disabled={submitting}
                className={`px-4 py-2 rounded-lg text-white text-sm disabled:opacity-50
                  ${form.registration_intent === 'Deployment' ? 'bg-green-600 hover:bg-green-700' : 'bg-[#003580] hover:bg-[#002060]'}`}>
                {submitting ? 'Saving…' : form.registration_intent === 'Deployment' ? 'Deploy' : 'Add to Stock'}
              </button>
            </div>
          </Modal>
        )}

        {/* Delete Modal */}
        {deleteId && (
          <Modal title="Confirm Delete" onClose={() => setDeleteId(null)}>
            <p className="text-slate-600 mb-6">Permanently delete this equipment record?</p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setDeleteId(null)} className="px-4 py-2 rounded-lg border text-sm">Cancel</button>
              <button onClick={handleDelete} className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm">Delete</button>
            </div>
          </Modal>
        )}

        <Toast msg={toast.msg} type={toast.type} />
      </div>
    </Layout>
  );
}
