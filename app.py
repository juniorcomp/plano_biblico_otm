from flask import Flask, render_template, request
from pulp import *
import pandas as pd
import os 
from datetime import datetime, timedelta

app = Flask(__name__)
#tenta buscar os dados de arquivo da bíblia e validação de erro
try:
    DATA_FILE = os.path.join(os.path.dirname(__file__), 'dados_biblia.csv')
    df_biblia = pd.read_csv(DATA_FILE, index_col=0) 
    DADOS_LEITURA = df_biblia.T.to_dict('list')
    CAPITULOS = df_biblia.index.tolist()
    print(f"✅ Base de dados da Bíblia carregada com sucesso. {len(CAPITULOS)} capítulos encontrados.")
except Exception as e:
    print(f"ERRO CRÍTICO AO CARREGAR 'dados_biblia.csv': {e}")
    DADOS_LEITURA = {}
    CAPITULOS = []

MAPA_FORM_KEY = { 0: 'segunda', 1: 'terça', 2: 'quarta', 3: 'quinta', 4: 'sexta', 5: 'sábado', 6: 'domingo' }
MAPA_NOME_DIA = { 0: 'Segunda-feira', 1: 'Terça-feira', 2: 'Quarta-feira', 3: 'Quinta-feira', 4: 'Sexta-feira', 5: 'Sábado', 6: 'Domingo' }


@app.route('/', methods=['GET', 'POST'])
def otimizar_leitura():
    
    if not CAPITULOS:
        return "Erro: O arquivo dados_biblia.csv não foi carregado. Verifique o terminal para detalhes.", 500

    if request.method == 'POST':
        
        ppm = int(request.form.get('ppm', 250))
        
        tipo_leitura = request.form.get('tipo_leitura', '0')
        leitura_alternada = request.form.get('leitura_alternada', '0')
        restricao_genero = request.form.get('restricao_genero', '0')

        tempo_disponivel_dia = {} 
        for i in range(7):
            dia_key = MAPA_FORM_KEY[i]
            tempo_str = request.form.get(f'tempo_{dia_key}', '00:00')
            try:
                horas, minutos = map(int, tempo_str.split(':'))
                tempo_minutos = (horas * 60) + minutos
            except ValueError:
                tempo_minutos = 0 
            tempo_disponivel_dia[dia_key] = tempo_minutos
        plano_diario_final = []
        status_solucao = "Não Processado"
        total_palavras_lidas = 0
        tempo_total_utilizado = 0

        # LEiTURA LITERÁRIA SIMPLES 
        if tipo_leitura == '0' and leitura_alternada == '0':
            print("INFO: Rodando o AGENDADOR de Leitura Literária (Sequencial Padrão)")
            trilha_de_leitura = CAPITULOS 
            capitulo_idx = 0
            dia_atual = datetime.now().date() #Data atual
            while capitulo_idx < len(trilha_de_leitura):  
                dia_semana_num = dia_atual.weekday() # NUMERAÇÃO DO DIA DA SEMANA
                dia_form_key = MAPA_FORM_KEY[dia_semana_num]
                nome_dia_semana = MAPA_NOME_DIA[dia_semana_num]
                tempo_disponivel_hoje = tempo_disponivel_dia.get(dia_form_key, 0)
                capitulos_hoje = []
                tempo_usado_hoje = 0.0
                if tempo_disponivel_hoje > 0:
                    while tempo_usado_hoje < tempo_disponivel_hoje and capitulo_idx < len(trilha_de_leitura):     
                        cap_atual = trilha_de_leitura[capitulo_idx]
                        palavras_cap = DADOS_LEITURA[cap_atual][0] 
                        custo_cap_atual = (palavras_cap / ppm)
                        if tempo_usado_hoje + custo_cap_atual <= tempo_disponivel_hoje:
                            tempo_usado_hoje += custo_cap_atual
                            capitulos_hoje.append(cap_atual)
                            capitulo_idx += 1     
                            total_palavras_lidas += palavras_cap
                            tempo_total_utilizado += custo_cap_atual
                        else:
                            break 
                plano_diario_final.append({
                    'data': dia_atual.strftime('%d/%m/%Y'),
                    'dia_semana': nome_dia_semana,
                    'capitulos_str': ", ".join(capitulos_hoje) if capitulos_hoje else "Descanso (Tempo 0)",
                    'tempo_usado': round(tempo_usado_hoje, 2)
                })
                dia_atual += timedelta(days=1)
                if len(plano_diario_final) > 10000:
                    print("AVISO: Loop interrompido. Tempo de planejamento muito longo.")
                    break 
            status_solucao = "Plano Concluído"
        # Opção 2: Leitura Literária & Leitura Alternada
        if tipo_leitura == '0' and leitura_alternada == '1':
                    print("INFO: Rodando o AGENDADOR de Leitura Literária (Alternada por Dia)")
                    antigo_livros = []
                    novo_livros = []
                    for cap in CAPITULOS:
                        if DADOS_LEITURA[cap][2] == 'Antigo':
                            antigo_livros.append(cap)
                        else:
                            novo_livros.append(cap)
                    idx_antigo = 0
                    idx_novo = 0
                    count_alt = 0
                    dia_atual = datetime.now()
                    while idx_antigo < len(antigo_livros) or idx_novo < len(novo_livros):
                        dia_semana_num = dia_atual.weekday() 
                        dia_form_key = MAPA_FORM_KEY[dia_semana_num]
                        nome_dia_semana = MAPA_NOME_DIA[dia_semana_num]
                        tempo_disponivel_hoje = tempo_disponivel_dia.get(dia_form_key, 0)
                        capitulos_hoje = []
                        tempo_usado_hoje = 0.0
                        passo_at = (count_alt % 2 == 0)
                        if passo_at and idx_antigo >= len(antigo_livros):
                            passo_at = False 
                        elif not passo_at and idx_novo >= len(novo_livros):
                            passo_at = True 
                        if passo_at:
                            trilha_atual = antigo_livros
                            idx_local = idx_antigo 
                        else:
                            trilha_atual = novo_livros
                            idx_local = idx_novo   
                        if tempo_disponivel_hoje > 0:
                            while tempo_usado_hoje < tempo_disponivel_hoje and idx_local < len(trilha_atual):
                                
                                cap_atual = trilha_atual[idx_local]
                                palavras_cap = DADOS_LEITURA[cap_atual][0] 
                                custo_cap_atual = (palavras_cap / ppm)

                                if tempo_usado_hoje + custo_cap_atual <= tempo_disponivel_hoje:
                                    tempo_usado_hoje += custo_cap_atual
                                    capitulos_hoje.append(cap_atual)
                                    idx_local += 1 
                                    
                                    total_palavras_lidas += palavras_cap
                                    tempo_total_utilizado += custo_cap_atual
                                else:
                                    break 
                        if passo_at:
                            idx_antigo = idx_local
                        else:
                            idx_novo = idx_local
                        # Salvar no plano final
                        plano_diario_final.append({
                            'data': dia_atual.strftime('%d/%m/%Y'),
                            'dia_semana': nome_dia_semana,
                            # Adicionei uma dica visual de qual testamento foi lido
                            'capitulos_str': (f"[Antigo Testamento] " if passo_at else f"[Novo Testamento] ") + (", ".join(capitulos_hoje) if capitulos_hoje else "Descanso"),
                            'tempo_usado': round(tempo_usado_hoje, 2)
                        })
                        dia_atual += timedelta(days=1)
                        count_alt += 1 
                        if len(plano_diario_final) > 10000:
                            print("AVISO: Loop interrompido.")
                            break 
                    status_solucao = "Plano Concluído"
        # Opção 3: Leitura Cronológica           
        if tipo_leitura == '1':
            print("INFO: Rodando leitura cronológica (Sequencial Padrão)")
            trilha_de_leitura = [] 
            arquivo_cronologia = os.path.join(os.path.dirname(__file__), 'cronológica.txt')
            try:
                with open(arquivo_cronologia, 'r', encoding='utf-8') as f:
                    for linha in f:
                        capitulo = linha.strip()
                        if capitulo in DADOS_LEITURA:
                            trilha_de_leitura.append(capitulo)
                        else:
                            print(f"AVISO: Capítulo '{capitulo}' na cronologia não encontrado na base de dados.")
            except FileNotFoundError:
                print(f"ERRO: Arquivo de cronologia '{arquivo_cronologia}' não encontrado.")
                status_solucao = "Erro na Cronologia"
                return render_template('index.html', 
                                       plano_gerado=True,
                                       status_solucao=status_solucao,
                                       total_palavras=total_palavras_lidas,
                                       tempo_utilizado=tempo_total_utilizado,
                                       plano_diario=plano_diario_final, 
                                       user_inputs=request.form)
            
            capitulo_idx = 0
            dia_atual = datetime.now().date()

            while capitulo_idx < len(trilha_de_leitura):
                dia_semana_num = dia_atual.weekday() 
                dia_form_key = MAPA_FORM_KEY[dia_semana_num]
                nome_dia_semana = MAPA_NOME_DIA[dia_semana_num]
                tempo_disponivel_hoje = tempo_disponivel_dia.get(dia_form_key, 0)

                capitulos_hoje = []
                tempo_usado_hoje = 0.0
                if tempo_disponivel_hoje > 0:
                    while tempo_usado_hoje < tempo_disponivel_hoje and capitulo_idx < len(trilha_de_leitura):
                        cap_atual = trilha_de_leitura[capitulo_idx]
                        palavras_cap = DADOS_LEITURA[cap_atual][0] 
                        custo_cap_atual = (palavras_cap / ppm)
                        if tempo_usado_hoje + custo_cap_atual <= tempo_disponivel_hoje:
                            tempo_usado_hoje += custo_cap_atual
                            capitulos_hoje.append(cap_atual)
                            capitulo_idx += 1 
                            total_palavras_lidas += palavras_cap
                            tempo_total_utilizado += custo_cap_atual
                        else:
                            break 
                
                plano_diario_final.append({
                    'data': dia_atual.strftime('%d/%m/%Y'),
                    'dia_semana': nome_dia_semana,
                    'capitulos_str': ", ".join(capitulos_hoje) if capitulos_hoje else "Descanso (Tempo 0)",
                    'tempo_usado': round(tempo_usado_hoje, 2)
                })
                
                dia_atual += timedelta(days=1)
                
                if len(plano_diario_final) > 10000:
                    print("AVISO: Loop interrompido. Tempo de planejamento muito longo.")
                    break 
            
            status_solucao = "Plano Concluído"
        
        # Opção 4: Leitura Livre com Otimização sem retrições
        if tipo_leitura == '2' and restricao_genero == '0':
            print("INFO: Rodando OTIMIZAÇÃO DIÁRIA (Foco no Hoje + Max 2 Livros)")

            capitulos_restantes = list(CAPITULOS) 
            set_caps_restantes = set(CAPITULOS)

            # Mapeamento e Agrupamento
            livros_db = {}
            for cap in CAPITULOS:
                nome = DADOS_LEITURA[cap][3] 
                if nome not in livros_db:
                    livros_db[nome] = []
                livros_db[nome].append(cap)

            livros_em_andamento = set()
            
            dia_atual_iteracao = datetime.now()
            max_dias_seguranca = 2000 
            dia_count = 0

            # --- LOOP PRINCIPAL (UM DIA DE CADA VEZ) ---
            while len(capitulos_restantes) > 0 and dia_count < max_dias_seguranca:
                dia_count += 1
                
                dia_semana_num = dia_atual_iteracao.weekday()
                nome_dia_semana = MAPA_NOME_DIA[dia_semana_num]
                dia_key = MAPA_FORM_KEY[dia_semana_num]
                capacidade_tempo_hoje = tempo_disponivel_dia.get(dia_key, 0)

                capitulos_agendados_hoje = []
                tempo_usado_hoje = 0.0

                if capacidade_tempo_hoje > 0:
                    
                    # 2. SELEÇÃO DE CANDIDATOS (Visão Total)
                    # Enviamos TODOS os capítulos restantes.
                    # Isso garante que o solver ache o "tapa-buraco" perfeito (ex: 3 João)
                    # A restrição de Max 2 Livros impedirá a bagunça.
                    
                    candidatos_rodada = capitulos_restantes # (Cuidado: Pode ser lento se a lista for enorme. Se travar, reduza para os próx 500)

                    # 3. VETORIZAÇÃO
                    cap_nomes_rodada = []
                    c_list_solver = [] 
                    c_list_real = []
                    a_list = []
                    
                    mapa_cap_livro = {}   
                    mapa_livro_indices = {}
                    livros_na_matriz = set()

                    for idx, cap in enumerate(candidatos_rodada):
                        cap_nomes_rodada.append(cap)
                        
                        palavras_cap = DADOS_LEITURA[cap][0]
                        tempo = palavras_cap / ppm
                        nome_livro = DADOS_LEITURA[cap][3]
                        
                        # --- PESOS ---
                        # Prioridade Absoluta para o que já começou.
                        if nome_livro in livros_em_andamento:
                            peso = palavras_cap * 1000000 
                        else:
                            # Peso normal para livros novos (competição por melhor encaixe)
                            peso = palavras_cap * 1 

                        c_list_solver.append(peso)
                        c_list_real.append(palavras_cap)
                        a_list.append(tempo)
                        
                        livros_na_matriz.add(nome_livro)
                        mapa_cap_livro[idx] = nome_livro
                        
                        if nome_livro not in mapa_livro_indices:
                            mapa_livro_indices[nome_livro] = []
                        mapa_livro_indices[nome_livro].append(idx)

                    max_cap_rodada = len(cap_nomes_rodada)
                    lista_livros_unicos = list(livros_na_matriz)

                    # 4. DEFINIÇÃO DO PROBLEMA
                    prob = LpProblem(f"Dia_{dia_count}", LpMaximize)
                    
                    x = [LpVariable(f"x_{c}", cat=LpBinary) for c in range(max_cap_rodada)]
                    
                    # Variável Y: Livro Ativo no Dia
                    y = {livro: LpVariable(f"y_{livro}", cat=LpBinary) for livro in lista_livros_unicos}

                    # Objetivo
                    prob += lpSum([c_list_solver[c] * x[c] for c in range(max_cap_rodada)])

                    # Restrição Tempo
                    prob += lpSum([a_list[c] * x[c] for c in range(max_cap_rodada)]) <= capacidade_tempo_hoje

                    # Ligação X -> Y (Ativação do Livro)
                    for c in range(max_cap_rodada):
                        prob += x[c] <= y[mapa_cap_livro[c]]

                    # --- A TRAVA ANTI-BAGUNÇA ---
                    # Máximo de 2 livros diferentes no mesmo dia.
                    # Isso força o solver a escolher o MELHOR par (ex: Ezequiel + 2 João) 
                    # em vez de pegar pedaços de 10 livros.
                    prob += lpSum([y[livro] for livro in lista_livros_unicos]) <= 2

                    # Ordem Interna (Obrigatório)
                    for livro, indices in mapa_livro_indices.items():
                        for k in range(len(indices) - 1):
                            prob += x[indices[k+1]] <= x[indices[k]]

                    # 5. RESOLVER
                    # 8 segundos para garantir que ele explore bem as combinações de pares
                    solver = PULP_CBC_CMD(msg=0, timeLimit=8) 
                    prob.solve(solver)

                    # 6. PROCESSAR
                    livros_lidos_hoje_set = set()
                    if prob.status == 1: 
                        for c in range(max_cap_rodada):
                            if x[c].varValue and x[c].varValue > 0.9:
                                nome_cap = cap_nomes_rodada[c]
                                capitulos_agendados_hoje.append(nome_cap)
                                
                                tempo_usado_hoje += a_list[c]
                                total_palavras_lidas += c_list_real[c]
                                livros_lidos_hoje_set.add(mapa_cap_livro[c])
                
                # 7. REMOÇÃO E ATUALIZAÇÃO
                for cap_lido in capitulos_agendados_hoje:
                    if cap_lido in capitulos_restantes:
                        capitulos_restantes.remove(cap_lido)
                    if cap_lido in set_caps_restantes:
                        set_caps_restantes.remove(cap_lido)

                # Atualiza Livros em Andamento
                for livro_lido in livros_lidos_hoje_set:
                    ainda_tem = False
                    for cap in livros_db[livro_lido]:
                        if cap in set_caps_restantes:
                            ainda_tem = True
                            break
                    if ainda_tem:
                        livros_em_andamento.add(livro_lido)
                    else:
                        if livro_lido in livros_em_andamento:
                            livros_em_andamento.remove(livro_lido)

                # 8. REGISTRAR
                tempo_total_utilizado += tempo_usado_hoje
                
                plano_diario_final.append({
                    'data': dia_atual_iteracao.strftime('%d/%m/%Y'),
                    'dia_semana': nome_dia_semana,
                    'capitulos_str': ", ".join(capitulos_agendados_hoje) if capitulos_agendados_hoje else "Descanso / Sem Tempo",
                    'tempo_usado': round(tempo_usado_hoje, 2)
                })

                dia_atual_iteracao += timedelta(days=1)

            status_solucao = "Plano Concluído"

        if tipo_leitura == '2' and restricao_genero == '1':
            print("INFO: Rodando LEITURA COM FOCO DIÁRIO (Gênero + Ordem Interna)")
            
            # 1. ESTRUTURAS DE DADOS
            # Agrupar por gênero e depois por livro
            generos_db = {}
            for cap in CAPITULOS:
                genero = DADOS_LEITURA[cap][1]  # Gênero
                livro = DADOS_LEITURA[cap][2]   # Nome do livro
                
                if genero not in generos_db:
                    generos_db[genero] = {}
                if livro not in generos_db[genero]:
                    generos_db[genero][livro] = []
                
                generos_db[genero][livro].append(cap)
            
            # Ordenar capítulos dentro de cada livro (mantém ordem canônica)
            for genero in generos_db:
                for livro in generos_db[genero]:
                    generos_db[genero][livro].sort(key=lambda cap: CAPITULOS.index(cap))
            
            # 2. CALCULAR TEMPO POR GÊNERO E LIVRO
            generos_info = {}
            for genero, livros in generos_db.items():
                generos_info[genero] = {
                    'livros_ordenados': sorted(livros.keys()),  # Ordem alfabética para consistência
                    'tempo_total': 0,
                    'livros_info': {}
                }
                
                for livro, capitulos in livros.items():
                    tempo_livro = sum(DADOS_LEITURA[cap][0] for cap in capitulos) / ppm
                    palavras_livro = sum(DADOS_LEITURA[cap][0] for cap in capitulos)
                    
                    generos_info[genero]['livros_info'][livro] = {
                        'capitulos': capitulos,
                        'tempo': tempo_livro,
                        'palavras': palavras_livro,
                        'proximo_capitulo': 0  # Índice do próximo capítulo a ler
                    }
                    generos_info[genero]['tempo_total'] += tempo_livro
            
            # 3. CONFIGURAÇÃO INICIAL
            dia_atual = datetime.now()
            plano_diario_final = []
            
            # Estado: controle de progresso por gênero
            progresso_generos = {genero: {'livro_atual': None, 'livros_completos': set()} 
                               for genero in generos_db.keys()}
            
            # 4. OTIMIZAÇÃO DIÁRIA POR GÊNERO
            dias_simulados = 0
            max_dias = 365
            
            while dias_simulados < max_dias:
                dia_semana_num = dia_atual.weekday()
                dia_key = MAPA_FORM_KEY[dia_semana_num]
                nome_dia_semana = MAPA_NOME_DIA[dia_semana_num]
                capacidade_tempo_hoje = tempo_disponivel_dia.get(dia_key, 0)
                
                capitulos_agendados_hoje = []
                tempo_usado_hoje = 0.0
                palavras_hoje = 0
                genero_escolhido = None
                livro_escolhido = None
                
                if capacidade_tempo_hoje > 0:
                    # 5. ESCOLHER MELHOR GÊNERO PARA HOJE
                    melhor_genero = None
                    melhor_eficiencia = -1
                    
                    for genero in generos_db.keys():
                        # Pular gêneros completos
                        if len(progresso_generos[genero]['livros_completos']) >= len(generos_db[genero]):
                            continue
                        
                        # Calcular eficiência deste gênero
                        livros_pendentes = [livro for livro in generos_db[genero].keys() 
                                          if livro not in progresso_generos[genero]['livros_completos']]
                        
                        if not livros_pendentes:
                            continue
                        
                        # Priorizar gêneros com livro atual em andamento
                        livro_atual = progresso_generos[genero]['livro_atual']
                        if livro_atual and livro_atual in livros_pendentes:
                            # Continuar livro atual
                            tempo_necessario = generos_info[genero]['livros_info'][livro_atual]['tempo']
                            eficiencia = capacidade_tempo_hoje / tempo_necessario if tempo_necessario > 0 else 0
                            livro_candidato = livro_atual
                        else:
                            # Começar novo livro - pegar o primeiro da ordem
                            primeiro_livro = livros_pendentes[0]
                            tempo_necessario = generos_info[genero]['livros_info'][primeiro_livro]['tempo']
                            eficiencia = capacidade_tempo_hoje / tempo_necessario if tempo_necessario > 0 else 0
                            livro_candidato = primeiro_livro
                        
                        if eficiencia > melhor_eficiencia:
                            melhor_eficiencia = eficiencia
                            melhor_genero = genero
                            livro_escolhido = livro_candidato
                    
                    genero_escolhido = melhor_genero
                
                # 6. AGENDAR CAPÍTULOS DO GÊNERO ESCOLHIDO
                if genero_escolhido and capacidade_tempo_hoje > 0:
                    genero_info = generos_info[genero_escolhido]
                    progresso = progresso_generos[genero_escolhido]
                    
                    # Usar livro escolhido na otimização
                    livro_atual = livro_escolhido
                    progresso['livro_atual'] = livro_atual
                    
                    if livro_atual:
                        livro_info = genero_info['livros_info'][livro_atual]
                        capitulos_livro = livro_info['capitulos']
                        idx_proximo = livro_info['proximo_capitulo']
                        
                        # Agendar capítulos sequenciais do livro atual
                        tempo_restante = capacidade_tempo_hoje
                        
                        while (idx_proximo < len(capitulos_livro) and 
                               tempo_restante > 0 and 
                               tempo_usado_hoje < capacidade_tempo_hoje):
                            
                            cap_atual = capitulos_livro[idx_proximo]
                            tempo_cap = DADOS_LEITURA[cap_atual][0] / ppm
                            
                            if tempo_cap <= tempo_restante:
                                capitulos_agendados_hoje.append(cap_atual)
                                tempo_usado_hoje += tempo_cap
                                tempo_restante -= tempo_cap
                                palavras_hoje += DADOS_LEITURA[cap_atual][0]
                                idx_proximo += 1
                                
                                # Atualizar progresso
                                livro_info['proximo_capitulo'] = idx_proximo
                                
                                # Verificar se livro foi completado
                                if idx_proximo >= len(capitulos_livro):
                                    progresso['livros_completos'].add(livro_atual)
                                    progresso['livro_atual'] = None
                                    break
                            else:
                                break
                
                # 7. REGISTRAR DIA - FORMATO CORRIGIDO
                total_palavras_lidas += palavras_hoje
                tempo_total_utilizado += tempo_usado_hoje
                
                # Montar string descritiva COM CAPÍTULOS ESPECÍFICOS
                if genero_escolhido and capitulos_agendados_hoje:
                    # Formatar: [GÊNERO] LIVRO CAP1, CAP2, CAP3...
                    livro_nome = DADOS_LEITURA[capitulos_agendados_hoje[0]][2]
                    
                    # Abreviar nomes dos capítulos (ex: "MT 1, MT 2, MT 3")
                    capitulos_abreviados = []
                    for cap in capitulos_agendados_hoje:
                        # Manter apenas a abreviação do livro + número
                        partes = cap.split()
                        if len(partes) >= 2:
                            livro_abrev = partes[0]
                            num_cap = partes[1]
                            capitulos_abreviados.append(f"{livro_abrev} {num_cap}")
                        else:
                            capitulos_abreviados.append(cap)
                    
                    capitulos_str = ", ".join(capitulos_abreviados)
                    descricao = f"[{genero_escolhido.upper()}] {capitulos_str}"
                    
                elif genero_escolhido:
                    descricao = f"[{genero_escolhido.upper()}] - Sem tempo suficiente"
                else:
                    descricao = "Descanso / Todos gêneros completos"
                
                plano_diario_final.append({
                    'data': dia_atual.strftime('%d/%m/%Y'),
                    'dia_semana': nome_dia_semana,
                    'capitulos_str': descricao,
                    'tempo_usado': round(tempo_usado_hoje, 2)
                })
                
                dia_atual += timedelta(days=1)
                dias_simulados += 1
                
                # Verificar se todos os gêneros estão completos
                todos_completos = all(
                    len(progresso['livros_completos']) >= len(generos_db[genero])
                    for genero, progresso in progresso_generos.items()
                )
                if todos_completos:
                    break

            status_solucao = "Plano Concluído"

        #if tipo_leitura == '2' and restricao_genero == '0' and restricao_interna == '1':

        #if tipo_leitura == '2' and restricao_genero == '1' and restricao_interna == '1':


        # -----------------------------------------------------------------
        # 3. RENDERIZAR O RESULTADO (do POST)
        # -----------------------------------------------------------------
        return render_template('index.html', 
                               plano_gerado=True,
                               status_solucao=status_solucao,
                               total_palavras=total_palavras_lidas,
                               tempo_utilizado=tempo_total_utilizado,
                               plano_diario=plano_diario_final, 
                               user_inputs=request.form) # Passa os dados de volta
    
    # -----------------------------------------------------------------
    # SE O MÉTODO FOR GET (Primeira visita à página)
    # -----------------------------------------------------------------
    else:
        return render_template('index.html', plano_gerado=False)

if __name__ == '__main__':
    app.run(debug=True)