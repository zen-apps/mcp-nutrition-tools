#!/usr/bin/env python3
import os
import sys
import requests
from dotenv import load_dotenv

def quick_test():
    """Test USDA FoodData Central API with synchronous requests"""
    api_key = os.getenv("FDC_API_KEY")
    if not api_key:
        print("ERROR: FDC_API_KEY not found")
        return False
    
    print("Testing API Key: " + api_key[:8] + "...")
    print("Python version: " + sys.version)
    
    try:
        response = requests.post(
            "https://api.nal.usda.gov/fdc/v1/foods/search",
            headers={"X-Api-Key": api_key},
            json={"query": "apple", "pageSize": 1},
            timeout=10.0
        )
        
        if response.status_code == 200:
            data = response.json()
            total_hits = data.get('totalHits', 0)
            print("SUCCESS: USDA API working! Found " + str(total_hits) + " foods")
            if data.get('foods'):
                food = data['foods'][0]
                description = food.get('description', 'Unknown')
                print("Sample food: " + description)
            return True
        else:
            print("ERROR: API error - HTTP " + str(response.status_code))
            print("Response: " + response.text)
            return False
    except requests.exceptions.RequestException as e:
        print("ERROR: Network error - " + str(e))
        return False
    except Exception as e:
        print("ERROR: Unexpected error - " + str(e))
        return False

if __name__ == "__main__":
    load_dotenv()
    success = quick_test()
    if success:
        print("Ready to go!")
    else:
        print("Check your API key and internet connection")