import asyncio
import logging
import redis
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis client
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# MongoDB client  
mongo_client = AsyncIOMotorClient('mongodb://localhost:27017')
analytics_db = mongo_client.chatbot_analytics

class AnalyticsWorker:
    def __init__(self):
        self.running = True
        self.consumer_group = "analytics_group"
        self.consumer_name = "worker_1"
        self.stream_name = "chat_events"

#Δημιουργεί ένα consumer group στο Redis Stream
#Το group θα παρακολουθεί ποια messages έχουν επεξεργαστεί
    async def setup_consumer_group(self):
        try:
            redis_client.xgroup_create(
                self.stream_name, 
                self.consumer_group, 
                id="0",
                mkstream=True
            )
            logger.info(f"Created consumer group '{self.consumer_group}'")
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.info(f"Consumer group '{self.consumer_group}' already exists")
            else:
                raise

    

    #Παίρνει ένα chat message από το Redis και το μετατρέπει σε MongoDB document
    #Το αποθηκεύει στο MongoDB και λέει στο Redis "το επεξεργάστηκα επιτυχώς"
    async def process_message(self, msg_id: str, fields: dict):
        try:
            mongo_doc = {
                "event_id": fields.get("event_id"),
                "session_id": fields.get("session_id"),
                "role": fields.get("role"),
                "content": fields.get("content"),
                "company_name": fields.get("company_name"),
                "timestamp": fields.get("timestamp"),
                "api_key": fields.get("api_key"),
                "response_time_ms": float(fields.get("response_time_ms", 0)) if fields.get("response_time_ms") else None,
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = await analytics_db.chat_events.insert_one(mongo_doc)
            
            if result.inserted_id:
                redis_client.xack(self.stream_name, self.consumer_group, msg_id)
                logger.info(f"Processed message {msg_id}")
                return True
            else:
                logger.error(f"Failed to insert message {msg_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing message {msg_id}: {e}")
            return False

    #Περιμένει στο Redis stream για νέα chat messages
    #Επεξεργάζεται κάθε message που έρχεται (στέλνει στο MongoDB)
    async def listen_for_events(self):
        logger.info("Starting real-time event listening...")
        
        while self.running:
            try:
                messages = redis_client.xreadgroup(
                    self.consumer_group,
                    self.consumer_name,
                    streams={self.stream_name: ">"},
                    count=10,
                    block=1000
                )
                
                if messages:
                    for stream_name, stream_messages in messages:
                        logger.info(f"Received {len(stream_messages)} new events")
                        
                        for msg_id, fields in stream_messages:
                            await self.process_message(msg_id, fields)
                            
            except Exception as e:
                logger.error(f"Error in event listener: {e}")
                await asyncio.sleep(1)

    async def run(self):
        logger.info("Analytics Worker starting...")
        
        try:
            await self.setup_consumer_group()
            await self.listen_for_events()
            
        except Exception as e:
            logger.error(f"Fatal error in worker: {e}")
        finally:
            logger.info("Analytics Worker shutting down...")
            mongo_client.close()

async def main():
    worker = AnalyticsWorker()
    await worker.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker crashed: {e}")
