import redis
import json
import sys
import os

# Ensure we can import from the api directory
sys.path.append(os.getcwd())

from api.config.config import settings

def trigger_event():
    print(f"Connecting to Redis at: {settings.REDIS_PUBSUB_URL}")
    try:
        r = redis.StrictRedis.from_url(settings.REDIS_PUBSUB_URL)
        r.ping()
        print("Connected successfully!")
    except Exception as e:
        print(f"Could not connect to Redis: {e}")
        return

    # Message format matches celery_service\tasks\transcription.py
    # We need a valid recording ID. Since we don't know one, we'll use a placeholder.
    # The user should verify by looking for a recording ID in their browser network tab or DB.
    # For now, let's just use a string that might match if they have one, or they can edit it.
    
    # NOTE: You must replace 'YOUR_RECORDING_ID_HERE' with a real ID from your list to see the UI change!
    print("IMPORTANT: Edit this script to use a real recording_id from your database to test the UI update.")
    
    message = {
        "transcription_id": "test_transcription_123",
        "recording_id": "YOUR_RECORDING_ID_HERE", 
        "status": "completed"
    }
    
    channel = "transcription_completed"
    
    # Publish
    count = r.publish(channel, json.dumps(message))
    print(f"Published message to channel '{channel}'. Subscriber count: {count}")

if __name__ == "__main__":
    trigger_event()
