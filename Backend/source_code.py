from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager # For Chrome
# from selenium.webdriver.firefox.service import Service as FirefoxService
# from selenium.webdriver.firefox.options import Options as FirefoxOptions
# from webdriver_manager.firefox import GeckoDriverManager # For Firefox
import time # Optional, for adding explicit waits if needed

def get_website_source_code_selenium(url, wait_for_dynamic_content_seconds=0, headless=True):
    """
    Fetches the HTML source code of a given URL using Selenium,
    allowing JavaScript to execute.

    Args:
        url (str): The URL of the website.
        wait_for_dynamic_content_seconds (int): Optional number of seconds to explicitly
                                               wait after the page loads, to allow
                                               more JavaScript to execute.
                                               Use with caution; explicit waits are
                                               generally less reliable than WebDriverWait.
        headless (bool): If True, runs the browser in headless mode (no visible UI).

    Returns:
        str: The HTML source code as a string, or None if an error occurs.
    """
    # --- Chrome Setup ---
    chrome_options = ChromeOptions()
    if headless:
        chrome_options.add_argument("--headless") # Run in headless mode
    chrome_options.add_argument("--disable-gpu") # Recommended for headless
    chrome_options.add_argument("--no-sandbox") # Bypass OS security model, can be necessary in some environments
    chrome_options.add_argument("--disable-dev-shm-usage") # Overcome limited resource problems
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")


    # Use webdriver_manager to automatically download and manage ChromeDriver
    try:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        print(f"Error setting up Chrome WebDriver: {e}")
        print("Please ensure Google Chrome is installed and webdriver-manager can access the internet.")
        return None

    # --- Firefox Setup (Alternative) ---
    # firefox_options = FirefoxOptions()
    # if headless:
    #     firefox_options.add_argument("--headless")
    # firefox_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/89.0")
    # try:
    #     service = FirefoxService(GeckoDriverManager().install())
    #     driver = webdriver.Firefox(service=service, options=firefox_options)
    # except Exception as e:
    #     print(f"Error setting up Firefox WebDriver: {e}")
    #     print("Please ensure Mozilla Firefox is installed and webdriver-manager can access the internet.")
    #     return None

    try:
        print(f"Navigating to {url} with Selenium...")
        driver.get(url)

        # Optional: Add an explicit wait if you know the page needs more time
        # for specific JavaScript to load content.
        # Using WebDriverWait for a specific element is more robust if possible.
        if wait_for_dynamic_content_seconds > 0:
            print(f"Waiting for {wait_for_dynamic_content_seconds} seconds for dynamic content...")
            time.sleep(wait_for_dynamic_content_seconds)

        # Get the page source after JavaScript has potentially modified the DOM
        html_source = driver.page_source
        return html_source

    except Exception as e:
        print(f"An error occurred with Selenium: {e}")
        return None
    finally:
        if 'driver' in locals() and driver:
            print("Closing browser...")
            driver.quit()

# --- Example Usage ---
# if __name__ == "__main__":
#     target_url = "https://www.conferience.com/eventPage/WM25" # The Conferience event page
#     # target_url = "https://www.example.com" # A simpler page for testing

#     print(f"Fetching source code for: {target_url} using Selenium")

#     # You can adjust the wait time if you suspect a lot of late-loading JS
#     # Set headless=False if you want to see the browser window open
#     html_source = get_website_source_code_selenium(
#         target_url,
#         wait_for_dynamic_content_seconds=3, # Wait 3 seconds after initial load
#         headless=True
#     )

#     if html_source:
#         print("\n----- HTML Source Code (First 1000 characters) -----")
#         print(html_source[:1000] + "...")
#         with open("source.html", "w", encoding="utf-8") as f:
#             f.write(html_source)
#         print("\nCleaned HTML saved to cleaned_for_content.html")

#         # Now you can pass this to your cleaning function
#         # from your_cleaning_script import clean_html_for_content # Assuming your cleaning function is in this file
#         # cleaned_html = clean_html_for_content(html_source)
#         # print("\n----- Cleaned HTML (First 500 characters) -----")
#         # print(cleaned_html[:500] + "...")

#         # Or save the full source to a file:
#         # with open("fetched_website_source_selenium.html", "w", encoding="utf-8") as f:
#         #     f.write(html_source)
#         # print("\nFull HTML source (from Selenium) saved to fetched_website_source_selenium.html")
#     else:
#         print("Failed to retrieve the website source code using Selenium.")
