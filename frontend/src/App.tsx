import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { AnonymizePage } from "./pages/AnonymizePage";
import { ConfigPage } from "./pages/ConfigPage";
import { StatsPage } from "./pages/StatsPage";
import { MappingsPage } from "./pages/MappingsPage";

function Navigation() {
  return (
    <nav className="bg-white border-b border-gray-200 overflow-x-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex space-x-4 sm:space-x-8 min-w-max">
          <NavLink
            to="/"
            className={({ isActive }) =>
              `inline-flex items-center px-1 pt-1 pb-3 text-sm font-medium border-b-2 transition-colors ${
                isActive
                  ? "border-primary-500 text-primary-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`
            }
          >
            Anonymize
          </NavLink>
          <NavLink
            to="/mappings"
            className={({ isActive }) =>
              `inline-flex items-center px-1 pt-1 pb-3 text-sm font-medium border-b-2 transition-colors ${
                isActive
                  ? "border-primary-500 text-primary-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`
            }
          >
            Mappings
          </NavLink>
          <NavLink
            to="/config"
            className={({ isActive }) =>
              `inline-flex items-center px-1 pt-1 pb-3 text-sm font-medium border-b-2 transition-colors ${
                isActive
                  ? "border-primary-500 text-primary-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`
            }
          >
            Settings
          </NavLink>
          <NavLink
            to="/stats"
            className={({ isActive }) =>
              `inline-flex items-center px-1 pt-1 pb-3 text-sm font-medium border-b-2 transition-colors ${
                isActive
                  ? "border-primary-500 text-primary-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`
            }
          >
            Statistics
          </NavLink>
        </div>
      </div>
    </nav>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col bg-gray-50">
        {/* Header */}
        <header className="bg-gradient-to-r from-primary-600 to-primary-700 shadow-lg">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center">
                  <svg
                    className="w-6 h-6 text-white"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                    />
                  </svg>
                </div>
                <div>
                  <h1 className="text-xl font-semibold text-white">
                    PII Anonymizer
                  </h1>
                  <p className="text-primary-200 text-sm">
                    Powered by Microsoft Presidio
                  </p>
                </div>
              </div>
              <div className="hidden sm:flex items-center space-x-2 text-primary-200 text-sm">
                <span className="w-2 h-2 bg-green-400 rounded-full"></span>
                <span>v1.0.0</span>
              </div>
            </div>
          </div>
        </header>

        {/* Navigation */}
        <Navigation />

        {/* Main Content */}
        <main className="flex-1">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <Routes>
              <Route path="/" element={<AnonymizePage />} />
              <Route path="/mappings" element={<MappingsPage />} />
              <Route path="/config" element={<ConfigPage />} />
              <Route path="/stats" element={<StatsPage />} />
            </Routes>
          </div>
        </main>

        {/* Footer */}
        <footer className="bg-white border-t border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <p className="text-center text-sm text-gray-500">
              PII Anonymizer - Consistent substitution for privacy protection
            </p>
          </div>
        </footer>
      </div>
    </BrowserRouter>
  );
}

export default App;
