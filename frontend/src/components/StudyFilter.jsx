import React from 'react';

export default function StudyFilter({ plans, filters, onFilterChange }) {
  // Extract unique values from plans
  const uniqueStatuses = ['all', ...new Set(plans.map((p) => p.status).filter(Boolean))];
  const uniqueConceptTypes = ['all', ...new Set(plans.map((p) => p.concept_type).filter(Boolean))];

  const handleStatusChange = (e) => {
    onFilterChange({
      ...filters,
      status: e.target.value,
    });
  };

  const handleConceptTypeChange = (e) => {
    onFilterChange({
      ...filters,
      concept_type: e.target.value,
    });
  };

  const handleSortChange = (e) => {
    onFilterChange({
      ...filters,
      sort_by: e.target.value,
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
          onChange={handleStatusChange}
        >
          {uniqueStatuses.map((status) => (
            <option key={status} value={status}>
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-group">
        <label htmlFor="concept-filter">Concept Type</label>
        <select
          id="concept-filter"
          value={filters.concept_type || 'all'}
          onChange={handleConceptTypeChange}
        >
          {uniqueConceptTypes.map((type) => (
            <option key={type} value={type}>
              {type.charAt(0).toUpperCase() + type.slice(1)}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-group">
        <label htmlFor="sort-filter">Sort By</label>
        <select
          id="sort-filter"
          value={filters.sort_by || 'created_at'}
          onChange={handleSortChange}
        >
          <option value="created_at">Date Created</option>
          <option value="priority_score">Priority</option>
        </select>
      </div>
    </div>
  );
}
