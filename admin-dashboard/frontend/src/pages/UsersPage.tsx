import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { usersAPI } from '../api/client';

const UsersPage: React.FC = () => {
  const [search, setSearch] = useState('');
  const [tierFilter, setTierFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const [selectedUser, setSelectedUser] = useState<any>(null);
  const queryClient = useQueryClient();

  const limit = 50;

  const { data: usersData, isLoading } = useQuery({
    queryKey: ['users', page, tierFilter, statusFilter, search],
    queryFn: async () => {
      const response = await usersAPI.list({
        skip: (page - 1) * limit,
        limit,
        tier: tierFilter || undefined,
        status: statusFilter || undefined,
        search: search || undefined,
      });
      return response.data;
    },
  });

  const banMutation = useMutation({
    mutationFn: ({ userId, reason }: { userId: number; reason: string }) =>
      usersAPI.ban(userId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setSelectedUser(null);
      alert('User banned successfully');
    },
  });

  const unbanMutation = useMutation({
    mutationFn: (userId: number) => usersAPI.unban(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setSelectedUser(null);
      alert('User unbanned successfully');
    },
  });

  const handleBan = () => {
    const reason = prompt('Enter ban reason:');
    if (reason && selectedUser) {
      banMutation.mutate({ userId: selectedUser.user_id, reason });
    }
  };

  const handleUnban = () => {
    if (selectedUser && confirm('Are you sure you want to unban this user?')) {
      unbanMutation.mutate(selectedUser.user_id);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-neon-pink via-neon-cyan to-neon-purple text-neon-glow">
          USER MANAGEMENT
        </h1>
        <p className="text-gray-400 mt-2 font-mono">Manage bot users and subscriptions</p>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <input
            type="text"
            placeholder="Search by username or name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input-cyber"
          />
          
          <select
            value={tierFilter}
            onChange={(e) => setTierFilter(e.target.value)}
            className="input-cyber"
          >
            <option value="">All Tiers</option>
            <option value="free">Free</option>
            <option value="basic">Basic</option>
            <option value="premium">Premium</option>
            <option value="enterprise">Enterprise</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="input-cyber"
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="expired">Expired</option>
            <option value="suspended">Suspended</option>
            <option value="banned">Banned</option>
          </select>

          <button
            onClick={() => {
              setSearch('');
              setTierFilter('');
              setStatusFilter('');
              setPage(1);
            }}
            className="btn-neon-pink"
          >
            Clear Filters
          </button>
        </div>
      </div>

      {/* Users Table */}
      <div className="card overflow-x-auto">
        {isLoading ? (
          <div className="text-center py-8 text-neon-cyan animate-pulse">Loading users...</div>
        ) : (
          <>
            <table className="table-cyber">
              <thead>
                <tr>
                  <th>User ID</th>
                  <th>Username</th>
                  <th>Name</th>
                  <th>Tier</th>
                  <th>Status</th>
                  <th>Downloads</th>
                  <th>Last Active</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {usersData?.users?.map((user: any) => (
                  <tr key={user.user_id} onClick={() => setSelectedUser(user)}>
                    <td className="font-mono text-neon-cyan">{user.user_id}</td>
                    <td>@{user.username || 'N/A'}</td>
                    <td>{user.first_name} {user.last_name || ''}</td>
                    <td>
                      <span className={`px-2 py-1 rounded text-xs font-bold ${
                        user.subscription_tier === 'premium' ? 'bg-neon-pink text-dark-900' :
                        user.subscription_tier === 'basic' ? 'bg-neon-cyan text-dark-900' :
                        'bg-dark-600 text-gray-400'
                      }`}>
                        {user.subscription_tier.toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <span className={`px-2 py-1 rounded text-xs font-bold ${
                        user.subscription_status === 'active' ? 'bg-green-500 text-dark-900' :
                        user.subscription_status === 'banned' ? 'bg-red-500 text-white' :
                        'bg-yellow-500 text-dark-900'
                      }`}>
                        {user.subscription_status.toUpperCase()}
                      </span>
                    </td>
                    <td className="font-mono">{user.downloads_count}</td>
                    <td className="text-sm text-gray-400 font-mono">
                      {user.last_active ? new Date(user.last_active).toLocaleDateString() : 'Never'}
                    </td>
                    <td>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedUser(user);
                        }}
                        className="text-neon-cyan hover:text-neon-pink transition-colors"
                      >
                        View →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            <div className="flex justify-between items-center mt-6">
              <div className="text-gray-400 font-mono text-sm">
                Showing {usersData?.users?.length || 0} of {usersData?.total || 0} users
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="btn-neon disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  ← Previous
                </button>
                <span className="px-4 py-2 text-neon-cyan font-mono">
                  Page {page} of {usersData?.pages || 1}
                </span>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={page >= (usersData?.pages || 1)}
                  className="btn-neon disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next →
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* User Detail Modal */}
      {selectedUser && (
        <div className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50 p-4">
          <div className="card max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-6">
              <div>
                <h2 className="text-2xl font-bold text-neon-pink">User Details</h2>
                <p className="text-gray-400 font-mono text-sm mt-1">ID: {selectedUser.user_id}</p>
              </div>
              <button
                onClick={() => setSelectedUser(null)}
                className="text-gray-400 hover:text-neon-pink text-2xl"
              >
                ×
              </button>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-gray-500 uppercase">Username</label>
                  <p className="text-neon-cyan font-mono">@{selectedUser.username || 'N/A'}</p>
                </div>
                <div>
                  <label className="text-xs text-gray-500 uppercase">Name</label>
                  <p>{selectedUser.first_name} {selectedUser.last_name || ''}</p>
                </div>
                <div>
                  <label className="text-xs text-gray-500 uppercase">Tier</label>
                  <p className="text-neon-pink font-bold">{selectedUser.subscription_tier.toUpperCase()}</p>
                </div>
                <div>
                  <label className="text-xs text-gray-500 uppercase">Status</label>
                  <p className="text-neon-cyan font-bold">{selectedUser.subscription_status.toUpperCase()}</p>
                </div>
                <div>
                  <label className="text-xs text-gray-500 uppercase">Total Downloads</label>
                  <p className="font-mono text-xl">{selectedUser.downloads_count}</p>
                </div>
                <div>
                  <label className="text-xs text-gray-500 uppercase">AI Searches</label>
                  <p className="font-mono text-xl">{selectedUser.ai_searches_count}</p>
                </div>
                <div>
                  <label className="text-xs text-gray-500 uppercase">Daily Limit</label>
                  <p className="font-mono">{selectedUser.daily_download_limit}</p>
                </div>
                <div>
                  <label className="text-xs text-gray-500 uppercase">Monthly Limit</label>
                  <p className="font-mono">{selectedUser.monthly_download_limit}</p>
                </div>
              </div>

              {selectedUser.is_banned && (
                <div className="bg-red-500 bg-opacity-20 border border-red-500 rounded-lg p-4">
                  <p className="text-red-400 font-bold">⚠️ BANNED</p>
                  <p className="text-sm mt-2">Reason: {selectedUser.ban_reason}</p>
                </div>
              )}

              {selectedUser.notes && (
                <div>
                  <label className="text-xs text-gray-500 uppercase">Notes</label>
                  <p className="text-sm text-gray-400">{selectedUser.notes}</p>
                </div>
              )}

              <div className="flex gap-3 pt-4 border-t border-dark-600">
                {selectedUser.is_banned ? (
                  <button
                    onClick={handleUnban}
                    className="btn-neon flex-1"
                    disabled={unbanMutation.isPending}
                  >
                    {unbanMutation.isPending ? 'Unbanning...' : 'Unban User'}
                  </button>
                ) : (
                  <button
                    onClick={handleBan}
                    className="btn-neon-pink flex-1"
                    disabled={banMutation.isPending}
                  >
                    {banMutation.isPending ? 'Banning...' : 'Ban User'}
                  </button>
                )}
                <button
                  onClick={() => setSelectedUser(null)}
                  className="px-6 py-3 border-2 border-gray-600 rounded-lg hover:border-gray-400 transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UsersPage;
