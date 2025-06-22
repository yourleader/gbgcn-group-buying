#!/usr/bin/env python3
"""
GBGCN API Complete Test Script - Updated for new route prefixes
Tests all major endpoints to verify API functionality
"""

import requests
import json
from datetime import datetime
import time

# API Configuration
BASE_URL = "http://localhost:8000"
API_VERSION = "/api/v1"

# Test credentials
TEST_USER = {
    "email": "test@example.com",
    "password": "testpassword123"
}

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_result(success, message, details=None):
    icon = "✅" if success else "❌"
    print(f"{icon} {message}")
    if details:
        print(f"ℹ️  {details}")

def print_info(message):
    print(f"ℹ️  {message}")

def test_health():
    """Test health check endpoint"""
    print_section("HEALTH CHECK")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print_result(True, "Health check passed!")
            print_info(f"Status: {data.get('status')}")
            print_info(f"Services: {data.get('services')}")
            return True
        else:
            print_result(False, f"Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Health check error: {str(e)}")
        return False

def test_auth():
    """Test authentication"""
    print_section("AUTHENTICATION TEST")
    try:
        response = requests.post(
            f"{BASE_URL}{API_VERSION}/login",
            json=TEST_USER
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print_result(True, f"Login successful! Token: {token[:50]}...")
            return token
        else:
            print_result(False, f"Login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print_result(False, f"Auth error: {str(e)}")
        return None

def test_user_profile(token):
    """Test user profile endpoint"""
    print_section("USER PROFILE TEST")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}{API_VERSION}/me", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print_result(True, "User profile retrieved!")
            print_info(f"User: {data.get('email')} (ID: {data.get('id')})")
            return True
        else:
            print_result(False, f"Profile failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Profile error: {str(e)}")
        return False

def test_items_list(token):
    """Test items list endpoint - MAIN FIX TARGET"""
    print_section("ITEMS LIST TEST (MAIN FIX)")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}{API_VERSION}/items/", headers=headers)
        print_info(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"Items list successful! Found {len(data)} items")
            
            # Show sample items
            for i, item in enumerate(data[:3]):
                print_info(f"Item {i+1}: {item.get('name', 'Unknown')} - ${item.get('base_price', 0)}")
            
            return data
        else:
            print_result(False, f"Items list failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print_result(False, f"Items error: {str(e)}")
        return None

def test_items_filtered(token):
    """Test items with filters"""
    print_section("FILTERED ITEMS TEST")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{BASE_URL}{API_VERSION}/items/?limit=5&min_price=100",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"Filtered items successful! Found {len(data)} items")
            return True
        else:
            print_result(False, f"Filtered items failed: {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Filtered items error: {str(e)}")
        return False

def test_item_detail(token, items_data):
    """Test single item detail"""
    print_section("ITEM DETAIL TEST")
    if not items_data or len(items_data) == 0:
        print_result(False, "Could not get items list for detail test")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        item_id = items_data[0]['id']
        response = requests.get(
            f"{BASE_URL}{API_VERSION}/items/{item_id}",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"Item detail successful! Item: {data.get('name')}")
            return True
        else:
            print_result(False, f"Item detail failed: {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Item detail error: {str(e)}")
        return False

def test_categories(token):
    """Test categories endpoint"""
    print_section("CATEGORIES TEST")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{BASE_URL}{API_VERSION}/items/stats/categories",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"Categories successful! Found {len(data)} categories")
            return True
        else:
            print_result(False, f"Categories failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Categories error: {str(e)}")
        return False

def test_item_creation(token):
    """Test creating a new item"""
    print_section("ITEM CREATION TEST")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        item_data = {
            "name": "Test Product",
            "description": "A test product for API testing",
            "base_price": 99.99,
            "brand": "TestBrand",
            "min_group_size": 2,
            "max_group_size": 10
        }
        response = requests.post(
            f"{BASE_URL}{API_VERSION}/items/",
            json=item_data,
            headers=headers
        )
        if response.status_code == 201:
            data = response.json()
            print_result(True, f"Item creation successful! ID: {data.get('item_id')}")
            return True
        else:
            print_result(False, f"Item creation failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Item creation error: {str(e)}")
        return False

def main():
    """Run complete API test suite"""
    print_section("STARTING GBGCN API COMPLETE TEST")
    print_info(f"Testing API at: {BASE_URL}{API_VERSION}")
    print_info(f"Timestamp: {datetime.now()}")
    
    # Track test results
    tests = []
    
    # Health check
    health_ok = test_health()
    tests.append(("Health Check", health_ok))
    
    if not health_ok:
        print("\n❌ Health check failed - stopping tests")
        return
    
    # Authentication
    token = test_auth()
    tests.append(("Login", token is not None))
    
    if not token:
        print("\n❌ Authentication failed - stopping tests")
        return
    
    # User profile
    profile_ok = test_user_profile(token)
    tests.append(("User Profile", profile_ok))
    
    # Items list (main target)
    items_data = test_items_list(token)
    tests.append(("Items List (MAIN FIX)", items_data is not None))
    
    # Filtered items
    filtered_ok = test_items_filtered(token)
    tests.append(("Filtered Items", filtered_ok))
    
    # Item detail
    detail_ok = test_item_detail(token, items_data)
    tests.append(("Item Detail", detail_ok))
    
    # Categories
    categories_ok = test_categories(token)
    tests.append(("Categories", categories_ok))
    
    # Item creation
    creation_ok = test_item_creation(token)
    tests.append(("Item Creation", creation_ok))
    
    # Results summary
    print_section("TEST RESULTS SUMMARY")
    passed = 0
    for test_name, result in tests:
        print_result(result, test_name)
        if result:
            passed += 1
    
    print_section("FINAL SUMMARY")
    total = len(tests)
    success_rate = (passed / total) * 100
    
    print_info(f"Tests Passed: {passed}")
    print_info(f"Tests Failed: {total - passed}")
    print_info(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print_info(f"🎉 {passed}/{total} tests passed. API is working well!")
    elif success_rate >= 60:
        print_info(f"⚠️ {passed}/{total} tests passed. Some issues to fix.")
    else:
        print_info(f"📊 {passed}/{total} tests passed. Some issues remain.")

if __name__ == "__main__":
    main() 