import requests
import json

# Test direct access to the actual endpoints
BASE_URL = 'http://localhost:8000'

print('=== TESTING ENDPOINT ROUTES DIRECTLY ===')

# 1. Test root endpoint
try:
    response = requests.get(f'{BASE_URL}/')
    print(f'Root (/) - Status: {response.status_code}')
    if response.status_code == 200:
        data = response.json()
        print(f'Available endpoints: {data.get("quick_links", {})}')
except Exception as e:
    print(f'Root test error: {e}')

# 2. Test docs endpoint
try:
    response = requests.get(f'{BASE_URL}/docs')
    print(f'Docs (/docs) - Status: {response.status_code}')
except Exception as e:
    print(f'Docs test error: {e}')

# 3. Test actual items endpoint with token
try:
    # Login first
    login_response = requests.post(f'{BASE_URL}/api/v1/login', json={
        'email': 'test@example.com',
        'password': 'testpassword123'
    })
    
    if login_response.status_code == 200:
        token = login_response.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        
        # Test items endpoint
        items_response = requests.get(f'{BASE_URL}/api/v1/items', headers=headers)
        print(f'Items (/api/v1/items) - Status: {items_response.status_code}')
        if items_response.status_code != 200:
            print(f'Error: {items_response.text}')
        else:
            data = items_response.json()
            print(f'Items found: {len(data)}')
            if len(data) > 0:
                print(f'First item: {data[0].get("name", "Unknown")}')
    else:
        print(f'Could not login: {login_response.status_code}')
        
except Exception as e:
    print(f'Items test error: {e}')

# 4. Test with different routes to debug
try:
    # Test if items router is loaded at all
    response = requests.get(f'{BASE_URL}/api/v1/items/stats/categories')
    print(f'Categories (/api/v1/items/stats/categories) - Status: {response.status_code}')
    if response.status_code != 200:
        print(f'Categories Error: {response.text}')
except Exception as e:
    print(f'Categories test error: {e}') 