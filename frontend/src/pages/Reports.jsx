import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { reportsApi } from '../services/api';

const EQUIPMENT_TYPES = [
  { key: 'Desktop',          label: 'Desktops',        color: '#003366' },
  { key: 'Laptop',           label: 'Laptops',         color: '#003366' },
  { key: 'Server',           label: 'Servers',         color: '#003366' },
  { key: 'TV Screen',        label: 'TV Screens',      color: '#003366' },
  { key: 'Projector',        label: 'Projectors',      color: '#003366' },
  { key: 'Decoder',          label: 'Decoders',        color: '#003366' },
  { key: 'Printer',          label: 'Printers',        color: '#003366' },
  { key: 'Network Device',   label: 'Network Devices', color: '#003366' },
  { key: 'Telephone',        label: 'Telephones',      color: '#003366' },
  { key: 'External Storage', label: 'Ext. Storage',    color: '#003366' },
  { key: 'Peripheral',       label: 'Peripherals',     color: '#003366' },
  { key: 'UPS',              label: 'UPS',             color: '#003366' },
];

const UNIT_COLOR   = '#003366';
const REGION_COLOR = '#003366';
const DPU_COLOR    = '#003366';

function DlBtn({ label, icon, onClick, loading, color = '#003366' }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all disabled:opacity-50 disabled:cursor-not-allowed"
      style={{ borderColor: color, color }}
      onMouseEnter={e => { e.currentTarget.style.background = color; e.currentTarget.style.color = '#fff'; }}
      onMouseLeave={e => { e.currentTarget.style.background = ''; e.currentTarget.style.color = color; }}
    >
      {loading ? <span className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" /> : icon}
      {label}
    </button>
  );
}

function ReportCard({ label, count, total, color, onExcel, onPdf }) {
  const [busy, setBusy] = useState({ excel: false, pdf: false });
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;

  const dl = (format) => {
    setBusy(b => ({ ...b, [format]: true }));
    try { if (format === 'excel') onExcel(); else onPdf(); }
    finally { setTimeout(() => setBusy(b => ({ ...b, [format]: false })), 300); }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div>
            <p className="font-semibold text-slate-800 text-sm leading-tight">{label}</p>
            <p className="text-2xl font-bold text-slate-800">{count ?? '…'}</p>
          </div>
        </div>
        <span className="text-xs font-medium text-slate-400 mt-1">{pct}%</span>
      </div>
      <div className="h-1.5 bg-slate-100 rounded-full mb-4 overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
      <div className="flex gap-2 flex-wrap">
        <DlBtn icon="📊" label="Excel" onClick={() => dl('excel')} loading={busy.excel} color={color} />
        <DlBtn icon="📄" label="PDF"   onClick={() => dl('pdf')}   loading={busy.pdf}   color={color} />
      </div>
    </div>
  );
}

function Section({ title, subtitle, accent, totalLabel, totalValue, onExcel, onPdf, gridLabel, children }) {
  const [allBusy, setAllBusy] = useState({ excel: false, pdf: false });
  const dlAll = (format) => {
    setAllBusy(b => ({ ...b, [format]: true }));
    try { if (format === 'excel') onExcel(); else onPdf(); }
    finally { setTimeout(() => setAllBusy(b => ({ ...b, [format]: false })), 300); }
  };

  return (
    <div className="mb-10">
      <div className="rounded-2xl p-5 mb-5 flex items-center justify-between flex-wrap gap-4"
        style={{ background: accent }}>
        <div className="text-white">
          <p className="text-xs font-semibold uppercase tracking-widest opacity-80">{subtitle}</p>
          <p className="text-3xl font-bold mt-0.5">{totalValue ?? '…'}</p>
          <p className="text-sm opacity-70 mt-0.5">{totalLabel}</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-white text-xs opacity-70 font-medium">Full {title} Report:</span>
          <button onClick={() => dlAll('excel')} disabled={allBusy.excel}
            className="flex items-center gap-1.5 bg-white/20 hover:bg-white/30 text-white px-4 py-2 rounded-xl text-sm font-medium disabled:opacity-50 transition-colors">
            {allBusy.excel ? <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> : '📊'}
            Excel
          </button>
          <button onClick={() => dlAll('pdf')} disabled={allBusy.pdf}
            className="flex items-center gap-1.5 bg-white/20 hover:bg-white/30 text-white px-4 py-2 rounded-xl text-sm font-medium disabled:opacity-50 transition-colors">
            {allBusy.pdf ? <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> : '📄'}
            PDF
          </button>
        </div>
      </div>
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-600 uppercase tracking-wide">
          {gridLabel ?? 'Per Equipment Type'}
        </h2>
        <p className="text-xs text-slate-400">Click Excel / PDF on a card to export individually</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {children}
      </div>
    </div>
  );
}

export default function Reports() {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  useEffect(() => {
    // Single aggregated call — replaces ~60 individual requests
    reportsApi.counts()
      .then(d => { setData(d); setLoading(false); })
      .catch(() => { setError('Failed to load report data.'); setLoading(false); });
  }, []);

  // Derived values — only computed once data is available
  const { totals, equipment_counts, stock_counts, unit_counts, region_counts, dpu_counts } = data ?? {};

  const eqCounts     = equipment_counts ?? {};
  const stockCounts  = stock_counts     ?? {};
  const unitCounts   = unit_counts      ?? {};
  const regionCounts = region_counts    ?? {};
  const dpuCounts    = dpu_counts       ?? {};

  const eqTotal     = Object.values(eqCounts).reduce((s, v) => s + (v || 0), 0);
  const stockTotal  = Object.values(stockCounts).reduce((s, v) => s + (v || 0), 0);

  // unit_counts / region_counts / dpu_counts shape: { "<uuid>": { count, name } }
  const unitEntries   = Object.entries(unitCounts).sort((a, b) => a[1].name.localeCompare(b[1].name));
  const regionEntries = Object.entries(regionCounts).sort((a, b) => a[1].name.localeCompare(b[1].name));
  const dpuEntries    = Object.entries(dpuCounts).sort((a, b) => a[1].name.localeCompare(b[1].name));

  const unitTotal   = unitEntries.reduce((s, [, v]) => s + v.count, 0);
  const regionTotal = regionEntries.reduce((s, [, v]) => s + v.count, 0);
  const dpuTotal    = dpuEntries.reduce((s, [, v]) => s + v.count, 0);

  const emptyMsg = (label) => (
    <p className="text-slate-400 text-sm col-span-3 py-4 text-center">No {label} with equipment found.</p>
  );

  return (
    <Layout>
      <div className="p-6 max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-800">Reports</h1>
          <p className="text-slate-500 text-sm mt-0.5">
            Get a report on any equipment type from any Unit, Region or DPU
          </p>
        </div>

        {loading ? (
          <div className="grid place-items-center py-24">
            <div className="w-10 h-10 border-4 border-[#003366] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : error ? (
          <div className="p-6 text-center text-red-500">{error}</div>
        ) : (
          <>
            {/* EQUIPMENT */}
            <Section title="Equipment" subtitle="Total IT Equipment" accent="#003366"
              totalValue={totals.equipment}
              totalLabel={`Active deployments: ${totals.deployments ?? '…'}`}
              onExcel={() => reportsApi.excelAll()} onPdf={() => reportsApi.pdfAll()}>
              {EQUIPMENT_TYPES.map(def => (
                <ReportCard key={def.key} label={def.label} color={def.color}
                  count={eqCounts[def.key] ?? 0} total={eqTotal}
                  onExcel={() => reportsApi.excelByType(def.key)}
                  onPdf={()   => reportsApi.pdfByType(def.key)} />
              ))}
            </Section>

            {/* STOCK */}
            <Section title="Stock" subtitle="Devices Currently in Stock" accent="#003366"
              totalValue={totals.stock}
              totalLabel="Devices held in stock across all types"
              onExcel={() => reportsApi.stockExcelAll()} onPdf={() => reportsApi.stockPdfAll()}>
              {EQUIPMENT_TYPES.map(def => (
                <ReportCard key={def.key} label={def.label} color={def.color}
                  count={stockCounts[def.key] ?? 0} total={stockTotal}
                  onExcel={() => reportsApi.stockExcelByType(def.key)}
                  onPdf={()   => reportsApi.stockPdfByType(def.key)} />
              ))}
            </Section>

            {/* UNITS */}
            <Section title="Unit" subtitle="Equipment by Organisational Unit" accent={UNIT_COLOR}
              totalValue={unitTotal}
              totalLabel={`Across ${unitEntries.length} unit${unitEntries.length !== 1 ? 's' : ''} `}
              onExcel={() => reportsApi.unitExcelAll()} onPdf={() => reportsApi.unitPdfAll()}
              gridLabel="Per Organisational Unit">
              {unitEntries.length === 0 ? emptyMsg('units') : unitEntries.map(([id, { name, count }]) => (
                <ReportCard key={id} label={name} color={UNIT_COLOR}
                  count={count} total={unitTotal}
                  onExcel={() => reportsApi.unitExcelById(id, name)}
                  onPdf={()   => reportsApi.unitPdfById(id, name)} />
              ))}
            </Section>

            {/* REGIONS */}
            <Section title="Region" subtitle="Organised by Region" accent={REGION_COLOR}
              totalValue={regionTotal}
              totalLabel={`Across ${regionEntries.length} region${regionEntries.length !== 1 ? 's' : ''} `}
              onExcel={() => reportsApi.regionExcelAll()} onPdf={() => reportsApi.regionPdfAll()}
              gridLabel="Per Organisational Region">
              {regionEntries.length === 0 ? emptyMsg('regions') : regionEntries.map(([id, { name, count }]) => (
                <ReportCard key={id} label={name} color={REGION_COLOR}
                  count={count} total={regionTotal}
                  onExcel={() => reportsApi.regionExcelById(id, name)}
                  onPdf={()   => reportsApi.regionPdfById(id, name)} />
              ))}
            </Section>

            {/* DPUs */}
            <Section title="DPU" subtitle="Equipment in DPU HQRs and Stations" accent={DPU_COLOR}
              totalValue={dpuTotal}
              totalLabel={`Across ${dpuEntries.length} DPU${dpuEntries.length !== 1 ? 's' : ''} `}
              onExcel={() => reportsApi.dpuExcelAll()} onPdf={() => reportsApi.dpuPdfAll()}
              gridLabel="Per DPU">
              {dpuEntries.length === 0 ? emptyMsg('DPUs') : dpuEntries.map(([id, { name, count }]) => (
                <ReportCard key={id} label={name} color={DPU_COLOR}
                  count={count} total={dpuTotal}
                  onExcel={() => reportsApi.dpuExcelById(id, name)}
                  onPdf={()   => reportsApi.dpuPdfById(id, name)} />
              ))}
            </Section>
          </>
        )}
      </div>
    </Layout>
  );
}