import { useState, useEffect } from "react";
import { Routes, Route, Navigate, useNavigate } from "react-router-dom";
import { LogOut, Shield } from "lucide-react";

import CompanyCard    from "./components/CompanyCard";
import SearchBar      from "./components/SearchBar";
import ProtectedRoute from "./components/ProtectedRoute";
import Login          from "./pages/Login";
import Register       from "./pages/Register";
import AdminDashboard from "./pages/AdminDashboard";
import { useAuth }    from "./context/AuthContext";
import { apiFetch }   from "./api/client";

const DEFAULT_TICKERS = [
  { ticker: "AAPL",  company: "Apple Inc."            },
  { ticker: "MSFT",  company: "Microsoft Corporation" },
  { ticker: "NVDA",  company: "NVIDIA Corporation"    },
  { ticker: "META",  company: "Meta Platforms"        },
  { ticker: "GOOGL", company: "Alphabet Inc."         },
];

function Dashboard() {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const [watchlist, setWatchlist] = useState(DEFAULT_TICKERS);
  const [data,    setData]    = useState({});
  const [loading, setLoading] = useState({});
  const [error,   setError]   = useState({});

  useEffect(() => {
    watchlist.forEach(({ ticker, company }) => fetchTicker(ticker, company));
  }, []);

  async function fetchTicker(ticker, company = "", refresh = false) {
    setLoading(prev => ({ ...prev, [ticker]: true }));
    setError(prev   => ({ ...prev, [ticker]: null }));

    const endpoint = refresh
      ? `/api/intelligence/${ticker}/refresh`
      : `/api/intelligence/${ticker}?company=${encodeURIComponent(company)}`;

    try {
      const resp = await apiFetch(endpoint);
      if (!resp.ok) throw new Error(`API error ${resp.status}`);
      const obj = await resp.json();
      setData(prev => ({ ...prev, [ticker]: obj }));
    } catch (e) {
      setError(prev => ({ ...prev, [ticker]: e.message }));
    } finally {
      setLoading(prev => ({ ...prev, [ticker]: false }));
    }
  }

  function addTicker(ticker, company) {
    const t = ticker.toUpperCase().trim();
    if (!t || watchlist.find(w => w.ticker === t)) return;
    setWatchlist(prev => [...prev, { ticker: t, company }]);
    fetchTicker(t, company);
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">MarketPulse AI</h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Pre-earnings intelligence · powered by Bright Data + Claude
          </p>
        </div>
        <div className="flex items-center gap-3">
          {isAdmin && (
            <button
              onClick={() => navigate("/admin")}
              className="flex items-center gap-1.5 text-xs text-purple-400 hover:text-purple-300 px-3 py-1.5 rounded-lg hover:bg-gray-800 transition-colors"
            >
              <Shield size={13} /> Admin
            </button>
          )}
          <span className="text-xs text-gray-500 hidden sm:block">{user?.name || user?.email}</span>
          <button
            onClick={() => { logout(); navigate("/login"); }}
            className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-red-400 px-3 py-1.5 rounded-lg hover:bg-gray-800 transition-colors"
          >
            <LogOut size={13} /> Sign out
          </button>
          <span className="text-xs bg-blue-900 text-blue-300 px-3 py-1 rounded-full font-medium hidden md:block">
            Track 2 · Finance & Market Intelligence
          </span>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        <SearchBar onAdd={addTicker} />
        <div className="mt-8 grid grid-cols-1 gap-6">
          {watchlist.map(({ ticker, company }) => (
            <CompanyCard
              key={ticker}
              ticker={ticker}
              company={company}
              data={data[ticker]}
              loading={loading[ticker]}
              error={error[ticker]}
              onRefresh={() => fetchTicker(ticker, company, true)}
            />
          ))}
        </div>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login"    element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/" element={
        <ProtectedRoute><Dashboard /></ProtectedRoute>
      } />
      <Route path="/admin" element={
        <ProtectedRoute adminOnly><AdminDashboard /></ProtectedRoute>
      } />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
