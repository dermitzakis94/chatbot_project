import json
import os
from typing import Dict, Any, Optional, List
from ai_filter import AIContentFilter  
from fastapi import FastAPI, HTTPException, Query , Form , File, UploadFile
from pydantic import BaseModel, HttpUrl
from scrapping_control2 import ScrapingController
from openai import OpenAI
from datetime import datetime
from collections import defaultdict
from fastapi.responses import StreamingResponse, HTMLResponse
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import time
import tiktoken  # για token counting
import logging
from file_extractor import extract_text_from_files
import aiomysql
import secrets
import hashlib


load_dotenv()

#κωδικοι για εισχώρηση στην βάση
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'db': os.getenv('DB_NAME', 'chatbot_db'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'charset': 'utf8mb4'
}

#global variables
db_pool = None
cached_prompts = {}
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
website_data_db: Dict[str, str] = {}
files_data_db: Dict[str, str] = {}      
chat_history_db: Dict[str, List[Dict]] = defaultdict(list)  
companies_db: Dict[str, CompanyInfo] = {}

# Database functions
async def init_database_pool():
    global db_pool
    try:
        db_pool = await aiomysql.create_pool(
            minsize=5,
            maxsize=20,
            **DB_CONFIG
        )
        print("✅ Database pool created successfully")
    except Exception as e:
        print(f"❌ Database pool creation failed: {e}")
        raise

async def init_database_pool():
    global db_pool
    db_pool = await aiomysql.create_pool(
        minsize=5,
        maxsize=20,
        **DB_CONFIG
    )

#δημιουργεί πίνακα αν αυτός δεν υπάρχει 
async def create_database_tables():
    async with db_pool.acquire() as connection:
        cursor = await connection.cursor()
        
        await cursor.execute("CREATE DATABASE IF NOT EXISTS chatbot_db")
        await cursor.execute("USE chatbot_db")
        
        create_table = """
        CREATE TABLE IF NOT EXISTS bots (
            bot_id INT AUTO_INCREMENT PRIMARY KEY,
            company_slug VARCHAR(100) UNIQUE NOT NULL,
            company_name VARCHAR(255) NOT NULL,
            api_key_hash VARCHAR(255) UNIQUE NOT NULL,
            website_data LONGTEXT,
            files_data LONGTEXT,
            prompt_snapshot LONGTEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        await cursor.execute(create_table)
        await connection.commit()

#αποθηκευει τα απαραίτητα στοιχεία για να δημιουργηθεί το bot στην βάση δεδομένων
async def save_bot_to_database(company_info, website_data, files_data, api_key_hash, prompt_snapshot):
    async with db_pool.acquire() as connection:
        cursor = await connection.cursor()
        
        # Δημιουργία company_slug από το company_name
        company_slug = company_info.companyName.lower().replace(' ', '-').replace('.', '').replace(',', '')
        
        sql = """
        INSERT INTO bots (
            company_slug, company_name, api_key_hash, 
            industry, industry_other, website_url, description, 
            questions, greeting, end_message, keywords, persona,
            website_data, files_data, prompt_snapshot, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        values = (
            company_slug, company_info.companyName, api_key_hash,
            company_info.industry, company_info.industryOther, str(company_info.websiteURL),
            company_info.description, company_info.questions, company_info.greeting,
            company_info.endMessage, getattr(company_info, 'keywords', ''), 
            company_info.persona,  # Αφαίρεσα το getattr από εδώ
            website_data, files_data, prompt_snapshot, 'active'
        )
        
        await cursor.execute(sql, values)
        await connection.commit()
        
        # Επιστροφή του bot_id
        return cursor.lastrowid

#παιρνουμε τα δεδομένα από την βάση
async def get_bot_by_company_name(company_name):
    """Παίρνει bot από τη βάση με company name"""
    async with db_pool.acquire() as connection:
        cursor = await connection.cursor()
        sql = "SELECT * FROM bots WHERE company_name = %s"
        await cursor.execute(sql, (company_name,))
        result = await cursor.fetchone()
        return result

#για ήδη υπάρχον api key
async def get_bot_by_api_key_hash(api_key_hash):
    """Βρίσκει bot με βάση το hash του API key"""
    async with db_pool.acquire() as connection:
        cursor = await connection.cursor()
        sql = "SELECT * FROM bots WHERE api_key_hash = %s"
        await cursor.execute(sql, (api_key_hash,))
        result = await cursor.fetchone()
        return result


#δημιουργια τυχαίου API KEY
def generate_api_key():
    # Δημιουργία 20 τυχαίων αριθμών
    random_numbers = ''.join(secrets.choice('0123456789') for _ in range(20))
    
    # API key: sf + 20 αριθμοί
    api_key = f"sf{random_numbers}"
    return api_key



def hash_api_key(api_key):
    """Δημιουργεί SHA-256 hash από το API key"""
    hash_object = hashlib.sha256(api_key.encode('utf-8'))
    return hash_object.hexdigest()


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#count tokens for given text,fullback if not gpt4turbo
def count_tokens(text: str, model: str = "gpt-4o") -> int:    
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except:
        # Fallback estimation
        return len(text.split()) * 1.3

#δημιουργία prompt snapshot
def build_prompt_snapshot(company_info, website_data, files_data):
    """Δημιουργεί το έτοιμο system prompt για αποθήκευση στη βάση"""
    
    prompt_snapshot = f"""
=== ΠΛΗΡΟΦΟΡΙΕΣ ΙΣΤΟΤΟΠΟΥ ===
{website_data}

=== ΠΛΗΡΟΦΟΡΙΕΣ ΑΠΟ ΑΡΧΕΙΑ ===
{files_data}

=== ΠΕΡΙΓΡΑΦΗ ΕΤΑΙΡΙΑΣ ===
{company_info.description}

=== ΣΥΧΝΕΣ ΕΡΩΤΗΣΕΙΣ ===
{company_info.questions}

=== ΠΡΟΣΩΠΙΚΟΤΗΤΑ ===
{company_info.persona}

=== ΣΥΜΠΕΡΙΦΟΡΑ ===
- Χρησιμοποίησε τις πληροφορίες του ιστοτόπου και των αρχείων ως context
SOS:Απάντησε με μέγεθος γύρω στις 150—200 λέξεις.
Αν η απάντηση απαιτεί περισσότερα, δώσε μια πρώτη ενότητα
και κλείσε με: "Θέλετε να συνεχίσω με περισσότερες λεπτομέρειες;"."""

    return prompt_snapshot

app = FastAPI(
    title="Chatbot",
    description="API for a chatbot that uses scraped website content as its knowledge base.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#δημιουργεί τον πίνακα αν δεν υπάρχει
@app.on_event("startup")
async def startup_event():
    await init_database_pool()
    await create_database_tables()
    print("Application started successfully")

class ChatMessage(BaseModel):
    message: str
    
class ChatResponse(BaseModel):
    response: str
    timestamp: str

class CompanyInfo(BaseModel):
    companyName: str
    websiteURL: HttpUrl
    industry: str
    industryOther: Optional[str] = None
    description: str
    questions: str
    greeting: str
    persona: str
    endMessage: str





class ScrapingRequest(BaseModel):
    websiteURL: HttpUrl
    companyName: str



@app.post("/chat/{companyName}")
async def chat_with_company(companyName: str, message_data: ChatMessage):
    # === TIMING START ===
    start_time = time.time()
    logger.info(f"🚀 Chat request started for {companyName}")
    
    if companyName not in companies_db:
        raise HTTPException(status_code=404, detail="Company not found")
    
    company = companies_db[companyName]
    website_data = website_data_db.get(companyName, "")
    files_data = files_data_db.get(companyName, "")
    chat_history = chat_history_db.get(companyName, [])

    system_prompt = f"""
=== WEBSITE DATA ===
{website_data}

=== FILES DATA ===
{files_data}

=== COMPANY DESCRIPTION ===
{company.description}

=== FREQUENTLY ASKED QUESTIONS ===
{company.questions}

=== PERSONALITY ===
{company.persona}

=== INSTRUCTIONS ===
- Χρησιμοποίησε τις πληροφορίες του ιστοτόπου και των αρχείων ως context
SOS:Απάντησε με μέγεθος γύρω στις 150–200 λέξεις.
Αν η απάντηση απαιτεί περισσότερα, δώσε μια πρώτη ενότητα
και κλείσε με: "Θέλετε να συνεχίσω με περισσότερες λεπτομέρειες;"."""
    
    prep_time = time.time()
    system_tokens = count_tokens(system_prompt)
    history_tokens = count_tokens(str(chat_history)) if chat_history else 0
    user_tokens = count_tokens(message_data.message)
    total_tokens = system_tokens + history_tokens + user_tokens

    logger.info(f"📊 System prompt: {system_tokens} tokens")
    logger.info(f"📊 History: {history_tokens} tokens") 
    logger.info(f"📊 User message_data.message: {user_tokens} tokens")
    logger.info(f"📊 Total context: {total_tokens} tokens")
    logger.info(f"⏱️ Preparation time: {prep_time - start_time:.3f}s")

    messages = [
        {"role": "system", "content": system_prompt},
        *chat_history,
        {"role": "user", "content": message_data.message}
    ]

    async def stream_response():
        try:
            api_start_time = time.time()
            logger.info("🔄 Starting OpenAI API call...")
            
            stream = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                stream=True,
                temperature=0.5,
                max_tokens=1000
            )

            full_response = ""
            first_chunk_time = None

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:

                    if first_chunk_time is None:
                        first_chunk_time = time.time()
                        logger.info(f"⚡ First chunk received: {first_chunk_time - api_start_time:.3f}s")
                    
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield f"data: {json.dumps({'response': content, 'timestamp': datetime.now().isoformat()})}\n\n"
                    await asyncio.sleep(0.05)

            yield "data: [DONE]\n\n"

            total_time = time.time() - start_time
            streaming_time = time.time() - api_start_time if 'api_start_time' in locals() else 0
            logger.info(f"🏁 Total request time: {total_time:.3f}s")
            logger.info(f"🏁 OpenAI streaming time: {streaming_time:.3f}s")
            logger.info(f"🏁 Response length: {len(full_response)} characters")

            chat_history_db[companyName].append({"role": "user", "content": message_data.message})
            chat_history_db[companyName].append({"role": "assistant", "content": full_response})

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            raise HTTPException(status_code=500, detail=str(e))

    return StreamingResponse(stream_response(), media_type="text/event-stream")

@app.post("/create_chatbot")
async def create_chatbot_unified(
    company_info: str = Form(...),
    files: List[UploadFile] = File(default=[])
):
    try:
        
        # Parse το JSON string
        company_data = json.loads(company_info)
        # Δημιουργία CompanyInfo object με validation
        company_info_obj = CompanyInfo(**company_data)

        
        print(f"✅ Company '{company_info_obj.companyName}' registered")


        print(f"🔄 Starting scraping for: {company_info_obj.websiteURL}")
        scraper = ScrapingController()
        scraped_data = await scraper.scrape_website_async(str(company_info_obj.websiteURL))
        
        json_filename = f"company_data/{company_info_obj.companyName}_scraped_data.json"
        os.makedirs(os.path.dirname(json_filename), exist_ok=True)
        
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(scraped_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Scraped data saved to: {json_filename}")
        
        print(f"📝 Extracting plain text content...")
        website_data = ""
        if scraped_data.get("main_page", {}).get("status") == "success":
            website_data += scraped_data["main_page"].get("plain_text", "")
        for link in scraped_data.get("discovered_links", []):
            if link.get("status") == "success":
                website_data += "\n" + link.get("plain_text", "")
        
        files_content = await extract_text_from_files(files)
        print(f"✅ Website και files επεξεργασία ολοκληρώθηκε")

        api_key = generate_api_key()
        api_key_hash = hash_api_key(api_key)

        # Δημιουργία prompt snapshot  
        prompt_snapshot = build_prompt_snapshot(company_info_obj, website_data[:50000], files_content)

        # Αποθήκευση στη βάση
        bot_id = await save_bot_to_database(company_info_obj, website_data[:50000], files_content, api_key_hash, prompt_snapshot)

        print(f"Bot created with ID: {bot_id}, API key: {api_key}")

        return {
            "message": f"Chatbot created successfully for {company_info_obj.companyName}!",
            "chat_url": f"/widget/{company_info_obj.companyName}",
            "status": "success"
        }
    except Exception as e:
        print(f"❌ Error creating chatbot: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating chatbot: {str(e)}")

@app.get("/widget/{companyName}", response_class=HTMLResponse)
async def get_chat_widget(companyName: str):
    try:
        with open("chat_widget.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Chat widget template not found")
