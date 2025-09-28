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

openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
website_data_db: Dict[str, str] = {}
files_data_db: Dict[str, str] = {}      
chat_history_db: Dict[str, List[Dict]] = defaultdict(list)  
companies_db: Dict[str, CompanyInfo] = {}

@app.post("/register_company")
async def register_company(company_info: CompanyInfo):
    companies_db[company_info.companyName] = company_info
    return {"message": f"Company '{company_info.companyName}' registered successfully."}

class ScrapingRequest(BaseModel):
    websiteURL: HttpUrl
    companyName: str

@app.post("/scrape_website")
async def start_scraping(request: ScrapingRequest):
    try:
        scraper = ScrapingController()
        target_url = str(request.websiteURL)
        print(f"Starting scraping for URL: {request.websiteURL}")
        scraped_data = scraper.scrape_website(target_url)
        print("Scraping finished successfully.")
        
        json_filename = f"company_data/{request.companyName}_scraped_data.json"
        os.makedirs(os.path.dirname(json_filename), exist_ok=True)
        
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(scraped_data, f, indent=2, ensure_ascii=False)
        
        return {"message": f"Scraping completed for {request.companyName}", "data": scraped_data}
    except Exception as e:
        print(f"Error during scraping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
=== ΠΛΗΡΟΦΟΡΙΕΣ ΙΣΤΟΤΟΠΟΥ ===
{website_data}

=== ΠΛΗΡΟΦΟΡΙΕΣ ΑΠΟ ΑΡΧΕΙΑ ===
{files_data}

=== ΠΕΡΙΓΡΑΦΗ ΕΤΑΙΡΙΑΣ ===
{company.description}

=== ΣΥΧΝΕΣ ΕΡΩΤΗΣΕΙΣ ===
{company.questions}

=== ΠΡΟΣΩΠΙΚΟΤΗΤΑ ===
{company.persona}

=== ΣΥΜΠΕΡΙΦΟΡΑ ===
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
