import React from 'react';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    BarElement,
    LineElement,
    PointElement,
    Title,
    Tooltip,
    Legend,
    ArcElement
} from 'chart.js';
import { Bar, Line, Doughnut } from 'react-chartjs-2';

// Register Chart.js components
ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    LineElement,
    PointElement,
    Title,
    Tooltip,
    Legend,
    ArcElement
);

// Default chart options for light theme
const defaultOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            labels: {
                color: 'rgba(31, 41, 55, 0.9)',
                font: {
                    family: 'Inter, sans-serif'
                }
            }
        },
        tooltip: {
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            titleColor: '#1F2937',
            bodyColor: 'rgba(31, 41, 55, 0.8)',
            borderColor: 'rgba(0, 0, 0, 0.1)',
            borderWidth: 1,
            cornerRadius: 8,
            padding: 12
        }
    },
    scales: {
        x: {
            ticks: { color: 'rgba(75, 85, 99, 0.9)' },
            grid: { color: 'rgba(0, 0, 0, 0.1)' }
        },
        y: {
            ticks: { color: 'rgba(75, 85, 99, 0.9)' },
            grid: { color: 'rgba(0, 0, 0, 0.1)' }
        }
    }
};

/**
 * Emissions bar chart for a single company
 */
export function EmissionsChart({ data, showLegend = true }) {
    if (!data || data.length === 0) {
        return (
            <div className="chart-container flex items-center justify-center">
                <span className="text-muted">No emissions data available</span>
            </div>
        );
    }

    // Sort by year
    const sortedData = [...data].sort((a, b) => (a.Reporting_Year || 0) - (b.Reporting_Year || 0));

    const labels = sortedData.map(d => d.Reporting_Year || 'N/A');
    const scope1Values = sortedData.map(d => d.Scope_1_Value || 0);
    const scope2Values = sortedData.map(d => d.Scope_2_Market_Value || 0);

    const chartData = {
        labels,
        datasets: [
            {
                label: 'Scope 1',
                data: scope1Values,
                backgroundColor: 'rgba(255, 98, 0, 0.8)',
                borderColor: '#FF6200',
                borderWidth: 1,
                borderRadius: 4
            },
            {
                label: 'Scope 2 (Market)',
                data: scope2Values,
                backgroundColor: 'rgba(0, 86, 164, 0.8)',
                borderColor: '#0056A4',
                borderWidth: 1,
                borderRadius: 4
            }
        ]
    };

    const options = {
        ...defaultOptions,
        plugins: {
            ...defaultOptions.plugins,
            legend: {
                display: showLegend,
                labels: defaultOptions.plugins.legend.labels
            }
        }
    };

    return (
        <div className="chart-container">
            <Bar data={chartData} options={options} />
        </div>
    );
}

/**
 * Combined emissions line chart for multiple companies
 */
export function CombinedEmissionsChart({ companiesData }) {
    if (!companiesData || companiesData.length === 0) {
        return (
            <div className="chart-container flex items-center justify-center">
                <span className="text-muted">Select companies to view combined data</span>
            </div>
        );
    }

    // Get all unique years
    const allYears = new Set();
    companiesData.forEach(company => {
        company.data?.forEach(d => {
            if (d.Reporting_Year) allYears.add(d.Reporting_Year);
        });
    });
    const sortedYears = Array.from(allYears).sort();

    // Generate colors for each company
    const colors = [
        '#FF6200', '#0056A4', '#10B981', '#F59E0B', '#EF4444',
        '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16', '#F97316'
    ];

    const datasets = companiesData.map((company, index) => {
        const dataByYear = {};
        company.data?.forEach(d => {
            if (d.Reporting_Year) {
                dataByYear[d.Reporting_Year] = d.Scope_1_Value || 0;
            }
        });

        return {
            label: company.name,
            data: sortedYears.map(year => dataByYear[year] || null),
            borderColor: colors[index % colors.length],
            backgroundColor: colors[index % colors.length] + '40',
            tension: 0.3,
            fill: false,
            spanGaps: true
        };
    });

    const chartData = {
        labels: sortedYears,
        datasets
    };

    return (
        <div className="chart-container" style={{ height: '300px' }}>
            <Line data={chartData} options={defaultOptions} />
        </div>
    );
}

/**
 * Risk distribution doughnut chart
 */
export function RiskDistributionChart({ companies }) {
    if (!companies || companies.length === 0) {
        return (
            <div className="chart-container flex items-center justify-center">
                <span className="text-muted">No data available</span>
            </div>
        );
    }

    const riskCounts = {
        high: 0,
        medium: 0,
        low: 0,
        insufficient: 0
    };

    companies.forEach(c => {
        const level = c.risk_level || 'insufficient';
        riskCounts[level] = (riskCounts[level] || 0) + 1;
    });

    const chartData = {
        labels: ['High Risk', 'Medium Risk', 'Low Risk', 'Insufficient Data'],
        datasets: [{
            data: [riskCounts.high, riskCounts.medium, riskCounts.low, riskCounts.insufficient],
            backgroundColor: [
                'rgba(239, 68, 68, 0.8)',
                'rgba(245, 158, 11, 0.8)',
                'rgba(16, 185, 129, 0.8)',
                'rgba(107, 114, 128, 0.8)'
            ],
            borderColor: [
                '#EF4444',
                '#F59E0B',
                '#10B981',
                '#6B7280'
            ],
            borderWidth: 2
        }]
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom',
                labels: {
                    color: 'rgba(31, 41, 55, 0.9)',
                    font: { family: 'Inter, sans-serif' },
                    padding: 16
                }
            }
        }
    };

    return (
        <div className="chart-container" style={{ height: '250px' }}>
            <Doughnut data={chartData} options={options} />
        </div>
    );
}

/**
 * Decision distribution chart
 */
export function DecisionDistributionChart({ companies }) {
    if (!companies || companies.length === 0) {
        return (
            <div className="chart-container flex items-center justify-center">
                <span className="text-muted">No data available</span>
            </div>
        );
    }

    const decisionCounts = {
        cooperate: 0,
        suspend: 0,
        pending: 0
    };

    companies.forEach(c => {
        if (c.decision === 'cooperate') {
            decisionCounts.cooperate++;
        } else if (c.decision === 'suspend') {
            decisionCounts.suspend++;
        } else {
            decisionCounts.pending++;
        }
    });

    const chartData = {
        labels: ['Cooperate', 'Suspend', 'Pending'],
        datasets: [{
            data: [decisionCounts.cooperate, decisionCounts.suspend, decisionCounts.pending],
            backgroundColor: [
                'rgba(16, 185, 129, 0.8)',
                'rgba(239, 68, 68, 0.8)',
                'rgba(107, 114, 128, 0.8)'
            ],
            borderColor: [
                '#10B981',
                '#EF4444',
                '#6B7280'
            ],
            borderWidth: 2
        }]
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom',
                labels: {
                    color: 'rgba(31, 41, 55, 0.9)',
                    font: { family: 'Inter, sans-serif' },
                    padding: 16
                }
            }
        }
    };

    return (
        <div className="chart-container" style={{ height: '250px' }}>
            <Doughnut data={chartData} options={options} />
        </div>
    );
}

export default {
    EmissionsChart,
    CombinedEmissionsChart,
    RiskDistributionChart,
    DecisionDistributionChart
};
