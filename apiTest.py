import requests
import json
import sys

BASE_URL = "http://localhost:5000/api"

# Global variables to store test data
token = None
user_id = None
note_id = None
tag_id = None
test_user_email = None


def print_result(test_name, success, response=None):
    """Print test result."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {test_name}")
    if not success and response:
        print(f"       Status: {response.status_code}")
        try:
            print(f"       Response: {response.json()}")
        except:
            print(f"       Response: {response.text}")


def get_headers():
    """Get headers with auth token."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


# ==================== HEALTH CHECK ====================

def test_health():
    """Test health check endpoint."""
    try:
        r = requests.get(f"{BASE_URL}/health")
        success = r.status_code == 200 and r.json().get('status') == 'healthy'
        print_result("Health Check", success, r)
        return success
    except requests.exceptions.ConnectionError:
        print("❌ FAIL - Health Check")
        print("       Could not connect to server. Is it running on localhost:5000?")
        return False


# ==================== AUTH TESTS ====================

def test_register():
    """Test user registration."""
    global token, user_id

    import time
    test_email = f"testuser_{int(time.time())}@example.com"

    data = {
        "name": "Test User",
        "email": test_email,
        "password": "testpass123"
    }

    # Store email globally for login test
    global test_user_email
    test_user_email = test_email

    r = requests.post(f"{BASE_URL}/auth/register", json=data)

    if r.status_code == 201:
        result = r.json()
        token = result.get('token')
        user_id = result.get('user', {}).get('user_id')
        print_result("Register User", True)
        return True
    elif r.status_code == 409:
        # Unlikely with timestamp email, but handle it
        print_result("Register User (email conflict - try again)", False, r)
        return False
    else:
        print_result("Register User", False, r)
        return False


def test_login():
    """Test user login."""
    global token, user_id

    data = {
        "email": test_user_email,
        "password": "testpass123"
    }

    r = requests.post(f"{BASE_URL}/auth/login", json=data)

    if r.status_code == 200:
        result = r.json()
        token = result.get('token')
        user_id = result.get('user', {}).get('user_id')
        print_result("Login User", True)
        return True
    else:
        print_result("Login User", False, r)
        return False


def test_login_wrong_password():
    """Test login with wrong password."""
    data = {
        "email": test_user_email if test_user_email else "fake@example.com",
        "password": "wrongpassword"
    }

    r = requests.post(f"{BASE_URL}/auth/login", json=data)
    success = r.status_code == 401
    print_result("Login Wrong Password (should fail)", success, r if not success else None)
    return success


def test_get_current_user():
    """Test get current user."""
    r = requests.get(f"{BASE_URL}/auth/me", headers=get_headers())
    success = r.status_code == 200 and 'user' in r.json()
    print_result("Get Current User", success, r if not success else None)
    return success


def test_protected_without_token():
    """Test accessing protected route without token."""
    r = requests.get(f"{BASE_URL}/auth/me")
    success = r.status_code == 401
    print_result("Protected Route Without Token (should fail)", success, r if not success else None)
    return success


# ==================== USER TESTS ====================

def test_get_user():
    """Test get user by ID."""
    r = requests.get(f"{BASE_URL}/users/{user_id}", headers=get_headers())
    success = r.status_code == 200
    print_result("Get User", success, r if not success else None)
    return success


def test_get_user_stats():
    """Test get user stats."""
    r = requests.get(f"{BASE_URL}/users/{user_id}/stats", headers=get_headers())
    success = r.status_code == 200 and 'stats' in r.json()
    print_result("Get User Stats", success, r if not success else None)
    return success


def test_update_user():
    """Test update user."""
    data = {"name": "Updated Test User"}
    r = requests.put(f"{BASE_URL}/users/{user_id}", json=data, headers=get_headers())
    success = r.status_code == 200
    print_result("Update User", success, r if not success else None)
    return success


# ==================== TAG TESTS ====================

def test_create_tag():
    """Test create tag."""
    global tag_id

    data = {
        "tag_name": "test-tag",
        "color": "#FF5733"
    }

    r = requests.post(f"{BASE_URL}/tags", json=data, headers=get_headers())

    if r.status_code == 201:
        tag_id = r.json().get('tag', {}).get('tag_id')
        print_result("Create Tag", True)
        return True
    elif r.status_code == 409:
        # Tag exists, get it
        print_result("Create Tag (already exists)", True)
        r2 = requests.get(f"{BASE_URL}/tags", headers=get_headers())
        if r2.status_code == 200:
            tags = r2.json().get('tags', [])
            for t in tags:
                if t['tag_name'] == 'test-tag':
                    tag_id = t['tag_id']
                    break
            if not tag_id and tags:
                tag_id = tags[0]['tag_id']
        return True
    else:
        print_result("Create Tag", False, r)
        return False


def test_get_tags():
    """Test get all tags."""
    r = requests.get(f"{BASE_URL}/tags", headers=get_headers())
    success = r.status_code == 200 and 'tags' in r.json()
    print_result("Get All Tags", success, r if not success else None)
    return success


def test_get_tag():
    """Test get single tag."""
    if not tag_id:
        print_result("Get Single Tag", False)
        return False

    r = requests.get(f"{BASE_URL}/tags/{tag_id}", headers=get_headers())
    success = r.status_code == 200
    print_result("Get Single Tag", success, r if not success else None)
    return success


def test_update_tag():
    """Test update tag."""
    if not tag_id:
        print_result("Update Tag", False)
        return False

    data = {"color": "#00FF00"}
    r = requests.put(f"{BASE_URL}/tags/{tag_id}", json=data, headers=get_headers())
    success = r.status_code == 200
    print_result("Update Tag", success, r if not success else None)
    return success


def test_create_tag_invalid_color():
    """Test create tag with invalid color."""
    data = {
        "tag_name": "invalid-tag",
        "color": "not-a-color"
    }
    r = requests.post(f"{BASE_URL}/tags", json=data, headers=get_headers())
    success = r.status_code == 400
    print_result("Create Tag Invalid Color (should fail)", success, r if not success else None)
    return success


def test_create_tag_short_name():
    """Test create tag with short name."""
    data = {
        "tag_name": "a",
        "color": "#FF5733"
    }
    r = requests.post(f"{BASE_URL}/tags", json=data, headers=get_headers())
    success = r.status_code == 400
    print_result("Create Tag Short Name (should fail)", success, r if not success else None)
    return success


# ==================== NOTE TESTS ====================

def test_create_note():
    """Test create note."""
    global note_id

    data = {
        "title": "Test Note",
        "content": "This is test content",
        "status": "Active"
    }

    if tag_id:
        data["tag_ids"] = [tag_id]

    r = requests.post(f"{BASE_URL}/notes", json=data, headers=get_headers())

    if r.status_code == 201:
        note_id = r.json().get('note', {}).get('note_id')
        print_result("Create Note", True)
        return True
    else:
        print_result("Create Note", False, r)
        return False


def test_create_note_no_title():
    """Test create note without title."""
    data = {
        "content": "Content without title"
    }
    r = requests.post(f"{BASE_URL}/notes", json=data, headers=get_headers())
    success = r.status_code == 400
    print_result("Create Note No Title (should fail)", success, r if not success else None)
    return success


def test_create_note_invalid_status():
    """Test create note with invalid status."""
    data = {
        "title": "Test",
        "status": "InvalidStatus"
    }
    r = requests.post(f"{BASE_URL}/notes", json=data, headers=get_headers())
    success = r.status_code == 400
    print_result("Create Note Invalid Status (should fail)", success, r if not success else None)
    return success


def test_get_notes():
    """Test get all notes."""
    r = requests.get(f"{BASE_URL}/notes", headers=get_headers())
    success = r.status_code == 200 and 'notes' in r.json()
    print_result("Get All Notes", success, r if not success else None)
    return success


def test_get_notes_filtered():
    """Test get notes with filters."""
    r = requests.get(f"{BASE_URL}/notes?status=Active&sort_by=last_modified&order=desc", headers=get_headers())
    success = r.status_code == 200
    print_result("Get Notes Filtered", success, r if not success else None)
    return success


def test_get_note():
    """Test get single note."""
    if not note_id:
        print_result("Get Single Note", False)
        return False

    r = requests.get(f"{BASE_URL}/notes/{note_id}", headers=get_headers())
    success = r.status_code == 200 and 'note' in r.json()
    print_result("Get Single Note", success, r if not success else None)
    return success


def test_update_note():
    """Test update note."""
    if not note_id:
        print_result("Update Note", False)
        return False

    data = {
        "title": "Updated Test Note",
        "content": "Updated content"
    }
    r = requests.put(f"{BASE_URL}/notes/{note_id}", json=data, headers=get_headers())
    success = r.status_code == 200
    print_result("Update Note", success, r if not success else None)
    return success


def test_update_note_status_pinned():
    """Test pin note."""
    if not note_id:
        print_result("Pin Note", False)
        return False

    data = {"status": "Pinned"}
    r = requests.patch(f"{BASE_URL}/notes/{note_id}/status", json=data, headers=get_headers())
    success = r.status_code == 200
    print_result("Pin Note", success, r if not success else None)
    return success


def test_update_note_status_archived():
    """Test archive note."""
    if not note_id:
        print_result("Archive Note", False)
        return False

    data = {"status": "Archived"}
    r = requests.patch(f"{BASE_URL}/notes/{note_id}/status", json=data, headers=get_headers())
    success = r.status_code == 200
    print_result("Archive Note", success, r if not success else None)
    return success


def test_update_note_status_active():
    """Test activate note."""
    if not note_id:
        print_result("Activate Note", False)
        return False

    data = {"status": "Active"}
    r = requests.patch(f"{BASE_URL}/notes/{note_id}/status", json=data, headers=get_headers())
    success = r.status_code == 200
    print_result("Activate Note", success, r if not success else None)
    return success


# ==================== NOTE-TAG ASSOCIATION TESTS ====================

def test_get_note_tags():
    """Test get tags for a note."""
    if not note_id:
        print_result("Get Note Tags", False)
        return False

    r = requests.get(f"{BASE_URL}/notes/{note_id}/tags", headers=get_headers())
    success = r.status_code == 200 and 'tags' in r.json()
    print_result("Get Note Tags", success, r if not success else None)
    return success


def test_add_tag_to_note():
    """Test add tag to note."""
    if not note_id or not tag_id:
        print_result("Add Tag to Note", False)
        return False

    r = requests.post(f"{BASE_URL}/notes/{note_id}/tags/{tag_id}", headers=get_headers())
    success = r.status_code in [201, 409]  # 409 if already exists
    print_result("Add Tag to Note", success, r if not success else None)
    return success


def test_get_notes_by_tag():
    """Test get notes by tag."""
    if not tag_id:
        print_result("Get Notes by Tag", False)
        return False

    r = requests.get(f"{BASE_URL}/tags/{tag_id}/notes", headers=get_headers())
    success = r.status_code == 200 and 'notes' in r.json()
    print_result("Get Notes by Tag", success, r if not success else None)
    return success


def test_remove_tag_from_note():
    """Test remove tag from note."""
    if not note_id or not tag_id:
        print_result("Remove Tag from Note", False)
        return False

    r = requests.delete(f"{BASE_URL}/notes/{note_id}/tags/{tag_id}", headers=get_headers())
    success = r.status_code in [200, 404]  # 404 if not exists
    print_result("Remove Tag from Note", success, r if not success else None)
    return success


# ==================== SEARCH TESTS ====================

def test_search_notes():
    """Test search notes."""
    r = requests.get(f"{BASE_URL}/search?q=test", headers=get_headers())
    success = r.status_code == 200 and 'notes' in r.json()
    print_result("Search Notes", success, r if not success else None)
    return success


def test_search_notes_no_query():
    """Test search without query."""
    r = requests.get(f"{BASE_URL}/search", headers=get_headers())
    success = r.status_code == 400
    print_result("Search No Query (should fail)", success, r if not success else None)
    return success


# ==================== CLEANUP TESTS ====================

def test_delete_note():
    """Test delete note."""
    if not note_id:
        print_result("Delete Note", False)
        return False

    r = requests.delete(f"{BASE_URL}/notes/{note_id}", headers=get_headers())
    success = r.status_code == 200
    print_result("Delete Note", success, r if not success else None)
    return success


def test_delete_tag():
    """Test delete tag."""
    if not tag_id:
        print_result("Delete Tag", False)
        return False

    r = requests.delete(f"{BASE_URL}/tags/{tag_id}", headers=get_headers())
    success = r.status_code == 200
    print_result("Delete Tag", success, r if not success else None)
    return success


# ==================== MAIN ====================

def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("NOTE-TAKING API TEST SUITE")
    print("=" * 60)

    passed = 0
    failed = 0

    tests = [
        # Health
        ("Health Check", test_health),

        # Auth
        ("Register/Login", test_register),
        ("Login Wrong Password", test_login_wrong_password),
        ("Get Current User", test_get_current_user),
        ("Protected Without Token", test_protected_without_token),

        # User
        ("Get User", test_get_user),
        ("Get User Stats", test_get_user_stats),
        ("Update User", test_update_user),

        # Tags
        ("Create Tag", test_create_tag),
        ("Get All Tags", test_get_tags),
        ("Get Single Tag", test_get_tag),
        ("Update Tag", test_update_tag),
        ("Create Tag Invalid Color", test_create_tag_invalid_color),
        ("Create Tag Short Name", test_create_tag_short_name),

        # Notes
        ("Create Note", test_create_note),
        ("Create Note No Title", test_create_note_no_title),
        ("Create Note Invalid Status", test_create_note_invalid_status),
        ("Get All Notes", test_get_notes),
        ("Get Notes Filtered", test_get_notes_filtered),
        ("Get Single Note", test_get_note),
        ("Update Note", test_update_note),
        ("Pin Note", test_update_note_status_pinned),
        ("Archive Note", test_update_note_status_archived),
        ("Activate Note", test_update_note_status_active),

        # Note-Tag Associations
        ("Get Note Tags", test_get_note_tags),
        ("Add Tag to Note", test_add_tag_to_note),
        ("Get Notes by Tag", test_get_notes_by_tag),
        ("Remove Tag from Note", test_remove_tag_from_note),

        # Search
        ("Search Notes", test_search_notes),
        ("Search No Query", test_search_notes_no_query),

        # Cleanup
        ("Delete Note", test_delete_note),
        ("Delete Tag", test_delete_tag),
    ]

    print("\n--- Running Tests ---\n")

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ FAIL - {name}")
            print(f"       Error: {str(e)}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)