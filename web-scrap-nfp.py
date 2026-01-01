from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import time
import os
import subprocess
import re

# --- CONFIGURAÇÕES DE AMBIENTE ---
os.environ['WDM_SSL_VERIFY'] = '0'
os.environ['WDM_LOG_LEVEL'] = '0'

def fechar_edge_forca_bruta():
    """Garante que não existam processos do Edge travando o perfil."""
    try:
        print("--- Limpando processos antigos do Edge... ---")
        subprocess.run(["taskkill", "/F", "/IM", "msedge.exe"], 
                       stdout=subprocess.DEVNULL, 
                       stderr=subprocess.DEVNULL)
        time.sleep(2)
    except Exception:
        pass

def encontrar_executavel_edge():
    """Tenta localizar onde o Edge está instalado no Windows."""
    caminhos_comuns = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\Application\msedge.exe")
    ]
    for caminho in caminhos_comuns:
        if os.path.exists(caminho):
            return caminho
    return None

def extrair_chave_da_url(url):
    """
    Extrai a chave numérica de 44 dígitos de uma URL completa.
    """
    try:
        if not url: return None
        # Procura sequência de 44 dígitos (ex: chNFe=3525...)
        match = re.search(r"([0-9]{44})", url)
        if match:
            return match.group(1)
        return None
    except Exception:
        return None

def processar_todas_paginas(driver):
    """
    Navega página por página, clica em cada nota, pega a chave da nova aba e fecha.
    """
    arquivo_saida = "chaves_notas.txt"
    total_chaves = 0
    pagina_atual = 1
    
    # Cria/Limpa arquivo
    with open(arquivo_saida, "w") as f:
        f.write("--- LISTA DE CHAVES CAPTURADAS ---\n")

    print(f"\n--- INICIANDO EXTRAÇÃO (MÉTODO CLIQUE) ---")
    print(f"As chaves serão salvas em: {os.path.abspath(arquivo_saida)}")

    # Armazena o identificador da janela principal (a lista)
    janela_principal = driver.current_window_handle

    while True:
        print(f"\n>>> Processando PÁGINA {pagina_atual}...")
        time.sleep(3) # Espera tabela carregar

        # 1. Identificar linhas da tabela
        linhas = []
        try:
            # Tenta pegar pela tabela específica ou genérica
            linhas = driver.find_elements(By.XPATH, "//table[contains(@id,'gdvConsulta')]//tr")
            if not linhas:
                linhas = driver.find_elements(By.XPATH, "//table//tbody//tr")
        except:
            pass

        if not linhas:
            print("   [ALERTA] Nenhuma linha encontrada. Tentando recarregar elementos...")
            time.sleep(2)
            try:
                linhas = driver.find_elements(By.TAG_NAME, "tr")
            except:
                pass

        qtd_linhas = len(linhas)
        print(f"   > Total de linhas encontradas na página: {qtd_linhas}")
        
        chaves_pagina = 0

        # Iteramos pelo índice para garantir elementos frescos
        for i in range(qtd_linhas):
            try:
                # Recaptura a lista
                linhas_atualizadas = []
                try:
                    linhas_atualizadas = driver.find_elements(By.XPATH, "//table[contains(@id,'gdvConsulta')]//tr")
                    if not linhas_atualizadas:
                        linhas_atualizadas = driver.find_elements(By.XPATH, "//table//tbody//tr")
                except:
                    pass
                
                if i >= len(linhas_atualizadas): break
                
                linha = linhas_atualizadas[i]
                
                try:
                    texto_resumo = linha.text.replace("\n", " ")[:40]
                except:
                    continue

                # Filtros de cabeçalho e rodapé
                if "CNPJ" in texto_resumo or "Emitente" in texto_resumo or "Página" in texto_resumo:
                    continue
                
                # Procura o link clicável
                links = linha.find_elements(By.XPATH, ".//*[contains(@onclick, 'atob')]")
                if not links:
                    links = linha.find_elements(By.TAG_NAME, "a")
                
                if not links:
                    continue

                link_alvo = links[0]

                # --- AÇÃO DE CLIQUE ---
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link_alvo)
                time.sleep(0.5)
                
                # Clica via JS
                driver.execute_script("arguments[0].click();", link_alvo)
                
                # Espera a nova aba abrir (2 segundos é o suficiente para criar a janela)
                time.sleep(2)
                
                # --- TROCA DE ABA ---
                todas_janelas = driver.window_handles
                if len(todas_janelas) > 1:
                    # Muda para a última aba aberta
                    nova_janela = todas_janelas[-1]
                    
                    if nova_janela != janela_principal:
                        driver.switch_to.window(nova_janela)
                        
                        # --- CORREÇÃO DE TEMPO DE CARREGAMENTO ---
                        # Tenta ler a URL várias vezes. A primeira nota costuma demorar.
                        chave = None
                        url_atual = ""
                        
                        # Loop de persistência (5 segundos no máximo)
                        for _ in range(5):
                            url_atual = driver.current_url
                            chave = extrair_chave_da_url(url_atual)
                            if chave:
                                break # Achou a chave, sai do loop de espera
                            time.sleep(1) # Espera mais 1 segundo se não achou
                        
                        if chave:
                            print(f"   [OK] {chave}")
                            with open(arquivo_saida, "a") as f:
                                f.write(f"{chave}\n")
                            chaves_pagina += 1
                            total_chaves += 1
                        else:
                            print(f"   [!] Falha: URL carregada não tem chave: {url_atual[:50]}...")

                        # Fecha e volta
                        driver.close()
                        driver.switch_to.window(janela_principal)
                else:
                    # Se não abriu aba, ignora
                    pass

            except Exception as e:
                # Garante retorno à janela principal em caso de erro
                try:
                    if driver.current_window_handle != janela_principal:
                        driver.close()
                        driver.switch_to.window(janela_principal)
                except:
                    driver.switch_to.window(janela_principal)
                continue

        print(f"   > Fim da página {pagina_atual}. Chaves salvas: {chaves_pagina}")

        # --- PAGINAÇÃO ---
        try:
            # Procura botão Próxima
            try:
                btn_proxima = driver.find_element(By.ID, "lkBtnProxima")
            except:
                btn_proxima = driver.find_element(By.XPATH, "//a[contains(text(), 'Próxima')]")

            href = btn_proxima.get_attribute("href")
            classe = btn_proxima.get_attribute("class") or ""
            
            # Se não tiver href ou estiver desabilitado, acabou
            if not href or "Disabled" in classe or "javascript:void" in href:
                print("\n--- FIM DA PAGINAÇÃO ---")
                break
            
            print("   > Avançando página...")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_proxima)
            driver.execute_script("arguments[0].click();", btn_proxima)
            
            # Tempo generoso para carregar próxima página
            time.sleep(6)
            pagina_atual += 1
            
        except Exception:
            print("\n--- FIM (Botão 'Próxima' não encontrado) ---")
            break

    print(f"\n--- PROCESSO CONCLUÍDO ---")
    print(f"Total de chaves salvas: {total_chaves}")
    print(f"Arquivo: {arquivo_saida}")

def iniciar_edge_com_certificado():
    fechar_edge_forca_bruta()

    edge_path = encontrar_executavel_edge()
    if not edge_path:
        print("ERRO: Executável do Edge não encontrado.")
        return

    user_home = os.path.expanduser("~")
    user_data_dir = os.path.join(user_home, r"AppData\Local\Microsoft\Edge\User Data")
    profile_directory = "Default" 
    
    url_final = "https://www.nfp.fazenda.sp.gov.br/login.aspx?ReturnUrl=/"

    # --- MÉTODO DIRETO PARA PASSAR CAPTCHA ---
    comando_launch = [
        edge_path,
        f"--remote-debugging-port=9222",
        f"--user-data-dir={user_data_dir}",
        f"--profile-directory={profile_directory}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-popup-blocking",
        "--ignore-certificate-errors",
        url_final
    ]

    print(f"--- Iniciando Edge (Debug Port 9222) ---")
    subprocess.Popen(comando_launch)
    time.sleep(4) 

    print("Conectando automação...")
    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

    try:
        try:
            service = Service(EdgeChromiumDriverManager().install())
            driver = webdriver.Edge(service=service, options=options)
        except Exception:
            driver = webdriver.Edge(options=options)
            
        print("\n--- SUCESSO: CONECTADO ---")
        print("1. Faça o LOGIN manualmente.")
        print("2. Vá para a TABELA DE NOTAS.")
        
        input("\n>>> QUANDO A TABELA ESTIVER VISÍVEL, PRESSIONE [ENTER]... <<<")
        
        processar_todas_paginas(driver)
        
        print("\nPressione Ctrl+C para encerrar.")
        while True: time.sleep(1)

    except Exception as e:
        print(f"\nERRO: {e}")

if __name__ == "__main__":
    iniciar_edge_com_certificado()