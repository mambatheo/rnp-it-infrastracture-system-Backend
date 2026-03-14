import { useState } from "react";

// ─── API ─────────────────────────────────────────────
const API_BASE = "http://localhost:8000/api/v1/accounts/auth";

// ─── Token Helper ────────────────────────────────────
const storeSession = (data) => {
  localStorage.setItem("access_token", data.access);
  localStorage.setItem("refresh_token", data.refresh);
  localStorage.setItem("user", JSON.stringify(data.user));
  localStorage.setItem("role", data.user?.role || '');
};

// ─── Simple Icons ─────────────────────────────────────
const EyeIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
      d="M2.458 12C3.732 7.943 7.523 5 12 5
      c4.478 0 8.268 2.943 9.542 7
      -1.274 4.057-5.064 7-9.542 7
      -4.477 0-8.268-2.943-9.542-7z"/>
  </svg>
);

const EyeOffIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
      d="M13.875 18.825A10.05 10.05 0 0112 19
      c-4.478 0-8.268-2.943-9.543-7
      a9.97 9.97 0 011.563-3.029
      m5.858.908a3 3 0 114.243 4.243
      M9.878 9.878l4.242 4.242"/>
  </svg>
);

const Spinner = () => (
  <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24">
    <circle className="opacity-25" cx="12" cy="12" r="10"
      stroke="currentColor" strokeWidth="4" fill="none"/>
    <path className="opacity-75" fill="currentColor"
      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
  </svg>
);

// ─── Input Component ─────────────────────────────────
const Input = ({
  label,
  type = "text",
  name,
  value,
  onChange,
  error,
  rightElement
}) => (
  <div>
    <label className="block text-xs font-semibold mb-2 text-slate-500">
      {label}
    </label>
    <div className="relative">
      <input
        type={type}
        name={name}
        value={value}
        onChange={onChange}
        className={`w-full px-4 py-3 border rounded-xl text-sm
          ${error ? "border-red-400 bg-red-50" : "border-slate-200"}
          focus:ring-2 focus:ring-[#003580]/30 focus:outline-none`}
      />
      {rightElement && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2">
          {rightElement}
        </div>
      )}
    </div>
    {error && (
      <p className="text-xs text-red-500 mt-1">{error}</p>
    )}
  </div>
);

// ─── Main Component ──────────────────────────────────
export default function AuthPage() {
  const [form, setForm] = useState({ email: "", password: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});

  const handleChange = (e) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const validate = () => {
    const errors = {};
    if (!form.email) errors.email = "Email required";
    if (!form.password) errors.password = "Password required";
    return errors;
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    const errors = validate();
    if (Object.keys(errors).length) {
      setFieldErrors(errors);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/login/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });

      const data = await res.json();

      if (res.ok) {
        storeSession(data);
        window.location.href = "/dashboard";
      } else {
        setError(data.error || data.detail || "Invalid credentials");
      }
    } catch {
      setError("Network error. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="min-h-screen flex">

        {/* Left Panel */}
        <div className="hidden lg:flex w-5/12 bg-[#001f3f] text-white
                        items-center justify-center p-12">
          <div>
            <h1 className="text-4xl font-bold mb-4">
              IT Infrastructure
            </h1>
            <p className="text-white/70">
              Rwanda National Police
            </p>
          </div>
        </div>

        {/* Right Panel */}
        <div className="flex-1 flex items-center justify-center bg-slate-100 p-6">
          <div className="w-full max-w-md bg-white p-8 rounded-2xl shadow-xl">

            <h2 className="text-2xl font-bold mb-6 text-slate-800">
              Welcome Back
            </h2>

            {error && (
              <div className="mb-4 text-red-600 text-sm">
                {error}
              </div>
            )}

            <form onSubmit={handleLogin} className="space-y-5">

              <Input
                label="Email"
                type="email"
                name="email"
                value={form.email}
                onChange={handleChange}
                error={fieldErrors.email}
              />

              <Input
                label="Password"
                type={showPassword ? "text" : "password"}
                name="password"
                value={form.password}
                onChange={handleChange}
                error={fieldErrors.password}
                rightElement={
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                  </button>
                }
              />

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-[#003580] text-white py-3 rounded-xl
                           flex items-center justify-center gap-2
                           disabled:opacity-50"
              >
                {loading ? <Spinner /> : "Sign In"}
              </button>

            </form>
          </div>
        </div>
      </div>
    </>
  );
}