import json
from typing import Dict, Any, Optional, List , Literal

from aiohttp import request
from ai_filter import AIContentFilter  
from fastapi import FastAPI, HTTPException, Query , Form , File, UploadFile, Request
from pydantic import BaseModel, HttpUrl , Field
from scrapping_control2 import ScrapingController
from openai import OpenAI
from datetime import datetime
from collections import defaultdict
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
import os
from urllib.parse import urlparse
import re
#import redis.commands.streams as streams
import uuid
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import timezone
import redis
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import pymysql
import pymysql.cursors
from fastapi import Body
from migration import migrate_daily_analytics
import base64 #μετατροπή εικόνων σε string για αποθήκευση στην βάση
from create_system_prompt import create_system_prompt
from fastapi.responses import RedirectResponse

templates = Jinja2Templates(directory="templates")



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
            botName, greeting, botRestrictions, files_data,
            website_data, prompt_snapshot, api_key, script , allowedDomains,
            primaryColor, position, themeStyle, suggestedPrompts, 
            coreFeatures, leadCaptureFields,
            chatbotLanguage, logo_url, botAvatar, personaSelect, 
            defaultFailResponse, botTypePreset, faq_data, appointment_settings
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s,%s,%s,%s,%s,%s,%s)
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
            company_data['botRestrictions'],  
            company_data['files_data'],
            company_data['website_data'],
            company_data['prompt_snapshot'],
            company_data['api_key'],
            company_data['script'],
            company_data['allowedDomains'],
            company_data.get('primaryColor', '#4f46e5'),
            company_data.get('position', 'Bottom Right'),
            company_data.get('themeStyle', 'Minimal'),
            company_data.get('suggestedPrompts', ''),
            json.dumps(company_data.get('coreFeatures', {})),
            json.dumps(company_data.get('leadCaptureFields', {})),
            company_data.get('chatbotLanguage', ''),
            company_data.get('logo_url', ''),     # ✅ εδώ
            company_data.get('botAvatar', ''), 
            company_data.get('personaSelect', ''),
            company_data.get('defaultFailResponse', ''),
            company_data.get('botTypePreset', ''),
            company_data.get('faq_data', '[]'),
            company_data.get('appointment_settings', '{}') 
        )
        
        cursor.execute(insert_sql, values)
        conn.commit()
        
        print(f"✅ Company '{company_data['companyName']}' inserted successfully")
        return True
        
    
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
        
        select_sql = "SELECT * FROM companies WHERE api_key = %s"
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
        
        update_sql = "UPDATE companies SET script = %s WHERE companyName = %s"
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
    botName: str
    botRestrictions: str
    keywords:str
    allowedDomains:str
    primaryColor: Optional[str] = "#4f46e5"
    position: Optional[str] = "Bottom Right"
    themeStyle: Optional[str] = "Minimal"
    suggestedPrompts: Optional[str] = ""
    coreFeatures: Optional[dict] = Field(default_factory=dict)
    leadCaptureFields: Optional[dict] = Field(default_factory=dict)
    chatbotLanguage: Optional[str] = ""
    personaSelect: Optional[str] = ""
    defaultFailResponse: Optional[str] = ""
    botTypePreset: Optional[str] = ""
    faqItems: Optional[List[dict]] = Field(default_factory=list)
    appointmentSettings: Optional[dict] = Field(default_factory=dict)

API_BASE = os.getenv('API_BASE')
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
                      api_key:str,response_time_ms: Optional[float] = None) -> None:
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
        "api_key": api_key,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    if response_time_ms is not None:
        event_data["response_time_ms"] = response_time_ms
    
    # Στέλνει το event στο Redis Stream
    redis_client.xadd("chat_events", event_data)

    try:
        redis_client.hincrby(f"stats:{api_key}", "total_messages", 1)

        if role == "user":
            redis_client.hincrby(f"stats:{api_key}", "total_user_messages", 1)
        elif role == "assistant":
            redis_client.hincrby(f"stats:{api_key}", "total_assistant_messages", 1)
        
#Ενημερώνει μέσο χρόνο απόκρισης
            if response_time_ms is not None:
                redis_client.hincrbyfloat(f"response_stats:{api_key}", "total_time", response_time_ms/1000)
            
                total_time = float(redis_client.hget(f"response_stats:{api_key}", "total_time") or 0)
                assistant_count = int(redis_client.hget(f"stats:{api_key}", "total_assistant_messages") or 0)
            
                if assistant_count > 0:
                    new_avg = total_time / assistant_count
                    redis_client.hset(f"response_stats:{api_key}", "avg", new_avg)
        #last meessage time
        redis_client.hset(f"stats:{api_key}", "last_message_at", datetime.now(timezone.utc).isoformat())

        
    except Exception as e:
        logger.error(f"Failed to update counters: {e}")

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

    # ΠΡΟΣΘΗΚΗ - Track active session για γρήγορο counting
    pipe.sadd(f"active_sessions:{api_key}", session_id)
    pipe.expire(f"active_sessions:{api_key}", 1800)  # 30 λεπτά TTL
    
    pipe.execute()

#migration κάθε μέρα




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
        redis_client.hincrby(f"stats:{api_key}", "total_sessions", 1) #προσθέτει +1 στο total session

    else:
        session_id = message_data.session_id
        logger.info(f"Continuing widget session: {session_id}")

# Publish user message event
    publish_chat_event(
        session_id=session_id,
        role="user", 
        content=message_data.message,
        api_key=api_key,
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
                api_key=api_key,
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
    files: List[UploadFile] = File(default=[]),
    logo: UploadFile = File(None),     # ← Company logo
    botAvatar: UploadFile = File(None) # ← Bot avatar
):
    try:
        
        # Parse το JSON string
        company_data = json.loads(company_info)
        # Δημιουργία CompanyInfo object με validation
        company_info_obj = CompanyInfo(**company_data)

        companies_db[company_info_obj.companyName] = company_info_obj
        print(f"✅ Company '{company_info_obj.companyName}' registered")

        # Process FAQ data
        faq_items = company_data.get('faqItems', [])
        print(f"📝 Received {len(faq_items)} FAQ items")

# Convert FAQ to text format for system prompt
        faq_text = ""
        if faq_items:
            faq_text = "\n=== FAQ SECTION ===\n"
            for item in faq_items:
                faq_text += f"Q: {item.get('question', '')}\nA: {item.get('answer', '')}\n\n"
            print(f"📝 FAQ text prepared: {len(faq_text)} characters")

        logo_data = ""
        if logo:
            logo_content = await logo.read()
            logo_base64 = base64.b64encode(logo_content).decode('utf-8')
            logo_data = f"data:{logo.content_type};base64,{logo_base64}"

       # Handle bot avatar
        bot_avatar_data = ""
        if botAvatar:
            avatar_content = await botAvatar.read()
            avatar_base64 = base64.b64encode(avatar_content).decode('utf-8')
            bot_avatar_data = f"data:{botAvatar.content_type};base64,{avatar_base64}"


        print(f"🔄 Starting scraping for: {company_info_obj.websiteURL}")
        scraper = ScrapingController()
        scraped_data = await scraper.scrape_website_async(str(company_info_obj.websiteURL))
        
        #json_filename = f"company_data/{company_info_obj.companyName}_scraped_data.json"
        #os.makedirs(os.path.dirname(json_filename), exist_ok=True)
        
        #with open(json_filename, "w", encoding="utf-8") as f:
        #    json.dump(scraped_data, f, indent=2, ensure_ascii=False)
        #print(f"✅ Scraped data saved to: {json_filename}")
        
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
            personaSelect=company_info_obj.personaSelect,
            botRestrictions=company_info_obj.botRestrictions,
            faq_text=faq_text,
            botTypePreset=company_data.get('botTypePreset', ''),
            coreFeatures=company_info_obj.coreFeatures or {},
            leadCaptureFields=company_info_obj.leadCaptureFields or {}
        )
        print(f"✅ System prompt created ({len(system_prompt)} characters)")
        
        # Δημιουργία Widget Script
        print(f"🎨 Δημιουργία widget script...")
        domain = os.getenv('WIDGET_DOMAIN') 
        widget_script = f'<script src="{domain}/widget.js?key={api_key}"></script>'
        print(f"✅ Widget script created")
        
        # Προετοιμασία δεδομένων για βάση
        company_data_for_db = {
            'companyName': company_info_obj.companyName,
            'websiteURL': str(company_info_obj.websiteURL),
            'industry': company_info_obj.industry,
            'industryOther': company_info_obj.industryOther or '',
            'description': company_info_obj.description,
            'botName': company_info_obj.botName,         
            'greeting': company_info_obj.greeting,
            'botRestrictions': company_info_obj.botRestrictions,  
            'files_data': files_content,
            'website_data': website_data,
            'prompt_snapshot': system_prompt,
            'api_key': api_key,
            'script': widget_script,
            'allowedDomains': company_info_obj.allowedDomains,
            'primaryColor': company_info_obj.primaryColor, 
            'position': company_info_obj.position,
            'themeStyle': company_info_obj.themeStyle,
            'suggestedPrompts': company_info_obj.suggestedPrompts,
            'coreFeatures': company_info_obj.coreFeatures,
            'leadCaptureFields': company_info_obj.leadCaptureFields,
            'chatbotLanguage': company_data.get('chatbotLanguage', ''),
            'logo_url': logo_data,
            'botAvatar': bot_avatar_data,
            'personaSelect': company_data.get('personaSelect', ''),
            'defaultFailResponse': company_data.get('defaultFailResponse', ''),
            'botTypePreset': company_data.get('botTypePreset', ''),
            'faq_data': json.dumps(faq_items),
            'appointment_settings': json.dumps(company_data.get('appointmentSettings', {}))
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








@app.get("/widget.js")
async def serve_widget(request: Request, key: str = Query(...)):
    try:
        company_data = get_company_by_api_key(key)
        if not company_data:
            raise HTTPException(status_code=403, detail="Invalid API key")
        # Load leadForm.js content
        try:
            with open("templates/leadForm.js", "r", encoding="utf-8") as f:
                lead_form_js = f.read()
        except FileNotFoundError:
            lead_form_js = "console.warn('leadForm.js not found');"
        
        # load appointmentForm.js
        try:
            with open("templates/appointmentForm.js", "r", encoding="utf-8") as f:
                appointment_form_js = f.read()
        except FileNotFoundError:
            appointment_form_js = "console.warn('appointmentForm.js not found');"



        return templates.TemplateResponse(
            "widget.js.j2",
            {
                "request": request,
                "company_display_name": company_data['botName'],
                "greeting": company_data['greeting'],
                "api_key": key,
                "api_base": API_BASE, 
                "primary_color": company_data['primaryColor'],
                "appointment_form_js": appointment_form_js,
                "lead_form_js": lead_form_js
            },
            media_type="application/javascript"
        )
        
    except Exception as e:
        print(f"⚠️ Widget error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Widget generation failed: {str(e)}")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    try:
        with open("dashboard.html", "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Dashboard file not found")

@app.get("/api/analytics/overview")
async def get_analytics_overview():
    try:
        # Total messages count
        total_messages = await analytics_db.chat_events.count_documents({})
        
        # Active chatbots (distinct company_name - api_key combinations)
        active_chatbots_pipeline = [
            {"$group": {"_id": {"company_name": "$company_name", "api_key": "$api_key"}}},
            {"$count": "total"}
        ]
        active_chatbots_result = await analytics_db.chat_events.aggregate(active_chatbots_pipeline).to_list(length=1)
        active_chatbots = active_chatbots_result[0]["total"] if active_chatbots_result else 0
        
        # Average response time (only for assistant messages)
        avg_response_pipeline = [
            {"$match": {"role": "assistant", "response_time_ms": {"$exists": True, "$ne": None}}},
            {"$group": {"_id": None, "avg_response": {"$avg": "$response_time_ms"}}}
        ]
        avg_response_result = await analytics_db.chat_events.aggregate(avg_response_pipeline).to_list(length=1)
        avg_response_time = avg_response_result[0]["avg_response"] if avg_response_result else 0
        
        return {
            "total_messages": total_messages,
            "active_chatbots": active_chatbots,
            "avg_response_time_ms": round(avg_response_time, 2) if avg_response_time else 0
        }
        
    except Exception as e:
        logger.error(f"Error fetching overview analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch analytics data")




@app.get("/api/analytics/company")
async def get_company_analytics(
    api_key: str = Query(..., description="Το API key του chatbot")
    ):
   
    
    try:
        # Βρες company info
        company_data = get_company_by_api_key(api_key)
        if not company_data:
            raise HTTPException(status_code=404, detail="Invalid API key")
        
        company_name = company_data['companyName']

        # 1. Today data από Redis (real-time)
        today_stats = redis_client.hgetall(f"stats:{api_key}")
        today_ratings = redis_client.hgetall(f"ratings:{api_key}")
        today_response = redis_client.hgetall(f"response_stats:{api_key}")

        today_messages = int(today_stats.get('total_messages', 0))
        today_user_messages = int(today_stats.get('total_user_messages', 0))
        today_assistant_messages = int(today_stats.get('total_assistant_messages', 0))
        today_sessions = int(today_stats.get('total_sessions', 0))

        today_ratings_sum = int(today_ratings.get('sum', 0))
        today_ratings_count = int(today_ratings.get('count', 0))
        today_avg_rating = today_ratings_sum / today_ratings_count if today_ratings_count > 0 else None
        today_avg_response_time = float(today_response.get('avg', 0))

# Real-time metrics
        active_sessions = redis_client.scard(f"active_sessions:{api_key}")
        last_message_at = redis_client.hget(f"stats:{api_key}", "last_message_at")

        # Συλλογή ιστορικών δεδομένων από MySQL
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Παίρνε συνολικά δεδομένα από total_analytics
        cursor.execute("SELECT * FROM total_analytics WHERE api_key = %s", (api_key,))
        historical_data = cursor.fetchone()
        
        

        # Συνδυασμός ιστορικών + σημερινών
        if historical_data:
            historical_messages = historical_data['total_messages']
            historical_user_messages = historical_data['total_user_messages']
            historical_assistant_messages = historical_data['total_assistant_messages']
            historical_sessions = historical_data['total_sessions']
            historical_ratings_sum = historical_data['total_ratings_sum']
            historical_ratings_count = historical_data['total_ratings_count']
            historical_avg_rating = historical_data['total_avg_rating']
            historical_avg_response_time = historical_data['total_avg_response_time']
            historical_response_time_sum = historical_data['total_response_time_sum']
        else:
            historical_messages = 0
            historical_user_messages = 0
            historical_assistant_messages = 0
            historical_sessions = 0
            historical_ratings_sum = 0
            historical_ratings_count = 0
            historical_avg_rating = 0
            historical_avg_response_time = 0
            historical_response_time_sum = 0
        
            

        cursor.execute("""
            SELECT * FROM daily_analytics 
            WHERE api_key = %s 
            ORDER BY date DESC 
            LIMIT 1
        """, (api_key,))

        yesterday_data = cursor.fetchone()

        conn.close()

        if yesterday_data:
            yesterday_messages = yesterday_data['total_messages']
            yesterday_user_messages = yesterday_data['user_messages']
            yesterday_assistant_messages = yesterday_data['assistant_messages']
            yesterday_sessions = yesterday_data['total_sessions']
            yesterday_ratings_sum = yesterday_data['daily_ratings_sum']
            yesterday_ratings_count = yesterday_data['daily_ratings_count']
            yesterday_avg_rating = yesterday_data['daily_avg_rating']
            yesterday_avg_response_time = yesterday_data['daily_avg_response_time']
            yesterday_response_time_sum = yesterday_data['daily_response_time_sum']
        else:
            yesterday_messages = yesterday_user_messages = yesterday_assistant_messages = yesterday_sessions = yesterday_ratings_sum = yesterday_ratings_count = yesterday_avg_rating = yesterday_avg_response_time = 0
            yesterday_response_time_sum = 0

        # Υπολογισμός συνολικών = Historical + Today
        if historical_data:
            total_messages = historical_messages + today_messages
            total_user_messages = historical_user_messages + today_user_messages
            total_assistant_messages = historical_assistant_messages + today_assistant_messages
            total_sessions = historical_sessions + today_sessions
    
    # Ratings συνολικά
            total_ratings_sum = historical_ratings_sum + today_ratings_sum
            total_ratings_count = historical_ratings_count + today_ratings_count
            total_avg_rating = total_ratings_sum / total_ratings_count if total_ratings_count > 0 else None
    
    # Response time συνολικά
            today_response_time_sum = float(today_response.get('total_time', 0))
            total_response_time_sum = historical_response_time_sum + today_response_time_sum
            total_avg_response_time = total_response_time_sum / total_assistant_messages if total_assistant_messages > 0 else 0
        else:
    # Μόνο σημερινά
            total_messages = today_messages
            total_user_messages = today_user_messages
            total_assistant_messages = today_assistant_messages
            total_sessions = today_sessions
            total_ratings_sum = today_ratings_sum
            total_ratings_count = today_ratings_count
            total_avg_rating = today_avg_rating
    
            today_response_time_sum = float(today_response.get('total_time', 0))
            total_avg_response_time = today_response_time_sum / today_assistant_messages if today_assistant_messages > 0 else 0
        # Δημιουργία response
        return {
            "company_name": company_name,
            "api_key": api_key,
    
    # Συνολικά metrics
            "total_messages": total_messages,
            "total_user_messages": total_user_messages,
            "total_assistant_messages": total_assistant_messages,
            "total_sessions": total_sessions,
            "total_avg_rating": total_avg_rating,
            "total_ratings_count": total_ratings_count,
            "total_avg_response_time_seconds": round(total_avg_response_time, 2),
    
    # Χθεσινά metrics
            "yesterday_messages": yesterday_messages,
            "yesterday_user_messages": yesterday_user_messages,
            "yesterday_assistant_messages": yesterday_assistant_messages,
            "yesterday_sessions": yesterday_sessions,
            "yesterday_avg_rating": yesterday_avg_rating,
            "yesterday_ratings_count": yesterday_ratings_count,
    
    # Σημερινά metrics
            "today_messages": today_messages,
            "today_user_messages": today_user_messages,
            "today_assistant_messages": today_assistant_messages,
            "today_sessions": today_sessions,
            "today_avg_rating": today_avg_rating,
            "today_ratings_count": today_ratings_count,
    
    # Real-time metrics
            "active_sessions": active_sessions,
            "avg_response_time_seconds": round(today_avg_response_time, 2),
            "last_message_at": last_message_at
  }
    
    except Exception as e:
        logger.error(f"Error fetching analytics for {api_key}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch analytics data")
        
        

@app.get("/dashboard/{api_key}", response_class=HTMLResponse)
async def dashboard_for_company(request: Request, api_key: str):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "api_key": api_key}
    )


#Αξιολόγηση
@app.post("/rating")
async def rating(
    request: Request,
    api_key: str=Query(...),
    data: dict = Body(...)
):
    try:
        company_data = get_company_by_api_key(api_key)
        if not company_data:
            return {"status": "error", "message": "invalid api key"}
            
        # Domain validation
        if not validate_domain(request, company_data.get('allowedDomains', '')):
            return {"status": "error", "message": "domain not allowed"}
        
        rating_value = int(data.get("rating", 0))
        session_id = data.get("session_id")

        if not (1 <= rating_value <= 5):
            return {"status": "error", "message": "invalid rating"}

        # Αποθήκευση counters στη Redis
        redis_client.hincrby(f"ratings:{api_key}", "count", 1)
        redis_client.hincrby(f"ratings:{api_key}", "sum", rating_value)

        # (προαιρετικά) αν θες να ξέρεις και ποιο session έδωσε rating:
        redis_client.set(f"rated:{session_id}", "1", ex=1800)  # TTL 30 λεπτά

        return {"status": "ok", "message": "rating stored"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

#έλεγχος αν έχει αξιολόγησει ο χρήστης   
@app.get("/api/has_rated")
async def has_rated(api_key: str, session_id: str):
    """
    Επιστρέφει true αν το συγκεκριμένο session έχει ήδη δώσει rating
    """
    has_rated = bool(redis_client.get(f"rated:{session_id}"))
    return {"hasRated": has_rated}

@app.post("/submit-lead")
async def submit_lead(request: Request, api_key: str = Query(...)):
    try:
        company_data = get_company_by_api_key(api_key)
        if not company_data:
            raise HTTPException(status_code=403, detail="Invalid API key")
        
        # Domain validation
        if not validate_domain(request, company_data.get('allowedDomains', '')):
            raise HTTPException(status_code=403, detail="Domain not allowed")
        
        # Parse JSON body
        body = await request.json()
        lead_data = body.get('leadData', {})
        company_name = body.get('companyName', company_data['companyName'])
        
        # Log lead capture (for now just console, later can save to database)
        logger.info(f"📝 Lead captured for {company_name}: {lead_data}")
        
        return {"status": "success", "message": "Lead data received"}
        
    except Exception as e:
        logger.error(f"Lead submission error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save lead data")
    
from calendar_helper import GoogleCalendarHelper

@app.get("/calendar-auth/{api_key}")
async def calendar_auth(api_key: str):
    """Δημιουργεί auth URL για συγκεκριμένη εταιρεία"""
    company_data = get_company_by_api_key(api_key)
    if not company_data:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    calendar_helper = GoogleCalendarHelper(api_key)
    auth_url = calendar_helper.get_auth_url()
    
    if auth_url:
        # Προσθέτουμε state parameter για να ξέρουμε ποια εταιρεία είναι
        return {"auth_url": auth_url}
    else:
        raise HTTPException(status_code=500, detail="Failed to create auth URL")

@app.get("/oauth2callback")
async def oauth2_callback(code: str | None = None, state: str | None = None):
    """Callback από Google OAuth - state περιέχει το api_key (popup flow)"""
    # helper για να γυρνάμε μικρό HTML που ενημερώνει τον opener και κλείνει το popup
    def post_message_and_close(js_obj_literal: str) -> HTMLResponse:
        return HTMLResponse(f"""
<!doctype html><html><head><meta charset="utf-8"/></head><body>
<script>
  try {{
    if (window.opener && !window.opener.closed) {{
      window.opener.postMessage({js_obj_literal}, "*");
    }}
  }} catch (e) {{}}
  window.close();
</script>
<p>Μπορείτε να κλείσετε αυτό το παράθυρο.</p>
</body></html>
        """.strip())

    if not state or not code:
        # στέλνουμε error προς τον parent
        return post_message_and_close("{ type: 'gcal_error', reason: 'missing_state_or_code' }")

    try:
        calendar_helper = GoogleCalendarHelper(state)  # state = api_key
        credentials = calendar_helper.get_credentials_from_code(code)
        if not credentials:
            return post_message_and_close("{ type: 'gcal_error', reason: 'invalid_grant' }")

        saved = calendar_helper.save_credentials_to_db(credentials)
        if not saved:
            return post_message_and_close("{ type: 'gcal_error', reason: 'save_failed' }")

        # ✅ Επιτυχία: ενημέρωσε τον parent και κλείσε το popup
        return post_message_and_close(f"{{ type: 'gcal_connected', api_key: '{state}' }}")

    except Exception:
        return post_message_and_close("{ type: 'gcal_error', reason: 'exception' }")


@app.get("/available-slots/{api_key}")
async def get_available_slots(api_key: str, date: str = Query(...)):
    company_data = get_company_by_api_key(api_key)
    if not company_data:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    appointment_settings = {}
    try:
        if company_data.get('appointment_settings'):
            appointment_settings = json.loads(company_data['appointment_settings'])
    except:
        pass
    
    calendar_helper = GoogleCalendarHelper(api_key)
    if not calendar_helper.load_credentials():
        raise HTTPException(status_code=409, detail="Calendar is not connected for this company")
    
    slots = calendar_helper.get_available_slots(date, appointment_settings)
    
    return {"available_slots": slots, "date": date}

@app.post("/create-appointment/{api_key}")
async def create_appointment(api_key: str, payload: Dict[str, Any] = Body(...)):
    """
    Δημιουργεί νέο ραντεβού στο Google Calendar της εταιρείας με το συγκεκριμένο api_key.
    Αναμένει JSON body από το appointmentForm.js, π.χ.:
    {
      "name": "Ονοματεπώνυμο",
      "email": "user@example.com",
      "phone": "6900000000",
      "appointment_date": "2025-09-25",     # (χρησιμοποιείται μόνο για slots)
      "start_datetime": "2025-09-25T11:00:00",  # ISO (local) από επιλογή slot
      "notes": "Προαιρετικό μήνυμα"
    }
    """
    # 1) Εύρεση εταιρείας & έλεγχος εγκυρότητας api_key
    company_data = get_company_by_api_key(api_key)
    if not company_data:
        raise HTTPException(status_code=403, detail="Invalid API key")

    # 2) Φόρτωση Google credentials της εταιρείας
    helper = GoogleCalendarHelper(api_key=api_key)
    creds = helper.load_credentials()
    if not creds:
        # Δεν έχει ολοκληρωθεί το OAuth για αυτή την εταιρεία
        raise HTTPException(status_code=409, detail="Calendar is not connected for this company")

    # 3) Ανάγνωση/έλεγχος πεδίων από το body
    start_datetime = payload.get("start_datetime")  # απαιτείται — ISO string
    if not start_datetime:
        raise HTTPException(status_code=400, detail="Missing 'start_datetime'")

    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip()
    phone = (payload.get("phone") or "").strip()
    notes = (payload.get("notes") or "").strip()

    # 4) Τίτλος & περιγραφή event (προσαρμόσιμα)
    company_display = company_data.get("botName") or company_data.get("companyName") or "Appointment"
    title = f"Ραντεβού με {name or 'Πελάτη'} - {company_display}"
    description_parts = []
    if notes:
        description_parts.append(f"Σημειώσεις: {notes}")
    if name:
        description_parts.append(f"Όνομα: {name}")
    if email:
        description_parts.append(f"Email: {email}")
    if phone:
        description_parts.append(f"Τηλέφωνο: {phone}")
    description = "\n".join(description_parts) if description_parts else "Αυτόματο ραντεβού από chatbot."

    # 5) Δημιουργία event (διάρκεια 60’ προεπιλογή)
    # Parse appointment settings για τη διάρκεια  
    appointment_settings = {}
    try:
        if company_data.get('appointment_settings'):
            appointment_settings = json.loads(company_data['appointment_settings'])
    except:
        pass

    duration = appointment_settings.get('slotDuration', 60)  # Default 60 λεπτά

# 5) Δημιουργία event με dynamic διάρκεια
    try:
        event_id = helper.create_event(
            title=title,
            description=description,
            start_datetime=start_datetime,   # π.χ. "2025-09-25T11:00:00"
            duration_minutes=duration,  # Χρήση της διάρκειας από settings
            attendee_email=email if email else None
      )
    except Exception as e:
    # Λογικά σφάλματα API, timezones, κ.λπ.
        raise HTTPException(status_code=500, detail=f"Failed to create event: {str(e)}")

        if not event_id:
            raise HTTPException(status_code=500, detail="Calendar event not created")

    # 6) Επιτυχής απόκριση
    return {
        "status": "ok",
        "event_id": event_id,
        "message": "Το ραντεβού δημιουργήθηκε επιτυχώς."
    }


