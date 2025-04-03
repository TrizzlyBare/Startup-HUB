import httpx
import asyncio
import json

async def test_registration():
    """Test the registration API endpoint directly."""
    print("Testing API registration endpoint...")
    
    # Minimal test payload
    payload = {
        "username": "testuser123",
        "email": "testuser123@example.com",
        "password": "password123"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    url = "http://127.0.0.1:8000/api/auth/register/"
    
    print(f"Making POST request to: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            
            print(f"Response status code: {response.status_code}")
            
            try:
                print(f"Response body: {response.text}")
                response_json = response.json()
                print(f"JSON response: {json.dumps(response_json, indent=2)}")
            except Exception as e:
                print(f"Error parsing response: {e}")
    except Exception as e:
        print(f"Error making request: {e}")

# Run the test
if __name__ == "__main__":
    asyncio.run(test_registration()) 