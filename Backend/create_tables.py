import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def create_companies_table():
    conn = pymysql.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', 3307)),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', 'MyAnalytics2024!'),
        database=os.getenv('MYSQL_DATABASE', 'chatbot_platform'),
        charset='utf8mb4'
    )
    
    try:
        with conn.cursor() as cursor:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS companies (
                id INT AUTO_INCREMENT PRIMARY KEY,
                companyName VARCHAR(255) UNIQUE NOT NULL,
                websiteURL TEXT NOT NULL,
                industry VARCHAR(255) ,
                industryOther VARCHAR(255),
                description TEXT ,
                botName VARCHAR(255) NOT NULL,
                greeting TEXT NOT NULL,
                persona TEXT NOT NULL,
                botRestrictions TEXT,
                files_data LONGTEXT,
                website_data LONGTEXT,
                prompt_snapshot LONGTEXT NOT NULL,
                api_key VARCHAR(255) UNIQUE NOT NULL,
                script LONGTEXT,
                allowedDomains TEXT,
                primaryColor VARCHAR(50) DEFAULT '#4f46e5',
                position VARCHAR(50) DEFAULT 'Bottom Right',
                themeStyle VARCHAR(50) DEFAULT 'Minimal',
                suggestedPrompts TEXT,
                coreFeatures JSON,
                leadCaptureFields JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            
            cursor.execute(create_table_sql)
            conn.commit()
            print("✅ Table 'companies' created successfully!")
            
    except Exception as e:
        print(f"❌ Error creating table: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_companies_table()
