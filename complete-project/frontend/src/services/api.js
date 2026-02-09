import axios from 'axios';

// Create axios instance with base configuration
const api = axios.create({
    baseURL: '/',
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor for logging
api.interceptors.request.use(
    (config) => {
        console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
        return config;
    },
    (error) => {
        console.error('[API] Request error:', error);
        return Promise.reject(error);
    }
);

// Response interceptor for error handling
api.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error('[API] Response error:', error.response?.data || error.message);
        return Promise.reject(error);
    }
);

// ============================================================================
// API Functions
// ============================================================================

/**
 * Get all ESG data
 */
export const getAllData = async () => {
    const response = await api.get('/api/data');
    return response.data;
};

/**
 * Get all companies with aggregated metrics
 */
export const getCompanies = async () => {
    const response = await api.get('/api/companies');
    return response.data;
};

/**
 * Get data for a specific company
 */
export const getCompany = async (companyName) => {
    const response = await api.get(`/api/company/${encodeURIComponent(companyName)}`);
    return response.data;
};

/**
 * Get all decisions
 */
export const getDecisions = async () => {
    const response = await api.get('/api/decisions');
    return response.data;
};

/**
 * Save a decision for a company
 */
export const saveDecision = async (company, decision) => {
    const response = await api.post('/api/decisions', null, {
        params: { company, decision }
    });
    return response.data;
};

/**
 * Upload PDF files for processing
 */
export const uploadPDFs = async (files, onProgress) => {
    const formData = new FormData();

    files.forEach((file) => {
        formData.append('files', file);
    });

    const response = await api.post('/process-batch', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
            if (onProgress) {
                const percentCompleted = Math.round(
                    (progressEvent.loaded * 100) / progressEvent.total
                );
                onProgress(percentCompleted);
            }
        },
    });

    return response.data;
};

/**
 * Upload a single PDF file
 */
export const uploadPDF = async (file, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/process-pdf', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
            if (onProgress) {
                const percentCompleted = Math.round(
                    (progressEvent.loaded * 100) / progressEvent.total
                );
                onProgress(percentCompleted);
            }
        },
    });

    return response.data;
};

/**
 * Check API health
 */
export const checkHealth = async () => {
    const response = await api.get('/health');
    return response.data;
};

export default api;
