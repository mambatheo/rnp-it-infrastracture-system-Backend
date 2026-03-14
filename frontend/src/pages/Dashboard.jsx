import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { usersApi, equipmentApi, stockApi, deploymentsApi } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { ROLES } from '../config/permissions';

function StatCard({ icon, label, value, sub, color = 'blue' }) {
  const colors = {
    blue:   'bg-blue-50 text-blue-600',
    green:  'bg-green-50 text-green-600',
    orange: 'bg-orange-50 text-orange-600',
    red:    'bg-red-50 text-red-600',
    purple: 'bg-purple-50 text-purple-600',
    slate:  'bg-slate-100 text-slate-600',
  };
  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 flex items-center gap-4">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-xl flex-shrink-0 ${colors[color]}`}>
        {icon}
      </div>
      <div>
        <p className="text-slate-400 text-xs font-medium uppercase tracking-wide">{label}</p>
        <p className="text-2xl font-bold text-slate-800">{value ?? '—'}</p>
        {sub && <p className="text-slate-400 text-xs mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div>
      <h2 className="text-base font-semibold text-slate-700 mb-3">{title}</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">{children}</div>
    </div>
  );
}

export default function Dashboard() {
  const { role, user } = useAuth();
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      const p1 = { page_size: 1 };
      const results = {};

      const safe = async (key, fn) => {
        try { results[key] = await fn(); } catch { results[key] = null; }
      };

      // Helper: fetch equipment count filtered by equipment_type
      const eqCount = (type) => equipmentApi.list({ page_size: 1, equipment_type: type });

      if (role === ROLES.ADMIN) {
        await Promise.allSettled([
          safe('users',        () => usersApi.list(p1)),
          // Equipment by type
          safe('desktops',     () => eqCount('Desktop')),
          safe('laptops',      () => eqCount('Laptop')),
          safe('servers',      () => eqCount('Server')),
          safe('tvscreens',    () => eqCount('TV Screen')),
          safe('projectors',   () => eqCount('Projector')),
          safe('decoders',     () => eqCount('Decoder')),
          safe('printers',     () => eqCount('Printer')),
          safe('networks',     () => eqCount('Network Device')),
          safe('telephones',   () => eqCount('Telephone')),
          safe('exstorages',   () => eqCount('External Storage')),
          safe('peripherals',  () => eqCount('Peripheral')),
          safe('ups',          () => eqCount('UPS')),
          // Totals
          safe('allEquipment', () => equipmentApi.list(p1)),
          safe('stock',        () => stockApi.list(p1)),
          safe('deployments',  () => deploymentsApi.list(p1)),
        ]);
      } else if (role === ROLES.IT_STAFF) {
        await Promise.allSettled([
          safe('desktops',     () => eqCount('Desktop')),
          safe('laptops',      () => eqCount('Laptop')),
          safe('servers',      () => eqCount('Server')),
          safe('printers',     () => eqCount('Printer')),
          safe('allEquipment', () => equipmentApi.list(p1)),
          safe('stock',        () => stockApi.list(p1)),
          safe('deployments',  () => deploymentsApi.list(p1)),
        ]);
      }
      // Technician and User roles: maintenance module not yet available

      setStats(results);
      setLoading(false);
    };
    load();
  }, [role]);

  const count = key => {
    const d = stats[key];
    if (!d) return '…';
    if (typeof d.count === 'number') return d.count;
    if (Array.isArray(d)) return d.length;
    if (Array.isArray(d.results)) return d.results.length;
    return '—';
  };

  return (
    <Layout>
      <div className="p-6 max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-800">
            Good {new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 17 ? 'afternoon' : 'evening'}, {user?.first_name || 'there'} 
          </h1>
          <p className="text-slate-500 text-sm mt-0.5 capitalize">
            {role?.replace('_',' ') || 'User'} · {new Date().toLocaleDateString('en-GB', { weekday:'long', day:'numeric', month:'long', year:'numeric' })}
          </p>
        </div>

        {loading ? (
          <div className="grid place-items-center py-24">
            <div className="w-10 h-10 border-4 border-[#003580] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="space-y-8">
            {/* ── ADMIN ── */}
            {role === ROLES.ADMIN && (
              <>
                <Section title="Users">
                  <StatCard icon="👥" label="Total Users"    value={count('users')}       color="blue" />
                </Section>
                <Section title="Equipment Overview">
                  <StatCard icon="📦" label="All Equipment"  value={count('allEquipment')} color="blue" />
                  <StatCard icon="🏪" label="In Stock"       value={count('stock')}        color="green" />
                  <StatCard icon="🚚" label="Deployments"    value={count('deployments')} color="orange" />
                </Section>
                <Section title="Equipment by Type">
                  <StatCard icon="🖥️" label="Desktops"        value={count('desktops')}    color="blue" />
                  <StatCard icon="💻" label="Laptops"          value={count('laptops')}     color="blue" />
                  <StatCard icon="🗄️" label="Servers"          value={count('servers')}     color="blue" />
                  <StatCard icon="📺" label="TV Screens"        value={count('tvscreens')}   color="purple" />
                  <StatCard icon="📽️" label="Projectors"        value={count('projectors')}  color="purple" />
                  <StatCard icon="📡" label="Decoders"          value={count('decoders')}    color="purple" />
                  <StatCard icon="🖨️" label="Printers"          value={count('printers')}    color="slate" />
                  <StatCard icon="🌐" label="Network Devices"   value={count('networks')}    color="green" />
                  <StatCard icon="📞" label="Telephones"        value={count('telephones')}  color="orange" />
                  <StatCard icon="💾" label="Ext. Storage"      value={count('exstorages')}  color="slate" />
                  <StatCard icon="🖱️" label="Peripherals"       value={count('peripherals')} color="slate" />
                  <StatCard icon="🔋" label="UPS"               value={count('ups')}         color="slate" />
                </Section>
                <Section title="Maintenance">
                  <StatCard icon="🔧" label="Total Requests"   value={count('requests')}  color="orange" />
                  <StatCard icon="⏳" label="Pending Requests" value={count('pending')}   color="red"
                    sub="Needs attention" />
                </Section>
              </>
            )}

            {/* ── IT STAFF ── */}
            {role === ROLES.IT_STAFF && (
              <>
                <Section title="Equipment Overview">
                  <StatCard icon="📦" label="All Equipment"  value={count('allEquipment')} color="blue" />
                  <StatCard icon="🏪" label="In Stock"       value={count('stock')}        color="green" />
                  <StatCard icon="🚚" label="Deployments"    value={count('deployments')} color="orange" />
                </Section>
                <Section title="Equipment by Type">
                  <StatCard icon="🖥️" label="Desktops"  value={count('desktops')}  color="blue" />
                  <StatCard icon="💻" label="Laptops"    value={count('laptops')}   color="blue" />
                  <StatCard icon="🗄️" label="Servers"    value={count('servers')}   color="blue" />
                  <StatCard icon="🖨️" label="Printers"   value={count('printers')}  color="slate" />
                </Section>
                <Section title="Maintenance">
                  <StatCard icon="🔧" label="All Requests" value={count('requests')} color="orange" />
                  <StatCard icon="⏳" label="Pending"      value={count('pending')}  color="red" />
                </Section>
              </>
            )}

            {/* ── TECHNICIAN ── */}
            {role === ROLES.TECHNICIAN && (
              <Section title="Maintenance">
                <div className="col-span-4 bg-slate-50 rounded-xl p-6 text-center text-slate-400">
                  🔧 Maintenance module coming soon
                </div>
              </Section>
            )}

            {/* ── USER ── */}
            {role === ROLES.USER && (
              <Section title="My Activity">
                <div className="col-span-4 bg-slate-50 rounded-xl p-6 text-center text-slate-400">
                  🔧 Maintenance module coming soon
                </div>
              </Section>
            )}
          </div>
        )}
      </div>
    </Layout>
  );
}
