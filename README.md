# Business Automation & Data Extraction Toolkit

This repository contains a collection of Python-based automation scripts designed for business intelligence and lead generation. The toolkit is divided into two main modules, each serving a distinct data extraction purpose.

---

## Modules

### 1. Keyword Monitor (`/Palavra-chave`)

A powerful web monitoring tool that continuously scans a list of websites for specific keywords and logs the results to a Google Sheet.

**Features:**
- **Continuous Monitoring:** The script runs in a loop, automatically checking for new websites added to `sites.txt`.
- **Dynamic Content Handling:** Uses the Playwright library to control a headless Chromium browser, enabling it to scrape modern, JavaScript-heavy websites.
- **Cloud Integration:** Authenticates with Google Sheets using a `secret.json` service account file and appends results directly to a specified spreadsheet.
- **Resilient:** Includes error handling and retry logic for network issues.

**Use Cases:**
- Competitive analysis.
- Brand mention tracking.
- Market research and product hunting.
- Monitoring websites for specific updates or content changes.

### 2. CIB Company Data Extractor (`/CIB`)

A specialized web scraper designed to extract detailed company information from the Brazilian government portal `cib.dpr.gov.br` (Cadastro de Intervenientes em Operações de Comércio Exterior).

**Features:**
- **Targeted Extraction:** Precisely parses the HTML of the CIB portal to extract valuable company data.
- **Data Points:** Collects Company Name, CNPJ (Tax ID), Email, Website, Key Contact Person, Import Range, and Address.
- **Lightweight & Efficient:** Uses the `requests` and `BeautifulSoup` libraries for fast and efficient scraping of server-rendered pages.
- **Local Storage:** Saves all extracted data neatly into a `empresas.csv` file for easy access with Excel or other data analysis tools.
- **Evolved Scripts:** Includes several versions of the script (`cib.py`, `cib2.py`, etc.), showcasing different functionalities like saving to CSV vs. Google Sheets.

**Use Cases:**
- Building lead lists for sales and marketing teams.
- Market analysis of import/export companies.
- Creating a database of potential business partners or suppliers.

---

## Setup

1.  **Clone the repository.**
2.  **Install dependencies:**
    ```bash
    pip install requests beautifulsoup4 playwright gspread oauth2client google-api-python-client colorama
    playwright install
    ```
3.  **Configure Credentials:** Populate the `secret.json` files with your own Google Cloud Platform service account credentials to enable Google Sheets integration.
4.  **Customize Inputs:** Edit the `.txt` files in each module (`sites.txt`, `palavras.txt`) to match your specific targets.
5.  **Run the scripts:**
    ```bash
    python Palavra-chave/extrator.py
    # or
    python CIB/cib.py
    ```