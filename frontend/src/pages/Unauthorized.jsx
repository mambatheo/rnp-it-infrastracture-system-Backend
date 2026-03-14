import { useNavigate } from 'react-router-dom';

export default function Unauthorized() {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100">
      <div className="bg-white rounded-2xl shadow-xl p-10 text-center max-w-sm w-full">
        <p className="text-5xl mb-4">🚫</p>
        <h1 className="text-xl font-bold text-slate-800 mb-2">Access Denied</h1>
        <p className="text-slate-500 text-sm mb-6">You don't have permission to view this page.</p>
        <button
          onClick={() => navigate('/dashboard')}
          className="bg-[#003580] text-white px-6 py-2.5 rounded-xl text-sm font-medium hover:bg-[#002060] transition-colors"
        >
          Back to Dashboard
        </button>
      </div>
    </div>
  );
}
