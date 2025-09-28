import redis
import pymysql
import os
from datetime import datetime, date
from dotenv import load_dotenv
import logging

load_dotenv()


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
#database connection
def get_database_connection():
    """Σύνδεση στη MySQL"""
    conn = pymysql.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', 3307)),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', 'MyAnalytics2024!'),
        database=os.getenv('MYSQL_DATABASE', 'chatbot_platform'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    return conn


#redis connection
def get_redis_connection():
    """Σύνδεση στο Redis"""
    return redis.Redis(host='localhost', port=6379, decode_responses=True)


def migrate_daily_analytics():
    """
    Μεταφέρει σημερινά δεδομένα από Redis στη MySQL και καθαρίζει το Redis.
    """
    redis_client = get_redis_connection()
    mysql_conn = get_database_connection()
    
    try:
        cursor = mysql_conn.cursor()
        today = date.today()

        # Βρες όλες τις ενεργές εταιρείες
        cursor.execute("SELECT api_key, companyName FROM companies")
        companies = cursor.fetchall()
        
        logger.info(f"Starting migration for {len(companies)} companies")

        for company in companies:
            api_key = company['api_key']
            company_name = company['companyName']
        
        # Παίρνε δεδομένα από Redis
            redis_stats = redis_client.hgetall(f"stats:{api_key}")
            redis_ratings = redis_client.hgetall(f"ratings:{api_key}")
            redis_response = redis_client.hgetall(f"response_stats:{api_key}")

        # Μετατροπή σε integers/floats
            total_messages = int(redis_stats.get('total_messages', 0))
            user_messages = int(redis_stats.get('total_user_messages', 0))
            assistant_messages = int(redis_stats.get('total_assistant_messages', 0))
            total_sessions = int(redis_stats.get('total_sessions', 0))
        
            ratings_sum = int(redis_ratings.get('sum', 0))
            ratings_count = int(redis_ratings.get('count', 0))
        
        # Υπολογισμός averages
            daily_avg_response_time = float(redis_response.get('avg', 0))
            daily_avg_rating = ratings_sum / ratings_count if ratings_count > 0 else 0
            daily_response_time_sum = float(redis_response.get('total_time', 0))

        # Daily analytics insert με νέα structure
            daily_insert_sql = """
            INSERT INTO daily_analytics 
            (api_key, date, company_name, total_messages, user_messages, assistant_messages,
             total_sessions, daily_ratings_sum, daily_ratings_count, 
             daily_avg_response_time, daily_avg_rating,daily_response_time_sum)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)
          """
        
            cursor.execute(daily_insert_sql, (
                api_key, today, company_name, total_messages, user_messages, assistant_messages,
                total_sessions, ratings_sum, ratings_count, daily_avg_response_time, daily_avg_rating,daily_response_time_sum
           ))

        # Total analytics update
            total_update_sql = """
            UPDATE total_analytics SET
            total_messages = total_messages + %s,
            total_user_messages = total_user_messages + %s,
            total_assistant_messages = total_assistant_messages + %s,
            total_sessions = total_sessions + %s,
            total_ratings_sum = total_ratings_sum + %s,
            total_ratings_count = total_ratings_count + %s,
            total_response_time_sum = total_response_time_sum + %s,
            last_updated = %s
            WHERE api_key = %s
        """
        
            cursor.execute(total_update_sql, (
                total_messages, user_messages, assistant_messages,
                total_sessions, ratings_sum, ratings_count, 
                daily_response_time_sum, today, api_key
  ))
    # Commit όλες τις αλλαγές
        mysql_conn.commit()
        logger.info("All database changes committed successfully")
        # Καθάρισμα Redis
        cleanup_redis(redis_client, companies)

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        mysql_conn.rollback()
        raise
    finally:
        mysql_conn.close()
        logger.info("Migration process finished")

def cleanup_redis(redis_client, companies):
    """
    Καθαρίζει μόνο τα στατιστικά δεδομένα από το Redis.
    Τα sessions και άλλα ενεργά δεδομένα παραμένουν.
    """
    for company in companies:
        api_key = company['api_key']
        
        # Διαγραφή μόνο στατιστικών
        redis_client.delete(f"stats:{api_key}")
        redis_client.delete(f"ratings:{api_key}")
        redis_client.delete(f"response_stats:{api_key}")
        
        logger.info(f"Cleaned statistics for {company['companyName']}")
    
    logger.info("Statistics cleanup completed")

if __name__ == "__main__":
    migrate_daily_analytics()
