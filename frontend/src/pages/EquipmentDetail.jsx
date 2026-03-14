import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import { equipmentApi } from '../services/api';

const TYPE_ICONS = {
  'Desktop': '🖥️', 'Laptop': '💻', 'Server': '🗄️',
  'TV Screen': '📺', 'Projector': '📽️', 'Decoder': '📡',
  'Printer': '🖨️', 'Network Device': '🌐', 'Telephone': '📞',
  'External Storage': '💾', 'Peripheral': '🖱️', 'UPS': '🔋',
};

function Field({ label, value }) {
  if (!value && value !== 0) return null;
  return (
    <div>
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-0.5">{label}</p>
      <p className="text-sm text-slate-800">{value}</p>
    </div>
  );
}

function Section({ title, children }) {
  const hasContent = Array.isArray(children)
    ? children.some(Boolean)
    : Boolean(children);
  if (!hasContent) return null;
  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
      <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">{title}</h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-5">
        {children}
      </div>
    </div>
  );
}

export default function EquipmentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [item, setItem]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  useEffect(() => {
    equipmentApi.retrieve(id)
      .then(d => setItem(d))
      .catch(() => setError('Equipment not found'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return (
    <Layout>
      <div className="flex items-center justify-center h-64">
        <div className="w-10 h-10 border-4 border-[#003580] border-t-transparent rounded-full animate-spin" />
      </div>
    </Layout>
  );

  if (error || !item) return (
    <Layout>
      <div className="p-6 max-w-4xl mx-auto text-center py-24">
        <p className="text-slate-400 text-lg">{error || 'Not found'}</p>
        <button onClick={() => navigate('/equipment')}
          className="mt-4 px-4 py-2 bg-[#003580] text-white rounded-xl text-sm">
          ← Back to Equipment
        </button>
      </div>
    </Layout>
  );

  const icon = TYPE_ICONS[item.equipment_type] || '📦';

  const hasCompute  = ['Desktop', 'Laptop', 'Server'].includes(item.equipment_type);
  const hasServer   = item.equipment_type === 'Server';
  const hasPhone    = item.equipment_type === 'Telephone';
  const hasStorage  = item.equipment_type === 'External Storage';
  const hasDisplay  = item.equipment_type === 'TV Screen';

  return (
    <Layout>
      <div className="p-6 max-w-5xl mx-auto space-y-5">

        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-slate-500">
          <button onClick={() => navigate('/equipment')} className="hover:text-[#003580]">Equipment</button>
          <span>/</span>
          <span className="text-slate-700 font-medium">{item.name || item.serial_number || id}</span>
        </nav>

        {/* Header card */}
        <div className="bg-[#003580] rounded-2xl p-6 text-white flex items-start justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-white/10 flex items-center justify-center text-3xl flex-shrink-0">
              {icon}
            </div>
            <div>
              <p className="text-blue-200 text-xs font-semibold uppercase tracking-widest mb-1">{item.equipment_type || 'Equipment'}</p>
              <h1 className="text-xl font-bold">{item.name || item.model || '—'}</h1>
              <p className="text-blue-200 text-sm mt-0.5">{item.serial_number || ''}</p>
            </div>
          </div>
          <div className="flex flex-col items-end gap-3">
            {item.status_name && (
              <span className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-white/10 text-white">
                {item.status_name}
              </span>
            )}
            {item.is_in_stock && (
              <span className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-emerald-400/20 text-emerald-200">
                In Stock
              </span>
            )}
            <button
              onClick={() => navigate('/equipment')}
              className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-xl text-xs font-medium transition-colors">
              ← Back to List
            </button>
          </div>
        </div>

        {/* Identity */}
        <Section title="Identity">
          <Field label="Device Name"     value={item.name} />
          <Field label="Equipment Type" value={item.equipment_type} />
          <Field label="Brand"          value={item.brand_name} />
          <Field label="Model"          value={item.model} />
          <Field label="Serial Number"  value={item.serial_number} />
          <Field label="Marking Code"   value={item.marking_code} />
          {item.printer_type    && <Field label="Printer Type"    value={item.printer_type} />}
          {item.network_type    && <Field label="Network Type"    value={item.network_type} />}
          {item.telephone_type  && <Field label="Telephone Type"  value={item.telephone_type} />}
          {item.exstorage_type  && <Field label="Storage Type"    value={item.exstorage_type} />}
          {item.peripheral_type && <Field label="Peripheral Type" value={item.peripheral_type} />}
          {item.screen_size     && <Field label="Screen Size"     value={item.screen_size} />}
        </Section>

        {/* Technical specs */}
        {(hasCompute || hasPhone || hasStorage || hasDisplay) && (
  <Section title="Technical Specifications">
    {(hasCompute || hasPhone) && <>
      <Field label="CPU"              value={item.CPU} />
      <Field label="GPU"              value={item.GPU} />
      <Field label="RAM"              value={item.ram_size} />
      <Field label="Storage"          value={item.storage_size} />
      <Field label="Operating System" value={item.operating_system} />
    </>}
    {hasServer && <>
      <Field label="RAM Slots"     value={item.ram_slots} />
      <Field label="Storage Slots" value={item.storage_slots} />
      <Field label="Storage Type"  value={item.storage_type} />
    </>}
    {hasStorage && <Field label="Storage Capacity" value={item.storage_size} />}
    {hasDisplay && <Field label="Screen Size" value={item.screen_size} />}  {/* ← added */}
  </Section>
)}
        
      

        {/* Location */}
        <Section title="Location">
          <Field label="Region"      value={item.region_name} />
          <Field label="DPU"         value={item.dpu_name} />
          <Field label="Station"     value={item.station_name} />
          <Field label="Unit"        value={item.unit_name} />
          <Field label="Directorate" value={item.directorate_name} />
          <Field label="Department"  value={item.department_name} />
          <Field label="Office"      value={item.office_name} />
        </Section>

        {/* Lifecycle */}
        <Section title="Lifecycle">
          <Field label="Deployment Date"  value={item.deployment_date} />
          <Field label="Returned Date"    value={item.returned_date} />
          <Field label="Warranty Expiry"  value={item.warranty_expiration} />
          <Field label="Age (Deployed)"   value={item.age_since_deployed} />
        </Section>

        {/* Comments */}
        {item.comments && (
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Comments</h3>
            <p className="text-sm text-slate-700 whitespace-pre-line">{item.comments}</p>
          </div>
        )}

        {/* Audit */}
        <Section title="Audit">
          <Field label="Created At"   value={item.created_at?.slice(0, 16).replace('T', ' ')} />
          <Field label="Last Updated" value={item.updated_at?.slice(0, 16).replace('T', ' ')} />
          <Field label="Created By"   value={item.created_by_name} />
          <Field label="Updated By"   value={item.updated_by_name} />
        </Section>

      </div>
    </Layout>
  );
}
