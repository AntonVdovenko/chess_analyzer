import React from 'react';

export default function StudyFilter({ plans, filters, onFilterChange }) {
  const statusOptions = ['all', 'active', 'completed', 'paused'].filter((status, index) => {
    if (index === 0) return true;
    return plans.some((plan) => plan.status === status) || filters.status === status || !plans.length;
  });

  const handleFilterChange = (fieldName) => (e) => {
    onFilterChange({
      ...filters,
      [fieldName]: e.target.value,
    });
  };

  return (
    <div className="study-filter">
      <h3>Filters</h3>

      <div className="filter-group">
        <label htmlFor="status-filter">Status</label>
        <select
          id="status-filter"
          value={filters.status || 'all'}
          onChange={handleFilterChange('status')}
        >
          {statusOptions.map((status) => (
            <option key={status} value={status}>
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-group">
        <label htmlFor="sort-filter">Sort By</label>
        <select
          id="sort-filter"
          value={filters.sort_by || 'created_at'}
          onChange={handleFilterChange('sort_by')}
        >
          <option value="created_at">Date Created</option>
          <option value="priority_score">Priority</option>
        </select>
      </div>
    </div>
  );
}
