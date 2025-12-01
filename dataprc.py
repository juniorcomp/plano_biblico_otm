import pandas as pd
import json
import re
import os

# Mapeamento de abreviação do livro (minúscula) para o Gênero.
# Importante para a Restrição de Foco Diário.
GENERO_MAP = {
    # Pentateuco
    'gn': 'Pentateuco', 'ex': 'Pentateuco', 'lv': 'Pentateuco', 'nm': 'Pentateuco', 'dt': 'Pentateuco',
    # Históricos
    'js': 'Historia', 'jz': 'Historia', 'rt': 'Historia', 
    '1sm': 'Historia', '2sm': 'Historia', '1rs': 'Historia', '2rs': 'Historia', 
    '1cr': 'Historia', '2cr': 'Historia', 'ed': 'Historia', 'ne': 'Historia', 'et': 'Historia', 
    # Poesia
    'jó': 'Poesia', 'sl': 'Poesia', 'pv': 'Poesia', 'ec': 'Poesia', 'ct': 'Poesia', 
    # Profetas Maiores
    'is': 'ProfetasMaiores', 'jr': 'ProfetasMaiores', 'lm': 'ProfetasMaiores', 'ez': 'ProfetasMaiores', 'dn': 'ProfetasMaiores', 
    # Profetas Menores
    'os': 'ProfetasMenores', 'jl': 'ProfetasMenores', 'am': 'ProfetasMenores', 'ob': 'ProfetasMenores', 
    'jn': 'ProfetasMenores', 'mq': 'ProfetasMenores', 'na': 'ProfetasMenores', 'hc': 'ProfetasMenores', 
    'sf': 'ProfetasMenores', 'ag': 'ProfetasMenores', 'zc': 'ProfetasMenores', 'ml': 'ProfetasMenores',
    # Novo Testamento
    'mt': 'Evangelho', 'mc': 'Evangelho', 'lc': 'Evangelho', 'jo': 'Evangelho', 
    # Atos
    'at': 'Atos',
    # Epístolas Paulinas
    'rm': 'EpistolasPaulinas', '1co': 'EpistolasPaulinas', '2co': 'EpistolasPaulinas', 'gl': 'EpistolasPaulinas', 
    'ef': 'EpistolasPaulinas', 'fp': 'EpistolasPaulinas', 'cl': 'EpistolasPaulinas', '1ts': 'EpistolasPaulinas', 
    '2ts': 'EpistolasPaulinas', '1tm': 'EpistolasPaulinas', '2tm': 'EpistolasPaulinas', 'tt': 'EpistolasPaulinas', 
    'fm': 'EpistolasPaulinas', 
    # Epístolas Gerais
    'hb': 'EpistolasGerais', 'tg': 'EpistolasGerais', '1pe': 'EpistolasGerais', 
    '2pe': 'EpistolasGerais', '1jo': 'EpistolasGerais', '2jo': 'EpistolasGerais', '3jo': 'EpistolasGerais', 
    'jd': 'EpistolasGerais', 
    # Apocalíptico
    'ap': 'Apocaliptico'
}
TESTAMENTO_ANTIGO = {
    'Pentateuco', 'Historia', 'Poesia',
    'ProfetasMaiores', 'ProfetasMenores'
}
TESTAMENTO_NOVO = {
    'Evangelho', 'Atos', 'EpistolasPaulinas', 
    'EpistolasGerais', 'Apocaliptico'
}
def contagem_palavras(text):
    if isinstance(text, str):
        # Encontra sequências de letras/números e as conta.
        words = re.findall(r'\b\w+\b', text.lower())
        return len(words)
    return 0
def processar_json(json_file_path, output_csv_path):
    # Testa erro na leitura do arquivo JSON
    try:
        with open(json_file_path, 'r', encoding='utf-8-sig') as f:
            # O JSON é esperado ser uma LISTA de Livros.
            dados_biblia = json.load(f)
    except FileNotFoundError:
        print(f"ERRO: Arquivo JSON '{json_file_path}' não encontrado.")
        return
    except json.JSONDecodeError as e:
        print(f"ERRO DE DECODIFICAÇÃO JSON: O arquivo não está formatado corretamente. {e}")
        print("Verifique se o arquivo começa com '[' e termina com ']' e se não tem caracteres extras.")
        return

    registros = []
    
    for livro_data in dados_biblia:
        # Extrai informações do livro
        abrev_livro = livro_data.get('abbrev', '').lower()
        nome_livro_completo = livro_data.get('name', 'Desconhecido') 
        # Mapeamento do Gênero
        genero = GENERO_MAP.get(abrev_livro, 'Atos') # 'Outros' se a abreviação não for encontrada
        if 'chapters' in livro_data:
            capitulos_data = livro_data['chapters']
            # Iteração sobre a LISTA de Capítulos (onde o índice + 1 é o número do capítulo)
            for index, versiculos_list in enumerate(capitulos_data):
                cap_num = index + 1 # O número do capítulo real         
                # 'versiculos_list' é a lista de strings (versículos) do capítulo.
                texto_capitulo = " ".join(versiculos_list)       
                palavras = contagem_palavras(texto_capitulo)
                # Cria a chave única para a coluna 'Capitulo' (ex: GN 1)
                capitulo_chave = f"{abrev_livro.upper()} {cap_num}"         
                registros.append({
                    'Capitulo': capitulo_chave,
                    'Palavras': palavras,
                    'Genero': genero,
                    'Testamento': 'Antigo' if genero in TESTAMENTO_ANTIGO else 'Novo',
                    'Livro': nome_livro_completo,
                    'Livro_Abrev': abrev_livro,
                    'Capitulo_Num': cap_num
                })
    # Cria o DataFrame, define o índice e salva como CSV
    df = pd.DataFrame(registros)
    df = df.set_index('Capitulo') 
    df.to_csv(output_csv_path)
    print(f"Processamento concluído. {len(df)} capítulos salvos em '{output_csv_path}'.")
# Execução direta do script
if __name__ == '__main__':
    # VARIÁVEIS DE ENTRADA E SAÍDA
    JSON_ENTRADA = 'nvi.json' 
    CSV_SAIDA = 'dados_biblia.csv'
    print("Iniciando processamento de dados para otimização...")
    processar_json(JSON_ENTRADA, CSV_SAIDA)
    print("\nPróximo Passo: Execute 'python app.py' para iniciar o servidor Flask.")