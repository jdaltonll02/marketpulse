import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Shield, Users, BarChart2, Activity, Trash2, ChevronRight } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { apiFetch } from "../api/client";

function StatCard({ icon: Icon, label, value, sub }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <div className="flex items-center gap-3 mb-2">
        <Icon size={18} className="text-blue-400" />
        <span className="text-xs text-gray-400 uppercase tracking-wide">{label}</span>
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  );
}

function RoleBadge({ role }) {
  return role === "admin"
    ? <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-purple-900/50 text-purple-300 border border-purple-700">Admin</span>
    : <span className="text-xs px-2 py-0.5 rounded-full bg-gray-800 text-gray-400 border border-gray-700">User</span>;
}

export default function AdminDashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [users,   setUsers]   = useState([]);
  const [health,  setHealth]  = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiFetch("/api/admin/users").then(r => r.json()),
      apiFetch("/api/health").then(r => r.json()),
    ]).then(([u, h]) => {
      setUsers(u);
      setHealth(h);
    }).finally(() => setLoading(false));
  }, []);

  async function toggleRole(uid, currentRole) {
    const newRole = currentRole === "admin" ? "user" : "admin";
    await apiFetch(`/api/admin/users/${uid}/role`, {
      method: "PATCH",
      body: JSON.stringify({ role: newRole }),
    });
    setUsers(prev => prev.map(u => u.id === uid ? { ...u, role: newRole } : u));
  }

  async function deleteUser(uid, email) {
    if (!confirm(`Delete ${email}?`)) return;
    await apiFetch(`/api/admin/users/${uid}`, { method: "DELETE" });
    setUsers(prev => prev.filter(u => u.id !== uid));
  }

  function fmt(iso) {
    if (!iso) return "Never";
    return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield size={20} className="text-purple-400" />
          <div>
            <h1 className="text-xl font-bold text-white">Admin Dashboard</h1>
            <p className="text-xs text-gray-400">MarketPulse AI · Superadmin</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white px-3 py-1.5 rounded-lg hover:bg-gray-800 transition-colors"
          >
            Dashboard <ChevronRight size={12} />
          </button>
          <span className="text-xs text-gray-500">{user?.email}</span>
          <button
            onClick={() => { logout(); navigate("/login"); }}
            className="text-xs text-gray-400 hover:text-red-400 px-3 py-1.5 rounded-lg hover:bg-gray-800 transition-colors"
          >
            Sign out
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {loading ? (
          <div className="flex items-center justify-center py-20 text-gray-500">Loading…</div>
        ) : (
          <>
            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <StatCard icon={Users}    label="Total Users"    value={users.length}  sub={`${users.filter(u => u.role === "admin").length} admin(s)`} />
              <StatCard icon={BarChart2} label="Cached Tickers" value={health?.cached?.length ?? 0} sub="in-memory" />
              <StatCard icon={Activity}  label="Scheduler"      value={health?.scheduler ?? "—"} sub="auto-refresh active" />
              <StatCard icon={Shield}    label="Your Role"      value="Superadmin" sub={user?.email} />
            </div>

            {/* Users table */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
              <div className="px-5 py-4 border-b border-gray-800 flex items-center justify-between">
                <h2 className="font-semibold text-white">Registered Users</h2>
                <span className="text-xs text-gray-500">{users.length} total</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-800">
                      {["Name", "Email", "Role", "Joined", "Last Login", "Actions"].map(h => (
                        <th key={h} className="text-left px-5 py-3 text-xs text-gray-500 font-medium uppercase tracking-wide">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {users.map(u => (
                      <tr key={u.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                        <td className="px-5 py-3 text-white font-medium">{u.name || "—"}</td>
                        <td className="px-5 py-3 text-gray-300">{u.email}</td>
                        <td className="px-5 py-3"><RoleBadge role={u.role} /></td>
                        <td className="px-5 py-3 text-gray-400">{fmt(u.created_at)}</td>
                        <td className="px-5 py-3 text-gray-400">{fmt(u.last_login)}</td>
                        <td className="px-5 py-3">
                          {u.id !== user?.id && (
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => toggleRole(u.id, u.role)}
                                className="text-xs text-blue-400 hover:text-blue-300 px-2 py-1 rounded hover:bg-blue-900/30 transition-colors"
                              >
                                {u.role === "admin" ? "→ User" : "→ Admin"}
                              </button>
                              <button
                                onClick={() => deleteUser(u.id, u.email)}
                                className="text-gray-600 hover:text-red-400 p-1 rounded transition-colors"
                              >
                                <Trash2 size={13} />
                              </button>
                            </div>
                          )}
                          {u.id === user?.id && (
                            <span className="text-xs text-gray-600 italic">You</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Cached tickers */}
            {health?.cached?.length > 0 && (
              <div className="mt-6 bg-gray-900 border border-gray-800 rounded-xl p-5">
                <h2 className="font-semibold text-white mb-3">Live Cache</h2>
                <div className="flex flex-wrap gap-2">
                  {health.cached.map(t => (
                    <span key={t} className="text-xs px-3 py-1 bg-green-900/30 border border-green-800 text-green-400 rounded-full font-mono">
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
