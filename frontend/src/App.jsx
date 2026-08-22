import { NavLink, Outlet } from 'react-router-dom'

const navItems = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/transactions', label: 'Transactions' },
  { to: '/investigations', label: 'Investigations' },
  { to: '/evaluation', label: 'Evaluation' },
  { to: '/audit', label: 'Audit' },
]

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-brand-900 text-white">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">RiskLens AI</h1>
            <p className="text-xs text-brand-600">Autonomous Payment Risk Investigation &amp; Decision System</p>
          </div>
          <nav className="flex gap-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `px-3 py-2 rounded-md text-sm font-medium transition ${
                    isActive ? 'bg-white text-brand-900' : 'text-brand-50 hover:bg-brand-800'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8">
        <Outlet />
      </main>
      <footer className="text-center text-xs text-brand-600 py-4">
        Synthetic data only · Prototype for Razorpay AI Buildathon 2026
      </footer>
    </div>
  )
}
