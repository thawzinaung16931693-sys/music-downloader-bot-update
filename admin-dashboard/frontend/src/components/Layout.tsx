import React from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

const Layout: React.FC = () => {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-64 bg-dark-800 border-r-2 border-dark-600 flex flex-col">
        <div className="p-6 border-b-2 border-dark-600">
          <h1 className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-neon-pink to-neon-cyan">
            ADMIN
          </h1>
          <p className="text-xs text-gray-500 font-mono mt-1">Bar Lar Lar</p>
        </div>

        <nav className="flex-1 p-4 space-y-2">
          <NavItem to="/dashboard" icon="📊" label="Dashboard" />
          <NavItem to="/users" icon="👥" label="Users" />
          <NavItem to="/subscriptions" icon="💎" label="Subscriptions" />
          <NavItem to="/trials" icon="🎯" label="Trials" />
          <NavItem to="/analytics" icon="📈" label="Analytics" />
          <NavItem to="/settings" icon="⚙️" label="Settings" />
        </nav>

        <div className="p-4 border-t-2 border-dark-600">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-neon-pink to-neon-cyan flex items-center justify-center text-xl">
              👤
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-neon-cyan truncate">
                {user?.first_name}
              </p>
              <p className="text-xs text-gray-500 font-mono truncate">
                @{user?.username}
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full px-4 py-2 border-2 border-red-500 text-red-500 rounded-lg hover:bg-red-500 hover:text-white transition-all font-bold text-sm"
          >
            LOGOUT
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="p-8">
          <Outlet />
        </div>
      </main>

      {/* Scanline effect */}
      <div className="fixed inset-0 scanline pointer-events-none z-50"></div>
    </div>
  );
};

interface NavItemProps {
  to: string;
  icon: string;
  label: string;
}

const NavItem: React.FC<NavItemProps> = ({ to, icon, label }) => {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center space-x-3 px-4 py-3 rounded-lg transition-all ${
          isActive
            ? 'bg-dark-700 border-2 border-neon-cyan text-neon-cyan shadow-neon-cyan'
            : 'border-2 border-transparent text-gray-400 hover:text-neon-pink hover:border-neon-pink'
        }`
      }
    >
      <span className="text-xl">{icon}</span>
      <span className="font-bold">{label}</span>
    </NavLink>
  );
};

export default Layout;
