import requests
from bs4 import BeautifulSoup
import time
import csv
from datetime import datetime, timedelta

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

# Função para verificar novos CNPJs
def verificar_novos_cnpjs(referencia_cnpjs):
    print("Verificando novos CNPJs...")
    novos_cnpjs = []
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
    while True:
        response = requests.post(URL_PESQUISA_COMPLETA, headers=HEADERS_POST, data=payload_post)
        if response.status_code != 200:
            print(f"Erro ao acessar página {payload_post['PaginaAtual']}: {response.status_code}")
            break
        soup = BeautifulSoup(response.text, 'html.parser')
        empresas = soup.find_all("div", class_="item-lista")
        if not empresas:
            break
        for empresa in empresas:
            razao_social = empresa.find("h4").get_text(strip=True)
            cnpj_id = empresa["data-codigo-empresa"]
            if cnpj_id not in referencia_cnpjs:
                novos_cnpjs.append(cnpj_id)
        # Atualiza a página
        payload_post["PaginaAtual"] += 1
        if payload_post["PaginaAtual"] > 10:  # Limita a 10 páginas
            break
    return novos_cnpjs

# Função para extrair dados de uma empresa
def extrair_dados_empresa(html):
    soup = BeautifulSoup(html, 'html.parser')

    def extrair_valor(label):
        # Corrigido: Usando string para encontrar o elemento
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

# Função para processar todas as empresas
def processar_empresas(n_empresas):
    print(f"Processando {n_empresas} empresas...")
    with open("empresas.csv", "w", newline="", encoding="utf-8") as arquivo_csv:
        campos = ["Razão Social", "CNPJ", "E-mail", "Website", "Tomador de Decisões", "Faixa de Importação", "Bairro", "Cidade-Estado", "CEP", "Telefone"]
        escritor = csv.DictWriter(arquivo_csv, fieldnames=campos)
        escritor.writeheader()

        for empresa_id in range(1, n_empresas + 1):
            print(f"Processando empresa {empresa_id}...")
            response = requests.get(URL_DETALHE_EMPRESA + str(empresa_id), headers=HEADERS_GET)
            if response.status_code == 200:
                dados = extrair_dados_empresa(response.text)
                escritor.writerow(dados)
                print(f"Dados extraídos: {dados}")
            else:
                print(f"Erro ao acessar empresa {empresa_id}: {response.status_code}")
            
            # Aguarda 1 minuto antes de processar a próxima empresa
            print("Aguardando 1 minuto para a próxima requisição...")
            time.sleep(60)

# Função principal
def main():
    referencia_cnpjs = set()
    ultima_verificacao = datetime.now()

    while True:
        # Verifica novos CNPJs a cada 7 dias
        if datetime.now() >= ultima_verificacao + timedelta(days=7):
            novos_cnpjs = verificar_novos_cnpjs(referencia_cnpjs)
            if novos_cnpjs:
                print(f"Novos CNPJs encontrados: {novos_cnpjs}")
                referencia_cnpjs.update(novos_cnpjs)
            ultima_verificacao = datetime.now()

        # Processa todas as empresas
        processar_empresas(10)

        # Aguarda 7 dias antes de verificar novamente
        print("Aguardando 7 dias para a próxima verificação...")
        time.sleep(7 * 24 * 60 * 60)  # 7 dias em segundos

if __name__ == "__main__":
    main()
