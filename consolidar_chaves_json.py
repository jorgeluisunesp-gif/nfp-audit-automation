import json
import os

ARQUIVO_CHAVES = "chaves_notas.txt"
ARQUIVO_JSON_PORTAL = "notas_portal_limpo.json"
ARQUIVO_FINAL = "notas_fiscais_completo_final.json"

# Mapeamentos de Estado (Códigos IBGE)
CODIGOS_UF = {
    '11': 'RO', '12': 'AC', '13': 'AM', '14': 'RR', '15': 'PA', '16': 'AP', '17': 'TO',
    '21': 'MA', '22': 'PI', '23': 'CE', '24': 'RN', '25': 'PB', '26': 'PE', '27': 'AL',
    '28': 'SE', '29': 'BA', '31': 'MG', '32': 'ES', '33': 'RJ', '35': 'SP', '41': 'PR',
    '42': 'SC', '43': 'RS', '50': 'MS', '51': 'MT', '52': 'GO', '53': 'DF'
}

MODELOS = {
    '55': 'NF-e (Nota Grande)',
    '65': 'NFC-e (Consumidor)',
    '59': 'SAT (Cupom Fiscal)'
}

def decodificar_chave(chave):
    """
    Extrai dados embutidos na chave de acesso de 44 dígitos.
    Lida com a diferença de layout entre NFe/NFCe e SAT.
    """
    if len(chave) != 44 or not chave.isdigit(): return None
    
    cUF = chave[0:2]
    aamm = chave[2:6]
    cnpj = chave[6:20]
    mod = chave[20:22]
    
    # Lógica de extração baseada no Modelo
    if mod == '59':
        # --- LAYOUT SAT (CFe) ---
        # Pos 22-31: nSAT (Número de Série do Equipamento - 9 dígitos)
        # Pos 31-37: cCF (Número do Cupom Fiscal - 6 dígitos) -> É ISSO QUE QUEREMOS
        serie_ou_sat = chave[22:31] 
        nNF = chave[31:37]
    else:
        # --- LAYOUT NFe / NFCe ---
        # Pos 22-25: Série (3 dígitos)
        # Pos 25-34: nNF (Número da Nota - 9 dígitos)
        serie_ou_sat = chave[22:25]
        nNF = chave[25:34]
    
    return {
        "chave_acesso": chave,
        "uf": CODIGOS_UF.get(cUF, "Desconhecido"),
        "mes_ano_chave": f"{aamm[2:4]}/{'20' + aamm[0:2]}",
        "cnpj_limpo": cnpj,
        "modelo_codigo": mod,
        "modelo_descricao": MODELOS.get(mod, "Outros"),
        "serie_ou_sat": serie_ou_sat, 
        "numero_nota": int(nNF) # Converte para inteiro para remover zeros à esquerda (021010 -> 21010)
    }

def main():
    print("--- INICIANDO CONSOLIDAÇÃO FINAL (COM CORREÇÃO SAT) ---")

    # 1. Carrega JSON do Portal (Dados Financeiros)
    if not os.path.exists(ARQUIVO_JSON_PORTAL):
        print(f"Erro: Arquivo '{ARQUIVO_JSON_PORTAL}' não encontrado.")
        print("Rode o script 'converter_csv_para_json.py' primeiro.")
        return
        
    with open(ARQUIVO_JSON_PORTAL, 'r', encoding='utf-8') as f:
        dados_portal = json.load(f)
        
    print(f"Dados financeiros carregados: {len(dados_portal)} registros.")

    # 2. Carrega Chaves (Identidade Única)
    if not os.path.exists(ARQUIVO_CHAVES):
        print(f"Erro: Arquivo '{ARQUIVO_CHAVES}' não encontrado.")
        return

    with open(ARQUIVO_CHAVES, 'r') as f:
        # Filtra apenas linhas válidas
        chaves = [l.strip() for l in f.readlines() if len(l.strip()) == 44 and l.strip().isdigit()]
        
    print(f"Chaves para processar: {len(chaves)}")

    notas_finais = []
    encontradas = 0
    nao_encontradas = 0
    
    # 3. Cruzamento e Enriquecimento
    for chave in chaves:
        meta_dados = decodificar_chave(chave)
        if not meta_dados: continue
        
        # Busca correspondência no JSON do portal
        # Critério: CNPJ e Número da Nota devem ser iguais
        match = next((item for item in dados_portal if 
                      str(item['cnpj_limpo']) == str(meta_dados['cnpj_limpo']) and 
                      int(item['numero_limpo']) == int(meta_dados['numero_nota'])), None)
        
        if match:
            # Enriquecimento com dados do portal
            meta_dados.update({
                "emitente_nome": match['emitente_nome'],
                "valor_total": match['valor_total'],
                "data_emissao": match['data_emissao'],
                "status_match": "COMPLETO (Chave + Portal)"
            })
            encontradas += 1
        else:
            # Tenta um "Match de Segurança" pelo valor/data se tiver poucos itens (opcional, mantive desativado para precisão)
            meta_dados.update({
                "emitente_nome": "Não encontrado no CSV do Portal",
                "valor_total": "0,00",
                "data_emissao": meta_dados['mes_ano_chave'],
                "status_match": "PARCIAL (Apenas Chave)"
            })
            nao_encontradas += 1
            # Debug para entender por que não casou (se precisar)
            # if meta_dados['modelo_codigo'] == '59':
            #    print(f"DEBUG NO MATCH SAT: CNPJ {meta_dados['cnpj_limpo']} NUM {meta_dados['numero_nota']}")

        notas_finais.append(meta_dados)

    # 4. Salva Resultado Final
    with open(ARQUIVO_FINAL, 'w', encoding='utf-8') as f:
        json.dump(notas_finais, f, indent=4, ensure_ascii=False)
        
    print(f"\n--- RELATÓRIO FINAL ---")
    print(f"Notas Completas (Valor + Detalhes): {encontradas}")
    print(f"Notas Parciais (Sem Valor): {nao_encontradas}")
    print(f"Total Gerado: {len(notas_finais)}")
    print(f"\nArquivo salvo em: {os.path.abspath(ARQUIVO_FINAL)}")

if __name__ == "__main__":
    main()