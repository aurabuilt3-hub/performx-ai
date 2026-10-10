import React from 'react';

export default function MetricCard({ 
  icon: Icon, 
  iconColor = 'orange', 
  label, 
  value, 
  subtext, 
  badgeText, 
  badgeType = 'orange',
  progress,
  onClick
}) {
  return (
    <div className={`metric-card ${onClick ? 'card-hoverable' : ''}`} onClick={onClick} style={{ cursor: onClick ? 'pointer' : 'default' }}>
      <div className="metric-card-top">
        <div className={`metric-icon-box metric-icon-${iconColor}`}>
          {Icon && <Icon size={22} />}
        </div>
        {badgeText && (
          <span className={`badge badge-${badgeType}`}>{badgeText}</span>
        )}
      </div>

      <div className="flex-col gap-1">
        <span className="metric-label">{label}</span>
        <span className="metric-value">{value}</span>
      </div>

      {progress !== undefined && (
        <div className="progress-bar-container">
          <div 
            className={`progress-bar-fill progress-${iconColor}`} 
            style={{ width: `${Math.min(100, Math.max(0, progress))}%` }} 
          />
        </div>
      )}

      {subtext && (
        <span className="metric-subtext">{subtext}</span>
      )}
    </div>
  );
}
