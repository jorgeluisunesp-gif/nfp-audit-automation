import csv
import json
import os
import re

ARQUIVO_CSV_ENTRADA = "ConsultaNFP_36513739837.csv"
ARQUIVO_JSON_SAIDA = "notas_portal_limpo.json"

def limpar_valor(valor):
    """Remove aspas duplas, espaços extras e caracteres invisíveis."""
    if not valor: return ""
    v = str(valor)
    # Remove caracteres nulos e BOM
    v = v.replace('\x00', '').replace('\ufeff', '')
    # Remove aspas do início e fim e espaços
    v = v.strip().strip('"').strip()
    return v

def limpar_apenas_numeros(texto):
    """Deixa apenas dígitos (0-9)."""
    if not texto: return ""
    limpo = limpar_valor(texto)
    return re.sub(r'\D', '', limpo)

def converter_csv_sujo():
    if not os.path.exists(ARQUIVO_CSV_ENTRADA):
        print(f"Erro: Arquivo '{ARQUIVO_CSV_ENTRADA}' não encontrado.")
        return

    print(f"Lendo CSV bruto: {ARQUIVO_CSV_ENTRADA}")
    
    linhas = []
    
    # Tenta ler com encoding UTF-16 (padrão exportação NFP)
    try:
        with open(ARQUIVO_CSV_ENTRADA, 'r', encoding='utf-16') as f:
            # Lê tudo para memória para tratar nulos globalmente
            conteudo = f.read()
            # Remove nulos que quebram o CSV
            conteudo = conteudo.replace('\x00', '')
            linhas = conteudo.splitlines()
            print("   > Arquivo lido com sucesso (UTF-16).")
    except Exception as e:
        print(f"   > Falha com UTF-16 ({e}). Tentando UTF-8...")
        try:
            with open(ARQUIVO_CSV_ENTRADA, 'r', encoding='utf-8') as f:
                linhas = f.readlines()
        except:
            print("ERRO FATAL: Não foi possível ler o arquivo.")
            return

    if not linhas:
        print("ERRO: Arquivo vazio.")
        return

    # Processa cabeçalho
    # O arquivo tem separador TAB (\t)
    cabecalho_raw = linhas[0].strip().split('\t')
    cabecalho = [limpar_valor(c) for c in cabecalho_raw]
    
    print(f"Colunas detectadas: {cabecalho}")
    
    # Mapeia índices dinamicamente
    idx_cnpj = -1
    idx_num = -1
    idx_valor = -1
    idx_data = -1
    idx_emitente = -1
    
    for i, col in enumerate(cabecalho):
        c = col.lower()
        if "cnpj" in c: idx_cnpj = i
        if "no." in c or "nº" in c: idx_num = i
        if "valor" in c: idx_valor = i
        if "emissão" in c or "emissao" in c: idx_data = i
        if "emitente" in c and "cnpj" not in c: idx_emitente = i

    if idx_cnpj == -1 or idx_num == -1:
        print("ERRO: Colunas 'CNPJ' e 'Número' não encontradas após limpeza.")
        return

    registros = []
    count = 0
    
    # Processa linhas de dados
    for i in range(1, len(linhas)):
        linha = linhas[i].strip()
        if not linha: continue
        
        colunas = linha.split('\t')
        
        if len(colunas) < len(cabecalho): continue
        
        cnpj_raw = limpar_valor(colunas[idx_cnpj])
        num_raw = limpar_valor(colunas[idx_num])
        
        cnpj_limpo = limpar_apenas_numeros(cnpj_raw)
        
        try:
            num_limpo = int(limpar_apenas_numeros(num_raw))
        except:
            continue 
            
        item = {
            "cnpj_limpo": cnpj_limpo,
            "numero_limpo": num_limpo,
            "emitente_nome": limpar_valor(colunas[idx_emitente]) if idx_emitente != -1 else "",
            "valor_total": limpar_valor(colunas[idx_valor]) if idx_valor != -1 else "0,00",
            "data_emissao": limpar_valor(colunas[idx_data]) if idx_data != -1 else ""
        }
        
        registros.append(item)
        count += 1

    # Salva JSON limpo
    with open(ARQUIVO_JSON_SAIDA, 'w', encoding='utf-8') as f:
        json.dump(registros, f, indent=4, ensure_ascii=False)
        
    print(f"Sucesso! {count} registros convertidos para '{ARQUIVO_JSON_SAIDA}'")

if __name__ == "__main__":
    converter_csv_sujo()