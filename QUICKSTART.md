# Chess Analyzer - Quick Start Guide

Get the chess analyzer running in 5 minutes.

## Prerequisites

- **PostgreSQL 15+** (or Docker)
- **Python 3.12+**
- **Node.js 18+** with npm
- **Stockfish** chess engine installed (optional for now)

## Quick Setup

### 1. Start Database (Choose One)

**Option A: Docker (Recommended)**
```bash
docker run -d --name chess-db \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=chess_analyzer \
  -p 5432:5432 \
  postgres:15
```

**Option B: Local PostgreSQL**
```bash
# Ensure PostgreSQL service is running
# Database should be accessible at localhost:5432
```

### 2. Start Backend

```bash
cd /Users/User/Workspace/Python/chess_analyzer

# Option A: Using UV (fast)
uv run python -m uvicorn src.chess_analyzer.main:app --reload

# Option B: Using pip
python -m uvicorn src.chess_analyzer.main:app --reload
```

✅ Backend ready at: `http://localhost:8000`  
📖 API docs at: `http://localhost:8000/docs`

### 3. Start Frontend

In a new terminal:

```bash
cd /Users/User/Workspace/Python/chess_analyzer/frontend
npm start
```

✅ Frontend ready at: `http://localhost:3000`

### 4. Use the Application

1. Open browser to `http://localhost:3000`
2. Enter chess.com username (e.g., "hikaru", "danny", "anna_chess")
3. Click "Analyze Games"
4. Wait for analysis to complete
5. View statistics and weakness patterns

---

## Testing

### Run Backend Tests

```bash
cd /Users/User/Workspace/Python/chess_analyzer
pytest tests/ -v

# Run specific test file
pytest tests/test_game_fetcher.py -v

# Run with coverage
pytest tests/ --cov=src
```

### Test Frontend

```bash
cd frontend
npm test
```

---

## Available API Endpoints

Once backend is running, access:

- **POST** `/api/analyze` - Start analyzing games
- **GET** `/api/games` - List analyzed games
- **GET** `/api/stats` - Get player statistics
- **GET** `/api/patterns` - Get weakness patterns
- **GET** `/api/analysis/{task_id}` - Check analysis status
- **GET** `/api/study-plan` - Get study recommendations

View interactive API docs at: `http://localhost:8000/docs`

---

## Configuration

Edit `.env` file to customize:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/chess_analyzer
STOCKFISH_PATH=/usr/games/stockfish
DEBUG=True
```

---

## Troubleshooting

### Backend won't start
- Ensure PostgreSQL is running
- Check `.env` file for correct credentials
- Verify port 8000 is available

### Frontend won't start
- Delete `node_modules` and `package-lock.json`
- Run `npm install` again
- Ensure port 3000 is available

### Tests failing
- Ensure PostgreSQL is running
- Install all dependencies: `pip install -e .`
- Check Stockfish is installed (optional)

### Games not loading
- Verify chess.com username is correct (public account)
- Check API rate limits (chess.com has limits)
- Review backend logs for errors

---

## Next Steps

- Read `PHASE_1_COMPLETE.md` for full system overview
- Read `docs/superpowers/specs/2026-04-12-chess-analyzer-design.md` for architecture
- Check `tests/` for usage examples
- Explore `src/chess_analyzer/` for implementation

---

## Development

### Adding a Feature

1. Write a test in `tests/test_*.py`
2. Implement in `src/chess_analyzer/`
3. Run tests: `pytest tests/ -v`
4. Check code quality: `ruff check src/`
5. Format code: `ruff format src/`
6. Commit: `git add . && git commit -m "feat: add feature"`

### Code Quality

```bash
# Check code
ruff check src/ tests/

# Format code
ruff format src/ tests/

# Run tests
pytest tests/ -v

# Build frontend
npm run build
```

---

## Documentation

- **System Design**: `docs/superpowers/specs/2026-04-12-chess-analyzer-design.md`
- **Implementation Plan**: `docs/superpowers/plans/2026-04-12-chess-analyzer-implementation.md`
- **Completion Summary**: `PHASE_1_COMPLETE.md`
- **API Docs**: `http://localhost:8000/docs` (Swagger)

---

## Support

For issues or questions:
1. Check logs in terminal
2. Review error messages
3. Check API docs at `/docs`
4. Review test files for usage examples
5. Check git history: `git log`

---

That's it! You should now have a fully functional chess analyzer running locally.

Happy analyzing! 🎯
