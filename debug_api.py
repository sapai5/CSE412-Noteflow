import requests
import time

BASE_URL = "http://localhost:5000/api"

# Test health
print("1. Testing health...")
r = requests.get(f"{BASE_URL}/health")
print(f"   Status: {r.status_code}")
print(f"   Response: {r.json()}")

# Test register with unique email
print("\n2. Testing register...")
test_email = f"debug_{int(time.time())}@test.com"
print(f"   Using email: {test_email}")

r = requests.post(f"{BASE_URL}/auth/register", json={
    "name": "Debug User",
    "email": test_email,
    "password": "password123"
})
print(f"   Status: {r.status_code}")
print(f"   Response: {r.json()}")

if r.status_code == 201:
    token = r.json().get('token')
    user_id = r.json().get('user', {}).get('user_id')
    print(f"   Token: {token[:50]}...")
    print(f"   User ID: {user_id}")

    # Test login
    print("\n3. Testing login...")
    r = requests.post(f"{BASE_URL}/auth/login", json={
        "email": test_email,
        "password": "password123"
    })
    print(f"   Status: {r.status_code}")
    print(f"   Response: {r.json()}")

    # Test protected route
    print("\n4. Testing protected route (get notes)...")
    r = requests.get(f"{BASE_URL}/notes", headers={
        "Authorization": f"Bearer {token}"
    })
    print(f"   Status: {r.status_code}")
    print(f"   Response: {r.json()}")

    # Test create note
    print("\n5. Testing create note...")
    r = requests.post(f"{BASE_URL}/notes",
                      json={"title": "Debug Note", "content": "Test content"},
                      headers={"Authorization": f"Bearer {token}"}
                      )
    print(f"   Status: {r.status_code}")
    print(f"   Response: {r.json()}")

else:
    print("\n   Registration failed, cannot continue tests")