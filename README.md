# AI Document Processor

Full-stack document processing scaffold built with Flask, EasyOCR, and a React/Vite frontend.

## Stack

- Backend: Flask, SQLAlchemy, EasyOCR, OpenCV, PyMuPDF, Pillow, openpyxl
- Frontend: React 18, Vite, Tailwind CSS, react-dropzone, react-zoom-pan-pinch, TanStack Table, Recharts, react-hot-toast

## Quick Start

1. Copy `.env.example` to `.env` and set `LLM_PROVIDER`, `LLM_MODEL`, and `LLM_API_KEY`.
2. Install backend dependencies from `backend/requirements.txt`.
3. From `frontend/`, run `npm install` and `npm run dev`.
4. Run the Flask app from `backend/app.py`.

## Key Endpoints

- `POST /api/upload`
- `POST /api/upload/batch`
- `POST /api/classify`
- `POST /api/extract`
- `GET /api/documents`
- `GET /api/documents/<id>`
- `POST /api/export`
- `GET /api/batch/<id>/status`
- `GET /api/stats`
- `GET /api/health`
