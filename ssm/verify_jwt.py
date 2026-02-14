import requests
import json
import base64

BASE_URL = 'http://127.0.0.1:8000/api/auth/'

# Helper to decode JWT payload (without verifying signature)
def decode_jwt(token):
    try:
        payload_part = token.split('.')[1]
        # Padding
        payload_part += '=' * (-len(payload_part) % 4)
        payload = base64.urlsafe_b64decode(payload_part).decode('utf-8')
        return json.loads(payload)
    except Exception as e:
        print(f"Error decoding token: {e}")
        return {}

def test_mobile_login(username, password):
    print("\n--- Testing Mobile Login (Long-lived) ---")
    headers = {'X-Client-Type': 'mobile'}
    data = {'username': username, 'password': password} # SimpleJWT uses 'username' field, assumed 'staff_id' mapped?
    # Wait, the request uses 'staff_id' in your project's custom auth? 
    # Standard SimpleJWT expects 'username' and 'password'.
    # If using custom User model where USERNAME_FIELD is 'staff_id', then 'username' keys in JSON map to that.
    # Let's check assumptions. 
    # For now, I'll try standard keys.
    
    # Correction: Your project likely uses 'staff_id' or 'student_roll_number'.
    # SimpleJWT defaults to 'username' / 'password' keys in the JSON body, 
    # but Django's authenticate() method handles the field mapping (e.g. staff_id).
    
    # IMPORTANT: Need to know what field the custom auth expects.
    # Assuming 'username' key in JSON maps to 'staff_id' or 'roll_number' internally.
    
    payload = {
        'username': username, # This will be the staff_id or roll_number
        'password': password
    }

    try:
        response = requests.post(BASE_URL + 'token/', json=payload, headers=headers)
        if response.status_code == 200:
            print("Login Successful")
            tokens = response.json()
            access = tokens.get('access')
            refresh = tokens.get('refresh')
            
            if access and refresh:
                print("Access and Refresh tokens received in body.")
                
                # Verify Refresh Token Lifetime
                refresh_data = decode_jwt(refresh)
                exp = refresh_data.get('exp')
                iat = refresh_data.get('iat')
                if exp and iat:
                    duration = (exp - iat) / 86400 # Days
                    print(f"Refresh Token Duration: {duration:.2f} days (Expected ~90.00)")
                
                # Check cookies (should be empty for mobile)
                if not response.cookies:
                    print("No cookies set (Correct for Mobile).")
                else:
                    print("WARNING: Cookies were set for mobile client.")
            else:
                 print("FAILED: Tokens missing from body.")
        else:
            print(f"Login Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Request Error: {e}")

def test_web_login(username, password):
    print("\n--- Testing Web Login (Cookie-based) ---")
    headers = {'X-Client-Type': 'web'}
    payload = {
        'username': username,
        'password': password
    }

    try:
        response = requests.post(BASE_URL + 'token/', json=payload, headers=headers)
        if response.status_code == 200:
            print("Login Successful")
            tokens = response.json()
            
            # Check Cookies
            access_cookie = response.cookies.get('access_token')
            refresh_cookie = response.cookies.get('refresh_token')
            
            if access_cookie and refresh_cookie:
                print("Access and Refresh tokens set in COOKIES.")
                
                # Verify Access Token Lifetime (from body for easier decoding, assuming body matches cookie)
                # Note: Logic in view returns body too.
                access_token_body = tokens.get('access')
                access_data = decode_jwt(access_token_body)
                exp = access_data.get('exp')
                iat = access_data.get('iat')
                
                if exp and iat:
                    duration = (exp - iat) / 60 # Minutes
                    print(f"Access Token Duration: {duration:.2f} minutes (Expected ~30.00)")
                
            else:
                print("FAILED: Cookies missing.")
                print(f"Cookies received: {response.cookies.get_dict()}")
                
        else:
             print(f"Login Failed: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"Request Error: {e}")

if __name__ == "__main__":
    # You need to provide valid credentials here or create a test user
    # Ideally, we create a test user first via Django shell, but for now
    # I will ask the user to run this script or provide credentials.
    # Or I can try to use a known user if one exists in your dev DB.
    
    print("Please edit the script with valid credentials or run it manually.")
    # username = 'staff_id_here'
    # password = 'password_here'
    # test_mobile_login(username, password)
    # test_web_login(username, password)
