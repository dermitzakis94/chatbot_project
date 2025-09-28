import json
from typing import Dict, Any, Optional, List , Literal
from ai_filter import AIContentFilter  
from fastapi import FastAPI, HTTPException, Query , Form , File, UploadFile
from pydantic import BaseModel, HttpUrl , Field
from scrapping_control2 import ScrapingController
from openai import OpenAI
from datetime import datetime
from collections import defaultdict
from widget_template import generate_widget_js
from fastapi.responses import StreamingResponse, HTMLResponse , Response
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import time
import tiktoken  # για token counting
import logging
from file_extractor import extract_text_from_files
import secrets
import string
import sqlite3
import os
 



load_dotenv()

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

#Συνάρτηση που δημιουργεί το system prompt
def create_system_prompt(website_data: str, files_data: str, description: str,persona: str) -> str:
   """
   Δημιουργεί το system prompt για το chatbot της εταιρείας
   """
   system_prompt = f"""=== ΠΛΗΡΟΦΟΡΙΕΣ ΙΣΤΟΤΟΠΟΥ ===
{website_data}

=== ΠΛΗΡΟΦΟΡΙΕΣ ΑΠΟ ΑΡΧΕΙΑ ===
{files_data}

=== ΠΕΡΙΓΡΑΦΗ ΕΤΑΙΡΙΑΣ ===
{description}

=== ΠΡΟΣΩΠΙΚΟΤΗΤΑ ===
{persona}

=== ΣΥΜΠΕΡΙΦΟΡΑ ===
- Χρησιμοποίησε τις πληροφορίες του ιστοτόπου και των αρχείων ως context
SOS:Απάντησε με μέγεθος γύρω στις 150–200 λέξεις.
Αν η απάντηση απαιτεί περισσότερα, δώσε μια πρώτη ενότητα
και κλείσε με: "Θέλετε να συνεχίσω με περισσότερες λεπτομέρειες;"."""

   return system_prompt

#συνάρτηση για δημιουργία API KEY
def generate_api_key(length: int = 32) -> str:
   """
   Δημιουργεί ένα τυχαίο API key για την εταιρεία
   """
   # Χρησιμοποιούμε γράμματα και αριθμούς
   characters = string.ascii_letters + string.digits
   
   # Δημιουργούμε τυχαίο string
   api_key = ''.join(secrets.choice(characters) for _ in range(length))
   
   # Προσθέτουμε prefix για ευκολία αναγνώρισης
   return f"cb_{api_key}"


#ΟΙ ΠΑΡΑΚΑΤΩ ΣΥΝΑΡΤΗΣΕΙΣ:
#σκοπό έχουν σύνδεση με βάση δεδομένων , εισχώρηση εταιρίας στην βάση
#ενημέρωση και ανάκτηση δεδομένων από την βάση


def get_database_connection():
    """
    Δημιουργεί σύνδεση με την SQLite βάση δεδομένων
    """
    db_path = "companies.db"
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file {db_path} not found")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Επιστρέφει rows ως dictionaries
    return conn

def insert_company(company_data: dict):
    """
    Εισάγει νέα εταιρεία στη βάση δεδομένων
    
    company_data πρέπει να περιέχει:
    - companyName, websiteURL, industry, industryOther, description,
    - greeting, persona, files_data, 
    - website_data, prompt_snapshot, api_key, script
    """
    conn = get_database_connection()
    try:
        cursor = conn.cursor()
        
        # SQL INSERT statement
        insert_sql = """
        INSERT INTO companies (
            companyName, websiteURL, industry, industryOther, description,
            botName, greeting, persona, botRestrictions, files_data,
            website_data, prompt_snapshot, api_key, script
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # Τα δεδομένα για εισαγωγή
        values = (
            company_data['companyName'],
            company_data['websiteURL'],
            company_data['industry'],
            company_data.get('industryOther', ''),
            company_data['description'],
            company_data['botName'],          
            company_data['greeting'],
            company_data['persona'],
            company_data['botRestrictions'],  
            company_data['files_data'],
            company_data['website_data'],
            company_data['prompt_snapshot'],
            company_data['api_key'],
            company_data['script']
        )
        
        cursor.execute(insert_sql, values)
        conn.commit()
        
        print(f"✅ Company '{company_data['companyName']}' inserted successfully")
        return True
        
    except sqlite3.IntegrityError as e:
        print(f"❌ Company '{company_data['companyName']}' already exists")
        return False
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        return False
    finally:
        conn.close()

#παίρνει τις πλήροφορίες από την βάση δείχνονττας το api_key
def get_company_by_api_key(api_key: str):
    """
    Αναζητά στοιχεία εταιρείας από τη βάση δεδομένων με API key
    
    Returns: dictionary με όλα τα στοιχεία ή None αν δεν βρεθεί
    """
    conn = get_database_connection()
    try:
        cursor = conn.cursor()
        
        select_sql = "SELECT * FROM companies WHERE api_key = ?"
        cursor.execute(select_sql, (api_key,))
        
        row = cursor.fetchone()
        if row:
            # Μετατρέπουμε το Row σε dictionary
            return dict(row)
        else:
            return None
            
    except Exception as e:
        print(f"⚠️ Database error: {str(e)}")
        return None
    finally:
        conn.close()

def update_company_script(company_name: str, new_script: str):
    """
    Ενημερώνει το script μιας εταιρείας (για μελλοντική χρήση)
    """
    conn = get_database_connection()
    try:
        cursor = conn.cursor()
        
        update_sql = "UPDATE companies SET script = ? WHERE companyName = ?"
        cursor.execute(update_sql, (new_script, company_name))
        conn.commit()
        
        if cursor.rowcount > 0:
            print(f"✅ Script updated for company '{company_name}'")
            return True
        else:
            print(f"❌ Company '{company_name}' not found")
            return False
            
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        return False
    finally:
        conn.close()

def generate_widget_script(company_name: str, api_key: str, greeting: str ) -> str:
    """
    Δημιουργεί το μικρό widget script που θα πάρει ο client (μία γραμμή)
    """
    
    domain = "http://127.0.0.1:8000"
    
    script = f'<script src="{domain}/widget.js?key={api_key}"></script>'
    
    return script




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

class Turn(BaseModel):
    role: Literal["user", "assistant"]  
    content: str

class ChatMessage(BaseModel):
    message: str
    history: List[Turn] = Field(default_factory=list)
    
class ChatResponse(BaseModel):
    response: str
    timestamp: str

class CompanyInfo(BaseModel):
    companyName: str
    websiteURL: HttpUrl
    industry: str
    industryOther: Optional[str] = None
    description: str
    greeting: str
    persona: str
    botName: str
    botRestrictions: str
    keywords:str

openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
website_data_db: Dict[str, str] = {}
files_data_db: Dict[str, str] = {}      
  
companies_db: Dict[str, CompanyInfo] = {}




@app.post("/chat")
async def chat_with_company(message_data: ChatMessage, api_key: str = Query(...)):
    # === TIMING START ===
    start_time = time.time()
    logger.info(f"🚀 Chat request started with API key")

    company_data = get_company_by_api_key(api_key)
    if not company_data:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    companyName = company_data['companyName']  # Παίρνουμε το όνομα από τη βάση
    logger.info(f"✅ Chat request for company: {companyName}")

    system_prompt = company_data['prompt_snapshot']
     
    
    prep_time = time.time()
    system_tokens = count_tokens(system_prompt)
    history_text = ' '.join([f"{turn.role}: {turn.content}" for turn in message_data.history])
    history_tokens = count_tokens(history_text) if message_data.history else 0
    user_tokens = count_tokens(message_data.message)
    total_tokens = system_tokens + history_tokens + user_tokens

    logger.info(f"📊 System prompt: {system_tokens} tokens")
    logger.info(f"📊 History: {history_tokens} tokens") 
    logger.info(f"📊 User message_data.message: {user_tokens} tokens")
    logger.info(f"📊 Total context: {total_tokens} tokens")
    logger.info(f"⏱️ Preparation time: {prep_time - start_time:.3f}s")

    messages = [
        {"role": "system", "content": system_prompt},
        *[{"role": turn.role, "content": turn.content} for turn in message_data.history],
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

        companies_db[company_info_obj.companyName] = company_info_obj
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

        website_data_db[company_info_obj.companyName] = website_data
        files_data_db[company_info_obj.companyName] = files_content
        print(f"✅ Website και files επεξεργασία ολοκληρώθηκε")


        # Δημιουργία API Key
        print(f"🔑 Δημιουργία API key...")
        api_key = generate_api_key()
        print(f"✅ API key created: {api_key}")
        
        # Δημιουργία System Prompt
        print(f"📝 Δημιουργία system prompt...")
        system_prompt = create_system_prompt(
            website_data=website_data,  
            files_data=files_content,
            description=company_info_obj.description,
            persona=company_info_obj.persona
        )
        print(f"✅ System prompt created ({len(system_prompt)} characters)")
        
        # Δημιουργία Widget Script
        print(f"🎨 Δημιουργία widget script...")
        widget_script = generate_widget_script(
            company_name=company_info_obj.companyName,
            api_key=api_key,
            greeting=company_info_obj.greeting
        )
        print(f"✅ Widget script created")
        
        # Προετοιμασία δεδομένων για βάση
        company_data_for_db = {
            'companyName': company_info_obj.companyName,
            'websiteURL': str(company_info_obj.websiteURL),
            'industry': company_info_obj.industry,
            'industryOther': company_info_obj.industryOther or '',
            'description': company_info_obj.description,
            'botName': company_info_obj.botName,          # ΠΡΟΣΘΗΚΗ
            'greeting': company_info_obj.greeting,
            'persona': company_info_obj.persona,
            'botRestrictions': company_info_obj.botRestrictions,  # ΠΡΟΣΘΗΚΗ
            'files_data': files_content,
            'website_data': website_data,
            'prompt_snapshot': system_prompt,
            'api_key': api_key,
            'script': widget_script
        }
        
        
        # Αποθήκευση στη βάση δεδομένων
        print(f"💾 Αποθήκευση στη βάση δεδομένων...")
        success = insert_company(company_data_for_db)
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to save company data to database")
        
        print(f"✅ Όλα αποθηκεύτηκαν επιτυχώς στη βάση")
        
        # Ενημερωμένο response
        return {
            "message": f"Chatbot created successfully for {company_info_obj.companyName}!",
            "chat_url": f"/widget/{company_info_obj.companyName}",
            "widget_script": widget_script,  # Αυτό θα το εμφανίσει το frontend
            "api_key": api_key,  # Για debugging/info
            "status": "success"
        }
        
    except Exception as e:
        print(f"❌ Error creating chatbot: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating chatbot: {str(e)}")

#δημιουργία widget



@app.get("/widget.js")
async def serve_widget(key: str = Query(...)):
    """
    Επιστρέφει το JavaScript κώδικα για το chat widget
    """
    try:
        print(f"🔍 Widget request with API key: {key}")
        company_data = get_company_by_api_key(key)
        print(f"🔍 Company data found: {company_data is not None}")
        if not company_data:
            raise HTTPException(status_code=403, detail="Invalid API key")

        print(f"🔍 About to generate widget for: {company_data['companyName']}")
        
        # Δημιουργία του widget JavaScript
        widget_code = generate_widget_js(
            company_name=company_data['companyName'],
            company_display_name=company_data['companyName'], 
            greeting=company_data['greeting'],
            api_key=key
        )
        print(f"✅ Widget generated successfully")
        
        return Response(
            content=widget_code,
            media_type="application/javascript"
        )
        
    except Exception as e:
        print(f"❌ Widget error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Widget generation failed: {str(e)}")


