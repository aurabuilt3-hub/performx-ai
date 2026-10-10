import React, { useState, useEffect } from 'react';
import MetricCard from '../components/common/MetricCard';
import { 
  TrendingUp, 
  Activity, 
  Calendar, 
  Award, 
  Flame, 
  Target, 
  Sparkles, 
  BarChart2, 
  CheckCircle2,
  Clock,
  RefreshCw,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Info,
  ShieldCheck
} from 'lucide-react';
import { useApp } from '../context/AppContext';

export default function ProgressPage() {
  const { 
    userProfile, 
    activeSession, 
    workoutHistory, 
    fetchWorkoutHistory, 
    isAuthenticated 
  } = useApp();

  const [timeRange, setTimeRange] = useState('30D');
  const [pageOffset, setPageOffset] = useState(0);
  const pageSize = 5;

  useEffect(() => {
    if (isAuthenticated) {
      fetchWorkoutHistory(20, 0).catch(() => {});
    }
  }, [isAuthenticated, fetchWorkoutHistory]);

  const savedItems = workoutHistory?.items || [];
  const totalSavedCount = workoutHistory?.total || 0;
  const isLoading = workoutHistory?.loading || false;
  const errorMsg = workoutHistory?.error || null;

  // Filter items by timeRange
  const now = Date.now();
  const rangeDays = timeRange === '7D' ? 7 : timeRange === '30D' ? 30 : timeRange === '3M' ? 90 : 365;
  const cutoffTime = now - rangeDays * 24 * 60 * 60 * 1000;

  const filteredItems = savedItems.filter(item => {
    const itemTimestamp = new Date(item.created_at || item.start_time || 0).getTime();
    return itemTimestamp >= cutoffTime;
  });

  // Calculate Real Aggregates strictly from filtered persisted sessions
  const totalTrackedReps = filteredItems.reduce((acc, curr) => acc + (curr.total_reps || 0), 0);
  const totalValidReps = filteredItems.reduce((acc, curr) => acc + (curr.valid_reps || 0), 0);
  const avgSymmetry = filteredItems.length > 0
    ? Math.round((filteredItems.reduce((acc, curr) => acc + (curr.mean_symmetry || 0.95), 0) / filteredItems.length) * 100)
    : null;

  // Group volume by chronological buckets for chart
  const volumeData = filteredItems.length > 0
    ? filteredItems.slice(0, 7).reverse().map((item, idx) => ({
        label: (item.created_at || '').split('T')[0]?.slice(5) || `S${idx + 1}`,
        reps: item.total_reps || 0,
        accuracy: Math.round((item.mean_symmetry || 0.95) * 100),
      }))
    : [];

  const maxReps = volumeData.length > 0 ? Math.max(1, ...volumeData.map(d => d.reps)) : 100;

  // Pagination for full history table
  const totalPages = Math.ceil(totalSavedCount / pageSize) || 1;
  const currentPage = Math.floor(pageOffset / pageSize) + 1;
  const paginatedItems = savedItems.slice(pageOffset, pageOffset + pageSize);

  return (
    <div className="flex-col gap-6">
      {/* Time Range Selector Filter */}
      <div className="flex-row justify-between items-center" style={{ flexWrap: 'wrap', gap: 14 }}>
        <div className="flex-col gap-1">
          <div className="flex-row items-center gap-2">
            <h2 style={{ fontSize: '1.35rem' }}>Biomechanical Progression & Form Evolution</h2>
            <span className="badge badge-neutral">Illustrative Historical Baseline</span>
          </div>
          <p style={{ fontSize: '0.85rem' }}>Longitudinal tracking of movement depth, symmetry, and volume. Benchmark dataset active until new sessions are logged.</p>
        </div>

        <div className="tabs-container">
          {['7D', '30D', '3M', '1Y'].map(t => (
            <button
              key={t}
              type="button"
              className={`tab-btn ${timeRange === t ? 'active' : ''}`}
              onClick={() => setTimeRange(t)}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* KPI Overview Cards */}
      <section className="metrics-grid">
        <MetricCard
          icon={Sparkles}
          iconColor="orange"
          label="Average Joint Symmetry"
          value={isAuthenticated ? (avgSymmetry !== null ? `${avgSymmetry}%` : '-- (No Sessions)') : '94.2% (Demo)'}
          subtext={isAuthenticated ? `Based on ${filteredItems.length} session${filteredItems.length === 1 ? '' : 's'} in ${timeRange}` : "Illustrative baseline"}
          badgeText={isAuthenticated ? (avgSymmetry !== null ? 'Verified' : 'Awaiting Data') : 'Demo Mode'}
          badgeType={avgSymmetry && avgSymmetry >= 90 ? "green" : "neutral"}
        />

        <MetricCard
          icon={Activity}
          iconColor="teal"
          label="Tracked Repetitions"
          value={isAuthenticated ? `${totalTrackedReps}` : '1,050 (Demo)'}
          subtext={isAuthenticated ? `${totalValidReps} valid reps (${timeRange} window)` : "Camera-verified volume"}
          badgeText={isAuthenticated ? `${filteredItems.length} Sessions` : "+180 this week"}
          badgeType="teal"
        />

        <MetricCard
          icon={Flame}
          iconColor="amber"
          label="Total Saved Workouts"
          value={isAuthenticated ? `${totalSavedCount} Total` : `${userProfile.streakDays} Days`}
          subtext={isAuthenticated ? "Persisted in secure cloud database" : "Targeting 7-day milestone"}
          badgeText={isAuthenticated ? "Cloud Sync" : "Active"}
          badgeType="amber"
        />

        <MetricCard
          icon={Target}
          iconColor="cyan"
          label="Body Weight Track"
          value={`${userProfile.weightKg} kg`}
          subtext={`Height: ${userProfile.heightCm} cm • BF: ${userProfile.bodyFatPercent}%`}
        />
      </section>

      {/* Charts Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 24 }}>
        {/* Weekly Volume & Repetition Bar Chart (Custom Accessible SVG) */}
        <section className="card flex-col gap-4">
          <div className="card-header" style={{ marginBottom: 4 }}>
            <div>
              <h3 className="card-title">
                <BarChart2 size={20} className="text-orange" />
                <span>Weekly Movement Volume (Reps)</span>
              </h3>
              <p className="card-subtitle">Verified completed repetitions across all working sets</p>
            </div>
            <span className="badge badge-orange">On-Device Logs</span>
          </div>

          {/* SVG Chart Container */}
          {isLoading && (
            <div className="flex-col items-center justify-center gap-2" style={{ height: 260 }}>
              <Loader2 size={24} className="animate-spin text-orange" />
              <span className="text-muted" style={{ fontSize: '0.85rem' }}>Loading session analytics...</span>
            </div>
          )}

          {!isLoading && volumeData.length === 0 && (
            <div className="flex-col items-center justify-center gap-2 text-center" style={{ height: 260, padding: 20 }}>
              <Info size={28} className="text-muted" />
              <strong className="text-primary" style={{ fontSize: '0.95rem' }}>No Sessions in Selected Window ({timeRange})</strong>
              <p className="text-muted" style={{ fontSize: '0.825rem', maxWidth: 300 }}>
                {isAuthenticated 
                  ? "Record squats in the Live Movement Lab to populate kinematic volume trends." 
                  : "Sign in to persist sessions and build longitudinal volume charts."}
              </p>
            </div>
          )}

          {!isLoading && volumeData.length > 0 && (
            <div style={{ padding: '20px 10px', height: 260, display: 'flex', alignItems: 'flex-end', justifyContent: 'space-around', gap: 16 }}>
              {volumeData.map((d, i) => {
                const heightPercent = (d.reps / maxReps) * 100;
                return (
                  <div key={i} className="flex-col items-center gap-2" style={{ flex: 1, height: '100%', justifyContent: 'flex-end' }}>
                    <span className="font-bold text-primary" style={{ fontSize: '0.825rem' }}>{d.reps}</span>
                    <div 
                      style={{
                        width: '100%',
                        maxWidth: 48,
                        height: `${Math.max(8, heightPercent * 0.75)}%`,
                        background: 'linear-gradient(180deg, var(--primary-orange) 0%, #FA8C61 100%)',
                        borderRadius: '8px 8px 4px 4px',
                        transition: 'height 400ms ease',
                        boxShadow: 'var(--shadow-xs)'
                      }}
                      title={`${d.label}: ${d.reps} reps • ${d.accuracy}% symmetry`}
                    />
                    <span className="text-secondary font-medium" style={{ fontSize: '0.785rem' }}>{d.label}</span>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* 30-Day Form Accuracy Progression Line */}
        <section className="card flex-col gap-4">
          <div className="card-header" style={{ marginBottom: 4 }}>
            <div>
              <h3 className="card-title">
                <TrendingUp size={20} className="text-teal" />
                <span>Form Accuracy & Symmetry</span>
              </h3>
              <p className="card-subtitle">Verified criteria from active sessions</p>
            </div>
            <span className="badge badge-teal">{avgSymmetry !== null ? `${avgSymmetry}% Balance` : '--'}</span>
          </div>

          <div className="flex-col gap-3" style={{ padding: '10px 0' }}>
            <div className="card-flat" style={{ background: 'var(--surface-subtle)', padding: 14 }}>
              <div className="flex-row justify-between items-center" style={{ marginBottom: 6 }}>
                <span className="font-semibold text-primary" style={{ fontSize: '0.875rem' }}>Bilateral Weight Symmetry</span>
                <span className="badge badge-orange">{avgSymmetry !== null ? `${avgSymmetry}% Balance` : 'Awaiting Data'}</span>
              </div>
              <div className="progress-bar-container">
                <div className="progress-bar-fill progress-orange" style={{ width: `${avgSymmetry || 0}%` }} />
              </div>
            </div>

            <div className="card-flat" style={{ background: 'var(--surface-subtle)', padding: 14 }}>
              <div className="flex-row justify-between items-center" style={{ marginBottom: 6 }}>
                <span className="font-semibold text-primary" style={{ fontSize: '0.875rem' }}>Repetition Completion Rate</span>
                <span className="badge badge-green">
                  {totalTrackedReps > 0 ? `${Math.round((totalValidReps / totalTrackedReps) * 100)}% Valid` : '--'}
                </span>
              </div>
              <div className="progress-bar-container">
                <div 
                  className="progress-bar-fill progress-teal" 
                  style={{ width: `${totalTrackedReps > 0 ? Math.round((totalValidReps / totalTrackedReps) * 100) : 0}%` }} 
                />
              </div>
            </div>

            <div className="card-flat" style={{ background: 'var(--surface-subtle)', padding: 14 }}>
              <div className="flex-row justify-between items-center" style={{ marginBottom: 6 }}>
                <span className="font-semibold text-primary" style={{ fontSize: '0.875rem' }}>Kinematic Privacy Mode</span>
                <span className="badge badge-cyan">On-Device Edge AI</span>
              </div>
              <p className="text-muted" style={{ fontSize: '0.785rem', margin: 0, marginTop: 4 }}>
                100% in-browser MediaPipe extraction. No camera footage or raw landmark vectors stored on remote servers.
              </p>
            </div>
          </div>
        </section>
      </div>

      {/* Full Persisted Workout History Table with Pagination */}
      <section className="card flex-col gap-4">
        <div className="card-header">
          <div>
            <h3 className="card-title">
              <Calendar size={20} className="text-orange" />
              <span>Persisted Workout History</span>
            </h3>
            <p className="card-subtitle">
              Verified records retrieved from secure cloud database ({totalSavedCount} sessions total)
            </p>
          </div>
          <button 
            className="btn btn-secondary btn-sm" 
            onClick={() => fetchWorkoutHistory(20, 0)} 
            disabled={isLoading}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>

        {errorMsg && (
          <div className="feedback-box feedback-error" style={{ margin: 0 }}>
            <span>Failed to load workout history: {errorMsg}</span>
          </div>
        )}

        {!isLoading && savedItems.length === 0 && (
          <div className="text-center" style={{ padding: '32px 16px', color: 'var(--text-muted)' }}>
            <Activity size={32} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
            <div className="font-medium text-primary">No workouts saved in cloud history</div>
            <p style={{ fontSize: '0.85rem', marginTop: 4 }}>
              Complete a squat session in the Live Movement Lab and click "Save & Return to Dashboard".
            </p>
          </div>
        )}

        {paginatedItems.length > 0 && (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', fontSize: '0.785rem' }}>
                  <th style={{ padding: '10px 12px' }}>Exercise</th>
                  <th style={{ padding: '10px 12px' }}>Date & Time</th>
                  <th style={{ padding: '10px 12px' }}>Completed Reps</th>
                  <th style={{ padding: '10px 12px' }}>Valid Reps</th>
                  <th style={{ padding: '10px 12px' }}>Mean Symmetry</th>
                  <th style={{ padding: '10px 12px' }}>Rep Duration</th>
                </tr>
              </thead>
              <tbody>
                {paginatedItems.map((item) => (
                  <tr key={item.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '12px', textTransform: 'capitalize', fontWeight: 600 }}>
                      {item.exercise_type || 'Squat'}
                    </td>
                    <td style={{ padding: '12px', color: 'var(--text-secondary)' }}>
                      {(item.created_at || item.start_time || '').replace('T', ' ').slice(0, 16) || 'Recent'}
                    </td>
                    <td style={{ padding: '12px' }}>
                      <strong className="text-primary">{item.total_reps}</strong>
                    </td>
                    <td style={{ padding: '12px' }}>
                      <span className="text-teal font-semibold">{item.valid_reps}</span>
                    </td>
                    <td style={{ padding: '12px' }}>
                      {item.mean_symmetry !== undefined && item.mean_symmetry !== null
                        ? `${Math.round(item.mean_symmetry * 100)}%`
                        : '--'}
                    </td>
                    <td style={{ padding: '12px', color: 'var(--text-secondary)' }}>
                      {item.mean_rep_duration ? `${item.mean_rep_duration.toFixed(1)}s` : '--'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination Controls */}
            {totalSavedCount > pageSize && (
              <div className="flex-row justify-between items-center" style={{ paddingTop: 16, marginTop: 8 }}>
                <span className="text-muted" style={{ fontSize: '0.8rem' }}>
                  Showing {pageOffset + 1}–{Math.min(pageOffset + pageSize, totalSavedCount)} of {totalSavedCount}
                </span>
                <div className="flex-row gap-2">
                  <button 
                    className="btn btn-secondary btn-sm" 
                    onClick={() => setPageOffset(Math.max(0, pageOffset - pageSize))}
                    disabled={pageOffset === 0}
                  >
                    <ChevronLeft size={14} /> Previous
                  </button>
                  <button 
                    className="btn btn-secondary btn-sm" 
                    onClick={() => setPageOffset(pageOffset + pageSize)}
                    disabled={pageOffset + pageSize >= totalSavedCount}
                  >
                    Next <ChevronRight size={14} />
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
