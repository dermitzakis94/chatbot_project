import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def get_database_connection():
    """Σύνδεση στη βάση δεδομένων"""
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

def create_total_analytics_table():
    """
    Δημιουργεί τον πίνακα total_analytics για αποθήκευση συνολικών δεδομένων
    """
    conn = get_database_connection()
    try:
        cursor = conn.cursor()
        
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS total_analytics (
            api_key VARCHAR(100) PRIMARY KEY,
            company_name VARCHAR(255) NOT NULL,
            total_messages INT DEFAULT 0,
            total_user_messages INT DEFAULT 0,
            total_assistant_messages INT DEFAULT 0,
            total_sessions INT DEFAULT 0,
            total_ratings_sum INT DEFAULT 0,
            total_ratings_count INT DEFAULT 0,
            avg_response_time FLOAT DEFAULT 0,
            last_updated DATE,
            INDEX idx_company_name (company_name),
            INDEX idx_last_updated (last_updated)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        
        cursor.execute(create_table_sql)
        conn.commit()
        print("✅ Total analytics table created/verified")
        return True
        
    except Exception as e:
        print(f"❌ Error creating total analytics table: {str(e)}")
        return False
    finally:
        conn.close()

def initialize_existing_companies():
    """
    Αρχικοποιεί συνολικά δεδομένα για εταιρείες που υπάρχουν ήδη
    """
    conn = get_database_connection()
    try:
        cursor = conn.cursor()
        
        # Βρες όλα τα API keys και company names
        cursor.execute("SELECT api_key, companyName FROM companies")
        companies = cursor.fetchall()
        
        for company in companies:
            api_key = company['api_key']
            company_name = company['companyName']
            
            # Εισαγωγή αρχικής εγγραφής με μηδενικά
            insert_sql = """
            INSERT IGNORE INTO total_analytics 
            (api_key, company_name, total_messages, total_user_messages, total_assistant_messages,
             total_sessions, total_ratings_sum, total_ratings_count, avg_response_time, last_updated)
            VALUES (%s, %s, 0, 0, 0, 0, 0, 0, 0, CURDATE())
            """
            
            cursor.execute(insert_sql, (api_key, company_name))
        
        conn.commit()
        print(f"✅ Initialized {len(companies)} companies in total_analytics")
        return True
        
    except Exception as e:
        print(f"❌ Error initializing companies: {str(e)}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("Creating total analytics table...")
    create_total_analytics_table()
    
    print("Initializing existing companies...")
    initialize_existing_companies()
    
    print("Setup completed!")
