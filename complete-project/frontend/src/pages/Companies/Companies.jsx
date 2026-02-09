import React, { useState, useEffect } from 'react';
import { getCompanies } from '../../services/api';
import {
    RiskBadge,
    DecisionBadge,
    DataField,
    LoadingSpinner,
    EmptyState
} from '../../components/Shared';
import { EmissionsChart } from '../../components/Charts';

function Companies() {
    const [companies, setCompanies] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expandedCompany, setExpandedCompany] = useState(null);

    useEffect(() => {
        loadCompanies();
    }, []);

    const loadCompanies = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await getCompanies();
            if (response.success) {
                setCompanies(response.companies || []);
            } else {
                setError('Failed to load companies');
            }
        } catch (err) {
            console.error('Error loading companies:', err);
            setError(err.response?.data?.detail || err.message || 'Failed to load companies');
        } finally {
            setLoading(false);
        }
    };

    const toggleExpand = (companyName) => {
        setExpandedCompany(prev => prev === companyName ? null : companyName);
    };

    if (loading) {
        return <LoadingSpinner text="Loading companies..." />;
    }

    if (error) {
        return (
            <EmptyState
                icon="⚠️"
                title="Error Loading Data"
                description={error}
                action={
                    <button className="btn btn-primary" onClick={loadCompanies}>
                        Try Again
                    </button>
                }
            />
        );
    }

    if (companies.length === 0) {
        return (
            <EmptyState
                icon="🏢"
                title="No Companies Found"
                description="Upload sustainability reports to see company data here."
                action={
                    <a href="/" className="btn btn-primary">
                        Go to Upload
                    </a>
                }
            />
        );
    }

    return (
        <div>
            <div className="page-header">
                <h1 className="page-title">Company Overview</h1>
                <p className="page-subtitle">
                    {companies.length} companies with ESG data • Click a card for details
                </p>
            </div>

            {/* Summary Stats */}
            <div className="stats-grid">
                <div className="stat-card">
                    <div className="stat-value">{companies.length}</div>
                    <div className="stat-label">Total Companies</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value" style={{ color: 'var(--risk-low)' }}>
                        {companies.filter(c => c.risk_level === 'low').length}
                    </div>
                    <div className="stat-label">Low Risk</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value" style={{ color: 'var(--risk-medium)' }}>
                        {companies.filter(c => c.risk_level === 'medium').length}
                    </div>
                    <div className="stat-label">Medium Risk</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value" style={{ color: 'var(--risk-high)' }}>
                        {companies.filter(c => c.risk_level === 'high').length}
                    </div>
                    <div className="stat-label">High Risk</div>
                </div>
            </div>

            {/* Company Grid */}
            <div className="grid grid-2">
                {companies.map((company) => (
                    <div
                        key={company.name}
                        className="card"
                        style={{ cursor: 'pointer' }}
                        onClick={() => toggleExpand(company.name)}
                    >
                        {/* Header */}
                        <div className="card-header">
                            <div>
                                <h3 className="card-title" style={{ marginBottom: 'var(--spacing-xs)' }}>
                                    {company.name || 'Unknown Company'}
                                </h3>
                                <div className="flex gap-sm">
                                    <RiskBadge level={company.risk_level || 'insufficient'} />
                                    <DecisionBadge decision={company.decision} />
                                </div>
                            </div>
                            <div className="text-muted" style={{ fontSize: '0.875rem' }}>
                                {company.years_count || 0} years
                            </div>
                        </div>

                        {/* Key Metrics */}
                        <div className="card-body">
                            <div className="grid grid-2" style={{ gap: 'var(--spacing-md)' }}>
                                <DataField
                                    label="Latest Scope 1"
                                    value={company.latest_scope_1}
                                    unit={company.latest_scope_1_unit}
                                />
                                <DataField
                                    label="Latest Scope 2"
                                    value={company.latest_scope_2}
                                    unit={company.latest_scope_2_unit}
                                />
                                <DataField
                                    label="2030 Target"
                                    value={company.target_2030}
                                />
                                <DataField
                                    label="Assurance"
                                    value={company.has_assurance ? 'Yes ✓' : 'No'}
                                />
                            </div>

                            {/* Years available */}
                            <div className="mt-md">
                                <div className="data-field-label">Years Available</div>
                                <div className="flex gap-sm" style={{ flexWrap: 'wrap' }}>
                                    {company.years_available?.length > 0 ? (
                                        company.years_available.map(year => (
                                            <span
                                                key={year}
                                                style={{
                                                    padding: '2px 8px',
                                                    background: 'rgba(255, 98, 0, 0.2)',
                                                    borderRadius: 'var(--radius-sm)',
                                                    fontSize: '0.75rem'
                                                }}
                                            >
                                                {year}
                                            </span>
                                        ))
                                    ) : (
                                        <span className="text-muted">N/A</span>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Expanded Content */}
                        {expandedCompany === company.name && (
                            <div className="card-footer">
                                {/* Emissions Chart */}
                                <h4 style={{ marginBottom: 'var(--spacing-md)' }}>Emissions Over Time</h4>
                                <EmissionsChart data={company.data} showLegend={true} />

                                {/* Action Plan */}
                                {company.action_plan && (
                                    <div className="mt-lg">
                                        <div className="data-field-label">Action Plan Summary</div>
                                        <p style={{
                                            color: 'var(--gray-300)',
                                            fontSize: '0.875rem',
                                            lineHeight: '1.6'
                                        }}>
                                            {company.action_plan}
                                        </p>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}

export default Companies;
