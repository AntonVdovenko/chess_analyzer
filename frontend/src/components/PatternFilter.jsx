export default function PatternFilter({ filter, onFilterChange }) {
  return (
    <div className="pattern-filter">
      <h3>Filter & Sort</h3>
      <div className="filter-group">
        <label htmlFor="pattern-type">Pattern Type</label>
        <select
          id="pattern-type"
          value={filter.type}
          onChange={(e) =>
            onFilterChange({ ...filter, type: e.target.value })
          }
        >
          <option value="all">All Types</option>
          <option value="tactical">Tactical</option>
          <option value="positional">Positional</option>
          <option value="opening">Opening</option>
          <option value="endgame">Endgame</option>
        </select>
      </div>
      <div className="filter-group">
        <label htmlFor="sort-by">Sort By</label>
        <select
          id="sort-by"
          value={filter.sortBy}
          onChange={(e) =>
            onFilterChange({ ...filter, sortBy: e.target.value })
          }
        >
          <option value="frequency">Frequency</option>
          <option value="impact">Impact (Loss)</option>
        </select>
      </div>
      <div className="filter-group">
        <label htmlFor="min-frequency">Min Frequency</label>
        <select
          id="min-frequency"
          value={filter.minFrequency}
          onChange={(e) =>
            onFilterChange({
              ...filter,
              minFrequency: parseInt(e.target.value),
            })
          }
        >
          <option value={1}>1+</option>
          <option value={2}>2+</option>
          <option value={5}>5+</option>
          <option value={10}>10+</option>
          <option value={20}>20+</option>
        </select>
      </div>
    </div>
  );
}
