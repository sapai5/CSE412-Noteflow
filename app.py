# Run this before testing
# SELECT setval('users_user_id_seq', (SELECT MAX(user_id) FROM users) + 1);
# SELECT setval('notes_note_id_seq', (SELECT MAX(note_id) FROM notes) + 1);
# SELECT setval('tags_tag_id_seq', (SELECT MAX(tag_id) FROM tags) + 1);
# SELECT setval('notetags_notetag_id_seq', (SELECT MAX(notetag_id) FROM notetags) + 1);

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from functools import wraps
import psycopg
from psycopg.rows import dict_row
import bcrypt
import jwt
import os
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'notetaking'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')
}


def get_db_connection():
    """Create and return a database connection."""
    # psycopg uses 'dbname' instead of 'database'
    config = DB_CONFIG.copy()
    if 'database' in config:
        config['dbname'] = config.pop('database')
    conn = psycopg.connect(
        **config,
        row_factory=dict_row
    )
    return conn


def token_required(f):
    """Decorator to protect routes that require authentication."""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(current_user_id, *args, **kwargs)

    return decorated


# ==================== AUTH ENDPOINTS ====================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user."""
    try:
        data = request.get_json()

        required_fields = ['name', 'email', 'password']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400

        name = data['name']
        email = data['email']
        password = data['password']

        if '@' not in email:
            return jsonify({'error': 'Invalid email format'}), 400

        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute(
                """
                INSERT INTO users (name, email, password, created_at)
                VALUES (%s, %s, %s, NOW())
                RETURNING user_id, name, email, created_at
                """,
                (name, email, password_hash)
            )
            new_user = cur.fetchone()

            # Use ON CONFLICT to handle case where userstats entry might exist
            cur.execute(
                """
                INSERT INTO userstats (user_id, total_notes, total_active_tags, last_login_date)
                VALUES (%s, 0, 0, NOW())
                ON CONFLICT (user_id) DO UPDATE SET last_login_date = NOW()
                """,
                (new_user['user_id'],)
            )

            conn.commit()

            token = jwt.encode({
                'user_id': new_user['user_id'],
                'exp': datetime.utcnow() + timedelta(days=7)
            }, app.config['SECRET_KEY'], algorithm='HS256')

            return jsonify({
                'message': 'User registered successfully',
                'user': {
                    'user_id': new_user['user_id'],
                    'name': new_user['name'],
                    'email': new_user['email'],
                    'created_at': new_user['created_at'].isoformat()
                },
                'token': token
            }), 201

        except psycopg.errors.UniqueViolation as e:
            conn.rollback()
            error_msg = str(e)
            if 'email' in error_msg or 'users_email_key' in error_msg:
                return jsonify({'error': 'Email already exists'}), 409
            else:
                return jsonify({'error': f'Database conflict: {error_msg}'}), 409
        except Exception as e:
            conn.rollback()
            return jsonify({'error': f'Registration failed: {str(e)}'}), 500
        finally:
            cur.close()
            conn.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login an existing user."""
    try:
        data = request.get_json()

        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400

        email = data['email']
        password = data['password']

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()

        if not user:
            cur.close()
            conn.close()
            return jsonify({'error': 'Invalid email or password'}), 401

        if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            cur.close()
            conn.close()
            return jsonify({'error': 'Invalid email or password'}), 401

        cur.execute(
            "UPDATE userstats SET last_login_date = NOW() WHERE user_id = %s",
            (user['user_id'],)
        )
        conn.commit()

        cur.close()
        conn.close()

        token = jwt.encode({
            'user_id': user['user_id'],
            'exp': datetime.utcnow() + timedelta(days=7)
        }, app.config['SECRET_KEY'], algorithm='HS256')

        return jsonify({
            'message': 'Login successful',
            'user': {
                'user_id': user['user_id'],
                'name': user['name'],
                'email': user['email'],
                'created_at': user['created_at'].isoformat()
            },
            'token': token
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/me', methods=['GET'])
@token_required
def get_current_user(current_user_id):
    """Get current authenticated user's information."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT user_id, name, email, created_at FROM users WHERE user_id = %s",
            (current_user_id,)
        )
        user = cur.fetchone()

        cur.close()
        conn.close()

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'user': {
                'user_id': user['user_id'],
                'name': user['name'],
                'email': user['email'],
                'created_at': user['created_at'].isoformat()
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== USER ENDPOINTS ====================

@app.route('/api/users/<int:user_id>', methods=['GET'])
@token_required
def get_user(current_user_id, user_id):
    """Get user by ID."""
    if current_user_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT user_id, name, email, created_at FROM users WHERE user_id = %s",
            (user_id,)
        )
        user = cur.fetchone()

        cur.close()
        conn.close()

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'user': {
                'user_id': user['user_id'],
                'name': user['name'],
                'email': user['email'],
                'created_at': user['created_at'].isoformat()
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/users/<int:user_id>', methods=['PUT'])
@token_required
def update_user(current_user_id, user_id):
    """Update user profile."""
    if current_user_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        data = request.get_json()

        conn = get_db_connection()
        cur = conn.cursor()

        update_fields = []
        values = []

        if 'name' in data and data['name']:
            update_fields.append("name = %s")
            values.append(data['name'])

        if 'email' in data and data['email']:
            if '@' not in data['email']:
                return jsonify({'error': 'Invalid email format'}), 400
            update_fields.append("email = %s")
            values.append(data['email'])

        if 'password' in data and data['password']:
            password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            update_fields.append("password = %s")
            values.append(password_hash)

        if not update_fields:
            return jsonify({'error': 'No fields to update'}), 400

        values.append(user_id)

        cur.execute(
            f"""
            UPDATE users SET {', '.join(update_fields)}
            WHERE user_id = %s
            RETURNING user_id, name, email, created_at
            """,
            values
        )
        updated_user = cur.fetchone()
        conn.commit()

        cur.close()
        conn.close()

        return jsonify({
            'message': 'User updated successfully',
            'user': {
                'user_id': updated_user['user_id'],
                'name': updated_user['name'],
                'email': updated_user['email'],
                'created_at': updated_user['created_at'].isoformat()
            }
        }), 200

    except psycopg.errors.UniqueViolation:
        return jsonify({'error': 'Email already exists'}), 409
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@token_required
def delete_user(current_user_id, user_id):
    """Delete user account."""
    if current_user_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("DELETE FROM users WHERE user_id = %s RETURNING user_id", (user_id,))
        deleted = cur.fetchone()
        conn.commit()

        cur.close()
        conn.close()

        if not deleted:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({'message': 'User deleted successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== USER STATS ENDPOINTS ====================

@app.route('/api/users/<int:user_id>/stats', methods=['GET'])
@token_required
def get_user_stats(current_user_id, user_id):
    """Get user statistics dashboard."""
    if current_user_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM userstats WHERE user_id = %s", (user_id,))
        stats = cur.fetchone()

        cur.execute(
            """
            SELECT 
                COUNT(*) as total_notes,
                COUNT(CASE WHEN status = 'Active' THEN 1 END) as active_notes,
                COUNT(CASE WHEN status = 'Pinned' THEN 1 END) as pinned_notes,
                COUNT(CASE WHEN status = 'Archived' THEN 1 END) as archived_notes
            FROM notes WHERE user_id = %s
            """,
            (user_id,)
        )
        note_stats = cur.fetchone()

        cur.execute(
            """
            SELECT COUNT(DISTINCT nt.tag_id) as active_tags
            FROM notetags nt
            JOIN notes n ON nt.note_id = n.note_id
            WHERE n.user_id = %s
            """,
            (user_id,)
        )
        tag_stats = cur.fetchone()

        cur.close()
        conn.close()

        if not stats:
            return jsonify({'error': 'Stats not found'}), 404

        return jsonify({
            'stats': {
                'user_id': stats['user_id'],
                'total_notes': note_stats['total_notes'],
                'active_notes': note_stats['active_notes'],
                'pinned_notes': note_stats['pinned_notes'],
                'archived_notes': note_stats['archived_notes'],
                'total_active_tags': tag_stats['active_tags'],
                'last_login_date': stats['last_login_date'].isoformat() if stats['last_login_date'] else None
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def update_user_stats(cur, user_id):
    """Helper function to update user statistics."""
    cur.execute("SELECT COUNT(*) as count FROM notes WHERE user_id = %s", (user_id,))
    total_notes = cur.fetchone()['count']

    cur.execute(
        """
        SELECT COUNT(DISTINCT nt.tag_id) as count
        FROM notetags nt
        JOIN notes n ON nt.note_id = n.note_id
        WHERE n.user_id = %s
        """,
        (user_id,)
    )
    total_active_tags = cur.fetchone()['count']

    cur.execute(
        """
        UPDATE userstats 
        SET total_notes = %s, total_active_tags = %s
        WHERE user_id = %s
        """,
        (total_notes, total_active_tags, user_id)
    )


# ==================== NOTES ENDPOINTS ====================

@app.route('/api/notes', methods=['GET'])
@token_required
def get_notes(current_user_id):
    """Get all notes for the current user with optional filtering."""
    try:
        status = request.args.get('status')
        tag_id = request.args.get('tag_id')
        search = request.args.get('search')
        sort_by = request.args.get('sort_by', 'last_modified')
        order = request.args.get('order', 'desc')

        conn = get_db_connection()
        cur = conn.cursor()

        query = """
            SELECT DISTINCT n.note_id, n.title, n.content, n.status, 
                   n.created_date, n.last_modified, n.user_id
            FROM notes n
            LEFT JOIN notetags nt ON n.note_id = nt.note_id
            WHERE n.user_id = %s
        """
        params = [current_user_id]

        if status:
            query += " AND n.status = %s"
            params.append(status)

        if tag_id:
            query += " AND nt.tag_id = %s"
            params.append(tag_id)

        if search:
            query += " AND (n.title ILIKE %s OR n.content ILIKE %s)"
            search_param = f'%{search}%'
            params.extend([search_param, search_param])

        valid_sort_fields = ['created_date', 'last_modified', 'title']
        if sort_by not in valid_sort_fields:
            sort_by = 'last_modified'

        order = 'DESC' if order.lower() == 'desc' else 'ASC'
        query += f" ORDER BY n.{sort_by} {order}"

        cur.execute(query, params)
        notes = cur.fetchall()

        notes_list = []
        for note in notes:
            cur.execute(
                """
                SELECT t.tag_id, t.tag_name, t.color
                FROM tags t
                JOIN notetags nt ON t.tag_id = nt.tag_id
                WHERE nt.note_id = %s
                """,
                (note['note_id'],)
            )
            tags = cur.fetchall()

            notes_list.append({
                'note_id': note['note_id'],
                'title': note['title'],
                'content': note['content'],
                'status': note['status'],
                'created_date': note['created_date'].isoformat(),
                'last_modified': note['last_modified'].isoformat(),
                'user_id': note['user_id'],
                'tags': [{'tag_id': t['tag_id'], 'tag_name': t['tag_name'], 'color': t['color']} for t in tags]
            })

        cur.close()
        conn.close()

        return jsonify({'notes': notes_list}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notes/<int:note_id>', methods=['GET'])
@token_required
def get_note(current_user_id, note_id):
    """Get a specific note by ID."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT note_id, title, content, status, created_date, last_modified, user_id
            FROM notes WHERE note_id = %s AND user_id = %s
            """,
            (note_id, current_user_id)
        )
        note = cur.fetchone()

        if not note:
            cur.close()
            conn.close()
            return jsonify({'error': 'Note not found'}), 404

        cur.execute(
            """
            SELECT t.tag_id, t.tag_name, t.color
            FROM tags t
            JOIN notetags nt ON t.tag_id = nt.tag_id
            WHERE nt.note_id = %s
            """,
            (note_id,)
        )
        tags = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify({
            'note': {
                'note_id': note['note_id'],
                'title': note['title'],
                'content': note['content'],
                'status': note['status'],
                'created_date': note['created_date'].isoformat(),
                'last_modified': note['last_modified'].isoformat(),
                'user_id': note['user_id'],
                'tags': [{'tag_id': t['tag_id'], 'tag_name': t['tag_name'], 'color': t['color']} for t in tags]
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notes', methods=['POST'])
@token_required
def create_note(current_user_id):
    """Create a new note."""
    try:
        data = request.get_json()

        if not data.get('title'):
            return jsonify({'error': 'Title is required'}), 400

        title = data['title']
        content = data.get('content', '')
        status = data.get('status', 'Active')
        tag_ids = data.get('tag_ids', [])

        valid_statuses = ['Active', 'Archived', 'Pinned']
        if status not in valid_statuses:
            return jsonify({'error': f'Status must be one of: {", ".join(valid_statuses)}'}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO notes (title, content, status, user_id, created_date, last_modified)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            RETURNING note_id, title, content, status, created_date, last_modified, user_id
            """,
            (title, content, status, current_user_id)
        )
        new_note = cur.fetchone()

        tags = []
        for tag_id in tag_ids:
            try:
                cur.execute(
                    """
                    INSERT INTO notetags (note_id, tag_id, assigned_date)
                    VALUES (%s, %s, NOW())
                    """,
                    (new_note['note_id'], tag_id)
                )
                cur.execute("SELECT tag_id, tag_name, color FROM tags WHERE tag_id = %s", (tag_id,))
                tag = cur.fetchone()
                if tag:
                    tags.append({'tag_id': tag['tag_id'], 'tag_name': tag['tag_name'], 'color': tag['color']})
            except psycopg.errors.ForeignKeyViolation:
                conn.rollback()
                return jsonify({'error': f'Tag with id {tag_id} does not exist'}), 400

        update_user_stats(cur, current_user_id)

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            'message': 'Note created successfully',
            'note': {
                'note_id': new_note['note_id'],
                'title': new_note['title'],
                'content': new_note['content'],
                'status': new_note['status'],
                'created_date': new_note['created_date'].isoformat(),
                'last_modified': new_note['last_modified'].isoformat(),
                'user_id': new_note['user_id'],
                'tags': tags
            }
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notes/<int:note_id>', methods=['PUT'])
@token_required
def update_note(current_user_id, note_id):
    """Update an existing note."""
    try:
        data = request.get_json()

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT note_id FROM notes WHERE note_id = %s AND user_id = %s",
            (note_id, current_user_id)
        )
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({'error': 'Note not found'}), 404

        update_fields = ["last_modified = NOW()"]
        values = []

        if 'title' in data:
            if not data['title']:
                return jsonify({'error': 'Title cannot be empty'}), 400
            update_fields.append("title = %s")
            values.append(data['title'])

        if 'content' in data:
            update_fields.append("content = %s")
            values.append(data['content'])

        if 'status' in data:
            valid_statuses = ['Active', 'Archived', 'Pinned']
            if data['status'] not in valid_statuses:
                return jsonify({'error': f'Status must be one of: {", ".join(valid_statuses)}'}), 400
            update_fields.append("status = %s")
            values.append(data['status'])

        values.append(note_id)

        cur.execute(
            f"""
            UPDATE notes SET {', '.join(update_fields)}
            WHERE note_id = %s
            RETURNING note_id, title, content, status, created_date, last_modified, user_id
            """,
            values
        )
        updated_note = cur.fetchone()

        if 'tag_ids' in data:
            cur.execute("DELETE FROM notetags WHERE note_id = %s", (note_id,))

            for tag_id in data['tag_ids']:
                try:
                    cur.execute(
                        """
                        INSERT INTO notetags (note_id, tag_id, assigned_date)
                        VALUES (%s, %s, NOW())
                        """,
                        (note_id, tag_id)
                    )
                except psycopg.errors.ForeignKeyViolation:
                    conn.rollback()
                    return jsonify({'error': f'Tag with id {tag_id} does not exist'}), 400

        cur.execute(
            """
            SELECT t.tag_id, t.tag_name, t.color
            FROM tags t
            JOIN notetags nt ON t.tag_id = nt.tag_id
            WHERE nt.note_id = %s
            """,
            (note_id,)
        )
        tags = cur.fetchall()

        update_user_stats(cur, current_user_id)

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            'message': 'Note updated successfully',
            'note': {
                'note_id': updated_note['note_id'],
                'title': updated_note['title'],
                'content': updated_note['content'],
                'status': updated_note['status'],
                'created_date': updated_note['created_date'].isoformat(),
                'last_modified': updated_note['last_modified'].isoformat(),
                'user_id': updated_note['user_id'],
                'tags': [{'tag_id': t['tag_id'], 'tag_name': t['tag_name'], 'color': t['color']} for t in tags]
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notes/<int:note_id>/status', methods=['PATCH'])
@token_required
def update_note_status(current_user_id, note_id):
    """Update note status (pin/archive/activate)."""
    try:
        data = request.get_json()

        if 'status' not in data:
            return jsonify({'error': 'Status is required'}), 400

        status = data['status']
        valid_statuses = ['Active', 'Archived', 'Pinned']
        if status not in valid_statuses:
            return jsonify({'error': f'Status must be one of: {", ".join(valid_statuses)}'}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE notes SET status = %s, last_modified = NOW()
            WHERE note_id = %s AND user_id = %s
            RETURNING note_id, title, status, last_modified
            """,
            (status, note_id, current_user_id)
        )
        updated_note = cur.fetchone()

        if not updated_note:
            cur.close()
            conn.close()
            return jsonify({'error': 'Note not found'}), 404

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            'message': f'Note status updated to {status}',
            'note': {
                'note_id': updated_note['note_id'],
                'title': updated_note['title'],
                'status': updated_note['status'],
                'last_modified': updated_note['last_modified'].isoformat()
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notes/<int:note_id>', methods=['DELETE'])
@token_required
def delete_note(current_user_id, note_id):
    """Delete a note."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "DELETE FROM notes WHERE note_id = %s AND user_id = %s RETURNING note_id",
            (note_id, current_user_id)
        )
        deleted = cur.fetchone()

        if not deleted:
            cur.close()
            conn.close()
            return jsonify({'error': 'Note not found'}), 404

        update_user_stats(cur, current_user_id)

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'message': 'Note deleted successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== TAGS ENDPOINTS ====================

@app.route('/api/tags', methods=['GET'])
@token_required
def get_tags(current_user_id):
    """Get all available tags."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT tag_id, tag_name, color, created_at
            FROM tags
            ORDER BY tag_name
            """
        )
        tags = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify({
            'tags': [{
                'tag_id': t['tag_id'],
                'tag_name': t['tag_name'],
                'color': t['color'],
                'created_at': t['created_at'].isoformat()
            } for t in tags]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tags/<int:tag_id>', methods=['GET'])
@token_required
def get_tag(current_user_id, tag_id):
    """Get a specific tag by ID."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT tag_id, tag_name, color, created_at FROM tags WHERE tag_id = %s",
            (tag_id,)
        )
        tag = cur.fetchone()

        cur.close()
        conn.close()

        if not tag:
            return jsonify({'error': 'Tag not found'}), 404

        return jsonify({
            'tag': {
                'tag_id': tag['tag_id'],
                'tag_name': tag['tag_name'],
                'color': tag['color'],
                'created_at': tag['created_at'].isoformat()
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tags', methods=['POST'])
@token_required
def create_tag(current_user_id):
    """Create a new tag."""
    try:
        data = request.get_json()

        if not data.get('tag_name'):
            return jsonify({'error': 'Tag name is required'}), 400

        tag_name = data['tag_name']
        color = data.get('color', '#808080')

        if len(tag_name) < 2:
            return jsonify({'error': 'Tag name must be at least 2 characters long'}), 400

        if not re.match(r'^#[0-9A-Fa-f]{6}$', color):
            return jsonify({'error': 'Color must be in hex format (e.g., #FF5733)'}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute(
                """
                INSERT INTO tags (tag_name, color, created_at)
                VALUES (%s, %s, NOW())
                RETURNING tag_id, tag_name, color, created_at
                """,
                (tag_name, color)
            )
            new_tag = cur.fetchone()
            conn.commit()

            cur.close()
            conn.close()

            return jsonify({
                'message': 'Tag created successfully',
                'tag': {
                    'tag_id': new_tag['tag_id'],
                    'tag_name': new_tag['tag_name'],
                    'color': new_tag['color'],
                    'created_at': new_tag['created_at'].isoformat()
                }
            }), 201

        except psycopg.errors.UniqueViolation:
            conn.rollback()
            return jsonify({'error': 'Tag name already exists'}), 409

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tags/<int:tag_id>', methods=['PUT'])
@token_required
def update_tag(current_user_id, tag_id):
    """Update a tag."""
    try:
        data = request.get_json()

        conn = get_db_connection()
        cur = conn.cursor()

        update_fields = []
        values = []

        if 'tag_name' in data:
            if len(data['tag_name']) < 2:
                return jsonify({'error': 'Tag name must be at least 2 characters long'}), 400
            update_fields.append("tag_name = %s")
            values.append(data['tag_name'])

        if 'color' in data:
            if not re.match(r'^#[0-9A-Fa-f]{6}$', data['color']):
                return jsonify({'error': 'Color must be in hex format (e.g., #FF5733)'}), 400
            update_fields.append("color = %s")
            values.append(data['color'])

        if not update_fields:
            return jsonify({'error': 'No fields to update'}), 400

        values.append(tag_id)

        try:
            cur.execute(
                f"""
                UPDATE tags SET {', '.join(update_fields)}
                WHERE tag_id = %s
                RETURNING tag_id, tag_name, color, created_at
                """,
                values
            )
            updated_tag = cur.fetchone()

            if not updated_tag:
                cur.close()
                conn.close()
                return jsonify({'error': 'Tag not found'}), 404

            conn.commit()
            cur.close()
            conn.close()

            return jsonify({
                'message': 'Tag updated successfully',
                'tag': {
                    'tag_id': updated_tag['tag_id'],
                    'tag_name': updated_tag['tag_name'],
                    'color': updated_tag['color'],
                    'created_at': updated_tag['created_at'].isoformat()
                }
            }), 200

        except psycopg.errors.UniqueViolation:
            conn.rollback()
            return jsonify({'error': 'Tag name already exists'}), 409

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tags/<int:tag_id>', methods=['DELETE'])
@token_required
def delete_tag(current_user_id, tag_id):
    """Delete a tag."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("DELETE FROM tags WHERE tag_id = %s RETURNING tag_id", (tag_id,))
        deleted = cur.fetchone()

        if not deleted:
            cur.close()
            conn.close()
            return jsonify({'error': 'Tag not found'}), 404

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'message': 'Tag deleted successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== NOTE-TAG ASSOCIATION ENDPOINTS ====================

@app.route('/api/notes/<int:note_id>/tags', methods=['GET'])
@token_required
def get_note_tags(current_user_id, note_id):
    """Get all tags for a specific note."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT note_id FROM notes WHERE note_id = %s AND user_id = %s",
            (note_id, current_user_id)
        )
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({'error': 'Note not found'}), 404

        cur.execute(
            """
            SELECT t.tag_id, t.tag_name, t.color, nt.assigned_date
            FROM tags t
            JOIN notetags nt ON t.tag_id = nt.tag_id
            WHERE nt.note_id = %s
            ORDER BY t.tag_name
            """,
            (note_id,)
        )
        tags = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify({
            'tags': [{
                'tag_id': t['tag_id'],
                'tag_name': t['tag_name'],
                'color': t['color'],
                'assigned_date': t['assigned_date'].isoformat()
            } for t in tags]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notes/<int:note_id>/tags/<int:tag_id>', methods=['POST'])
@token_required
def add_tag_to_note(current_user_id, note_id, tag_id):
    """Add a tag to a note."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT note_id FROM notes WHERE note_id = %s AND user_id = %s",
            (note_id, current_user_id)
        )
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({'error': 'Note not found'}), 404

        cur.execute("SELECT tag_id FROM tags WHERE tag_id = %s", (tag_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({'error': 'Tag not found'}), 404

        try:
            cur.execute(
                """
                INSERT INTO notetags (note_id, tag_id, assigned_date)
                VALUES (%s, %s, NOW())
                RETURNING notetag_id, note_id, tag_id, assigned_date
                """,
                (note_id, tag_id)
            )
            new_notetag = cur.fetchone()

            update_user_stats(cur, current_user_id)

            conn.commit()

            cur.close()
            conn.close()

            return jsonify({
                'message': 'Tag added to note successfully',
                'notetag': {
                    'notetag_id': new_notetag['notetag_id'],
                    'note_id': new_notetag['note_id'],
                    'tag_id': new_notetag['tag_id'],
                    'assigned_date': new_notetag['assigned_date'].isoformat()
                }
            }), 201

        except psycopg.errors.UniqueViolation:
            conn.rollback()
            return jsonify({'error': 'Tag is already assigned to this note'}), 409

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notes/<int:note_id>/tags/<int:tag_id>', methods=['DELETE'])
@token_required
def remove_tag_from_note(current_user_id, note_id, tag_id):
    """Remove a tag from a note."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT note_id FROM notes WHERE note_id = %s AND user_id = %s",
            (note_id, current_user_id)
        )
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({'error': 'Note not found'}), 404

        cur.execute(
            "DELETE FROM notetags WHERE note_id = %s AND tag_id = %s RETURNING notetag_id",
            (note_id, tag_id)
        )
        deleted = cur.fetchone()

        if not deleted:
            cur.close()
            conn.close()
            return jsonify({'error': 'Tag association not found'}), 404

        update_user_stats(cur, current_user_id)

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'message': 'Tag removed from note successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tags/<int:tag_id>/notes', methods=['GET'])
@token_required
def get_notes_by_tag(current_user_id, tag_id):
    """Get all notes that have a specific tag."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT n.note_id, n.title, n.content, n.status, 
                   n.created_date, n.last_modified, n.user_id
            FROM notes n
            JOIN notetags nt ON n.note_id = nt.note_id
            WHERE nt.tag_id = %s AND n.user_id = %s
            ORDER BY n.last_modified DESC
            """,
            (tag_id, current_user_id)
        )
        notes = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify({
            'notes': [{
                'note_id': n['note_id'],
                'title': n['title'],
                'content': n['content'],
                'status': n['status'],
                'created_date': n['created_date'].isoformat(),
                'last_modified': n['last_modified'].isoformat(),
                'user_id': n['user_id']
            } for n in notes]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== SEARCH ENDPOINT ====================

@app.route('/api/search', methods=['GET'])
@token_required
def search_notes(current_user_id):
    """Search notes by title and content."""
    try:
        query = request.args.get('q', '')

        if not query:
            return jsonify({'error': 'Search query is required'}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        search_param = f'%{query}%'
        cur.execute(
            """
            SELECT DISTINCT n.note_id, n.title, n.content, n.status, 
                   n.created_date, n.last_modified, n.user_id
            FROM notes n
            WHERE n.user_id = %s AND (n.title ILIKE %s OR n.content ILIKE %s)
            ORDER BY n.last_modified DESC
            """,
            (current_user_id, search_param, search_param)
        )
        notes = cur.fetchall()

        notes_list = []
        for note in notes:
            cur.execute(
                """
                SELECT t.tag_id, t.tag_name, t.color
                FROM tags t
                JOIN notetags nt ON t.tag_id = nt.tag_id
                WHERE nt.note_id = %s
                """,
                (note['note_id'],)
            )
            tags = cur.fetchall()

            notes_list.append({
                'note_id': note['note_id'],
                'title': note['title'],
                'content': note['content'],
                'status': note['status'],
                'created_date': note['created_date'].isoformat(),
                'last_modified': note['last_modified'].isoformat(),
                'user_id': note['user_id'],
                'tags': [{'tag_id': t['tag_id'], 'tag_name': t['tag_name'], 'color': t['color']} for t in tags]
            })

        cur.close()
        conn.close()

        return jsonify({
            'query': query,
            'count': len(notes_list),
            'notes': notes_list
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== WEB INTERFACE ====================

@app.route('/')
def index():
    """Serve the web interface."""
    return render_template('index.html')


# ==================== HEALTH CHECK ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return jsonify({'status': 'healthy', 'database': 'connected'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'database': 'disconnected', 'error': str(e)}), 500


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Resource not found'}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)