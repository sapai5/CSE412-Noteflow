# NoteFlow - Note-Taking Application

A full-stack note-taking application built with Flask and PostgreSQL, featuring user authentication, tagging system, and a real-time statistics dashboard.

## Overview

NoteFlow helps users create, organize, and manage notes efficiently. Users can pin important notes, archive old ones, and categorize them with color-coded tags for easy retrieval.

## Tech Stack

- **Backend:** Python, Flask
- **Database:** PostgreSQL
- **Authentication:** JWT (JSON Web Tokens), bcrypt
- **Frontend:** HTML, CSS, JavaScript

## Features

- **User Authentication** - Secure registration/login with JWT tokens
- **Notes Management** - Create, read, update, delete notes
- **Note Status** - Pin, archive, or activate notes
- **Tagging System** - Color-coded tags with many-to-many relationships
- **Search** - Search notes by title and content
- **Filtering** - Filter notes by status, tags, or date
- **User Dashboard** - Real-time statistics (total notes, active tags, etc.)
- **Data Integrity** - CASCADE deletes, check constraints, parameterized queries

## Database Schema

- **users** - User accounts with bcrypt-hashed passwords
- **userstats** - Dashboard statistics per user
- **notes** - Notes with status (Active/Pinned/Archived)
- **tags** - Color-coded tags for categorization
- **notetags** - Junction table for note-tag associations

## Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL 12+

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/noteflow.git
cd noteflow

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install Flask Flask-CORS psycopg2-binary bcrypt PyJWT python-dotenv

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Run the server
python app.py
```

### Environment Variables

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=notetaking
DB_USER=postgres
DB_PASSWORD=your_password
SECRET_KEY=your_jwt_secret
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login user |
| GET | `/api/auth/me` | Get current user |

### Notes
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/notes` | Get all notes (filterable) |
| GET | `/api/notes/:id` | Get single note |
| POST | `/api/notes` | Create note |
| PUT | `/api/notes/:id` | Update note |
| PATCH | `/api/notes/:id/status` | Pin/Archive/Activate |
| DELETE | `/api/notes/:id` | Delete note |

### Tags
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tags` | Get all tags |
| POST | `/api/tags` | Create tag |
| PUT | `/api/tags/:id` | Update tag |
| DELETE | `/api/tags/:id` | Delete tag |

### Note-Tag Associations
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/notes/:id/tags/:tagId` | Add tag to note |
| DELETE | `/api/notes/:id/tags/:tagId` | Remove tag |

### Other
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users/:id/stats` | User dashboard stats |
| GET | `/api/search?q=query` | Search notes |
| GET | `/api/health` | Health check |

## Testing

```bash
# Run test suite
python DBtestConnection.py
python app.py
python apiTest.py
# If this doesn't work
python app.py
python debug_api.py
```

## Team

- Sahil Pai
- Brandon Lim
- Saahir Khan
- Sourish Tiwari

