import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { dashboardAPI } from '../api/client';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { format } from 'date-fns';

const DashboardPage: React.FC = () => {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const response = await dashboardAPI.getStats();
      return response.data;
    },
  });

  const { data: activity } = useQuery({
    queryKey: ['dashboard-activity'],
    queryFn: async () => {
      const response = await dashboardAPI.getActivity(10);
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30s
  });

  const { data: userGrowth } = useQuery({
    queryKey: ['user-growth'],
    queryFn: async () => {
      const response = await dashboardAPI.getUserGrowthChart(30);
      return response.data;
    },
  });

  const { data: downloads } = useQuery({
    queryKey: ['downloads-chart'],
    queryFn: async () => {
      const response = await dashboardAPI.getDownloadsChart(30);
      return response.data;
    },
  });

  if (statsLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-neon-cyan text-2xl animate-pulse">Loading...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-neon-pink via-neon-cyan to-neon-purple text-neon-glow">
          DASHBOARD OVERVIEW
        </h1>
        <p className="text-gray-400 mt-2 font-mono">Real-time system metrics and analytics</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <StatCard
          title="Total Users"
          value={stats?.total_users || 0}
          icon="👥"
          color="pink"
        />
        <StatCard
          title="Active Users"
          value={stats?.active_users || 0}
          subtitle="Last 7 days"
          icon="⚡"
          color="cyan"
        />
        <StatCard
          title="Premium Users"
          value={stats?.premium_users || 0}
          icon="💎"
          color="purple"
        />
        <StatCard
          title="Total Downloads"
          value={stats?.total_downloads || 0}
          icon="📥"
          color="cyan"
        />
        <StatCard
          title="Revenue"
          value={`$${stats?.revenue?.toFixed(2) || '0.00'}`}
          icon="💰"
          color="pink"
        />
        <StatCard
          title="Active Trials"
          value={stats?.active_trials || 0}
          icon="🎯"
          color="purple"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-xl font-bold text-neon-cyan mb-4 flex items-center">
            <span className="mr-2">📈</span>
            User Growth
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={userGrowth?.data || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2e2e48" />
              <XAxis 
                dataKey="date" 
                stroke="#00f5ff"
                tickFormatter={(value) => format(new Date(value), 'MMM dd')}
              />
              <YAxis stroke="#00f5ff" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#1a1a2e', 
                  border: '2px solid #00f5ff',
                  borderRadius: '8px'
                }}
              />
              <Line 
                type="monotone" 
                dataKey="count" 
                stroke="#ff006e" 
                strokeWidth={3}
                dot={{ fill: '#ff006e', strokeWidth: 2, r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h3 className="text-xl font-bold text-neon-pink mb-4 flex items-center">
            <span className="mr-2">📊</span>
            Daily Downloads
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={downloads?.data || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2e2e48" />
              <XAxis 
                dataKey="date" 
                stroke="#ff006e"
                tickFormatter={(value) => format(new Date(value), 'MMM dd')}
              />
              <YAxis stroke="#ff006e" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#1a1a2e', 
                  border: '2px solid #ff006e',
                  borderRadius: '8px'
                }}
              />
              <Line 
                type="monotone" 
                dataKey="count" 
                stroke="#00f5ff" 
                strokeWidth={3}
                dot={{ fill: '#00f5ff', strokeWidth: 2, r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Activity Feed */}
      <div className="card">
        <h3 className="text-xl font-bold text-neon-purple mb-4 flex items-center">
          <span className="mr-2">🔥</span>
          Recent Activity
        </h3>
        <div className="space-y-3">
          {activity?.activities?.map((item: any, index: number) => (
            <div 
              key={index}
              className="flex items-center justify-between p-4 bg-dark-700 rounded-lg border border-dark-600 hover:border-neon-cyan transition-all"
            >
              <div className="flex items-center space-x-4">
                <div className="text-2xl">
                  {item.type === 'user_joined' && '👤'}
                  {item.type === 'subscription' && '💎'}
                  {item.type === 'high_usage' && '⚡'}
                </div>
                <div>
                  <p className="text-gray-100">{item.message}</p>
                  <p className="text-xs text-gray-500 font-mono mt-1">
                    {item.user_id && `User ID: ${item.user_id}`}
                  </p>
                </div>
              </div>
              <div className="text-sm text-gray-400 font-mono">
                {format(new Date(item.timestamp), 'HH:mm:ss')}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: string;
  color: 'pink' | 'cyan' | 'purple';
}

const StatCard: React.FC<StatCardProps> = ({ title, value, subtitle, icon, color }) => {
  const colorClasses = {
    pink: 'border-neon-pink hover:shadow-neon-pink',
    cyan: 'border-neon-cyan hover:shadow-neon-cyan',
    purple: 'border-neon-purple hover:shadow-neon-purple',
  };

  const textColorClasses = {
    pink: 'text-neon-pink',
    cyan: 'text-neon-cyan',
    purple: 'text-neon-purple',
  };

  return (
    <div className={`stat-card ${colorClasses[color]}`}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider">{title}</h3>
        <span className="text-3xl">{icon}</span>
      </div>
      <div className={`text-4xl font-black ${textColorClasses[color]} text-neon-glow`}>
        {value}
      </div>
      {subtitle && (
        <p className="text-xs text-gray-500 mt-2 font-mono">{subtitle}</p>
      )}
    </div>
  );
};

export default DashboardPage;
