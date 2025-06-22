import requests

# Try to register the test user first
BASE_URL = 'http://localhost:8000/api/v1'
TEST_USER = {
    'email': 'test@example.com',
    'username': 'testuser123',
    'password': 'testpassword123',
    'first_name': 'Test',
    'last_name': 'User',
    'phone': '+1234567890'
}

print("=== REGISTERING TEST USER ===")
try:
    response = requests.post(f'{BASE_URL}/register', json=TEST_USER)
    if response.status_code == 201:
        print('✅ Test user registered successfully!')
        user_data = response.json()
        print(f'User ID: {user_data.get("id")}')
        print(f'Email: {user_data.get("email")}')
    elif response.status_code == 400:
        print('ℹ️  Test user already exists (expected)')
    else:
        print(f'❌ Registration failed: {response.status_code} - {response.text}')
except Exception as e:
    print(f'❌ Registration error: {e}')

print("\n=== TESTING LOGIN ===")        
# Now try to login
try:
    login_data = {
        'email': TEST_USER['email'],
        'password': TEST_USER['password']
    }
    response = requests.post(f'{BASE_URL}/login', json=login_data)
    if response.status_code == 200:
        data = response.json()
        print('✅ Test login successful!')
        print(f'Token: {data.get("access_token", "")[:50]}...')
    else:
        print(f'❌ Login failed: {response.status_code} - {response.text}')
except Exception as e:
    print(f'❌ Login error: {e}') 