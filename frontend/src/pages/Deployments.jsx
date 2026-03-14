import { useState, useEffect, useCallback, useRef } from 'react';
import Layout from '../components/Layout';
import { deploymentsApi, usersApi, equipmentApi, regionOfficesApi, regionsApi, dpuOfficesApi, dpusApi, stationsApi, unitsApi, officesApi, directoratesApi, departmentsApi } from '../services/api';

const EQUIPMENT_TYPES = [
  'Desktop','Laptop','Server','TV Screen','Projector','Decoder',
  'Printer','Network Device','Telephone','External Storage','Peripheral','UPS',
];

// ─── Amazon-style Equipment Combobox ──────────────────────────────────────────

function EqCombobox({ allEquipment, typeFilter, value, onChange }) {
  const [query, setQuery]   = useState('');
  const [open,  setOpen]    = useState(false);
  const ref                 = useRef(null);

  // Selected item label
  const selected = allEquipment.find(e => e.id === value);
  const display  = selected
    ? `${selected.name || selected.equipment_type} — ${selected.serial_number || selected.marking_code || ''}`
    : '';

  // Apply type pre-filter then text search
  const base     = typeFilter ? allEquipment.filter(e => e.equipment_type === typeFilter) : allEquipment;
  const filtered = query.trim() === ''
    ? base
    : base.filter(e => {
        const q = query.toLowerCase();
        return (e.serial_number  || '').toLowerCase().includes(q)
            || (e.marking_code   || '').toLowerCase().includes(q)
            || (e.name           || '').toLowerCase().includes(q)
            || (e.equipment_type || '').toLowerCase().includes(q);
      });

  // Close on outside click
  useEffect(() => {
    const handler = e => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const select = item => {
    onChange(item.id);
    setQuery('');
    setOpen(false);
  };

  const clear = () => { onChange(''); setQuery(''); setOpen(false); };

  return (
    <div ref={ref} className="relative">
      {/* Input row */}
      <div className="flex items-center border border-slate-200 rounded-xl overflow-hidden focus-within:ring-2 focus-within:ring-[#003580]/30">
        <span className="pl-3 text-slate-400 text-sm">🔍</span>
        <input
          type="text"
          className="flex-1 px-2 py-2.5 text-sm outline-none bg-white"
          placeholder={display || 'Search by name, serial or marking code…'}
          value={query}
          onFocus={() => setOpen(true)}
          onChange={e => { setQuery(e.target.value); setOpen(true); }}
          onKeyDown={e => e.key === 'Escape' && setOpen(false)}
        />
        {value && (
          <button type="button" onClick={clear}
            className="px-3 text-slate-400 hover:text-red-500 text-lg leading-none">✕</button>
        )}
      </div>

      {/* Selected badge */}
      {value && !open && (
        <p className="mt-1 text-xs text-[#003580] font-medium truncate px-1">✔ {display}</p>
      )}

      {/* Dropdown results */}
      {open && (
        <ul className="absolute z-50 w-full mt-1 bg-white border border-slate-200 rounded-xl shadow-lg max-h-56 overflow-y-auto">
          {filtered.length === 0 ? (
            <li className="px-4 py-3 text-sm text-slate-400">No equipment found.</li>
          ) : filtered.map(e => (
            <li key={e.id}
              className="px-4 py-2.5 text-sm cursor-pointer hover:bg-[#003580]/5 flex items-center justify-between gap-2"
              onMouseDown={() => select(e)}>
              <span className="font-medium text-slate-700">{e.name || e.equipment_type}</span>
              <span className="text-xs text-slate-400 font-mono shrink-0">
                {[e.serial_number, e.marking_code].filter(Boolean).join(' / ')}
                {e.equipment_type && ` · ${e.equipment_type}`}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const inputCls = "w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#003580]/30";

const STATUS_COLORS = {
  Active:   'bg-green-100 text-green-700',
  Returned: 'bg-slate-100 text-slate-600',
};

function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[92vh] overflow-y-auto">
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

const F = ({ label, children }) => (
  <div>
    <label className="block text-xs font-semibold text-slate-500 mb-1">{label}</label>
    {children}
  </div>
);

const READONLY_FIELDS = [
  'equipment_name', 'equipment_serial', 'equipment_type',
  'issued_to_user_name', 'issued_to_region_name', 'issued_to_dpu_name',
  'issued_to_unit_name', 'issued_to_directorate_name', 'issued_to_department_name', 'issued_to_office_name',
  'issued_by_name', 'return_confirmed_by_name',
  'created_at', 'updated_at',
];

export default function Deployments() {
  const [items, setItems]     = useState([]);
  const [total, setTotal]     = useState(0);
  const [page, setPage]       = useState(1);
  const [loading, setLoading] = useState(false);
  const [modal, setModal]     = useState(null);
  const [selected, setSelected] = useState(null);
  const [form, setForm]       = useState({});
  const [submitting, setSub]  = useState(false);
  const [deleteId, setDeleteId] = useState(null);
  const [toast, setToast]     = useState({ msg: '', type: 'success' });

  // Equipment filters (local UI state, not form fields)
  const [eqTypeFilter, setEqTypeFilter] = useState('');

  // Table-level search & filter
  const [tableSearch, setTableSearch] = useState('');
  const [tableType,   setTableType]   = useState('');

  // Reference data
  const [users, setUsers]                 = useState([]);
  const [equipment, setEquipment]         = useState([]);
  const [regionOffices, setRegionOffices] = useState([]);
  const [regions, setRegions]             = useState([]);
  const [dpuOffices, setDpuOffices]       = useState([]);
  const [dpus, setDpus]                   = useState([]);
  const [stations, setStations]           = useState([]);
  const [units, setUnits]                 = useState([]);
  const [directorates, setDirectorates]   = useState([]);
  const [departments, setDepartments]     = useState([]);
  const [offices, setOffices]             = useState([]);

  const pageSize = 15;
  const showToast = (msg, type = 'success') => { setToast({ msg, type }); setTimeout(() => setToast({ msg: '', type }), 3000); };

  // Load reference data
  useEffect(() => {
    const p = { page_size: 500 };
    usersApi.list(p).then(d => setUsers(d.results || [])).catch(() => {});
    equipmentApi.list(p).then(d => setEquipment(d.results || [])).catch(() => {});
    regionOfficesApi.list(p).then(d => setRegionOffices(d.results || [])).catch(() => {});
    regionsApi.list(p).then(d => setRegions(d.results || [])).catch(() => {});
    dpuOfficesApi.list(p).then(d => setDpuOffices(d.results || [])).catch(() => {});
    dpusApi.list(p).then(d => setDpus(d.results || [])).catch(() => {});
    stationsApi.list(p).then(d => setStations(d.results || [])).catch(() => {});
    unitsApi.list(p).then(d => setUnits(d.results || [])).catch(() => {});
    directoratesApi.list(p).then(d => setDirectorates(d.results || [])).catch(() => {});
    departmentsApi.list(p).then(d => setDepartments(d.results || [])).catch(() => {});
    officesApi.list(p).then(d => setOffices(d.results || [])).catch(() => {});
  }, []);

  const fetchItems = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, page_size: pageSize };
      if (tableSearch) params.search                       = tableSearch;
      if (tableType)   params.equipment__equipment_type    = tableType;
      const d = await deploymentsApi.list(params);
      setItems(d.results || []);
      setTotal(d.count || 0);
    } catch { showToast('Failed to load', 'error'); }
    finally { setLoading(false); }
  }, [page, tableSearch, tableType]);

  // Reset to page 1 when search/filter changes
  useEffect(() => { setPage(1); }, [tableSearch, tableType]);

  useEffect(() => { fetchItems(); }, [fetchItems]);

  const openCreate = () => { setForm({}); setSelected(null); setEqTypeFilter(''); setModal('form'); };
  const openEdit   = item => { setForm({ ...item }); setSelected(item); setEqTypeFilter(item.equipment_type || ''); setModal('form'); };

  const handleChange = e => {
    const { name, value } = e.target;
    setForm(f => {
      const updated = { ...f, [name]: value || null };
      // Auto-fill returned_date with today when status switches to Returned
      if (name === 'status' && value === 'Returned' && !f.returned_date) {
        updated.returned_date = new Date().toISOString().split('T')[0];
      }
      return updated;
    });
  };

  const handleSubmit = async () => {
    setSub(true);
    try {
      const payload = { ...form };
      READONLY_FIELDS.forEach(k => delete payload[k]);
      // Nullify empty FKs
      ['equipment', 'issued_to_region_office', 'issued_to_region',
       'issued_to_dpu_office', 'issued_to_dpu', 'issued_to_station',
       'issued_to_unit', 'issued_to_directorate', 'issued_to_department',
       'issued_to_office', 'issued_by', 'return_confirmed_by'].forEach(k => {
        if (payload[k] === '' || payload[k] === undefined) payload[k] = null;
      });

      if (selected) { await deploymentsApi.update(selected.id, payload); showToast('Deployment updated'); }
      else          { await deploymentsApi.create(payload); showToast('Deployment created'); }
      setModal(null); fetchItems();
    } catch (err) {
      // Surface DRF field-level validation errors (400) as readable messages
      let msg = 'Failed to save';
      if (err && typeof err === 'object') {
        const fieldMsgs = Object.entries(err)
          .map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs[0] : msgs}`)
          .join(' | ');
        msg = fieldMsgs || JSON.stringify(err);
      }
      showToast(msg, 'error');
    } finally { setSub(false); }
  };

  const handleDelete = async () => {
    try { await deploymentsApi.delete(deleteId); showToast('Deleted'); setDeleteId(null); fetchItems(); }
    catch { showToast('Failed to delete', 'error'); }
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <Layout>
      <div className="p-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-800">Deployments</h1>
            <p className="text-slate-500 text-sm mt-0.5">{total} total deployment records</p>
          </div>
          <button onClick={openCreate}
            className="inline-flex items-center gap-2 bg-[#003580] text-white px-4 py-2.5 rounded-xl text-sm font-medium hover:bg-[#002060]">
            <span className="text-lg leading-none">+</span> New Deployment
          </button>
        </div>

        {/* ── Search bar row ─────────────────────────────────────────────── */}
        <div className="flex flex-wrap items-center gap-3 mb-5">
          <input
            className="flex-1 border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#003580]/30"
            placeholder="Search serial, name, model…"
            value={tableSearch}
            onChange={e => { setTableSearch(e.target.value); setPage(1); }}
          />

          {/* Equipment Type filter */}
          <select
            className="border border-slate-200 rounded-xl px-3 py-2.5 text-sm bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-[#003580]/25 text-slate-700"
            value={tableType}
            onChange={e => setTableType(e.target.value)}
          >
            <option value="">All Types</option>
            {EQUIPMENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>

        {/* Table */}
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-100">
                  {['Equipment', 'Type', 'Issued To', 'Location', 'Issued Date', 'Status', 'Actions'].map(h => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={7} className="text-center py-12 text-slate-400">Loading…</td></tr>
                ) : items.length === 0 ? (
                  <tr><td colSpan={7} className="text-center py-12 text-slate-400">No deployments found.</td></tr>
                ) : items.map(item => (
                  <tr key={item.id} className="border-b border-slate-50 hover:bg-slate-50/50">
                    <td className="px-4 py-3">
                      <p className="font-medium text-slate-800">{item.equipment_name || '—'}</p>
                      <p className="text-xs text-slate-400 font-mono">{item.equipment_serial || ''}</p>
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-xs">{item.equipment_type || '—'}</td>
                    <td className="px-4 py-3">
                      <p className="text-slate-700">{item.issued_to_user || item.issued_to_office_name || '—'}</p>
                      {item.issued_to_unit_name && <p className="text-xs text-slate-400">{item.issued_to_unit_name}</p>}
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-xs">
                      {[item.issued_to_region_name, item.issued_to_dpu_name].filter(Boolean).join(' › ') || '—'}
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-xs">{item.issued_date || '—'}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${STATUS_COLORS[item.status] || 'bg-slate-100 text-slate-600'}`}>
                        {item.status || '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button onClick={() => openEdit(item)} className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs">Edit</button>
                        <button onClick={() => setDeleteId(item.id)} className="px-3 py-1.5 rounded-lg bg-red-100 hover:bg-red-200 text-red-600 text-xs">Delete</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t">
              <p className="text-xs text-slate-400">Page {page} of {totalPages}</p>
              <div className="flex gap-2">
                <button disabled={page===1} onClick={()=>setPage(p=>p-1)} className="px-3 py-1.5 text-xs border rounded-lg disabled:opacity-40">← Prev</button>
                <button disabled={page===totalPages} onClick={()=>setPage(p=>p+1)} className="px-3 py-1.5 text-xs border rounded-lg disabled:opacity-40">Next →</button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Form Modal */}
      {modal === 'form' && (
        <Modal title={selected ? 'Edit Deployment' : 'New Deployment'} onClose={() => setModal(null)}>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

            {/* Status */}
            <F label="Status *">
              <select className={inputCls} name="status" value={form.status || ''} onChange={handleChange}>
                <option value="">— Select —</option>
                <option value="Active">Active</option>
                <option value="Returned">Returned</option>
              </select>
            </F>

            {/* Equipment Type */}
            <F label="Equipment Type">
              <select className={inputCls} value={eqTypeFilter}
                onChange={e => { setEqTypeFilter(e.target.value); setForm(f => ({ ...f, equipment: null })); }}>
                <option value="">— All Types —</option>
                {EQUIPMENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </F>

            {/* Equipment combobox */}
            <div className="col-span-2">
              <F label="Equipment *">
                <EqCombobox
                  allEquipment={equipment}
                  typeFilter={eqTypeFilter}
                  value={form.equipment || ''}
                  onChange={id => setForm(f => ({ ...f, equipment: id || null }))}
                />
              </F>
            </div>
            <div className="col-span-2">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3 border-t pt-3">Individual Police Officer (Receiver)</p>
            </div>
            {/* Issued To — User (text) */}
            <F label="Issued To (Person Name)">
              <input className={inputCls} name="issued_to_user" value={form.issued_to_user || ''} onChange={handleChange}
                placeholder="e.g. John Doe" />
            </F>
            <div className="col-span-2">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3 border-t pt-3">IT Staff (Issuer)</p>
            </div>

            {/* Issued By */}
            <F label="Issued By *">
              <select className={inputCls} name="issued_by" value={form.issued_by || ''} onChange={handleChange}>
                <option value="">— Select Staff —</option>
                {users.map(u => <option key={u.id} value={u.id}>{u.first_name} {u.last_name} ({u.email})</option>)}
              </select>
            </F>

            {/* Location */}
            <div className="col-span-2">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3 border-t pt-3">Terretorial Units</p>
            </div>

            <F label="Region Office (HQ)">
              <select className={inputCls} name="issued_to_region_office" value={form.issued_to_region_office || ''} onChange={handleChange}>
                <option value="">— None —</option>
                {regionOffices.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
              </select>
            </F>
            <F label="Region">
              <select className={inputCls} name="issued_to_region" value={form.issued_to_region || ''} onChange={handleChange}>
                <option value="">— None —</option>
                {regions.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
              </select>
            </F>
            <F label="DPU Office (HQ)">
              <select className={inputCls} name="issued_to_dpu_office" value={form.issued_to_dpu_office || ''} onChange={handleChange}>
                <option value="">— None —</option>
                {dpuOffices.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </F>
            <F label="DPU">
              <select className={inputCls} name="issued_to_dpu" value={form.issued_to_dpu || ''} onChange={handleChange}>
                <option value="">— None —</option>
                {dpus.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </F>
            <F label="Station">
              <select className={inputCls} name="issued_to_station" value={form.issued_to_station || ''} onChange={handleChange}>
                <option value="">— None —</option>
                {stations.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </F>
            <div className="col-span-2">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3 border-t pt-3">Units and Departments</p>
            </div>
            <F label="Unit">
              <select className={inputCls} name="issued_to_unit" value={form.issued_to_unit || ''} onChange={handleChange}>
                <option value="">— None —</option>
                {units.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
              </select>
            </F>
            <F label="Directorate">
              <select className={inputCls} name="issued_to_directorate" value={form.issued_to_directorate || ''} onChange={handleChange}>
                <option value="">— None —</option>
                {directorates.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </F>
            <F label="Department">
              <select className={inputCls} name="issued_to_department" value={form.issued_to_department || ''} onChange={handleChange}>
                <option value="">— None —</option>
                {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </F>
            <F label="Office">
              <select className={inputCls} name="issued_to_office" value={form.issued_to_office || ''} onChange={handleChange}>
                <option value="">— None —</option>
                {offices.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
              </select>
            </F>

            {/* Dates */}
            <div className="col-span-2">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3 border-t pt-3">Dates</p>
            </div>

            <F label="Issue Date *">
              <input className={inputCls} type="date" name="issued_date" value={form.issued_date || ''} onChange={handleChange} />
            </F>
            <F label="Expected Return Date">
              <input className={inputCls} type="date" name="expected_return_date" value={form.expected_return_date || ''} onChange={handleChange} />
            </F>
            <F label={form.status === 'Returned' ? '🔴 Returned Date *' : 'Returned Date'}>
              <input
                className={`${inputCls} ${form.status === 'Returned' && !form.returned_date ? 'border-red-400 ring-2 ring-red-200' : ''}`}
                type="date" name="returned_date"
                value={form.returned_date || ''} onChange={handleChange} />
            </F>
            <F label="Condition on Return">
              <select className={inputCls} name="condition_on_return" value={form.condition_on_return || ''} onChange={handleChange}>
                <option value="">— None —</option>
                {['New','Good','Fair','Poor','Damaged','Under Repair'].map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </F>

            {/* Return confirmed by */}
            <F label="Return Confirmed By">
              <select className={inputCls} name="return_confirmed_by" value={form.return_confirmed_by || ''} onChange={handleChange}>
                <option value="">— None —</option>
                {users.map(u => <option key={u.id} value={u.id}>{u.first_name} {u.last_name}</option>)}
              </select>
            </F>

            {/* Purpose & Comments */}
            <div className="col-span-2">
              <F label="Purpose">
                <input className={inputCls} name="purpose" value={form.purpose || ''} onChange={handleChange} placeholder="Reason for deployment" />
              </F>
            </div>
            <div className="col-span-2">
              <F label="Comments">
                <textarea className={inputCls + ' resize-none'} name="comments" rows={3} value={form.comments || ''} onChange={handleChange} />
              </F>
            </div>
          </div>

          <div className="flex gap-3 justify-end mt-6">
            <button onClick={() => setModal(null)} className="px-4 py-2 rounded-lg border text-sm">Cancel</button>
            <button onClick={handleSubmit} disabled={submitting}
              className="px-4 py-2 rounded-lg bg-[#003580] text-white text-sm disabled:opacity-50">
              {submitting ? 'Saving…' : 'Save'}
            </button>
          </div>
        </Modal>
      )}

      {deleteId && (
        <Modal title="Confirm Delete" onClose={() => setDeleteId(null)}>
          <p className="text-slate-600 mb-6">Delete this deployment record?</p>
          <div className="flex gap-3 justify-end">
            <button onClick={() => setDeleteId(null)} className="px-4 py-2 rounded-lg border text-sm">Cancel</button>
            <button onClick={handleDelete} className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm">Delete</button>
          </div>
        </Modal>
      )}
      <Toast msg={toast.msg} type={toast.type} />
    </Layout>
  );
}
