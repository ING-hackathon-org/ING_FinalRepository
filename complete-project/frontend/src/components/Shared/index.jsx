import React from 'react';

/**
 * Display a data field with graceful handling of missing values
 */
export function DataField({ label, value, unit, className = '' }) {
    const displayValue = value !== null && value !== undefined && value !== ''
        ? (unit ? `${formatNumber(value)} ${unit}` : formatNumber(value))
        : null;

    return (
        <div className={`data-field ${className}`}>
            <div className="data-field-label">{label}</div>
            <div className={`data-field-value ${!displayValue ? 'muted' : ''}`}>
                {displayValue || 'N/A'}
            </div>
        </div>
    );
}

/**
 * Format numbers with appropriate precision
 */
function formatNumber(value) {
    if (typeof value !== 'number') return value;

    if (value >= 1000000) {
        return `${(value / 1000000).toFixed(2)}M`;
    } else if (value >= 1000) {
        return `${(value / 1000).toFixed(2)}K`;
    } else if (value < 1 && value > 0) {
        return value.toFixed(4);
    }
    return value.toLocaleString();
}

/**
 * Risk badge component
 */
export function RiskBadge({ level }) {
    const labels = {
        high: 'High Risk',
        medium: 'Medium Risk',
        low: 'Low Risk',
        insufficient: 'Insufficient Data'
    };

    return (
        <span className={`risk-badge ${level}`}>
            <span className="risk-dot"></span>
            {labels[level] || 'Unknown'}
        </span>
    );
}

/**
 * Decision badge component
 */
export function DecisionBadge({ decision }) {
    if (!decision) return null;

    const isCooperate = decision === 'cooperate';

    return (
        <span className={`risk-badge ${isCooperate ? 'low' : 'high'}`}>
            <span className="risk-dot"></span>
            {isCooperate ? 'Cooperate' : 'Suspend'}
        </span>
    );
}

/**
 * Loading spinner component
 */
export function LoadingSpinner({ text = 'Loading...' }) {
    return (
        <div className="loading-container">
            <div className="loading-spinner"></div>
            <span className="loading-text">{text}</span>
        </div>
    );
}

/**
 * Empty state component
 */
export function EmptyState({ icon = '📭', title, description, action }) {
    return (
        <div className="empty-state">
            <div className="empty-state-icon">{icon}</div>
            <h3 className="empty-state-title">{title}</h3>
            <p className="empty-state-description">{description}</p>
            {action && <div className="mt-lg">{action}</div>}
        </div>
    );
}

/**
 * Stat card component
 */
export function StatCard({ value, label, icon }) {
    return (
        <div className="stat-card">
            {icon && <div className="stat-icon">{icon}</div>}
            <div className="stat-value">{value ?? 'N/A'}</div>
            <div className="stat-label">{label}</div>
        </div>
    );
}

/**
 * Progress bar component
 */
export function ProgressBar({ progress = 0 }) {
    return (
        <div className="progress-bar">
            <div
                className="progress-bar-fill"
                style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
            />
        </div>
    );
}

export default {
    DataField,
    RiskBadge,
    DecisionBadge,
    LoadingSpinner,
    EmptyState,
    StatCard,
    ProgressBar
};
