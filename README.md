# CodeCraftHub

A personalized learning platform for tracking courses. Flask REST API backend + vanilla JS dashboard frontend, built for the IBM AI Developer final project.

## Stack
- Backend: Python, Flask, flask-cors (JSON file storage, no database)
- Frontend: single-file HTML/CSS/JS dashboard (generated with Bolt.new)

## Run
```bash
pip install -r requirements.txt
python app.py          # serves API on http://localhost:5001
open index.html        # dashboard (backend must be running)
```

## API
CRUD over `/api/courses` — GET, POST, PUT, DELETE — plus `/api/courses/stats` and `/api/courses/search`.
