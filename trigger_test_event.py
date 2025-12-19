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

    message = {
        "status": "completed",
        "file_name": "test_audio.mp3",
        "transcription": "This is a test transcription event."
    }
    
    channel = "transcription_completed"
    
    # Publish
    count = r.publish(channel, json.dumps(message))
    print(f"Published message to channel '{channel}'. Subscriber count: {count}")

if __name__ == "__main__":
    trigger_event()
