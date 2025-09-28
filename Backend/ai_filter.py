import os
import json
from typing import Dict, List, Any, Optional
from openai import OpenAI
import time
from dotenv import load_dotenv

load_dotenv()

class AIContentFilter:
    """
    AI-powered content filter που καθαρίζει scraped content από άσχετα στοιχεία
    """
    
    def __init__(self):
        """
        Αρχικοποίηση του AI Filter με OpenAI client
        """
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4-turbo"
    
    def process_page_content(self, title: str, plain_text: str, url: str) -> str:
        """
        Επεξεργάζεται το περιεχόμενο μιας σελίδας με AI
        
        Args:
            title: Ο τίτλος της σελίδας
            plain_text: Το καθαρό κείμενο της σελίδας
            url: Το URL της σελίδας
            
        Returns:
            str: Καθαρό, relevant περιεχόμενο
        """
        if not plain_text or len(plain_text.strip()) == 0:
            return ""
        
        # Δημιουργία του prompt για το AI
        prompt = f"""
Παρακαλώ καθάρισε το παρακάτω περιεχόμενο ιστοσελίδας αφαιρώντας:
- Navigation menus και links
- Footers και headers
- Cookie notices και pop-ups
- Social media buttons
- Advertisements
- Άσχετα στοιχεία UI

Κράτησε μόνο το κύριο, χρήσιμο περιεχόμενο που αφορά την εταιρεία, τις υπηρεσίες, ή τα προϊόντα.

URL: {url}
Τίτλος: {title}

Περιεχόμενο προς καθαρισμό:
{plain_text[:4000]}  

Απάντησε μόνο με το καθαρό περιεχόμενο, χωρίς επεξηγήσεις:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "Είσαι ένας expert content curator. Καθαρίζεις web content κρατώντας μόνο το relevant business information."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.1
            )
            
            cleaned_content = response.choices[0].message.content.strip()
            return cleaned_content if cleaned_content else ""
            
        except Exception as e:
            print(f"Error processing content for {url}: {e}")
            # Σε περίπτωση σφάλματος, επιστρέφουμε το original text (truncated)
            return plain_text[:1000] + "..." if len(plain_text) > 1000 else plain_text
    
    def filter_all_pages(self, scraped_data: Dict[str, Any]) -> str:
        """
        Επεξεργάζεται όλες τις σελίδες από το scraped JSON data
        
        Args:
            scraped_data: Το JSON data από το scraping
            
        Returns:
            str: Ενοποιημένο καθαρό περιεχόμενο όλων των σελίδων
        """
        all_clean_content = []
        
        # Επεξεργασία main page
        main_page = scraped_data.get("main_page", {})
        if main_page.get("status") == "success":
            title = main_page.get("title", "")
            plain_text = main_page.get("plain_text", "")
            url = main_page.get("url", "")
            
            if plain_text:
                print(f"Processing main page: {url}")
                clean_content = self.process_page_content(title, plain_text, url)
                if clean_content:
                    all_clean_content.append(f"=== MAIN PAGE: {title} ===\nURL: {url}\n{clean_content}\n")
        
        # Επεξεργασία discovered links
        discovered_links = scraped_data.get("discovered_links", [])
        for i, link_data in enumerate(discovered_links):
            if link_data.get("status") == "success":
                title = link_data.get("title", "")
                plain_text = link_data.get("plain_text", "")
                url = link_data.get("url", "")
                
                if plain_text:
                    print(f"Processing link {i+1}/{len(discovered_links)}: {url}")
                    clean_content = self.process_page_content(title, plain_text, url)
                    if clean_content:
                        all_clean_content.append(f"=== PAGE: {title} ===\nURL: {url}\n{clean_content}\n")
                    
                    # Μικρή παύση για να αποφύγουμε rate limiting
                    time.sleep(1)
        
        # Ενοποίηση όλου του περιεχομένου
        final_content = "\n" + "="*50 + "\n".join(all_clean_content)
        
        print(f"AI filtering completed. Total clean content length: {len(final_content)} characters")
        return final_content


    def smart_batch_filter_all_pages(self, scraped_data: Dict[str, Any]) -> str:

        all_pages_data = []
    
    # Συλλογή δεδομένων από main page
        main_page = scraped_data.get("main_page", {})
        if main_page.get("status") == "success":
            title = main_page.get("title", "")
            plain_text = main_page.get("plain_text", "")[:4000]
            url = main_page.get("url", "")
        
            if plain_text:
                all_pages_data.append({
                    "title": title,
                    "url": url,
                    "content": plain_text
                })
    
    # Συλλογή δεδομένων από discovered links
        discovered_links = scraped_data.get("discovered_links", [])
        for link_data in discovered_links:
            if link_data.get("status") == "success":
                title = link_data.get("title", "")
                plain_text = link_data.get("plain_text", "")[:4000]
                url = link_data.get("url", "")
            
                if plain_text:
                    all_pages_data.append({
                        "title": title,
                        "url": url,
                        "content": plain_text
                    })
    
        if not all_pages_data:
            return ""
    
        print(f"Smart batch filtering: Processing {len(all_pages_data)} pages in smaller batches")
    
    # Χωρισμός σε batches των 10 σελίδων
        batch_size = 3
        all_clean_content = []
    
        for i in range(0, len(all_pages_data), batch_size):
            batch = all_pages_data[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(all_pages_data) + batch_size - 1) // batch_size
        
            print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} pages)")
        
            try:
                batch_result = self._process_single_batch(batch, batch_num)
                if batch_result:
                    all_clean_content.extend(batch_result)
            except Exception as e:
                print(f"Error in batch {batch_num}: {e}")
                # Fallback: process pages individually
                print(f"Fallback: Processing batch {batch_num} pages individually")
                for page in batch:
                    try:
                        clean_content = self.process_page_content(
                            page['title'], 
                            page['content'], 
                            page['url']
                        )
                        if clean_content:
                            all_clean_content.append(
                                f"=== PAGE: {page['title']} ===\nURL: {page['url']}\n{clean_content}\n"
                            )
                    except Exception as page_error:
                        print(f"Error processing page {page['url']}: {page_error}")
                        continue
    
    # Ενοποίηση όλου του περιεχομένου
        final_content = "\n" + "="*50 + "\n".join(all_clean_content)
    
        print(f"Smart batch filtering completed. Total clean content length: {len(final_content)} characters")
        return final_content

    def _process_single_batch(self, batch_pages: List[Dict], batch_num: int) -> List[str]:

    # Δημιουργία batch content
        batch_content = ""
        for i, page in enumerate(batch_pages):
            batch_content += f"""
===ΣΕΛΙΔΑ {i+1}===
URL: {page['url']}
Τίτλος: {page['title']}
Περιεχόμενο: {page['content']}

---PAGE-SEPARATOR---

    """
    
    # API call για το batch
        prompt = f"""
Παρακαλώ καθάρισε τα παρακάτω περιεχόμενα ιστοσελίδων αφαιρώντας:
- Navigation menus και links
- Footers και headers  
- Cookie notices και pop-ups
- Social media buttons
- Advertisements
- Άσχετα στοιχεία UI

Κράτησε μόνο το κύριο, χρήσιμο περιεχόμενο για κάθε σελίδα.

{batch_content}

Απάντησε με καθαρό περιεχόμενο για κάθε σελίδα, χωρισμένα με ---PAGE-SEPARATOR---:"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system", 
                    "content": "Είσαι expert content curator. Καθαρίζεις web content κρατώντας μόνο relevant business information."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            max_tokens=4000,
            temperature=0.1
        )
    
        batch_result = response.choices[0].message.content.strip()
    
    # Parse το batch result
        clean_sections = batch_result.split("---PAGE-SEPARATOR---")
        formatted_results = []
    
        for i, section in enumerate(clean_sections):
            if section.strip() and i < len(batch_pages):
                page_info = batch_pages[i]
                formatted_results.append(
                    f"=== PAGE: {page_info['title']} ===\n"
                    f"URL: {page_info['url']}\n"
                    f"{section.strip()}\n"
                )
    
        return formatted_results

    def process_json_file(self, json_file_path: str) -> str:
        """
        Διαβάζει JSON αρχείο και το επεξεργάζεται με AI
        
        Args:
            json_file_path: Path προς το JSON αρχείο
            
        Returns:
            str: Καθαρό περιεχόμενο
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                scraped_data = json.load(f)
            
            return self.filter_all_pages(scraped_data)
            
        except Exception as e:
            print(f"Error processing JSON file {json_file_path}: {e}")
            return ""

# Helper function για εύκολη χρήση
def filter_scraped_content(json_file_path: str) -> str:
    """
    Convenience function για filtering scraped content
    
    Args:
        json_file_path: Path προς το JSON αρχείο με scraped data
        
    Returns:
        str: Καθαρό περιεχόμενο
    """
    filter_instance = AIContentFilter()
    return filter_instance.process_json_file(json_file_path)
