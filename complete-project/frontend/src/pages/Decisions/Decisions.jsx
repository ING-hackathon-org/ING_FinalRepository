import React, { useState, useEffect, useRef, useCallback } from 'react';
import { getCompanies, saveDecision } from '../../services/api';
import {
    RiskBadge,
    DataField,
    LoadingSpinner,
    EmptyState
} from '../../components/Shared';
import { EmissionsChart } from '../../components/Charts';

function Decisions() {
    const [companies, setCompanies] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [swipeDirection, setSwipeDirection] = useState(null);
    const [isDragging, setIsDragging] = useState(false);
    const [dragOffset, setDragOffset] = useState(0);
    const cardRef = useRef(null);
    const startX = useRef(0);

    useEffect(() => {
        loadCompanies();
    }, []);

    const loadCompanies = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await getCompanies();
            if (response.success) {
                // Filter to only show companies without decisions
                const pendingCompanies = response.companies?.filter(c => !c.decision) || [];
                setCompanies(pendingCompanies);
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

    const currentCompany = companies[currentIndex];

    const handleDecision = async (decision) => {
        if (!currentCompany) return;

        try {
            await saveDecision(currentCompany.name, decision);

            // Remove decided company from list
            setCompanies(prev => prev.filter((_, i) => i !== currentIndex));

            // Adjust current index if needed
            if (currentIndex >= companies.length - 1 && currentIndex > 0) {
                setCurrentIndex(prev => prev - 1);
            }
        } catch (err) {
            console.error('Error saving decision:', err);
        }

        setSwipeDirection(null);
        setDragOffset(0);
    };

    const handleMouseDown = (e) => {
        setIsDragging(true);
        startX.current = e.clientX;
    };

    const handleMouseMove = useCallback((e) => {
        if (!isDragging) return;

        const diff = e.clientX - startX.current;
        setDragOffset(diff);

        if (diff < -50) {
            setSwipeDirection('left');
        } else if (diff > 50) {
            setSwipeDirection('right');
        } else {
            setSwipeDirection(null);
        }
    }, [isDragging]);

    const handleMouseUp = () => {
        if (!isDragging) return;
        setIsDragging(false);

        if (swipeDirection === 'left') {
            handleDecision('suspend');
        } else if (swipeDirection === 'right') {
            handleDecision('cooperate');
        }

        setDragOffset(0);
        setSwipeDirection(null);
    };

    useEffect(() => {
        if (isDragging) {
            window.addEventListener('mousemove', handleMouseMove);
            window.addEventListener('mouseup', handleMouseUp);
            return () => {
                window.removeEventListener('mousemove', handleMouseMove);
                window.removeEventListener('mouseup', handleMouseUp);
            };
        }
    }, [isDragging, handleMouseMove, swipeDirection]);

    // Touch handlers for mobile
    const handleTouchStart = (e) => {
        setIsDragging(true);
        startX.current = e.touches[0].clientX;
    };

    const handleTouchMove = (e) => {
        if (!isDragging) return;

        const diff = e.touches[0].clientX - startX.current;
        setDragOffset(diff);

        if (diff < -50) {
            setSwipeDirection('left');
        } else if (diff > 50) {
            setSwipeDirection('right');
        } else {
            setSwipeDirection(null);
        }
    };

    const handleTouchEnd = () => {
        if (!isDragging) return;
        setIsDragging(false);

        if (swipeDirection === 'left') {
            handleDecision('suspend');
        } else if (swipeDirection === 'right') {
            handleDecision('cooperate');
        }

        setDragOffset(0);
        setSwipeDirection(null);
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
                icon="✅"
                title="All Caught Up!"
                description="You've made decisions for all companies. Check the Analytics page to see the summary."
                action={
                    <a href="/analytics" className="btn btn-primary">
                        View Analytics
                    </a>
                }
            />
        );
    }

    return (
        <div>
            <div className="page-header text-center">
                <h1 className="page-title">Make Decisions</h1>
                <p className="page-subtitle">
                    Swipe right to cooperate, left to suspend • {companies.length} remaining
                </p>
            </div>

            {/* Instructions */}
            <div className="flex justify-center gap-xl mb-lg">
                <div className="flex items-center gap-sm">
                    <span style={{ color: 'var(--risk-high)', fontSize: '1.5rem' }}>←</span>
                    <span className="text-muted">Suspend</span>
                </div>
                <div className="flex items-center gap-sm">
                    <span className="text-muted">Cooperate</span>
                    <span style={{ color: 'var(--risk-low)', fontSize: '1.5rem' }}>→</span>
                </div>
            </div>

            {/* Decision Card Container with Side Buttons */}
            <div className="decision-card-container">
                {/* Suspend Button - Left Side */}
                <button
                    className="decision-btn suspend decision-btn-side"
                    onClick={() => handleDecision('suspend')}
                    title="Suspend Collaboration"
                >
                    ✕
                </button>

                {/* Current Card */}
                {currentCompany && (
                    <div
                        ref={cardRef}
                        className={`decision-card ${swipeDirection ? `swiping-${swipeDirection}` : ''}`}
                        style={{
                            transform: `translateX(${dragOffset}px) rotate(${dragOffset * 0.05}deg)`,
                            zIndex: 20,
                            cursor: isDragging ? 'grabbing' : 'grab'
                        }}
                        onMouseDown={handleMouseDown}
                        onTouchStart={handleTouchStart}
                        onTouchMove={handleTouchMove}
                        onTouchEnd={handleTouchEnd}
                    >
                        {/* Swipe indicators */}
                        <div className="decision-overlay left">✕</div>
                        <div className="decision-overlay right">✓</div>

                        {/* Card Content */}
                        <div className="text-center mb-lg">
                            <h2 style={{ fontSize: '1.75rem', marginBottom: 'var(--spacing-sm)' }}>
                                {currentCompany.name}
                            </h2>
                            <RiskBadge level={currentCompany.risk_level || 'insufficient'} />
                        </div>

                        {/* Key Metrics */}
                        <div className="grid grid-2 gap-md mb-lg">
                            <DataField
                                label="Scope 1 Emissions"
                                value={currentCompany.latest_scope_1}
                                unit={currentCompany.latest_scope_1_unit}
                            />
                            <DataField
                                label="Scope 2 Emissions"
                                value={currentCompany.latest_scope_2}
                                unit={currentCompany.latest_scope_2_unit}
                            />
                            <DataField
                                label="2030 Target"
                                value={currentCompany.target_2030}
                            />
                            <DataField
                                label="Third-Party Assurance"
                                value={currentCompany.has_assurance ? 'Yes ✓' : 'No'}
                            />
                        </div>

                        {/* Emissions Chart */}
                        <EmissionsChart data={currentCompany.data} showLegend={false} />

                        {/* Action Plan */}
                        {currentCompany.action_plan && (
                            <div className="mt-lg">
                                <div className="data-field-label">Action Plan</div>
                                <p style={{
                                    fontSize: '0.8rem',
                                    color: 'var(--gray-600)',
                                    maxHeight: '60px',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis'
                                }}>
                                    {currentCompany.action_plan}
                                </p>
                            </div>
                        )}
                    </div>
                )}

                {/* Cooperate Button - Right Side */}
                <button
                    className="decision-btn cooperate decision-btn-side"
                    onClick={() => handleDecision('cooperate')}
                    title="Continue Collaboration"
                >
                    ✓
                </button>
            </div>

            {/* Keyboard hint */}
            <p className="text-center text-muted mt-lg" style={{ fontSize: '0.75rem' }}>
                You can also drag the card left or right
            </p>
        </div>
    );
}

export default Decisions;
