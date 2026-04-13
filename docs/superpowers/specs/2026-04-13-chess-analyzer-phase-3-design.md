# Chess Analyzer Phase 3: Study Planning - Design Specification

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate adaptive, personalized study plans that help players break repetitive mistake patterns through prioritized game review, chess concept mapping, and progress tracking.

**Architecture:** Modular study planning system that analyzes Phase 1+2 weaknesses, maps them to hybrid chess concepts (theory + opening + position type), prioritizes by frequency, and provides a dashboard for tracking study progress.

**Tech Stack:** FastAPI (new endpoints), PostgreSQL (3 new tables), React 19 (StudyPlan component suite), Stockfish (engine analysis reuse)

---

## System Architecture

### High-Level Data Flow

```
Phase 1+2 Results (patterns, weaknesses, anomalies)
           ↓
StudyPlanGenerator
├── Prioritize by frequency (0-1 score)
├── ConceptMapper → Map to hybrid chess concepts
├── Engine analysis lookup → Continuations
└── Create StudyPlan records
           ↓
Study Plan API + Dashboard UI
├── Dashboard: All weaknesses, filterable, sortable
├── Progress tracking: completion rate, priority distribution
└── Game review: Affected games with engine continuations
```

### Core Components

**Backend (Python/FastAPI):**
1. **StudyPlanGenerator** - Analyze Phase 1+2 results, create prioritized plans
2. **ConceptMapper** - Map weaknesses to hybrid chess concepts
3. **Study Plan API** - 6 new REST endpoints for dashboard + management
4. **Engine Analysis Integration** - Reuse existing PositionAnalyzer for continuations

**Frontend (React):**
1. **StudyPlan.jsx** - Main dashboard component
2. **StudyFilter.jsx** - Filtering and sorting controls
3. **StudyCard.jsx** - Individual weakness card
4. **StudyDetail.jsx** - Deep-dive weakness view

---

## Database Schema

### New Tables

#### `study_plans`
```sql
CREATE TABLE study_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    weakness_id UUID NOT NULL REFERENCES patterns(id),
    priority_score FLOAT NOT NULL,  -- 0-1, based on frequency
    status VARCHAR(50) DEFAULT 'pending',  -- pending, in_progress, completed
    marked_studied_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_study_plans_user_id ON study_plans(user_id);
CREATE INDEX idx_study_plans_status ON study_plans(status);
CREATE INDEX idx_study_plans_priority ON study_plans(priority_score DESC);
```

**Purpose:** Track study plan records for each weakness. Priority score (0-1) calculated from pattern frequency. Status tracks completion.

#### `concept_maps`
```sql
CREATE TABLE concept_maps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    weakness_id UUID NOT NULL REFERENCES patterns(id),
    concept_type VARCHAR(50) NOT NULL,  -- 'theory', 'opening', 'position_type'
    concept_name VARCHAR(255) NOT NULL,  -- e.g., 'weak_squares', 'sicilian_defense', 'rook_endgame'
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_concept_maps_weakness_id ON concept_maps(weakness_id);
CREATE INDEX idx_concept_maps_concept ON concept_maps(concept_type, concept_name);
```

**Purpose:** Junction table mapping weaknesses to multiple chess concepts. Supports hybrid categorization.

#### `study_sessions`
```sql
CREATE TABLE study_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    study_plan_id UUID NOT NULL REFERENCES study_plans(id),
    games_reviewed TEXT[] DEFAULT '{}',  -- Array of game IDs studied
    engine_analysis_count INT DEFAULT 0,  -- How many positions analyzed
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_study_sessions_study_plan_id ON study_sessions(study_plan_id);
```

**Purpose:** Track actual study sessions. Records which games were reviewed and how many positions were analyzed with engine.

---

## Backend Components

### 1. StudyPlanGenerator

**File:** `src/chess_analyzer/study_planning/study_plan_generator.py`

**Purpose:** Create prioritized study plans from Phase 1+2 results, organized by chess concepts.

**Key Methods:**

```python
class StudyPlanGenerator:
    def __init__(self, db_session):
        self.db = db_session
        self.concept_mapper = ConceptMapper()
    
    def generate_study_plan(self, username: str, game_limit: int = None) -> dict:
        """
        Generate complete study plan for user.
        
        Args:
            username: Chess.com username
            game_limit: Only consider last N games (optional)
        
        Returns:
            {
                username: str,
                total_weaknesses: int,
                study_plans_created: int,
                priority_distribution: {high: int, medium: int, low: int}
            }
        
        Algorithm:
        1. Get all patterns for user from Phase 1
        2. Calculate frequency-based priority:
           - priority_score = (pattern.frequency / max_frequency)
           - Clamp to 0-1 range
        3. For each pattern:
           a. Map to chess concepts (theory, opening, position type)
           b. Create StudyPlan record with priority_score
           c. Create ConceptMap records for each concept
        4. Return summary statistics
        """
```

**Frequency Calculation:**
- Analyze all patterns for user
- Find max frequency
- For each pattern: `priority_score = frequency / max_frequency`
- Patterns are studied in priority order (highest first)

### 2. ConceptMapper

**File:** `src/chess_analyzer/study_planning/concept_mapper.py`

**Purpose:** Map weaknesses to hybrid chess concepts (theory + opening + position type).

**Chess Concept Taxonomy:**

**Theory Concepts:**
- `weak_squares` - Squares that opponent can exploit
- `piece_coordination` - Pieces not working together
- `pawn_structure` - Weak pawn formation
- `king_safety` - Exposed king position
- `tempo` - Time advantage loss
- `material_balance` - Piece value imbalance
- `tactics` - Tactical motifs (pins, forks, etc.)
- `strategy` - Strategic positioning

**Opening Concepts:**
- `sicilian_defense` - Sicilian variations
- `ruy_lopez` - Ruy Lopez variations
- `french_defense` - French Defense variations
- `caro_kann` - Caro-Kann variations
- `italian_game` - Italian Game variations
- `english_opening` - English Opening
- `others` - Other openings

**Position Type Concepts:**
- `opening` - Opening phase (moves 1-12)
- `middlegame` - Middlegame phase (moves 13-35)
- `endgame` - Endgame phase (moves 36+)
- `rook_endgame` - Rook endgame
- `opposite_bishops` - Opposite colored bishops
- `passed_pawns` - Passed pawn positions
- `pawn_endgame` - Pawn-only endgame

**Key Methods:**

```python
class ConceptMapper:
    def __init__(self):
        self.theory_concepts = {...}
        self.opening_concepts = {...}
        self.position_concepts = {...}
    
    def map_weakness(self, pattern: Pattern) -> List[dict]:
        """
        Map a pattern to chess concepts.
        
        Args:
            pattern: Pattern object with type, opening, features
        
        Returns:
            [
                {"type": "theory", "name": "weak_squares"},
                {"type": "opening", "name": "sicilian_defense"},
                {"type": "position_type", "name": "middlegame"}
            ]
        
        Logic:
        1. Analyze pattern.type (tactical, positional, opening)
        2. Extract opening from pattern metadata
        3. Analyze position features (material, king safety, pawn structure)
        4. Return list of relevant concepts
        """
```

---

## REST API Endpoints

### 1. Generate Study Plan
```
POST /api/study-plan/generate

Request:
{
    username: string (required),
    game_limit: integer (optional, default: all)
}

Response (201 Created):
{
    username: string,
    total_weaknesses: integer,
    study_plans_created: integer,
    priority_distribution: {
        high: integer,    // priority_score >= 0.7
        medium: integer,  // 0.3 <= priority_score < 0.7
        low: integer      // priority_score < 0.3
    }
}

Errors:
- 400: Invalid username
- 500: Generation failed
```

**Purpose:** Analyze all weaknesses and generate study plan with concepts and priorities.

### 2. Get Study Plans (Dashboard)
```
GET /api/study-plan

Query Parameters:
?username=hikaru
&status=pending|in_progress|completed (optional, default: all)
&concept_type=theory|opening|position_type (optional, filter)
&opening=sicilian_defense (optional, filter)
&sort=priority|frequency|impact (optional, default: priority)

Response (200 OK):
[
    {
        id: UUID,
        weakness_id: UUID,
        weakness_name: string,
        weakness_type: string,
        priority_score: float (0-1),
        status: string,
        affected_games: integer,
        avg_centipawn_loss: float,
        concepts: [
            {type: "theory", name: "weak_squares"},
            {type: "opening", name: "sicilian_defense"}
        ],
        marked_studied_at: timestamp (null if pending)
    }
]

Sort Options:
- priority: by priority_score DESC
- frequency: by affected_games DESC
- impact: by avg_centipawn_loss DESC
```

**Purpose:** Dashboard view of all study plans with filtering and sorting.

### 3. Mark Weakness as Studied
```
PATCH /api/study-plan/{plan_id}/mark-studied

Request:
{
    games_reviewed: [game_id, game_id, ...] (optional),
    engine_analysis_count: integer (optional)
}

Response (200 OK):
{
    id: UUID,
    weakness_id: UUID,
    status: "completed",
    marked_studied_at: timestamp,
    study_session_id: UUID
}

Errors:
- 404: Study plan not found
- 400: Invalid request
```

**Purpose:** Mark a weakness as studied, track session details.

### 4. Get Available Concepts
```
GET /api/study-plan/concepts

Query Parameters:
?concept_type=theory|opening|position_type (optional, filter)
&search=weak (optional, search by name)

Response (200 OK):
[
    {
        type: "theory",
        name: "weak_squares",
        description: "Squares that the opponent can exploit for piece placement or tactical advantage",
        example_count: 5,  // How many weaknesses map to this
        example_patterns: ["Sicilian weakness", "King safety issue"]
    }
]
```

**Purpose:** Browse available chess concepts for learning reference.

### 5. Get Study Progress
```
GET /api/study-plan/progress

Query Parameters:
?username=hikaru

Response (200 OK):
{
    total_weaknesses: integer,
    studied: integer,
    in_progress: integer,
    remaining: integer,
    completion_rate: float (0-1),
    priority_completion_rate: float (0-1),  // % of high-priority weaknesses studied
    estimated_time_to_completion: string   // e.g., "5 hours" (rough estimate)
}
```

**Purpose:** Show overall study progress and stats.

### 6. Get Games to Study for Weakness
```
GET /api/study-plan/{plan_id}/games

Query Parameters:
?include_analysis=true|false (default: true)

Response (200 OK):
[
    {
        game_id: UUID,
        date: timestamp,
        result: "win|loss|draw",
        opponent: string,
        moves_with_mistakes: integer,
        key_positions: [
            {
                move_number: integer,
                fen: string,
                player_move: string,
                best_move: string,
                centipawn_loss: integer,
                concepts: [{type, name}],
                engine_continuation: string  // e.g., "Best: Nf3 then e4"
            }
        ]
    }
]
```

**Purpose:** Get specific games to study for a weakness with engine analysis.

---

## Frontend Components

### 1. StudyPlan.jsx

**File:** `frontend/src/components/StudyPlan.jsx`

**Purpose:** Main study planning dashboard.

**State:**
```javascript
{
    username: string,
    studyPlans: array,
    filters: {
        status: 'all' | 'pending' | 'in_progress' | 'completed',
        concept_type: 'all' | 'theory' | 'opening' | 'position_type',
        opening: string,
        sort: 'priority' | 'frequency' | 'impact'
    },
    progress: {
        total: int,
        studied: int,
        in_progress: int,
        remaining: int,
        completion_rate: float
    },
    selectedPlan: object or null,
    loading: boolean,
    error: string or null
}
```

**Features:**
- Input form for username
- Generate button to create study plan
- Progress bar showing completion
- Filter + sort controls (StudyFilter sub-component)
- Study plan list (StudyCard sub-components)
- Detail view (StudyDetail sub-component)
- Mark as studied workflow

### 2. StudyFilter.jsx

**File:** `frontend/src/components/StudyFilter.jsx`

**Purpose:** Filtering and sorting controls.

**Filters:**
- Status: pending, in_progress, completed, all
- Concept type: all, theory, opening, position_type
- Opening: dropdown of user's openings
- Sort: priority, frequency, impact

### 3. StudyCard.jsx

**File:** `frontend/src/components/StudyCard.jsx`

**Purpose:** Individual weakness card for list view.

**Displays:**
- Weakness name + type
- Priority badge (high/medium/low)
- Affected games count
- Average centipawn loss
- Concept tags
- "Mark Studied" button
- "View Games" button (expands to StudyDetail)

### 4. StudyDetail.jsx

**File:** `frontend/src/components/StudyDetail.jsx`

**Purpose:** Deep-dive view when weakness is selected.

**Displays:**
- Weakness overview (name, type, frequency)
- Concept mapping (organized by theory/opening/position)
- Games affected (scrollable list)
- For each game:
  - Date, opponent, result
  - Moves with mistakes count
  - Key positions with engine analysis
  - Best move vs. actual move
  - Engine continuation
- Mark as studied button
- Progress tracking

### 5. StudyPlan.css

**File:** `frontend/src/styles/StudyPlan.css`

**Layout:**
- Main dashboard grid: filters (left) + study plans (center) + progress (right)
- Responsive: single column on mobile, 3-column on desktop
- Card styling with priority colors
- Smooth expand/collapse animations
- Progress bar visualization

**Color Scheme:**
- High priority: #ff5252 (red)
- Medium priority: #ffa726 (orange)
- Low priority: #66bb6a (green)
- Completed: #42a5f5 (blue)

---

## Data Flow

### Study Plan Generation Flow

```
User enters username and clicks "Generate Study Plan"
    ↓
POST /api/study-plan/generate {username}
    ↓
StudyPlanGenerator.generate_study_plan(username)
    ├─ Query patterns table for user
    ├─ Calculate priority_score for each: frequency / max_frequency
    ├─ For each pattern:
    │  ├─ ConceptMapper.map_weakness() → concepts
    │  ├─ Insert StudyPlan record (priority_score, status='pending')
    │  └─ Insert ConceptMap records (1:N relationship)
    ├─ Categorize by priority: high (>=0.7), medium (0.3-0.7), low (<0.3)
    └─ Return {total_weaknesses, created, priority_distribution}
    ↓
Frontend shows success message + summary
    ↓
GET /api/study-plan?username=...&sort=priority
    ↓
Display dashboard with all weaknesses, sorted by priority
```

### Study Workflow

```
User views dashboard
    ↓
Clicks on weakness card
    ↓
GET /api/study-plan/{plan_id}/games?include_analysis=true
    ↓
Display games + engine analysis
    ↓
User reviews games with engine continuations
    ↓
Clicks "Mark as Studied"
    ↓
PATCH /api/study-plan/{plan_id}/mark-studied
    ├─ Update status → 'completed'
    ├─ Set marked_studied_at timestamp
    └─ Create StudySession record
    ↓
Dashboard updates:
    ├─ Card status → 'completed'
    ├─ Progress bar updates
    └─ Completion rate increases
```

---

## Testing Strategy

### Backend Tests

**test_study_plan_generator.py:**
- Generate study plan for user with multiple patterns
- Frequency-based priority calculation
- Concept mapping for each pattern
- StudyPlan and ConceptMap record creation
- Summary statistics (total, created, distribution)

**test_concept_mapper.py:**
- Map patterns to theory concepts
- Map patterns to opening concepts
- Map patterns to position type concepts
- Hybrid mapping (all three types)
- Edge cases (unknown opening, unclassifiable position)

**test_study_plan_api.py:**
- POST /api/study-plan/generate
- GET /api/study-plan with various filters
- GET /api/study-plan?sort=priority|frequency|impact
- PATCH /api/study-plan/{id}/mark-studied
- GET /api/study-plan/concepts
- GET /api/study-plan/progress
- GET /api/study-plan/{id}/games?include_analysis=true

**Integration tests:**
- Full flow: generate → filter → view → mark studied → check progress

### Frontend Tests

**StudyPlan.jsx:**
- Load study plans for username
- Display with correct sorting
- Filter by status/concept
- Mark weakness as studied
- Update progress bar

**StudyFilter.jsx:**
- Filter controls work
- Sort options change order
- Search filters results

**StudyCard.jsx:**
- Display weakness information
- Priority badge color correct
- Concepts render properly
- Mark studied button works

**StudyDetail.jsx:**
- Games list renders
- Engine analysis displays
- Key positions show best vs. actual moves

---

## Implementation Notes

### Reuse Existing Components

- **PositionAnalyzer:** Reuse for engine continuations in game review
- **Pattern model:** Study plans reference existing patterns table
- **Game/Position models:** No changes needed, only read-only access

### Priority Score Calculation

The priority score (0-1) is calculated as:
```
priority_score = pattern.frequency / max(all frequencies for user)
```

This ensures weaknesses are prioritized by frequency:
- A weakness in 10 games gets higher priority than one in 3 games
- User focuses on breaking repetitive patterns first

### Concept Mapping Strategy

Hybrid approach combines three dimensions:
1. **Theory:** What chess concept is violated (weak squares, tactics, etc.)
2. **Opening:** Which specific opening (Sicilian, Ruy Lopez, etc.)
3. **Position:** What type of position (middlegame, rook endgame, etc.)

Example: "Weak squares in Sicilian Defense middlegames"

This helps users understand WHAT to study (concept), WHEN they encounter it (opening), and WHERE in the game (position).

---

## Success Criteria

Phase 3 is complete when:

✅ Study plans generated with frequency-based prioritization
✅ Weaknesses mapped to hybrid chess concepts
✅ Dashboard filters and sorts study plans
✅ Users can mark weaknesses as studied
✅ Progress tracking shows completion rate
✅ Engine analysis provided for games to study
✅ 6 new REST API endpoints fully functional
✅ 3 new database tables with proper indexes
✅ 4 React components implemented and responsive
✅ All tests passing (backend + frontend)
✅ No console warnings or errors
