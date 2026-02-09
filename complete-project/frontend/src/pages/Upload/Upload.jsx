import React, { useState, useCallback } from 'react';
import { uploadPDFs } from '../../services/api';
import { ProgressBar, LoadingSpinner } from '../../components/Shared';

function Upload() {
    const [isDragOver, setIsDragOver] = useState(false);
    const [files, setFiles] = useState([]);
    const [uploading, setUploading] = useState(false);
    const [progress, setProgress] = useState(0);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);

    const handleDragOver = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragOver(true);
    }, []);

    const handleDragLeave = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragOver(false);
    }, []);

    const handleDrop = async (e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragOver(false);
        setError(null);

        // Helper function to read all files from a directory entry recursively
        const readDirectoryEntry = (directoryEntry) => {
            return new Promise((resolve) => {
                const reader = directoryEntry.createReader();
                const allEntries = [];

                const readEntries = () => {
                    reader.readEntries((entries) => {
                        if (entries.length === 0) {
                            resolve(allEntries);
                        } else {
                            allEntries.push(...entries);
                            readEntries();
                        }
                    });
                };

                readEntries();
            });
        };

        // Helper function to get File from FileEntry
        const getFileFromEntry = (fileEntry) => {
            return new Promise((resolve) => {
                fileEntry.file((file) => resolve(file));
            });
        };

        // Recursively collect all PDF files from entries
        const collectPDFsFromEntries = async (entries) => {
            const pdfFiles = [];

            for (const entry of entries) {
                if (entry.isFile) {
                    if (entry.name.toLowerCase().endsWith('.pdf')) {
                        const file = await getFileFromEntry(entry);
                        pdfFiles.push(file);
                    }
                } else if (entry.isDirectory) {
                    const subEntries = await readDirectoryEntry(entry);
                    const subPDFs = await collectPDFsFromEntries(subEntries);
                    pdfFiles.push(...subPDFs);
                }
            }

            return pdfFiles;
        };

        const items = e.dataTransfer.items;
        const entries = [];

        // Check if we have access to webkitGetAsEntry (folder support)
        if (items && items.length > 0 && items[0].webkitGetAsEntry) {
            for (let i = 0; i < items.length; i++) {
                const entry = items[i].webkitGetAsEntry();
                if (entry) {
                    entries.push(entry);
                }
            }

            try {
                const pdfFiles = await collectPDFsFromEntries(entries);

                if (pdfFiles.length === 0) {
                    setError('No PDF files found. Please drop PDF files or folders containing PDFs.');
                    return;
                }

                setFiles(prev => [...prev, ...pdfFiles]);
            } catch (err) {
                console.error('Error reading dropped items:', err);
                setError('Error reading files. Please try again.');
            }
        } else {
            // Fallback for browsers without folder support
            const droppedFiles = Array.from(e.dataTransfer.files);
            const pdfFiles = droppedFiles.filter(file =>
                file.type === 'application/pdf' || file.name.endsWith('.pdf')
            );

            if (pdfFiles.length === 0) {
                setError('No PDF files found. Please drop PDF files or folders containing PDFs.');
                return;
            }

            setFiles(prev => [...prev, ...pdfFiles]);
        }
    };

    const handleFileSelect = useCallback((e) => {
        const selectedFiles = Array.from(e.target.files);
        const pdfFiles = selectedFiles.filter(file =>
            file.type === 'application/pdf' || file.name.endsWith('.pdf')
        );
        setFiles(prev => [...prev, ...pdfFiles]);
    }, []);

    const removeFile = useCallback((index) => {
        setFiles(prev => prev.filter((_, i) => i !== index));
    }, []);

    const handleUpload = async () => {
        if (files.length === 0) return;

        setUploading(true);
        setProgress(0);
        setError(null);
        setResult(null);

        try {
            const response = await uploadPDFs(files, setProgress);
            setResult(response);
            setFiles([]);
        } catch (err) {
            console.error('Upload error:', err);
            setError(err.response?.data?.detail || err.message || 'Upload failed. Please try again.');
        } finally {
            setUploading(false);
            setProgress(0);
        }
    };

    const clearAll = () => {
        setFiles([]);
        setResult(null);
        setError(null);
    };

    return (
        <div>
            <div className="page-header">
                <h1 className="page-title">Upload Reports</h1>
                <p className="page-subtitle">
                    Drag and drop sustainability reports (PDF) to extract ESG data
                </p>
            </div>

            {/* Upload Zone */}
            <div
                className={`upload-zone ${isDragOver ? 'dragover' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => !uploading && document.getElementById('file-input').click()}
            >
                <input
                    id="file-input"
                    type="file"
                    accept=".pdf"
                    multiple
                    style={{ display: 'none' }}
                    onChange={handleFileSelect}
                    disabled={uploading}
                />
                <div className="upload-zone-icon" style={{ fontSize: '2rem', color: 'var(--ing-orange)' }}>PDF</div>
                <h3 className="upload-zone-title">
                    {isDragOver ? 'Drop files here' : 'Drag & Drop PDF Reports'}
                </h3>
                <p className="upload-zone-subtitle">
                    or click to browse files
                </p>
                <p className="upload-zone-subtitle mt-md">
                    <strong>Expected folder structure:</strong><br />
                    company_name / year / report.pdf
                </p>
            </div>

            {/* Error Message */}
            {error && (
                <div className="card mt-lg" style={{ borderColor: 'var(--risk-high)' }}>
                    <div className="flex items-center gap-md">
                        <span style={{ fontSize: '1.5rem', color: 'var(--risk-high)', fontWeight: 'bold' }}>!</span>
                        <div>
                            <h4 style={{ margin: 0, color: 'var(--risk-high)' }}>Upload Error</h4>
                            <p className="text-muted mb-sm">{error}</p>
                        </div>
                    </div>
                </div>
            )}

            {/* Success Message */}
            {result && result.success && (
                <div className="card mt-lg" style={{ borderColor: 'var(--risk-low)' }}>
                    <div className="flex items-center gap-md">
                        <span style={{ fontSize: '1.5rem', color: 'var(--risk-low)', fontWeight: 'bold' }}>✓</span>
                        <div>
                            <h4 style={{ margin: 0, color: 'var(--risk-low)' }}>Success!</h4>
                            <p className="text-muted mb-sm">{result.message}</p>
                            {result.csv_path && (
                                <p className="text-muted">Output: {result.csv_path}</p>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* File List */}
            {files.length > 0 && (
                <div className="card mt-lg">
                    <div className="card-header">
                        <h3 className="card-title">Selected Files ({files.length})</h3>
                        <button className="btn btn-ghost btn-sm" onClick={clearAll}>
                            Clear All
                        </button>
                    </div>
                    <div className="card-body">
                        {files.map((file, index) => (
                            <div
                                key={index}
                                className="flex items-center justify-between gap-md mb-sm"
                                style={{
                                    padding: 'var(--spacing-sm)',
                                    background: 'rgba(255, 255, 255, 0.05)',
                                    borderRadius: 'var(--radius-md)'
                                }}
                            >
                                <div className="flex items-center gap-md">
                                    <span style={{ color: 'var(--ing-orange)', fontWeight: 'bold' }}>PDF</span>
                                    <div>
                                        <div>{file.name}</div>
                                        <div className="text-muted" style={{ fontSize: '0.75rem' }}>
                                            {(file.size / 1024 / 1024).toFixed(2)} MB
                                        </div>
                                    </div>
                                </div>
                                <button
                                    className="btn btn-ghost btn-sm"
                                    onClick={(e) => { e.stopPropagation(); removeFile(index); }}
                                    disabled={uploading}
                                >
                                    ✕
                                </button>
                            </div>
                        ))}
                    </div>
                    <div className="card-footer">
                        {uploading ? (
                            <div>
                                <ProgressBar progress={progress} />
                                <p className="text-muted text-center mt-md">
                                    Uploading and processing... {progress}%
                                </p>
                            </div>
                        ) : (
                            <button
                                className="btn btn-primary btn-lg w-full"
                                onClick={handleUpload}
                            >
                                Process {files.length} File{files.length > 1 ? 's' : ''}
                            </button>
                        )}
                    </div>
                </div>
            )}

            {/* Instructions */}
            <div className="grid grid-3 mt-lg">
                <div className="card text-center">
                    <div style={{ fontSize: '1.5rem', marginBottom: 'var(--spacing-md)', color: 'var(--ing-orange)', fontWeight: 'bold' }}>Step 1</div>
                    <h4>Upload PDFs</h4>
                    <p className="text-muted">
                        Drag and drop sustainability reports from companies
                    </p>
                </div>
                <div className="card text-center">
                    <div style={{ fontSize: '1.5rem', marginBottom: 'var(--spacing-md)', color: 'var(--ing-orange)', fontWeight: 'bold' }}>Step 2</div>
                    <h4>AI Extraction</h4>
                    <p className="text-muted">
                        Our AI extracts ESG metrics, emissions data, and targets
                    </p>
                </div>
                <div className="card text-center">
                    <div style={{ fontSize: '1.5rem', marginBottom: 'var(--spacing-md)', color: 'var(--ing-orange)', fontWeight: 'bold' }}>Step 3</div>
                    <h4>View Results</h4>
                    <p className="text-muted">
                        Analyze risk and make collaboration decisions
                    </p>
                </div>
            </div>
        </div>
    );
}

export default Upload;
