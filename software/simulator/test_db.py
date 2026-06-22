import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv

# Load .env
base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(base_dir, '.env'))

uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
db_name = os.environ.get("MONGODB_DB_NAME", "battery_estimation_db")

print("="*60)
print("MongoDB Connection Diagnostic Tool")
print("="*60)
print(f"Connecting to database URI: {uri}")
print(f"Target Database: {db_name}")
print("Testing connection (timeout set to 5s)...")

try:
    client = MongoClient(uri)
    # Trigger connection check
    info = client.server_info()
    print("[SUCCESS] Connected successfully to MongoDB!")
    print(f"Server Info: Version {info.get('version', 'Unknown')} - Status: {info.get('ok', 0.0)}")
except Exception as e:
    print("[FAILED] Connection failed!")
    print(f"\nError Details:\n{e}\n")
    print("Troubleshooting steps:")
    print("1. Check if your internet connection is active.")
    print("2. Ensure your password/credentials in software/simulator/.env are correct.")
    print("3. Check if your local IP address is whitelisted in your MongoDB Atlas Project Network Access List:")
    print("   -> Log in to https://cloud.mongodb.com/")
    print("   -> Go to Security -> Network Access -> IP Access List.")
    print("   -> Click 'Add IP Address' -> Add your current IP (or allow access from anywhere '0.0.0.0/0' for testing).")
    print("4. Verify if the database cluster has been paused or deleted due to inactivity.")
print("="*60)
