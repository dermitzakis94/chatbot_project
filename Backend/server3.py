import json
from typing import Dict, Any, Optional, List , Literal
from ai_filter import AIContentFilter  
from fastapi import FastAPI, HTTPException, Query , Form , File, UploadFile, Request
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
from urllib.parse import urlparse
import re
#import redis.commands.streams as streams
import uuid
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import timezone
import redis
 



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
def create_system_prompt(website_data: str, files_data: str, description: str,persona: str , botRestrictions: str = "") -> str:
    system_prompt = f"""

=== BOT RESTRICTIONS ===
{botRestrictions}

CRITICAL: THE ABOVE RESTRICTIONS ARE ABSOLUTE - NO EXCEPTIONS!

=== WEBSITE CONTENT ===
{website_data}

=== FILES DATA ===
{files_data}

=== COMPANY DESCRIPTION ===
{description}

=== PERSONALITY ===
{persona}

=== BEHAVIOR ===
- FIRST PRIORITY: Check "BOT RESTRICTIONS" - if something is forbidden, DO NOT do it regardless of available data
- NEVER override restrictions, even if you have the information
- Use "COMPANY DESCRIPTION" and "PERSONALITY" to understand the context and tone
- Answer based on "WEBSITE CONTENT" and "FILES DATA"
IMPORTANT: Keep responses around 150-200 words.
If the answer requires more detail, provide an initial section
and close with: "Would you like me to continue with more details?"."""

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
            website_data, prompt_snapshot, api_key, script , allowedDomains
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? ,?)
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
            company_data['script'],
            company_data['allowedDomains']
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



def validate_domain(request: Request, allowedDomains: str) -> bool:
    """
    Ελέγχει αν το request προέρχεται από επιτρεπόμενο domain/URL
    Αγνοεί το πρωτόκολλο (http/https)
    """
    origin = request.headers.get('origin', '')
    referer = request.headers.get('referer', '')
    logger.info(f"🌐 Domain validation - Origin: '{origin}', Referer: '{referer}'")

    
    if not allowedDomains or allowedDomains.strip() == "":
        return True  # Αν δεν έχει ορίσει domains, επιτρέπει όλα
    logger.info(f"📋 Allowed domains: '{allowedDomains}'")
    
    # Parse allowed patterns - split με κόμματα, κενά, newlines
    allowed_patterns = []
    patterns = re.split(r'[,\s\n\r]+', allowedDomains)
    
    for pattern in patterns:
        pattern = pattern.strip()
        if pattern:
            # Add protocol if missing για το parsing
            if not pattern.startswith(('http://', 'https://')):
                pattern = 'http://' + pattern
            
            parsed = urlparse(pattern)
            domain = parsed.netloc.lower()
            path = parsed.path.rstrip('/') or '/'
            
            allowed_patterns.append((domain, path))

    logger.info(f"🔍 Parsed allowed patterns: {allowed_patterns}")
    
    # Check request headers
    for header_url in [request.headers.get('origin', ''), request.headers.get('referer', '')]:
        if header_url:
            parsed = urlparse(header_url)
            req_domain = parsed.netloc.lower()
            req_path = parsed.path.rstrip('/') or '/'

            logger.info(f"🔍 Checking request domain: '{req_domain}', path: '{req_path}'")
            
            for allowed_domain, allowed_path in allowed_patterns:
                if req_domain == allowed_domain:
                    # Αν το allowed_path είναι root ('/'), δεχόμαστε οποιοδήποτε path
                    if allowed_path == '/' or req_path.startswith(allowed_path):
                        logger.info(f"✅ Domain validation passed: {req_domain} matches {allowed_domain}")
                        return True

    logger.info("❌ Domain validation failed: No matching domains found")
    return False
    
    



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
    session_id: Optional[str] = None
    
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
    allowedDomains:str

openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
website_data_db: Dict[str, str] = {}
files_data_db: Dict[str, str] = {}      
  
companies_db: Dict[str, CompanyInfo] = {}

# Redis client για streams και sessions
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# MongoDB client για analytics
mongo_client = AsyncIOMotorClient('mongodb://localhost:27017')
analytics_db = mongo_client.chatbot_analytics

def generate_session_id() -> str:
    """
    Δημιουργεί unique session ID κάθε φορά που την καλείς
    """
    return f"sess_{str(uuid.uuid4()).replace('-', '')[:16]}"

def publish_chat_event(session_id: str, role: str, content: str, company_name: str, 
                      response_time_ms: Optional[float] = None) -> None:
    """
    η συνάρτηση παίρνει τις πληροφορίες ενός μηνύματος chat,
    τις συλλέγει σε ένα λεξικό και τις στέλνει σε ένα Redis
    Stream με την εντολή xadd,επιτρέποντας
    σε άλλες διεργασίες (καταναλωτές) να τις επεξεργαστούν ασύγχρονα.
    """
    event_data = {
        "event_id": str(uuid.uuid4()),
        "session_id": session_id,
        "role": role,  # "user" ή "assistant"
        "content": content,
        "company_name": company_name,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    if response_time_ms is not None:
        event_data["response_time_ms"] = response_time_ms
    
    # Στέλνει το event στο Redis Stream
    redis_client.xadd("chat_events", event_data)

def update_session_state(session_id: str, api_key: str, company_name: str) -> None:
    """
    Αυτή η συνάρτηση διαχειρίζεται την κατάσταση κάθε ενεργής συνομιλίας στο Redis.
    """
    session_key = f"session:{session_id}"
    
    # Atomic update με pipeline για thread safety
    pipe = redis_client.pipeline()
    pipe.hset(session_key, mapping={
        "api_key": api_key,
        "company_name": company_name,
        "last_activity": datetime.now(timezone.utc).isoformat()
    })
    pipe.hincrby(session_key, "total_messages", 1)
    pipe.expire(session_key, 1800)  # 30 λεπτά TTL
    pipe.execute()



#web app chat
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

@app.post("/widget-chat")
async def chat_with_company(message_data: ChatMessage,request: Request , api_key: str = Query(...)):
    # === TIMING START ===
    start_time = time.time()
    logger.info(f"🚀 Chat request started with API key")

    company_data = get_company_by_api_key(api_key)
    if not company_data:
        raise HTTPException(status_code=403, detail="Invalid API key")
    # Domain validation
    if not validate_domain(request, company_data.get('allowedDomains', '')):
        raise HTTPException(status_code=403, detail="Domain not allowed")
    
    companyName = company_data['companyName']  # Παίρνουμε το όνομα από τη βάση
    logger.info(f"✅ Chat request for company: {companyName}")

    # Session handling για widget
    if message_data.session_id is None:
        session_id = generate_session_id()
        logger.info(f"New widget session created: {session_id}")
    else:
        session_id = message_data.session_id
        logger.info(f"Continuing widget session: {session_id}")

# Publish user message event
    publish_chat_event(
        session_id=session_id,
        role="user", 
        content=message_data.message,
        company_name=companyName
    )

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

            first_chunk_sent = False
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    if first_chunk_time is None:
                        first_chunk_time = time.time()
                        logger.info(f"⚡ First chunk received: {first_chunk_time - api_start_time:.3f}s")
        
                    content = chunk.choices[0].delta.content
                    full_response += content
        
        # Include session_id in first chunk only
                    if not first_chunk_sent:
                        yield f"data: {json.dumps({'response': content, 'timestamp': datetime.now().isoformat(), 'session_id': session_id})}\n\n"
                        first_chunk_sent = True
                    else:
                        yield f"data: {json.dumps({'response': content, 'timestamp': datetime.now().isoformat()})}\n\n"
                    await asyncio.sleep(0.05)

            yield "data: [DONE]\n\n"

            # Calculate response time and publish bot event
            total_response_time_ms = (time.time() - api_start_time) * 1000

            publish_chat_event(
                session_id=session_id,
                role="assistant", 
                content=full_response,
                company_name=companyName,
                response_time_ms=total_response_time_ms
            )

            # Update session state
            update_session_state(session_id, api_key, companyName)

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
            persona=company_info_obj.persona,
            botRestrictions=company_info_obj.botRestrictions
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
            'script': widget_script,
            'allowedDomains': company_info_obj.allowedDomains
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
            company_display_name=company_data['botName'], 
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

