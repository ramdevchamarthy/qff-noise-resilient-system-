/**
 * Environment configuration for Noise-Resilient Quantum System.
 * In development or when served from the same origin, API_BASE is empty (relative /api calls).
 * In production when the backend is hosted on a separate URL, set VITE_API_URL.
 */
export const API_BASE = (((import.meta as any).env?.VITE_API_URL as string) || '').replace(/\/$/, '');
