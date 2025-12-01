-- NoteFlow Schema

-- Drop potentially pre-existing tables
DROP TABLE IF EXISTS notetags CASCADE;
DROP TABLE IF EXISTS notes CASCADE;
DROP TABLE IF EXISTS tags CASCADE;
DROP TABLE IF EXISTS userstats CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Users table
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User statistics table
CREATE TABLE userstats (
    user_id INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    total_notes INTEGER DEFAULT 0 CHECK (total_notes >= 0),
    total_active_tags INTEGER DEFAULT 0 CHECK (total_active_tags >= 0),
    last_login_date TIMESTAMP
);

-- Notes table
CREATE TABLE notes (
    note_id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL CHECK (LENGTH(title) > 0),
    content TEXT,
    status VARCHAR(20) DEFAULT 'Active' CHECK (status IN ('Active', 'Archived', 'Pinned')),
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE
);

-- Tags table
CREATE TABLE tags (
    tag_id SERIAL PRIMARY KEY,
    tag_name VARCHAR(50) UNIQUE NOT NULL CHECK (LENGTH(tag_name) >= 2),
    color VARCHAR(7) DEFAULT '#808080' CHECK (color ~* '^#[0-9A-Fa-f]{6}$'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Note-Tag junction table (many-to-many relationship)
CREATE TABLE notetags (
    notetag_id SERIAL PRIMARY KEY,
    note_id INTEGER NOT NULL REFERENCES notes(note_id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(tag_id) ON DELETE CASCADE,
    assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(note_id, tag_id)
);

-- Indexes for better query performance
CREATE INDEX idx_notes_user_id ON notes(user_id);
CREATE INDEX idx_notes_status ON notes(status);
CREATE INDEX idx_notes_last_modified ON notes(last_modified);
CREATE INDEX idx_notetags_note_id ON notetags(note_id);
CREATE INDEX idx_notetags_tag_id ON notetags(tag_id);
CREATE INDEX idx_users_email ON users(email);

-- Insert some default tags
INSERT INTO tags (tag_name, color) VALUES
    ('Work', '#FF5733'),
    ('Personal', '#33FF57'),
    ('Important', '#3357FF'),
    ('Ideas', '#F333FF'),
    ('Todo', '#FFD700');
