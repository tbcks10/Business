import os
import time
from playwright.sync_api import sync_playwright
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from colorama import Fore, Style

# Caminho da pasta de trabalho
WORK_DIR = os.path.join(os.getcwd(), "Palavra-chave")
SITES_FILE = os.path.join(WORK_DIR, "sites.txt")
PALAVRAS_FILE = os.path.join(WORK_DIR, "palavras.txt")
PROCESSADOS_FILE = os.path.join(WORK_DIR, "processados.txt")
SECRET_FILE = "secret.json"
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1ghQU4TODlkWPR82tlH07mP_gI2d5Mh5teVLTbQU87DU/edit#gid=0"

# Garantir que a pasta e arquivos existam
os.makedirs(WORK_DIR, exist_ok=True)
def ensure_file_exists(file_path, default_content):
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(default_content)

ensure_file_exists(SITES_FILE, "example.com\n")
ensure_file_exists(PALAVRAS_FILE, "exemplo\npalavra-chave\n")
ensure_file_exists(PROCESSADOS_FILE, "")

# Carregar arquivos
def load_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def save_processed(site):
    with open(PROCESSADOS_FILE, 'a', encoding='utf-8') as f:
        f.write(site + '\n')

def remove_processed_site(site):
    sites = load_file(SITES_FILE)
    sites = [s for s in sites if s != site]
    with open(SITES_FILE, 'w', encoding='utf-8') as f:
        f.writelines([s + '\n' for s in sites])

# Autenticação do Google Sheets
def autenticacao_google_sheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(SECRET_FILE, scope)
    client = gspread.authorize(creds)
    return client

def escrever_no_sheets(client, dados, spreadsheet_url):
    spreadsheet = client.open_by_url(spreadsheet_url)
    sheet = spreadsheet.sheet1
    sheet.append_row(dados)

# Função para mostrar uma animação de carregamento
def mostrar_carregando():
    print(f"{Fore.YELLOW}Esperando lista nova", end="")
    for _ in range(3):
        print(".", end="", flush=True)
        time.sleep(0.5)
    print(f"{Style.RESET_ALL}")

# Remover duplicados de sites
def remove_duplicados(sites):
    return list(set(sites))

# Processar sites
def process_sites(client, context, palavras):
    sites = load_file(SITES_FILE)
    sites = remove_duplicados(sites)  # Remove duplicados
    processados = set(load_file(PROCESSADOS_FILE))
    novos_sites = [site for site in sites if site not in processados]

    if not novos_sites:
        mostrar_carregando()  # Só exibe a mensagem "Esperando lista nova" quando não houver novos sites
        return

    print(f"{Fore.CYAN}Lista nova adicionada, processando ({1}/{len(novos_sites)})...{Style.RESET_ALL}")
    
    for idx, site in enumerate(novos_sites):
        print(f"{Fore.CYAN}Processando {idx + 1}/{len(novos_sites)} - {site}...{Style.RESET_ALL}")
        tentativas = 0
        processado = False
        while tentativas < 3 and not processado:
            for protocol in ["http://", "https://"]:
                url = protocol + site if not site.startswith("http") else site
                page = None  # Inicialize a variável antes do bloco try
                try:
                    page = context.new_page()
                    page.goto(url, timeout=15000)  # Timeout ajustado para 15 segundos
                    content = page.content().lower()
                    palavras_encontradas = [palavra for palavra in palavras if palavra.lower() in content]

                    if palavras_encontradas:
                        palavras_str = ", ".join(palavras_encontradas)
                        print(f"{Fore.GREEN}{site} - Palavra-chave encontrada - {palavras_str}{Style.RESET_ALL}")
                        escrever_no_sheets(client, [site, "Sim", palavras_str], SPREADSHEET_URL)
                    else:
                        print(f"{Fore.RED}{site} - Nenhuma palavra-chave encontrada{Style.RESET_ALL}")
                        escrever_no_sheets(client, [site, "Não", ""], SPREADSHEET_URL)

                    save_processed(site)
                    remove_processed_site(site)
                    processado = True
                    break
                except Exception as e:
                    tentativas += 1
                    print(f"{Fore.YELLOW}Erro ao processar {url}: {Style.RESET_ALL}")
                    # Caso o erro seja relacionado ao tempo de carregamento
                    if "Timeout" in str(e):
                        print(f"{Fore.RED}Site não carregou em 15 segundos! ({site}) Tentativa {tentativas}/3{Style.RESET_ALL}")
                    elif "ERR_NAME_NOT_RESOLVED" in str(e):
                        print(f"{Fore.RED}Erro de DNS ao tentar acessar {site}, tentativas {tentativas}/3{Style.RESET_ALL}")

                    if tentativas == 3:
                        print(f"{Fore.RED}Provavelmente não iremos conseguir processar - {site}{Style.RESET_ALL}")
                        # Remover o site da lista após 3 tentativas falhadas
                        remove_processed_site(site)
                    time.sleep(2)  # Aguardar um pouco antes da próxima tentativa
                finally:
                    if page:
                        page.close()

    mostrar_carregando()

# Inicializar servidor
def start_server():
    try:
        client = autenticacao_google_sheets()
    except Exception as e:
        print(f"{Fore.RED}Erro na autenticação do Google Sheets: {e}{Style.RESET_ALL}")
        exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        palavras = load_file(PALAVRAS_FILE)

        # Processar sites existentes no início
        process_sites(client, context, palavras)

        print(f"{Fore.CYAN}Servidor iniciado novamente! Aguardando por novos sites.{Style.RESET_ALL}")
        try:
            while True:
                process_sites(client, context, palavras)  # Verifica novos sites
                time.sleep(10)  # Verifica a cada 10 segundos
        except KeyboardInterrupt:
            print(f"{Fore.YELLOW}Encerrando o servidor...{Style.RESET_ALL}")

        browser.close()

if __name__ == "__main__":
    start_server()
