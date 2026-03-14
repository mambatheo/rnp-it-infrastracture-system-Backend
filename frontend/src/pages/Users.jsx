import { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { usersApi } from '../services/api';
import { ROLES, ROLE_LABELS } from '../config/permissions';

// ─── Helpers ──────────────────────────────────────────────────────────────────
const ROLE_OPTIONS = Object.entries(ROLE_LABELS).map(([v, l]) => ({ value: v, label: l }));

const STATUS_BADGE = {
  true:  'bg-green-100 text-green-700',
  false: 'bg-red-100 text-red-600',
};

const emptyForm = {
  email: '', first_name: '', last_name: '',
  phone_number: '', role: ROLES.USER,
  password: '', password_confirm: '',
};

// ─── Modal ────────────────────────────────────────────────────────────────────
function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h3 className="font-bold text-slate-800 text-lg">{title}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-xl leading-none">✕</button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

// ─── Field ────────────────────────────────────────────────────────────────────
function Field({ label, children }) {
  return (
    <div>
      <label className="block text-xs font-semibold text-slate-500 mb-1">{label}</label>
      {children}
    </div>
  );
}

const inputCls = "w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#003580]/30";

// ─── User Form ────────────────────────────────────────────────────────────────
function UserForm({ form, onChange, isEdit = false, errors = {} }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Field label="First Name">
          <input className={inputCls} name="first_name" value={form.first_name} onChange={onChange} />
          {errors.first_name && <p className="text-xs text-red-500 mt-1">{errors.first_name}</p>}
        </Field>
        <Field label="Last Name">
          <input className={inputCls} name="last_name" value={form.last_name} onChange={onChange} />
        </Field>
      </div>
      <Field label="Email">
        <input className={inputCls} type="email" name="email" value={form.email} onChange={onChange} />
        {errors.email && <p className="text-xs text-red-500 mt-1">{errors.email}</p>}
      </Field>
      <Field label="Phone Number (10 digits)">
        <input className={inputCls} name="phone_number" value={form.phone_number} onChange={onChange} maxLength={10} />
      </Field>
      <Field label="Role">
        <select className={inputCls} name="role" value={form.role} onChange={onChange}>
          {ROLE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </Field>
      {!isEdit && (
        <>
          <Field label="Password">
            <input className={inputCls} type="password" name="password" value={form.password} onChange={onChange} />
            {errors.password && <p className="text-xs text-red-500 mt-1">{errors.password}</p>}
          </Field>
          <Field label="Confirm Password">
            <input className={inputCls} type="password" name="password_confirm" value={form.password_confirm} onChange={onChange} />
          </Field>
        </>
      )}
      {isEdit && (
        <Field label="Active">
          <select className={inputCls} name="is_active" value={String(form.is_active)} onChange={onChange}>
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </select>
        </Field>
      )}
    </div>
  );
}

// ─── Confirm Dialog ───────────────────────────────────────────────────────────
function ConfirmDialog({ message, onConfirm, onCancel }) {
  return (
    <Modal title="Confirm Action" onClose={onCancel}>
      <p className="text-slate-600 mb-6">{message}</p>
      <div className="flex gap-3 justify-end">
        <button onClick={onCancel} className="px-4 py-2 rounded-lg border text-sm">Cancel</button>
        <button onClick={onConfirm} className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm hover:bg-red-700">Confirm</button>
      </div>
    </Modal>
  );
}

// ─── Toast ────────────────────────────────────────────────────────────────────
function Toast({ msg, type }) {
  if (!msg) return null;
  return (
    <div className={`fixed bottom-6 right-6 z-[100] px-5 py-3 rounded-xl shadow-lg text-sm font-medium text-white
      ${type === 'error' ? 'bg-red-500' : 'bg-green-500'}`}>
      {msg}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function Users() {
  const [users, setUsers]         = useState([]);
  const [total, setTotal]         = useState(0);
  const [page, setPage]           = useState(1);
  const [search, setSearch]       = useState('');
  const [loading, setLoading]     = useState(false);

  const [modal, setModal]         = useState(null); // 'create' | 'edit' | 'confirm'
  const [selected, setSelected]   = useState(null);
  const [form, setForm]           = useState(emptyForm);
  const [formErrors, setFormErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [confirmAction, setConfirmAction] = useState(null);

  const [toast, setToast]         = useState({ msg: '', type: 'success' });

  const pageSize = 15;

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast({ msg: '', type }), 3000);
  };

  // ── Fetch ──────────────────────────────────────────────────────────────────
  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await usersApi.list({ page, search, page_size: pageSize });
      setUsers(data.results || []);
      setTotal(data.count || 0);
    } catch (e) {
      showToast('Failed to load users', 'error');
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  // ── Form helpers ───────────────────────────────────────────────────────────
  const handleChange = e => {
    const { name, value } = e.target;
    setForm(f => ({ ...f, [name]: value }));
    setFormErrors(fe => ({ ...fe, [name]: undefined }));
  };

  const openCreate = () => {
    setForm(emptyForm);
    setFormErrors({});
    setSelected(null);
    setModal('create');
  };

  const openEdit = user => {
    setForm({ ...user, password: '', password_confirm: '' });
    setFormErrors({});
    setSelected(user);
    setModal('edit');
  };

  // ── Create ─────────────────────────────────────────────────────────────────
  const handleCreate = async () => {
    setSubmitting(true);
    try {
      await usersApi.create(form);
      showToast('User created successfully');
      setModal(null);
      fetchUsers();
    } catch (err) {
      if (typeof err === 'object') setFormErrors(err);
      else showToast('Failed to create user', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  // ── Edit ───────────────────────────────────────────────────────────────────
  const handleEdit = async () => {
    setSubmitting(true);
    try {
      const payload = {
        email: form.email,
        first_name: form.first_name,
        last_name: form.last_name,
        phone_number: form.phone_number,
        role: form.role,
        is_active: form.is_active === 'true' || form.is_active === true,
      };
      await usersApi.update(selected.id, payload);
      showToast('User updated');
      setModal(null);
      fetchUsers();
    } catch (err) {
      if (typeof err === 'object') setFormErrors(err);
      else showToast('Failed to update user', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  // ── Activate / Deactivate ──────────────────────────────────────────────────
  const handleToggleActive = (user) => {
    const action = user.is_active ? 'deactivate' : 'activate';
    setConfirmAction({
      message: `Are you sure you want to ${action} ${user.first_name} ${user.last_name}?`,
      onConfirm: async () => {
        try {
          if (user.is_active) await usersApi.deactivate(user.id);
          else                await usersApi.activate(user.id);
          showToast(`User ${action}d`);
          fetchUsers();
        } catch {
          showToast(`Failed to ${action} user`, 'error');
        }
        setConfirmAction(null);
      },
    });
  };

  // ── Delete ─────────────────────────────────────────────────────────────────
  const handleDelete = user => {
    setConfirmAction({
      message: `Permanently delete ${user.first_name} ${user.last_name}? This cannot be undone.`,
      onConfirm: async () => {
        try {
          await usersApi.delete(user.id);
          showToast('User deleted');
          fetchUsers();
        } catch {
          showToast('Failed to delete user', 'error');
        }
        setConfirmAction(null);
      },
    });
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <Layout>
      <div className="p-6 max-w-7xl mx-auto">
        {/* ── Header ── */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-800">Users</h1>
            <p className="text-slate-500 text-sm mt-0.5">{total} total users</p>
          </div>
          <button
            onClick={openCreate}
            className="inline-flex items-center gap-2 bg-[#003580] text-white px-4 py-2.5 rounded-xl text-sm font-medium hover:bg-[#002060] transition-colors"
          >
            <span className="text-lg leading-none">+</span> Add User
          </button>
        </div>

        {/* ── Search ── */}
        <div className="mb-4">
          <input
            className="w-full max-w-xs border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#003580]/30"
            placeholder="Search by name or email…"
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
          />
        </div>

        {/* ── Table ── */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-100">
                  {['Name', 'Email', 'Phone', 'Role', 'Status', 'Actions'].map(h => (
                    <th key={h} className="text-left px-4 py-3 font-semibold text-slate-600 text-xs uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={6} className="text-center py-12 text-slate-400">Loading…</td></tr>
                ) : users.length === 0 ? (
                  <tr><td colSpan={6} className="text-center py-12 text-slate-400">No users found.</td></tr>
                ) : users.map(u => (
                  <tr key={u.id} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-[#003580]/10 flex items-center justify-center flex-shrink-0">
                          <span className="text-[#003580] text-xs font-bold">
                            {(u.first_name?.[0] || '') + (u.last_name?.[0] || '')}
                          </span>
                        </div>
                        <span className="font-medium text-slate-800">{u.first_name} {u.last_name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{u.email}</td>
                    <td className="px-4 py-3 text-slate-500">{u.phone_number || '—'}</td>
                    <td className="px-4 py-3">
                      <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-[#003580]/10 text-[#003580]">
                        {ROLE_LABELS[u.role] || u.role}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${STATUS_BADGE[u.is_active]}`}>
                        {u.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 flex-wrap">
                        <button onClick={() => openEdit(u)}
                          className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium transition-colors">
                          Edit
                        </button>
                        <button onClick={() => handleToggleActive(u)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors
                            ${u.is_active ? 'bg-orange-100 hover:bg-orange-200 text-orange-700' : 'bg-green-100 hover:bg-green-200 text-green-700'}`}>
                          {u.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                        <button onClick={() => handleDelete(u)}
                          className="px-3 py-1.5 rounded-lg bg-red-100 hover:bg-red-200 text-red-600 text-xs font-medium transition-colors">
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* ── Pagination ── */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100">
              <p className="text-xs text-slate-400">Page {page} of {totalPages}</p>
              <div className="flex gap-2">
                <button disabled={page === 1} onClick={() => setPage(p => p - 1)}
                  className="px-3 py-1.5 rounded-lg text-xs border disabled:opacity-40 hover:bg-slate-50">← Prev</button>
                <button disabled={page === totalPages} onClick={() => setPage(p => p + 1)}
                  className="px-3 py-1.5 rounded-lg text-xs border disabled:opacity-40 hover:bg-slate-50">Next →</button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Modals ── */}
      {modal === 'create' && (
        <Modal title="Create New User" onClose={() => setModal(null)}>
          <UserForm form={form} onChange={handleChange} errors={formErrors} />
          <div className="flex gap-3 justify-end mt-6">
            <button onClick={() => setModal(null)} className="px-4 py-2 rounded-lg border text-sm">Cancel</button>
            <button onClick={handleCreate} disabled={submitting}
              className="px-4 py-2 rounded-lg bg-[#003580] text-white text-sm hover:bg-[#002060] disabled:opacity-50">
              {submitting ? 'Creating…' : 'Create User'}
            </button>
          </div>
        </Modal>
      )}

      {modal === 'edit' && selected && (
        <Modal title={`Edit — ${selected.first_name} ${selected.last_name}`} onClose={() => setModal(null)}>
          <UserForm form={form} onChange={handleChange} isEdit errors={formErrors} />
          <div className="flex gap-3 justify-end mt-6">
            <button onClick={() => setModal(null)} className="px-4 py-2 rounded-lg border text-sm">Cancel</button>
            <button onClick={handleEdit} disabled={submitting}
              className="px-4 py-2 rounded-lg bg-[#003580] text-white text-sm hover:bg-[#002060] disabled:opacity-50">
              {submitting ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </Modal>
      )}

      {confirmAction && (
        <ConfirmDialog
          message={confirmAction.message}
          onConfirm={confirmAction.onConfirm}
          onCancel={() => setConfirmAction(null)}
        />
      )}

      <Toast msg={toast.msg} type={toast.type} />
    </Layout>
  );
}
