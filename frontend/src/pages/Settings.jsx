import { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import {
  brandsApi, regionsApi, dpusApi, stationsApi, unitsApi,
  categoriesApi, statusesApi,
  directoratesApi, departmentsApi, officesApi, dpuOfficesApi, regionOfficesApi
} from '../services/api';

const inputCls = "w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#003580]/30";

function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h3 className="font-bold text-slate-800">{title}</h3>
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

// ─── ResourcePanel ────────────────────────────────────────────────────────────
const PAGE_SIZE = 20;

function ResourcePanel({ config }) {
  const { api, label, description, fields, columns } = config;

  const [items, setItems]       = useState([]);
  const [total, setTotal]       = useState(0);
  const [page, setPage]         = useState(1);
  const [loading, setLoading]   = useState(false);
  const [modal, setModal]       = useState(null);
  const [selected, setSelected] = useState(null);
  const [form, setForm]         = useState({});
  const [submitting, setSub]    = useState(false);
  const [deleteId, setDeleteId] = useState(null);
  const [toast, setToast]       = useState({ msg: '', type: 'success' });
  const [fkOptions, setFkOptions] = useState({});

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast({ msg: '', type }), 3000);
  };

  const emptyForm = () => Object.fromEntries(fields.map(f => [f.name, '']));

  // Load FK options for dropdowns
  useEffect(() => {
    fields.forEach(f => {
      if (f.type === 'fk' && f.optionsApi) {
        f.optionsApi({ page_size: 500 })
          .then(d => setFkOptions(prev => ({ ...prev, [f.name]: d.results || d || [] })))
          .catch(() => {});
      }
    });
  }, [fields]);

  const fetchItems = useCallback(async (p = page) => {
    setLoading(true);
    try {
      const d = await api.list({ page: p, page_size: PAGE_SIZE });
      setItems(d.results || d || []);
      setTotal(typeof d.count === 'number' ? d.count : (d.results || d || []).length);
    } catch { showToast('Failed to load ' + label, 'error'); }
    finally { setLoading(false); }
  }, [api, label, page]);

  useEffect(() => { fetchItems(page); }, [page, fetchItems]);

  const openCreate = () => { setForm(emptyForm()); setSelected(null); setModal('form'); };
  const openEdit = item => {
    const f = {};
    fields.forEach(field => { f[field.name] = item[field.name] ?? ''; });
    setForm(f); setSelected(item); setModal('form');
  };

  const handleSubmit = async () => {
    setSub(true);
    try {
      const writableKeys = fields.map(f => f.name);
      const payload = Object.fromEntries(
        Object.entries(form).filter(([k]) => writableKeys.includes(k))
      );
      fields.filter(f => f.type === 'fk').forEach(f => {
        if (!payload[f.name]) payload[f.name] = null;
      });
      if (selected) { await api.update(selected.id, payload); showToast(`${label} updated`); }
      else          { await api.create(payload);               showToast(`${label} created`); }
      setModal(null); fetchItems(page);
    } catch (err) {
      const msg = err && typeof err === 'object'
        ? Object.entries(err).map(([k,v]) => `${k}: ${Array.isArray(v) ? v[0] : v}`).join(' | ')
        : 'Failed to save';
      showToast(msg, 'error');
    } finally { setSub(false); }
  };

  const handleDelete = async () => {
    try { await api.delete(deleteId); showToast(`${label} deleted`); setDeleteId(null); fetchItems(page); }
    catch { showToast('Failed to delete', 'error'); }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-slate-800">{label}</h2>
          <p className="text-slate-400 text-xs mt-0.5">{description} &mdash; <span className="font-medium text-slate-500">{total} total</span></p>
        </div>
        <button onClick={openCreate}
          className="inline-flex items-center gap-1.5 bg-[#003580] text-white px-3 py-2 rounded-xl text-sm font-medium hover:bg-[#002060]">
          <span className="text-base leading-none">+</span> Add
        </button>
      </div>

      <div className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden">
        {loading ? (
          <p className="text-center py-10 text-slate-400 text-sm">Loading…</p>
        ) : items.length === 0 ? (
          <p className="text-center py-10 text-slate-400 text-sm">No {label.toLowerCase()} yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                {columns.map(c => (
                  <th key={c.key} className="text-left px-4 py-3 font-semibold text-slate-500 text-xs uppercase tracking-wide">{c.label}</th>
                ))}
                <th className="text-left px-4 py-3 font-semibold text-slate-500 text-xs uppercase">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map(item => (
                <tr key={item.id} className="border-b border-slate-50 hover:bg-slate-50/60 transition-colors">
                  {columns.map(c => (
                    <td key={c.key} className="px-4 py-3 text-slate-700">
                      {c.render ? c.render(item) : (item[c.key] || '—')}
                    </td>
                  ))}
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button onClick={() => openEdit(item)}
                        className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium">Edit</button>
                      <button onClick={() => setDeleteId(item.id)}
                        className="px-3 py-1.5 rounded-lg bg-red-100 hover:bg-red-200 text-red-600 text-xs font-medium">Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-3 px-1">
          <p className="text-xs text-slate-400">
            Page {page} of {totalPages} &mdash; {((page-1)*PAGE_SIZE)+1}–{Math.min(page*PAGE_SIZE, total)} of {total}
          </p>
          <div className="flex gap-2">
            <button onClick={() => setPage(p => Math.max(1, p-1))} disabled={page === 1}
              className="px-3 py-1.5 rounded-lg border text-xs font-medium disabled:opacity-40 hover:bg-slate-50">← Prev</button>
            <button onClick={() => setPage(p => Math.min(totalPages, p+1))} disabled={page === totalPages}
              className="px-3 py-1.5 rounded-lg border text-xs font-medium disabled:opacity-40 hover:bg-slate-50">Next →</button>
          </div>
        </div>
      )}

      {modal === 'form' && (
        <Modal title={selected ? `Edit ${label}` : `Add ${label}`} onClose={() => setModal(null)}>
          <div className="space-y-4">
            {fields.map(f => (
              <div key={f.name}>
                <label className="block text-xs font-semibold text-slate-500 mb-1">{f.label}</label>
                {f.type === 'fk' ? (
                  <select className={inputCls} value={form[f.name] || ''} onChange={e => setForm(x => ({ ...x, [f.name]: e.target.value }))}>
                    <option value="">— Select —</option>
                    {(fkOptions[f.name] || []).map(o => (
                      <option key={o.id} value={o.id}>{o.name}</option>
                    ))}
                  </select>
                ) : (
                  <input className={inputCls} type={f.type || 'text'} value={form[f.name] || ''}
                    onChange={e => setForm(x => ({ ...x, [f.name]: e.target.value }))} />
                )}
              </div>
            ))}
          </div>
          <div className="flex gap-3 justify-end mt-6">
            <button onClick={() => setModal(null)} className="px-4 py-2 rounded-lg border text-sm">Cancel</button>
            <button onClick={handleSubmit} disabled={submitting}
              className="px-4 py-2 rounded-lg bg-[#003580] text-white text-sm hover:bg-[#002060] disabled:opacity-50">
              {submitting ? 'Saving…' : 'Save'}
            </button>
          </div>
        </Modal>
      )}

      {deleteId && (
        <Modal title="Confirm Delete" onClose={() => setDeleteId(null)}>
          <p className="text-slate-600 mb-6">Are you sure you want to delete this {label.toLowerCase()}?</p>
          <div className="flex gap-3 justify-end">
            <button onClick={() => setDeleteId(null)} className="px-4 py-2 rounded-lg border text-sm">Cancel</button>
            <button onClick={handleDelete} className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm">Delete</button>
          </div>
        </Modal>
      )}

      <Toast msg={toast.msg} type={toast.type} />
    </div>
  );
}

// ─── Tab configs ──────────────────────────────────────────────────────────────
const TABS = [
  // ── Classification ─────────────────────────────────────────────────────────
  {
    key: 'categories',
    label: 'Categories',
    description: 'Equipment categories (Computer, Printer, Display, etc.)',
    api: categoriesApi,
    fields: [{ name: 'name', label: 'Category Name', type: 'text' }],
    columns: [{ key: 'name', label: 'Name' }],
  },
  {
    key: 'statuses',
    label: 'Statuses',
    description: 'Equipment statuses (Active, Faulty, Under Repair, etc.)',
    api: statusesApi,
    fields: [{ name: 'name', label: 'Status Name', type: 'text' }],
    columns: [{ key: 'name', label: 'Status' }],
  },
  {
    key: 'brands',
    label: 'Brands',
    description: 'Equipment brands linked to categories',
    api: brandsApi,
    fields: [
      { name: 'name', label: 'Brand Name', type: 'text' },
      { name: 'category', label: 'Category', type: 'fk', optionsApi: (p) => categoriesApi.list(p) },
    ],
    columns: [
      { key: 'name', label: 'Brand' },
      { key: 'category_name', label: 'Category' },
    ],
  },

  // ── Location ──────────────────────────────────────────────────────────────
  {
    key: 'regions',
    label: 'Regions',
    description: 'Regions',
    api: regionsApi,
    fields: [{ name: 'name', label: 'Region Name', type: 'text' }],
    columns: [{ key: 'name', label: 'Region' }],
  },
  {
    key: 'region-offices',
    label: 'Region HQ',
    description: 'Region Offices:',
    api: regionOfficesApi,
    fields: [
      { name: 'name', label: 'Office Name', type: 'text' },
      { name: 'region', label: 'Region', type: 'fk', optionsApi: (p) => regionsApi.list(p) },
    ],
    columns: [
      { key: 'name', label: 'Office Name' },
      { key: 'region_name', label: 'Region' },
    ],
  },
  {
    key: 'dpus',
    label: 'DPUs',
    description: 'DPU:',
    api: dpusApi,
    fields: [
      { name: 'name', label: 'DPU Name', type: 'text' },
      { name: 'region', label: 'Region', type: 'fk', optionsApi: (p) => regionsApi.list(p) },
    ],
    columns: [
      { key: 'name', label: 'DPU' },
      { key: 'region_name', label: 'Region' },
    ],
  },
  {
    key: 'dpu-offices',
    label: 'DPU HQ',
    description: 'DPU Offices:',
    api: dpuOfficesApi,
    fields: [
      { name: 'name', label: 'Office Name', type: 'text' },
      { name: 'dpu', label: 'DPU', type: 'fk', optionsApi: (p) => dpusApi.list(p) },
    ],
    columns: [
      { key: 'name', label: 'Office Name' },
      { key: 'dpu_name', label: 'DPU' },
    ],
  },
  {
    key: 'stations',
    label: 'Stations',
    description: 'Stations:',
    api: stationsApi,
    fields: [
      { name: 'name', label: 'Station Name', type: 'text' },
      { name: 'dpu', label: 'DPU', type: 'fk', optionsApi: (p) => dpusApi.list(p) },
    ],
    columns: [
      { key: 'name', label: 'Station' },
      { key: 'dpu_name', label: 'DPU' },
     
    ],
  },

  // ── Organisation ──────────────────────────────────────────────────────────
  {
    key: 'units',
    label: 'Units',
    description: 'Organisation units',
    api: unitsApi,
    fields: [{ name: 'name', label: 'Unit Name', type: 'text' }],
    columns: [{ key: 'name', label: 'Unit' }],
  },
  {
    key: 'directorates',
    label: 'Directorates',
    description: 'Directorates :',
    api: directoratesApi,
    fields: [
      { name: 'name', label: 'Directorate Name', type: 'text' },
      { name: 'unit', label: 'Unit', type: 'fk', optionsApi: (p) => unitsApi.list(p) },
    ],
    columns: [
      { key: 'name', label: 'Directorate' },
      { key: 'unit_name', label: 'Unit' },
    ],
  },
  {
    key: 'departments',
    label: 'Departments',
    description: 'Departments:',
    api: departmentsApi,
    fields: [
      { name: 'name', label: 'Department Name', type: 'text' },
      { name: 'directorate', label: 'Directorate', type: 'fk', optionsApi: (p) => directoratesApi.list(p) },
    ],
    columns: [
      { key: 'name', label: 'Department' },
      { key: 'directorate_name', label: 'Directorate' },
      { key: 'unit_name', label: 'Unit' },
    ],
  },
  {
    key: 'offices',
    label: 'Offices',
    description: 'Offices:',
    api: officesApi,
    fields: [
      { name: 'name', label: 'Office Name', type: 'text' },
      { name: 'department', label: 'Department', type: 'fk', optionsApi: (p) => departmentsApi.list(p) },
      { name: 'directorate', label: 'Directorate', type: 'fk', optionsApi: (p) => directoratesApi.list(p) },
      { name: 'unit', label: 'UNIT', type: 'fk', optionsApi: (p) => unitsApi.list(p) },
    ],
    columns: [
      { key: 'name', label: 'Office' },
      { key: 'department_name', label: 'Department' },
      { key: 'directorate_name', label: 'Directorate' },
      { key: 'unit_name', label: 'Unit' },
    ],
  },
];

// ─── Group tabs for navigation ────────────────────────────────────────────────
const TAB_GROUPS = [
  { label: 'Classification', keys: ['categories', 'statuses', 'brands'] },
  { label: 'Territorial Units', keys: ['regions', 'region-offices', 'dpus', 'dpu-offices', 'stations'] },
 
  { label: ' Special Units ',   keys: ['units', 'directorates', 'departments', 'offices'] },
];

// ─── Main ─────────────────────────────────────────────────────────────────────
export default function Settings() {
  const [activeTab, setActiveTab] = useState(TABS[0].key);
  const tab = TABS.find(t => t.key === activeTab);

  return (
    <Layout>
      <div className="p-6 max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-800">Settings</h1>
          <p className="text-slate-500 text-sm mt-0.5">Manage  data used across the system</p>
        </div>

        {/* Grouped Tabs */}
        <div className="space-y-2 mb-6">
          {TAB_GROUPS.map(group => (
            <div key={group.label}>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-1 mb-1">{group.label}</p>
              <div className="flex gap-1 flex-wrap">
                {group.keys.map(key => {
                  const t = TABS.find(x => x.key === key);
                  return (
                    <button key={key} onClick={() => setActiveTab(key)}
                      className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all
                        ${activeTab === key ? 'bg-[#003580] text-white shadow' : 'bg-white border border-slate-200 text-slate-600 hover:text-slate-800 hover:bg-slate-50'}`}>
                      {t?.label}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {tab && <ResourcePanel key={activeTab} config={tab} />}
      </div>
    </Layout>
  );
}
