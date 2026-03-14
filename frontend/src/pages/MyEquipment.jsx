import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { deploymentsApi } from '../services/api';

const TYPE_ICONS = {
  'Desktop': '🖥️', 'Laptop': '💻', 'Server': '🗄️',
  'TV Screen': '📺', 'Projector': '📽️', 'Decoder': '📡',
  'Printer': '🖨️', 'Network Device': '🌐', 'Telephone': '📞',
  'External Storage': '💾', 'Peripheral': '🖱️', 'UPS': '🔋',
};

export default function MyEquipment() {
  const [deployments, setDeployments] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    // Filter active deployments for current user (backend will filter by auth)
    deploymentsApi.list({ page_size: 50, status: 'Active' })
      .then(d => setDeployments(d?.results || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <Layout>
      <div className="p-6 max-w-5xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-800">My Equipment</h1>
          <p className="text-slate-500 text-sm mt-0.5">Equipment currently deployed to you</p>
        </div>

        {loading ? (
          <p className="text-center py-16 text-slate-400">Loading…</p>
        ) : deployments.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 text-center">
            <p className="text-5xl mb-4">🔧</p>
            <p className="text-slate-600 font-medium">No equipment assigned</p>
            <p className="text-slate-400 text-sm mt-1">Contact IT staff if you believe equipment should be assigned to you.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {deployments.map(dep => {
              const icon = TYPE_ICONS[dep.equipment_type] || '🔧';
              return (
                <div key={dep.id} className="bg-white rounded-xl border border-slate-100 shadow-sm p-5 hover:shadow-md transition-shadow">
                  <div className="flex items-center gap-3 mb-3">
                    <span className="text-3xl">{icon}</span>
                    <div>
                      <p className="font-semibold text-slate-800">{dep.equipment_name || dep.equipment_type || 'Device'}</p>
                      <p className="text-xs text-slate-400">{dep.equipment_type || ''}</p>
                    </div>
                  </div>
                  <div className="space-y-1 text-xs text-slate-500">
                    {dep.equipment_serial && <p><span className="font-medium">S/N:</span> {dep.equipment_serial}</p>}
                    {dep.issued_to_office_name && <p><span className="font-medium">Office:</span> {dep.issued_to_office_name}</p>}
                    {dep.issued_to_unit_name && <p><span className="font-medium">Unit:</span> {dep.issued_to_unit_name}</p>}
                    {dep.issued_date && <p><span className="font-medium">Deployed:</span> {dep.issued_date}</p>}
                    {dep.purpose && <p><span className="font-medium">Purpose:</span> {dep.purpose}</p>}
                  </div>
                  <span className="mt-3 inline-block px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
                    Active
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Layout>
  );
}
