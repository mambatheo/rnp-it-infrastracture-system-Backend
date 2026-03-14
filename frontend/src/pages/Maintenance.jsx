import Layout from '../components/Layout';

export default function Maintenance() {
  return (
    <Layout>
      <div className="p-6 max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold text-slate-800 mb-2">Maintenance</h1>
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 text-center mt-8">
          <p className="text-5xl mb-4">🔧</p>
          <p className="text-slate-700 font-semibold text-lg">Maintenance Module</p>
          <p className="text-slate-400 text-sm mt-2 max-w-sm mx-auto">
            The maintenance and repair request module is not yet enabled in this environment.
            Contact your system administrator to activate it.
          </p>
        </div>
      </div>
    </Layout>
  );
}
