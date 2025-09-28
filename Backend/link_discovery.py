"""
Link Explorer Module
Extracts and processes links from a given URL using Selenium WebDriver.
"""

import re
import time
import traceback
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse, urlunparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException


class LinkExplorer:
    """
    A class to explore and extract links from web pages using Selenium.
    """
    
    def __init__(self, headless: bool = True, wait_timeout: int = 10):
        """
        Initialize the LinkExplorer.
        
        Args:
            headless (bool): Whether to run Chrome in headless mode
            wait_timeout (int): Maximum time to wait for page elements
        """
        self.headless = headless
        self.wait_timeout = wait_timeout
        self.driver = None
    
    def _setup_driver(self) -> webdriver.Chrome:
        """Set up Chrome WebDriver with appropriate options."""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless')
        
        # Standard Chrome options for better compatibility
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        return webdriver.Chrome(options=chrome_options)
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL by adding protocol if missing."""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and not a fragment or JavaScript link."""
        if not url or url.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
            return False
        
        try:
            parsed = urlparse(url)
            return bool(parsed.netloc or parsed.path)
        except Exception:
            return False
    
    def _clean_and_resolve_url(self, link_url: str, base_url: str) -> Optional[str]:
        """Clean and resolve relative URLs to absolute URLs."""
        if not self._is_valid_url(link_url):
            return None
        
        try:
            # Resolve relative URLs
            absolute_url = urljoin(base_url, link_url)
            
            # Parse and clean the URL
            parsed = urlparse(absolute_url)
            
            # Remove fragment (everything after #)
            cleaned_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                ''  # Remove fragment
            ))
            
            return cleaned_url
        except Exception as e:
            print(f"Error cleaning URL '{link_url}': {e}")
            return None
    
    def _filter_links(self, links: List[str], base_domain: str, 
                     include_external: bool = False,
                     exclude_patterns: List[str] = None) -> List[str]:
        """
        Filter links based on various criteria.
        
        Args:
            links: List of URLs to filter
            base_domain: The original domain to compare against
            include_external: Whether to include external links
            exclude_patterns: List of regex patterns to exclude
        """
        if exclude_patterns is None:
            exclude_patterns = [
                r'\.(pdf|doc|docx|xls|xlsx|ppt|pptx|zip|rar|tar|gz)$',  # Documents/Archives
                r'\.(jpg|jpeg|png|gif|bmp|svg|ico)$',  # Images
                r'\.(mp3|mp4|avi|mov|wmv|flv|wav)$',  # Media files
                r'/(login|logout|signin|signup|register)',  # Auth pages
                r'/(admin|dashboard|settings|profile)',  # Admin pages
            ]
        
        filtered_links = []
        
        for link in links:
            try:
                parsed = urlparse(link)
                link_domain = parsed.netloc.lower()
                
                # Check if it's external
                if not include_external and link_domain != base_domain:
                    continue
                
                # Check exclude patterns
                if any(re.search(pattern, link, re.IGNORECASE) for pattern in exclude_patterns):
                    continue
                
                filtered_links.append(link)
                
            except Exception as e:
                print(f"Error filtering link '{link}': {e}")
                continue
        
        return filtered_links
    
    def extract_links_from_url(self, 
                              url: str, 
                              wait_for_dynamic_content: int = 5,
                              include_external: bool = False,
                              max_links: int = 50,
                              exclude_patterns: List[str] = None) -> Dict[str, any]:
        """
        Extract all links from a given URL.
        
        Args:
            url: The URL to extract links from
            wait_for_dynamic_content: Seconds to wait for dynamic content to load
            include_external: Whether to include external domain links
            max_links: Maximum number of links to return
            exclude_patterns: Custom regex patterns to exclude
            
        Returns:
            Dictionary containing:
            - 'success': Boolean indicating if extraction was successful
            - 'links': List of extracted URLs
            - 'total_found': Total number of links found before filtering
            - 'base_url': The base URL that was processed
            - 'error': Error message if extraction failed
        """
        url = self._normalize_url(url)
        base_domain = urlparse(url).netloc.lower()
        
        result = {
            'success': False,
            'links': [],
            'total_found': 0,
            'base_url': url,
            'error': None
        }
        
        try:
            # Setup WebDriver
            self.driver = self._setup_driver()
            
            print(f"LinkExplorer: Loading page '{url}'...")
            self.driver.get(url)
            
            # Wait for dynamic content
            if wait_for_dynamic_content > 0:
                time.sleep(wait_for_dynamic_content)
            
            # Find all anchor tags
            link_elements = self.driver.find_elements(By.TAG_NAME, 'a')
            raw_links = []
            
            for element in link_elements:
                try:
                    href = element.get_attribute('href')
                    if href:
                        cleaned_url = self._clean_and_resolve_url(href, url)
                        if cleaned_url:
                            raw_links.append(cleaned_url)
                except Exception as e:
                    print(f"Error processing link element: {e}")
                    continue
            
            # Remove duplicates while preserving order
            unique_links = list(dict.fromkeys(raw_links))
            result['total_found'] = len(unique_links)
            
            print(f"LinkExplorer: Found {len(unique_links)} unique links")
            
            # Filter links
            filtered_links = self._filter_links(
                unique_links, 
                base_domain, 
                include_external, 
                exclude_patterns
            )
            
            # Limit results
            if max_links and len(filtered_links) > max_links:
                filtered_links = filtered_links[:max_links]
                print(f"LinkExplorer: Limited results to {max_links} links")
            
            result['links'] = filtered_links
            result['success'] = True
            
            print(f"LinkExplorer: Returning {len(filtered_links)} filtered links")
            
        except TimeoutException as e:
            error_msg = f"Timeout loading page '{url}': {str(e)}"
            print(f"LinkExplorer: {error_msg}")
            result['error'] = error_msg
            
        except WebDriverException as e:
            error_msg = f"WebDriver error for '{url}': {str(e)}"
            print(f"LinkExplorer: {error_msg}")
            result['error'] = error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error extracting links from '{url}': {str(e)}"
            print(f"LinkExplorer: {error_msg}")
            traceback.print_exc()
            result['error'] = error_msg
            
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception as e:
                    print(f"Error closing WebDriver: {e}")
                self.driver = None
        
        return result


# Convenience functions for easy integration
def get_links_from_url(url: str, 
                      include_external: bool = False,
                      max_links: int = 50,
                      wait_time: int = 5) -> List[str]:
    """
    Simple function to get links from a URL.
    
    Args:
        url: The URL to extract links from
        include_external: Whether to include external links
        max_links: Maximum number of links to return
        wait_time: Seconds to wait for dynamic content
        
    Returns:
        List of URLs found on the page
    """
    explorer = LinkExplorer(headless=True)
    result = explorer.extract_links_from_url(
        url=url,
        wait_for_dynamic_content=wait_time,
        include_external=include_external,
        max_links=max_links
    )
    
    if result['success']:
        return result['links']
    else:
        print(f"Failed to extract links: {result.get('error', 'Unknown error')}")
        return []


def get_detailed_links_info(url: str, 
                           include_external: bool = False,
                           max_links: int = 50) -> Dict[str, any]:
    """
    Get detailed information about links extracted from a URL.
    
    Args:
        url: The URL to extract links from
        include_external: Whether to include external links
        max_links: Maximum number of links to return
        
    Returns:
        Detailed dictionary with extraction results
    """
    explorer = LinkExplorer(headless=True)
    return explorer.extract_links_from_url(
        url=url,
        include_external=include_external,
        max_links=max_links
    )


# Example usage
if __name__ == "__main__":
    # Example 1: Simple link extraction
    test_url = "https://www.lockhill.gr/apxikh.html"
    links = get_links_from_url(test_url, max_links=10)
    print(f"Found {len(links)} links:")
    for i, link in enumerate(links, 1):
        print(f"{i}. {link}")
    
    # Example 2: Detailed extraction with external links
    print("\n" + "="*50)
    detailed_result = get_detailed_links_info(
        test_url, 
        include_external=True, 
        max_links=20
    )
    
    if detailed_result['success']:
        print(f"Successfully extracted {len(detailed_result['links'])} links")
        print(f"Total found before filtering: {detailed_result['total_found']}")
        print("Links:")
        for i, link in enumerate(detailed_result['links'], 1):
            print(f"{i}. {link}")
    else:
        print(f"Extraction failed: {detailed_result['error']}")
