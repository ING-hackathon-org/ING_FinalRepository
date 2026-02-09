import React, { useState, useEffect, useMemo } from 'react';
import { getCompanies } from '../../services/api';
import {
    LoadingSpinner,
    EmptyState,
    StatCard
} from '../../components/Shared';
import {
    CombinedEmissionsChart,
    RiskDistributionChart,
    DecisionDistributionChart
} from '../../components/Charts';

function Analytics() {
    const [companies, setCompanies] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedCompanies, setSelectedCompanies] = useState(new Set());

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
                // Select all companies by default
                setSelectedCompanies(new Set(response.companies?.map(c => c.name) || []));
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

    const toggleCompany = (name) => {
        setSelectedCompanies(prev => {
            const newSet = new Set(prev);
            if (newSet.has(name)) {
                newSet.delete(name);
            } else {
                newSet.add(name);
            }
            return newSet;
        });
    };

    const selectAll = () => {
        setSelectedCompanies(new Set(companies.map(c => c.name)));
    };

    const selectNone = () => {
        setSelectedCompanies(new Set());
    };

    // Filter companies based on selection
    const filteredCompanies = useMemo(() => {
        return companies.filter(c => selectedCompanies.has(c.name));
    }, [companies, selectedCompanies]);

    // Calculate aggregate statistics
    const stats = useMemo(() => {
        if (filteredCompanies.length === 0) {
            return { totalScope1: 0, totalScope2: 0, avgScope1: 0, avgScope2: 0 };
        }

        let totalScope1 = 0;
        let totalScope2 = 0;
        let count1 = 0;
        let count2 = 0;

        filteredCompanies.forEach(company => {
            if (company.latest_scope_1 != null) {
                totalScope1 += company.latest_scope_1;
                count1++;
            }
            if (company.latest_scope_2 != null) {
                totalScope2 += company.latest_scope_2;
                count2++;
            }
        });

        return {
            totalScope1: totalScope1.toFixed(2),
            totalScope2: totalScope2.toFixed(2),
            avgScope1: count1 > 0 ? (totalScope1 / count1).toFixed(2) : 'N/A',
            avgScope2: count2 > 0 ? (totalScope2 / count2).toFixed(2) : 'N/A'
        };
    }, [filteredCompanies]);

    if (loading) {
        return <LoadingSpinner text="Loading analytics data..." />;
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
                icon="📊"
                title="No Data Available"
                description="Upload sustainability reports to see analytics."
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
                <h1 className="page-title">Combined Analytics</h1>
                <p className="page-subtitle">
                    Aggregate ESG metrics across selected companies
                </p>
            </div>

            <div className="layout-with-sidebar">
                {/* Sidebar with company selection */}
                <div className="sidebar">
                    <div className="sidebar-title">Select Companies</div>

                    <div className="flex gap-sm mb-md">
                        <button className="btn btn-ghost btn-sm" onClick={selectAll}>
                            Select All
                        </button>
                        <button className="btn btn-ghost btn-sm" onClick={selectNone}>
                            Clear
                        </button>
                    </div>

                    <div className="checkbox-list">
                        {companies.map((company) => (
                            <label key={company.name} className="checkbox-item">
                                <input
                                    type="checkbox"
                                    checked={selectedCompanies.has(company.name)}
                                    onChange={() => toggleCompany(company.name)}
                                />
                                <span>{company.name}</span>
                            </label>
                        ))}
                    </div>

                    <div className="mt-lg text-muted" style={{ fontSize: '0.75rem' }}>
                        {selectedCompanies.size} of {companies.length} selected
                    </div>
                </div>

                {/* Main content */}
                <div>
                    {/* Stats */}
                    <div className="stats-grid">
                        <StatCard
                            value={selectedCompanies.size}
                            label="Selected Companies"
                        />
                        <StatCard
                            value={stats.totalScope1}
                            label="Total Scope 1 (Latest)"
                        />
                        <StatCard
                            value={stats.avgScope1}
                            label="Avg Scope 1 (Latest)"
                        />
                        <StatCard
                            value={filteredCompanies.filter(c => c.has_assurance).length}
                            label="With Assurance"
                        />
                    </div>

                    {/* Charts */}
                    <div className="grid grid-2">
                        {/* Emissions Over Time */}
                        <div className="card">
                            <h4 className="card-title">Scope 1 Emissions Trend</h4>
                            <CombinedEmissionsChart companiesData={filteredCompanies} />
                        </div>

                        {/* Risk Distribution */}
                        <div className="card">
                            <h4 className="card-title">Risk Distribution</h4>
                            <RiskDistributionChart companies={filteredCompanies} />
                        </div>
                    </div>

                    {/* Decision Distribution */}
                    <div className="card mt-lg">
                        <h4 className="card-title">Decision Status</h4>
                        <div className="grid grid-2">
                            <DecisionDistributionChart companies={filteredCompanies} />
                            <div className="flex flex-col justify-center gap-md" style={{ padding: 'var(--spacing-lg)' }}>
                                <div>
                                    <div className="text-muted" style={{ fontSize: '0.875rem' }}>Cooperate</div>
                                    <div style={{ fontSize: '1.5rem', fontWeight: '600', color: 'var(--risk-low)' }}>
                                        {filteredCompanies.filter(c => c.decision === 'cooperate').length} companies
                                    </div>
                                </div>
                                <div>
                                    <div className="text-muted" style={{ fontSize: '0.875rem' }}>Suspend</div>
                                    <div style={{ fontSize: '1.5rem', fontWeight: '600', color: 'var(--risk-high)' }}>
                                        {filteredCompanies.filter(c => c.decision === 'suspend').length} companies
                                    </div>
                                </div>
                                <div>
                                    <div className="text-muted" style={{ fontSize: '0.875rem' }}>Pending Decision</div>
                                    <div style={{ fontSize: '1.5rem', fontWeight: '600', color: 'var(--gray-400)' }}>
                                        {filteredCompanies.filter(c => !c.decision).length} companies
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Data Table */}
                    <div className="card mt-lg">
                        <h4 className="card-title">Company Comparison</h4>
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{
                                width: '100%',
                                borderCollapse: 'collapse',
                                fontSize: '0.875rem'
                            }}>
                                <thead>
                                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                                        <th style={{ padding: 'var(--spacing-sm)', textAlign: 'left', color: 'var(--gray-400)' }}>Company</th>
                                        <th style={{ padding: 'var(--spacing-sm)', textAlign: 'right', color: 'var(--gray-400)' }}>Scope 1</th>
                                        <th style={{ padding: 'var(--spacing-sm)', textAlign: 'right', color: 'var(--gray-400)' }}>Scope 2</th>
                                        <th style={{ padding: 'var(--spacing-sm)', textAlign: 'center', color: 'var(--gray-400)' }}>Risk</th>
                                        <th style={{ padding: 'var(--spacing-sm)', textAlign: 'center', color: 'var(--gray-400)' }}>Decision</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredCompanies.map(company => (
                                        <tr key={company.name} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                            <td style={{ padding: 'var(--spacing-sm)' }}>{company.name}</td>
                                            <td style={{ padding: 'var(--spacing-sm)', textAlign: 'right' }}>
                                                {company.latest_scope_1 != null ? company.latest_scope_1.toLocaleString() : 'N/A'}
                                            </td>
                                            <td style={{ padding: 'var(--spacing-sm)', textAlign: 'right' }}>
                                                {company.latest_scope_2 != null ? company.latest_scope_2.toLocaleString() : 'N/A'}
                                            </td>
                                            <td style={{ padding: 'var(--spacing-sm)', textAlign: 'center' }}>
                                                <span className={`risk-badge ${company.risk_level}`}>
                                                    {company.risk_level || 'N/A'}
                                                </span>
                                            </td>
                                            <td style={{ padding: 'var(--spacing-sm)', textAlign: 'center' }}>
                                                {company.decision ? (
                                                    <span className={`risk-badge ${company.decision === 'cooperate' ? 'low' : 'high'}`}>
                                                        {company.decision}
                                                    </span>
                                                ) : (
                                                    <span className="text-muted">Pending</span>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default Analytics;
