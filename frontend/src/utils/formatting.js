/**
 * Formatting utilities for consistent data presentation across components.
 */

/**
 * Format a number as a percentage (0-1 scale).
 * @param {number} value - Value between 0 and 1
 * @param {number} decimals - Number of decimal places (default: 0)
 * @returns {string} Formatted percentage string (e.g., "75%")
 */
export const formatPercentage = (value, decimals = 0) => {
  if (value === null || value === undefined) return 'N/A';
  return `${(value * 100).toFixed(decimals)}%`;
};

/**
 * Format a number with fixed decimal places.
 * @param {number} value - Number to format
 * @param {number} decimals - Number of decimal places (default: 1)
 * @returns {string} Formatted number
 */
export const formatNumber = (value, decimals = 1) => {
  if (value === null || value === undefined) return 'N/A';
  return value.toFixed(decimals);
};

/**
 * Format centipawn loss for display.
 * @param {number} value - Centipawn loss value
 * @param {number} decimals - Number of decimal places (default: 0)
 * @returns {string} Formatted string (e.g., "150 cp")
 */
export const formatCentipawns = (value, decimals = 0) => {
  if (value === null || value === undefined) return 'N/A';
  return `${value.toFixed(decimals)} cp`;
};

/**
 * Format a date string for display.
 * @param {string|Date} dateValue - ISO date string or Date object
 * @param {object} options - Options for toLocaleDateString
 * @returns {string} Formatted date
 */
export const formatDate = (dateValue, options = {}) => {
  if (!dateValue) return 'N/A';
  try {
    const date = typeof dateValue === 'string' ? new Date(dateValue) : dateValue;
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      ...options,
    });
  } catch {
    return 'Invalid date';
  }
};

/**
 * Format a date with time for display.
 * @param {string|Date} dateValue - ISO date string or Date object
 * @returns {string} Formatted date with time
 */
export const formatDateTime = (dateValue) => {
  return formatDate(dateValue, { hour: '2-digit', minute: '2-digit' });
};
