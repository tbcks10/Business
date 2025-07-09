import requests
import gspread
import time
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials

# URLs base
URL_PESQUISA_COMPLETA = "https://cib.dpr.gov.br/Home/PesquisaCompleta"
URL_DETALHE_EMPRESA = "https://cib.dpr.gov.br/Home/DetalheEmpresaPartial/"

# Cabeçalhos das requisições
HEADERS_POST = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "content-type": "application/x-www-form-urlencoded",
    "referer": "https://cib.dpr.gov.br/Home/PesquisaCompleta",
    "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
}
HEADERS_GET = {
    "accept": "text/html, */*; q=0.01",
    "referer": "https://cib.dpr.gov.br/Home/PesquisaCompleta",
    "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
    "x-requested-with": "XMLHttpRequest",
}

# Função de autenticação do Google Sheets
def autenticacao_google_sheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('secret.json', scope)
    client = gspread.authorize(creds)
    return client

# Função para escrever dados no Google Sheets
def escrever_no_sheets(client, dados, spreadsheet_url):
    # Abre a planilha pelo URL
    spreadsheet = client.open_by_url(spreadsheet_url)
    # Seleciona a primeira aba (sheet)
    sheet = spreadsheet.sheet1

    # Preenche os dados na próxima linha disponível (supondo que a linha 1 tenha os cabeçalhos)
    sheet.append_row([ 
        dados["Razão Social"],
        dados["CNPJ"],
        dados["E-mail"],
        dados["Website"],
        dados["Tomador de Decisões"],
        dados["Faixa de Importação"],
        dados["Bairro"],
        dados["Cidade-Estado"],
        dados["CEP"],
        dados["Telefone"]
    ])

    print(f"Dados extraídos com sucesso para a empresa: {dados['Razão Social']}")

# Função para extrair dados de uma empresa
def extrair_dados_empresa(html):
    soup = BeautifulSoup(html, 'html.parser')

    def extrair_valor(label):
        elemento = soup.find("label", string=label)
        if elemento and elemento.find_next("span", class_="valor"):
            return elemento.find_next("span", class_="valor").get_text(strip=True)
        return "Sem informação!"

    razao_social_cnpj = soup.find("div", class_="campo-detalhe full")
    razao_social = "Sem informação!"
    cnpj = "Sem informação!"
    if razao_social_cnpj:
        razao_social_cnpj_text = razao_social_cnpj.find("span", class_="valor").get_text(strip=True)
        partes = razao_social_cnpj_text.split("CNPJ")
        razao_social = partes[0].strip() if len(partes) > 0 else "Sem informação!"
        cnpj = "CNPJ " + partes[1].strip() if len(partes) > 1 else "Sem informação!"

    dados = {
        "Razão Social": razao_social,
        "CNPJ": cnpj,
        "E-mail": extrair_valor("e-mail"),
        "Website": extrair_valor("Website"),
        "Tomador de Decisões": extrair_valor("Contato"),
        "Faixa de Importação": extrair_valor("Faixa de importação anual"),
        "Bairro": extrair_valor("Bairro"),
        "Cidade-Estado": extrair_valor("Cidade/Estado"),
        "CEP": extrair_valor("CEP"),
        "Telefone": extrair_valor("Telefone"),
    }

    return dados

# Função para verificar novos CNPJs
def verificar_novos_cnpjs():
    print("Verificando novos CNPJs...")
    novos_cnpjs = []
    
    # Faz a requisição para verificar o número de empresas
    payload_post = {
        "PaginaAtual": 1,
        "TamanhoPagina": 10,
        "CodigoProduto": "",
        "RazaoSocial": "",
        "CNPJ": "",
        "CodigoSubdivisaoPais": "",
        "CodigoPais": "",
        "CodigoFaixaImportacao": "",
    }
    
    response = requests.post(URL_PESQUISA_COMPLETA, headers=HEADERS_POST, data=payload_post)
    if response.status_code != 200:
        print(f"Erro ao acessar página de pesquisa: {response.status_code}")
        return [], 0

    soup = BeautifulSoup(response.text, 'html.parser')

    # Extrair o número total de empresas encontradas
    total_empresas = soup.find("h4", string=lambda text: text and "empresas encontradas" in text)
    if total_empresas:
        total_empresas = int(total_empresas.get_text().split()[0])
        print(f"Total de empresas encontradas: {total_empresas}")

    # Processar até 10 empresas da primeira página
    empresas = soup.find_all("div", class_="item-lista")
    for empresa in empresas[:10]:  # Limita a verificação para até 10 empresas
        cnpj_id = empresa["data-codigo-empresa"]
        novos_cnpjs.append(cnpj_id)

    return novos_cnpjs, total_empresas

# Função para remover CNPJ da planilha
def remover_cnpj_da_planilha(client, cnpj):
    spreadsheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1ckiMKo0NRFyDFC99pSiO5rMqD5UDeemQ6IGXKTmiRF4/edit?gid=0#gid=0')
    sheet = spreadsheet.sheet1
    cell = sheet.find(cnpj)
    
    if cell:
        row = cell.row
        sheet.delete_row(row)
        print(f"CNPJ {cnpj} encontrado e removido da planilha.")
    else:
        print(f"CNPJ {cnpj} não encontrado na planilha.")

# Função para processar as empresas e preencher no Sheets
def processar_empresas(n_empresas, client, spreadsheet_url, cnpjs_processados):
    print(f"Processando {n_empresas} empresas...")

    for empresa_id in range(1, min(n_empresas, 10) + 1):  # Limita para processar até 10 empresas
        print(f"Processando empresa {empresa_id}...")
        response = requests.get(URL_DETALHE_EMPRESA + str(empresa_id), headers=HEADERS_GET)
        if response.status_code == 200:
            dados = extrair_dados_empresa(response.text)
            # Verifica se o CNPJ já foi processado
            cnpj_extraido = dados["CNPJ"].replace("CNPJ", "").strip()
            if cnpj_extraido not in cnpjs_processados:
                escrever_no_sheets(client, dados, spreadsheet_url)
                cnpjs_processados.add(cnpj_extraido)
                # Salva o CNPJ no arquivo de texto
                with open("cnpjs_extraidos.txt", "a") as file:
                    file.write(cnpj_extraido + "\n")
            else:
                print(f"CNPJ já encontrado na planilha/txt, removendo: {cnpj_extraido}")
                # Remove o CNPJ duplicado da planilha
                remover_cnpj_da_planilha(client, cnpj_extraido)
        else:
            print(f"Erro ao acessar empresa {empresa_id}: {response.status_code}")
        
        # Aguarda 1 minuto antes de processar a próxima empresa
        print("Aguardando 1 minuto para a próxima requisição...")
        time.sleep(60)

# Função principal
def main():
    # Realiza a autenticação no Google Sheets
    client = autenticacao_google_sheets()

    # URL da planilha
    spreadsheet_url = 'https://docs.google.com/spreadsheets/d/1ckiMKo0NRFyDFC99pSiO5rMqD5UDeemQ6IGXKTmiRF4/edit?gid=0#gid=0'

    # Carrega os CNPJs já processados do arquivo
    cnpjs_processados = set()
    try:
        with open("cnpjs_extraidos.txt", "r") as file:
            cnpjs_processados = set(file.read().splitlines())
    except FileNotFoundError:
        print("Arquivo de CNPJs não encontrado, criando novo arquivo...")

    # Verifica se há novos CNPJs
    novos_cnpjs, total_empresas = verificar_novos_cnpjs()
    
    if total_empresas > 7467:  # Número de empresas aumentou, há novos CNPJs
        processar_empresas(total_empresas, client, spreadsheet_url, cnpjs_processados)
    else:
        print("Nenhum novo CNPJ encontrado.")
        input("Se deseja processar as 7467 empresas existentes, aperte Enter...")
        processar_empresas(7467, client, spreadsheet_url, cnpjs_processados)

# Executa a função principal
if __name__ == "__main__":
    main()