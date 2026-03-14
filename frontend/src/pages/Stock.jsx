import { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import {
  stockApi, equipmentApi, deploymentsApi, usersApi,
  regionOfficesApi, regionsApi, dpuOfficesApi, dpusApi,
  stationsApi, unitsApi, directoratesApi, departmentsApi, officesApi,
} from '../services/api';

const inputCls = "w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#003580]/30";

const CONDITION_COLORS = {
  'New':          'bg-blue-100 text-blue-700',
  'Good':         'bg-green-100 text-green-700',
  'Fair':         'bg-yellow-100 text-yellow-700',
  'Poor':         'bg-orange-100 text-orange-700',
  'Damaged':      'bg-red-100 text-red-600',
  'Under Repair': 'bg-purple-100 text-purple-700',
};

const CONDITIONS = ['New', 'Good', 'Fair', 'Poor', 'Damaged', 'Under Repair'];

function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[92vh] overflow-y-auto">
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

const PAGE_SIZE = 15;
const READONLY  = ['equipment_name', 'equipment_serial', 'added_by_name', 'created_at', 'updated_at', 'date_added'];

export default function Stock() {
  const [items, setItems]       = useState([]);
  const [total, setTotal]       = useState(0);
  const [page, setPage]         = useState(1);
  const [search, setSearch]     = useState('');
  const [loading, setLoading]   = useState(false);
  const [modal, setModal]       = useState(null);
  const [selected, setSelected] = useState(null);
  const [form, setForm]         = useState({});
  const [submitting, setSub]    = useState(false);
  const [deleteId, setDeleteId] = useState(null);
  const [toast, setToast]       = useState({ msg: '', type: 'success' });
  const [equipment, setEquipment] = useState([]);
  const [users, setUsers]         = useState([]);   // ← added

  // Deploy state
  const [deployItem,       setDeployItem]       = useState(null);
  const [deployForm,       setDeployForm]       = useState({});
  const [deploySubmitting, setDeploySubmitting] = useState(false);

  // Location reference data for deploy form
  const [locRefs, setLocRefs] = useState({
    regionOffices: [], regions:     [],
    dpuOffices:    [], dpus:        [],
    stations:      [], units:       [],
    directorates:  [], departments: [],
    offices:       [],
  });

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast({ msg: '', type }), 3000);
  };

  // ── Load reference data ────────────────────────────────────────────
  useEffect(() => {
    const p = { page_size: 500 };

    equipmentApi.list(p).then(d => setEquipment(d.results || [])).catch(() => {});
    usersApi.list(p).then(d => setUsers(d.results || [])).catch(() => {});  // ← added

    Promise.allSettled([
      regionOfficesApi.list(p), regionsApi.list(p),
      dpuOfficesApi.list(p),    dpusApi.list(p),
      stationsApi.list(p),      unitsApi.list(p),
      directoratesApi.list(p),  departmentsApi.list(p),
      officesApi.list(p),
    ]).then(([ro, r, dof, d, st, u, dir, dep, o]) => {
      setLocRefs({
        regionOffices: ro.value?.results  || [],
        regions:       r.value?.results   || [],
        dpuOffices:    dof.value?.results || [],
        dpus:          d.value?.results   || [],
        stations:      st.value?.results  || [],
        units:         u.value?.results   || [],
        directorates:  dir.value?.results || [],
        departments:   dep.value?.results || [],
        offices:       o.value?.results   || [],
      });
    });
  }, []);

  // ── Fetch stock items ──────────────────────────────────────────────
  const fetchItems = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, page_size: PAGE_SIZE };
      if (search) params.search = search;
      const d = await stockApi.list(params);
      setItems(d.results || []);
      setTotal(d.count   || 0);
    } catch {
      showToast('Failed to load stock', 'error');
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => { fetchItems(); }, [fetchItems]);

  // ── Form handlers ──────────────────────────────────────────────────

  // Stock Add/Edit form
  const handleChange = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }));

  // Deploy form — named `onChange` so all deploy fields use onChange={onChange}
  const onChange = e => {
    const { name, value } = e.target;
    setDeployForm(f => ({ ...f, [name]: value || null }));
  };

  // ── Modal openers ──────────────────────────────────────────────────
  const openCreate = () => { setForm({}); setSelected(null); setModal('form'); };
  const openEdit   = item => { setForm({ ...item }); setSelected(item); setModal('form'); };
  const openDeploy = item => {
    setDeployItem(item);
    setDeployForm({ issued_date: new Date().toISOString().split('T')[0] });
  };

  // ── Submit handlers ────────────────────────────────────────────────
  const handleSubmit = async () => {
    setSub(true);
    try {
      const payload = Object.fromEntries(
        Object.entries(form).filter(([k]) => !READONLY.includes(k))
      );
      if (!payload.equipment) payload.equipment = null;

      if (selected) { await stockApi.update(selected.id, payload); showToast('Stock item updated'); }
      else          { await stockApi.create(payload);               showToast('Stock item added');   }
      setModal(null);
      fetchItems();
    } catch (err) {
      const msg = typeof err === 'object' ? JSON.stringify(err) : 'Failed to save';
      showToast(msg, 'error');
    } finally {
      setSub(false);
    }
  };

  const handleDelete = async () => {
    try {
      await stockApi.delete(deleteId);
      showToast('Stock item deleted');
      setDeleteId(null);
      fetchItems();
    } catch {
      showToast('Failed to delete', 'error');
    }
  };

  const handleDeploy = async () => {
    const hasRecipient =
      deployForm.issued_to_user?.trim()  ||
      deployForm.issued_to_region_office ||
      deployForm.issued_to_region        ||
      deployForm.issued_to_dpu_office    ||
      deployForm.issued_to_dpu           ||
      deployForm.issued_to_station       ||
      deployForm.issued_to_unit          ||
      deployForm.issued_to_directorate   ||
      deployForm.issued_to_department    ||
      deployForm.issued_to_office;

    if (!hasRecipient) {
      showToast('Enter at least a recipient name or location', 'error');
      return;
    }

    setDeploySubmitting(true);
    try {
      const payload = {
        equipment:               deployItem.equipment,
        issued_to_user:          deployForm.issued_to_user          || null,
        issued_to_region_office: deployForm.issued_to_region_office || null,
        issued_to_region:        deployForm.issued_to_region        || null,
        issued_to_dpu_office:    deployForm.issued_to_dpu_office    || null,
        issued_to_dpu:           deployForm.issued_to_dpu           || null,
        issued_to_station:       deployForm.issued_to_station       || null,
        issued_to_unit:          deployForm.issued_to_unit          || null,
        issued_to_directorate:   deployForm.issued_to_directorate   || null,
        issued_to_department:    deployForm.issued_to_department    || null,
        issued_to_office:        deployForm.issued_to_office        || null,
        issued_date:             deployForm.issued_date             || new Date().toISOString().split('T')[0],
        issued_by:               deployForm.issued_by               || null,  // ← added to payload
        comments:                deployForm.comments                || null,
      };
      await deploymentsApi.create(payload);
      showToast(`${deployItem.equipment_name} deployed successfully`);
      setDeployItem(null);
      fetchItems();
    } catch (err) {
      const msg = err?.non_field_errors?.[0] || err?.detail || JSON.stringify(err);
      showToast(msg || 'Deploy failed', 'error');
    } finally {
      setDeploySubmitting(false);
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  // ── Render ─────────────────────────────────────────────────────────
  return (
    <Layout>
      <div className="p-6 max-w-7xl mx-auto">

        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-800">Stock</h1>
          <p className="text-slate-500 text-sm mt-0.5">Equipment held in storage — {total} items</p>
        </div>

        {/* Search + Add */}
        <div className="flex items-center gap-3 mb-5">
          <input
            className="border border-slate-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#003580]/30 max-w-xs w-full"
            placeholder="Search equipment name, serial, location…"
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
          />
          <button
            onClick={openCreate}
            className="ml-auto flex-shrink-0 inline-flex items-center gap-1.5 bg-[#003580] text-white px-4 py-2.5 rounded-xl text-sm font-medium hover:bg-[#002060]">
            <span className="text-lg leading-none">+</span> Add to Stock
          </button>
        </div>

        {/* Table */}
        <div className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-100">
                  {['Equipment', 'Serial Number', 'Condition', 'Storage Location', 'Date Added', 'Comments', 'Actions'].map(h => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={7} className="text-center py-12 text-slate-400">Loading…</td></tr>
                ) : items.length === 0 ? (
                  <tr><td colSpan={7} className="text-center py-12 text-slate-400">No stock items found.</td></tr>
                ) : items.map(item => (
                  <tr key={item.id} className="border-b border-slate-50 hover:bg-slate-50/50">
                    <td className="px-4 py-3">
                      <p className="font-medium text-slate-800">{item.equipment_name || '—'}</p>
                    </td>
                    <td className="px-4 py-3 text-slate-600 font-mono text-xs">{item.equipment_serial || '—'}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${CONDITION_COLORS[item.condition] || 'bg-slate-100 text-slate-600'}`}>
                        {item.condition || '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{item.storage_location || '—'}</td>
                    <td className="px-4 py-3 text-slate-500 text-xs">{item.date_added || '—'}</td>
                    <td className="px-4 py-3 text-slate-500 text-xs max-w-xs truncate">{item.comments || '—'}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button onClick={() => openEdit(item)}
                          className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs">Edit</button>
                        <button onClick={() => openDeploy(item)}
                          className="px-3 py-1.5 rounded-lg bg-green-100 hover:bg-green-200 text-green-700 text-xs font-medium">Deploy</button>
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
                <button disabled={page === 1}          onClick={() => setPage(p => p - 1)} className="px-3 py-1.5 text-xs border rounded-lg disabled:opacity-40">← Prev</button>
                <button disabled={page === totalPages} onClick={() => setPage(p => p + 1)} className="px-3 py-1.5 text-xs border rounded-lg disabled:opacity-40">Next →</button>
              </div>
            </div>
          )}
        </div>

        {/* ── Add / Edit Stock Modal ─────────────────────────────────── */}
        {modal === 'form' && (
          <Modal title={selected ? 'Edit Stock Item' : 'Add to Stock'} onClose={() => setModal(null)}>
            <div className="space-y-4">
              <F label="Equipment *">
                <select className={inputCls} name="equipment" value={form.equipment || ''} onChange={handleChange}>
                  <option value="">— Select Equipment —</option>
                  {equipment.map(e => (
                    <option key={e.id} value={e.id}>
                      {e.equipment_type ? `[${e.equipment_type}] ` : ''}{e.name || ''} — {e.serial_number || e.marking_code || e.id.slice(0, 8)}
                    </option>
                  ))}
                </select>
              </F>
              <F label="Condition">
                <select className={inputCls} name="condition" value={form.condition || ''} onChange={handleChange}>
                  <option value="">— Select Condition —</option>
                  {CONDITIONS.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </F>
              <F label="Storage Location">
                <input className={inputCls} name="storage_location" value={form.storage_location || ''} onChange={handleChange}
                  placeholder="e.g. IT Store Room, Shelf B3" />
              </F>
              <F label="Comments">
                <textarea className={inputCls + ' resize-none'} name="comments" rows={3}
                  value={form.comments || ''} onChange={handleChange} />
              </F>
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

        {/* ── Deploy Modal ───────────────────────────────────────────── */}
        {deployItem && (
          <Modal title={`Deploy — ${deployItem.equipment_name}`} onClose={() => setDeployItem(null)}>
            <div className="space-y-4">

              {/* Info banner */}
              <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-3 text-xs text-green-700">
                This will issue <strong>{deployItem.equipment_name}</strong> ({deployItem.equipment_serial || '—'}) and remove it from stock.
              </div>

              {/* ── IT Staff (Issuer) ─────────────────────────────── */}
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide border-t pt-3">
                IT Staff (Issuer)
              </p>
              <F label="Issued By *">
                <select className={inputCls} name="issued_by"
                  value={deployForm.issued_by || ''} onChange={onChange}>
                  <option value="">— Select Staff —</option>
                  {users.map(u => (
                    <option key={u.id} value={u.id}>
                      {u.first_name} {u.last_name} ({u.email})
                    </option>
                  ))}
                </select>
              </F>

              {/* ── Individual Receiver ──────────────────────────── */}
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide border-t pt-3">
                Individual Police Officer (Receiver)
              </p>
              <F label="Issued To (Person Name)">
                <input
                  className={inputCls}
                  name="issued_to_user"
                  value={deployForm.issued_to_user || ''}
                  onChange={onChange}
                  placeholder="e.g. AIP T MURA"
                />
              </F>

              {/* ── Territorial Units ──────────────────────────────── */}
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide border-t pt-3">
                Territorial Units
              </p>
              <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                Fill at least one location field or the person name above.
              </p>

              <div className="grid grid-cols-2 gap-3">
                <F label="Region Office (HQ)">
                  <select className={inputCls} name="issued_to_region_office"
                    value={deployForm.issued_to_region_office || ''} onChange={onChange}>
                    <option value="">— None —</option>
                    {locRefs.regionOffices.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                  </select>
                </F>
                <F label="Region">
                  <select className={inputCls} name="issued_to_region"
                    value={deployForm.issued_to_region || ''} onChange={onChange}>
                    <option value="">— None —</option>
                    {locRefs.regions.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                  </select>
                </F>
                <F label="DPU Office (HQ)">
                  <select className={inputCls} name="issued_to_dpu_office"
                    value={deployForm.issued_to_dpu_office || ''} onChange={onChange}>
                    <option value="">— None —</option>
                    {locRefs.dpuOffices.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                  </select>
                </F>
                <F label="DPU">
                  <select className={inputCls} name="issued_to_dpu"
                    value={deployForm.issued_to_dpu || ''} onChange={onChange}>
                    <option value="">— None —</option>
                    {locRefs.dpus.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                  </select>
                </F>
                <F label="Station">
                  <select className={inputCls} name="issued_to_station"
                    value={deployForm.issued_to_station || ''} onChange={onChange}>
                    <option value="">— None —</option>
                    {locRefs.stations.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                </F>
              </div>

              {/* ── Units and Departments ──────────────────────────── */}
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide border-t pt-3">
                Units and Departments
              </p>

              <div className="grid grid-cols-2 gap-3">
                <F label="Unit">
                  <select className={inputCls} name="issued_to_unit"
                    value={deployForm.issued_to_unit || ''} onChange={onChange}>
                    <option value="">— None —</option>
                    {locRefs.units.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
                  </select>
                </F>
                <F label="Directorate">
                  <select className={inputCls} name="issued_to_directorate"
                    value={deployForm.issued_to_directorate || ''} onChange={onChange}>
                    <option value="">— None —</option>
                    {locRefs.directorates.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                  </select>
                </F>
                <F label="Department">
                  <select className={inputCls} name="issued_to_department"
                    value={deployForm.issued_to_department || ''} onChange={onChange}>
                    <option value="">— None —</option>
                    {locRefs.departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                  </select>
                </F>
                <F label="Office">
                  <select className={inputCls} name="issued_to_office"
                    value={deployForm.issued_to_office || ''} onChange={onChange}>
                    <option value="">— None —</option>
                    {locRefs.offices.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
                  </select>
                </F>
              </div>

              {/* ── Dates & Notes ──────────────────────────────────── */}
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide border-t pt-3">
                Dates &amp; Notes
              </p>
              <F label="Issue Date">
                <input type="date" className={inputCls} name="issued_date"
                  value={deployForm.issued_date || ''} onChange={onChange} />
              </F>
              <F label="Comments">
                <textarea className={inputCls + ' resize-none'} rows={2} name="comments"
                  placeholder="Optional notes about this deployment…"
                  value={deployForm.comments || ''} onChange={onChange} />
              </F>

            </div>

            <div className="flex gap-3 justify-end mt-6">
              <button onClick={() => setDeployItem(null)} className="px-4 py-2 rounded-lg border text-sm">Cancel</button>
              <button onClick={handleDeploy} disabled={deploySubmitting}
                className="px-4 py-2 rounded-lg bg-green-600 hover:bg-green-700 text-white text-sm font-medium disabled:opacity-50">
                {deploySubmitting ? 'Deploying…' : 'Confirm Deploy'}
              </button>
            </div>
          </Modal>
        )}

        {/* ── Delete Modal ───────────────────────────────────────────── */}
        {deleteId && (
          <Modal title="Confirm Delete" onClose={() => setDeleteId(null)}>
            <p className="text-slate-600 mb-6">Remove this item from stock?</p>
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