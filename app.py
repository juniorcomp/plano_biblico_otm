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
# Mapas auxiliares
MAPA_FORM_KEY = { 0: 'segunda', 1: 'terça', 2: 'quarta', 3: 'quinta', 4: 'sexta', 5: 'sábado', 6: 'domingo' }
MAPA_NOME_DIA = { 0: 'Segunda-feira', 1: 'Terça-feira', 2: 'Quarta-feira', 3: 'Quinta-feira', 4: 'Sexta-feira', 5: 'Sábado', 6: 'Domingo' }

# Rota principal da aplicação
@app.route('/', methods=['GET', 'POST'])
def otimizar_leitura():
    # Verifica se os dados foram carregados
    if not CAPITULOS:
        return "Erro: O arquivo dados_biblia.csv não foi carregado. Verifique o terminal para detalhes.", 500

    if request.method == 'POST':
        # Coleta os dados do formulário
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

        # Opção 1: LEiTURA LITERÁRIA SIMPLES 
        if tipo_leitura == '0' and leitura_alternada == '0':
            print("INFO: Rodando o AGENDADOR de Leitura Literária (Sequencial Padrão)")
            trilha_de_leitura = CAPITULOS 
            capitulo_idx = 0
            dia_atual = datetime.now().date() #Data atual
            #first fit
            while capitulo_idx < len(trilha_de_leitura):  
                dia_semana_num = dia_atual.weekday() # NUMERAÇÃO DO DIA DA SEMANA
                dia_form_key = MAPA_FORM_KEY[dia_semana_num]
                nome_dia_semana = MAPA_NOME_DIA[dia_semana_num]
                tempo_disponivel_hoje = tempo_disponivel_dia.get(dia_form_key, 0)
                capitulos_hoje = []
                tempo_usado_hoje = 0.0
                # aloca capítulos enquanto houver tempo
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
                #adiciona no plano final
                plano_diario_final.append({
                    'data': dia_atual.strftime('%d/%m/%Y'),
                    'dia_semana': nome_dia_semana,
                    'capitulos_str': ", ".join(capitulos_hoje) if capitulos_hoje else "Descanso (Tempo 0)",
                    'tempo_usado': round(tempo_usado_hoje, 2)
                })
                # avança para o próximo dia
                dia_atual += timedelta(days=1)
                if len(plano_diario_final) > 10000:
                    print("AVISO: Loop interrompido. Tempo de planejamento muito longo.")
                    break 
            status_solucao = "Plano Concluído"
        # Opção 2: Leitura Literária & Leitura Alternada
        if tipo_leitura == '0' and leitura_alternada == '1':
                    print("INFO: Rodando o AGENDADOR de Leitura Literária (Alternada por Dia)")
                    # cria uma lista separada para cada testamento
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
                    # round robin alternado
                    while idx_antigo < len(antigo_livros) or idx_novo < len(novo_livros):
                        dia_semana_num = dia_atual.weekday() 
                        dia_form_key = MAPA_FORM_KEY[dia_semana_num]
                        nome_dia_semana = MAPA_NOME_DIA[dia_semana_num]
                        tempo_disponivel_hoje = tempo_disponivel_dia.get(dia_form_key, 0)
                        capitulos_hoje = []
                        tempo_usado_hoje = 0.0
                        passo_at = (count_alt % 2 == 0)
                        # Alterna entre os testamentos
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
                            # aloca capítulos enquanto houver tempo 
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
            # testa erro no arquivo de cronologia
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
            #indice do capitulo
            capitulo_idx = 0
            dia_atual = datetime.now().date()
            #
            # first fit com ordem cronológica
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
            print("INFO: Rodando Opção 4")
            total_palavras_lidas = 0
            tempo_total_utilizado = 0
            status_solucao = "Em Processamento..."
            plano_diario_final = []
            # Livros que permitem pular capítulos (ordem interna livre)
            livros_poeticos_livres = {'sl', 'pv', 'ec', 'ct'} 
            # Conjuntos de controle
            capitulos_restantes = list(CAPITULOS)
            set_caps_restantes = set(CAPITULOS)
            livros_em_andamento = set()
            # cria estrutura de livros em ordem e capítulos
            livros_db = {}    
            ordem_livros = []  
            # Agrupa capítulos por livro
            for cap in CAPITULOS:
                dados = DADOS_LEITURA[cap]
                nome_livro = dados[3] # Sigla
                if nome_livro not in livros_db:
                    livros_db[nome_livro] = []
                    ordem_livros.append(nome_livro)
                livros_db[nome_livro].append(cap)
            # Variáveis de Loop
            dia_atual_iteracao = datetime.now()
            max_dias = 2000 # para evitar loops infinitos
            dia_count = 0
            # Laço principal de otimização diária
            while capitulos_restantes and dia_count < max_dias:
                dia_count += 1
                # Dados do Dia
                dia_sem = dia_atual_iteracao.weekday()
                key_dia = MAPA_FORM_KEY[dia_sem]
                # variável de controle
                tempo_max = tempo_disponivel_dia.get(key_dia, 0)
                capitulos_hoje = []
                tempo_usado_hoje = 0.0 
                if tempo_max > 0:
                    # candidatos para o dia
                    candidatos = []
                    generos_bloqueados = set() 
                    livros_candidatos_set = set() 
                    # limite de palavras para candidatos
                    # margem de 20% para flexibilidade
                    limite_palavras_candidatas = (tempo_max * ppm) * 1.2
                    for livro in ordem_livros:
                        caps_do_livro = livros_db[livro]
                        pendentes = [c for c in caps_do_livro if c in set_caps_restantes]
                        if not pendentes: continue
                        # genero já selecionado hoje?
                        genero = DADOS_LEITURA[pendentes[0]][1]
                        if genero in generos_bloqueados:
                            continue 
                        # bloqueia gênero para o dia
                        generos_bloqueados.add(genero)
                        # Coleta capítulos
                        acc_palavras = 0
                        for c in pendentes:
                            candidatos.append(c)
                            livros_candidatos_set.add(livro)
                            acc_palavras += DADOS_LEITURA[c][0]
                            # Limite de palavras
                            if acc_palavras > limite_palavras_candidatas:
                                break
                    if not candidatos:
                        dia_atual_iteracao += timedelta(days=1)
                        continue
                    # MODELAGEM MILP 
                    prob = LpProblem(f"Dia_{dia_count}", LpMaximize)
                    # Variáveis de Decisão
                    x = LpVariable.dicts("x", candidatos, cat=LpBinary)
                    y = LpVariable.dicts("y", list(livros_candidatos_set), cat=LpBinary)
                    # Funções Auxiliares
                    def get_tempo(c): return DADOS_LEITURA[c][0] / ppm
                    def get_peso(c):
                        livro = DADOS_LEITURA[c][3]
                        base = DADOS_LEITURA[c][0] 
                        if livro in livros_em_andamento: return base * 1000 
                        return base
                    # Função Objetivo
                    prob += lpSum([x[c] * get_peso(c) for c in candidatos])
                    # Restrições 
                    prob += lpSum([x[c] * get_tempo(c) for c in candidatos]) <= tempo_max
                    prob += lpSum([y[l] for l in livros_candidatos_set]) <= 3
                    # Link X -> Y
                    for c in candidatos:
                        livro = DADOS_LEITURA[c][3]
                        prob += x[c] <= y[livro]
                    # Ordem Interna
                    candidatos_por_livro = {}
                    for c in candidatos:
                        l = DADOS_LEITURA[c][3]
                        if l not in candidatos_por_livro: candidatos_por_livro[l] = []
                        candidatos_por_livro[l].append(c)
                    # aplica restrição de ordem apenas para livros não-livres
                    for livro, caps_list in candidatos_por_livro.items():
                        if livro.lower() in livros_poeticos_livres:
                            continue 
                        # aplica ordem sequencial
                        for i in range(len(caps_list) - 1):
                            atual = caps_list[i]
                            proximo = caps_list[i+1]
                            prob += x[proximo] <= x[atual]
                    # Resolve o modelo
                    solver = PULP_CBC_CMD(msg=0, timeLimit=3)
                    prob.solve(solver)
                    livros_lidos_hoje = set()
                    if prob.status == 1: 
                        # Ordena para manter a ordem bíblica na exibição
                        candidatos_ordenados = [c for c in CAPITULOS if c in x] 
                        for c in candidatos_ordenados:
                            if x[c].value() > 0.9:
                                # atualização dos capítulos lidos hoje
                                capitulos_hoje.append(c)
                                tempo_cap = get_tempo(c)
                                palavras_cap = DADOS_LEITURA[c][0]
                                tempo_usado_hoje += tempo_cap
                                total_palavras_lidas += palavras_cap # Acumulador Global
                                nome_livro = DADOS_LEITURA[c][3]
                                livros_lidos_hoje.add(nome_livro)
                        # Atualiza acumulador Global de Tempo
                        tempo_total_utilizado += tempo_usado_hoje
                # Registra o dia no plano final
                if capitulos_hoje:
                    for c in capitulos_hoje:
                        set_caps_restantes.discard(c)
                        if c in capitulos_restantes: capitulos_restantes.remove(c)

                    for livro in livros_lidos_hoje:
                        todos_caps = livros_db[livro]
                        restam = any(c in set_caps_restantes for c in todos_caps)
                        
                        if restam:
                            livros_em_andamento.add(livro)
                        elif livro in livros_em_andamento:
                            livros_em_andamento.remove(livro)

                    plano_diario_final.append({
                        'data': dia_atual_iteracao.strftime('%d/%m/%Y'),
                        'dia_semana': MAPA_NOME_DIA[dia_sem],
                        'capitulos_str': ", ".join(capitulos_hoje),
                        'tempo_usado': round(tempo_usado_hoje, 2)
                    })
                else:
                    plano_diario_final.append({
                        'data': dia_atual_iteracao.strftime('%d/%m/%Y'),
                        'dia_semana': MAPA_NOME_DIA[dia_sem],
                        'capitulos_str': "Descanso / Ajuste",
                        'tempo_usado': 0
                    })

                dia_atual_iteracao += timedelta(days=1)
            status_solucao = "Plano Concluído"
        #Opção 5 Leitura Livre com Restrição por Gênero    
        if tipo_leitura == '2' and restricao_genero == '1':
            print("INFO: Rodando LEITURA COM FOCO DIÁRIO (Gênero + Ordem Interna)")
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
            generos_info = {}
            for genero, livros in generos_db.items():
                generos_info[genero] = {
                    'livros_ordenados': sorted(livros.keys()),  
                    'tempo_total': 0,
                    'livros_info': {}
                }
                # Calcular tempo e palavras por livro
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
            dia_atual = datetime.now()
            plano_diario_final = []
            # Controle de progresso por gênero
            progresso_generos = {genero: {'livro_atual': None, 'livros_completos': set()} 
                               for genero in generos_db.keys()}
            # restrições de loop
            dias_simulados = 0
            max_dias = 365
            # Laço principal de agendamento diário
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
                    melhor_genero = None
                    melhor_eficiencia = -1
                    for genero in generos_db.keys():
                        if len(progresso_generos[genero]['livros_completos']) >= len(generos_db[genero]):
                            continue
                        livros_pendentes = [livro for livro in generos_db[genero].keys() 
                                          if livro not in progresso_generos[genero]['livros_completos']]
                        if not livros_pendentes:
                            continue
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
                           #  Verificar se é a melhor eficiência
                        if eficiencia > melhor_eficiencia:
                            melhor_eficiencia = eficiencia
                            melhor_genero = genero
                            livro_escolhido = livro_candidato
                    genero_escolhido = melhor_genero   
                 #  Agendar capítulos do gênero escolhido
                if genero_escolhido and capacidade_tempo_hoje > 0:
                    genero_info = generos_info[genero_escolhido]
                    progresso = progresso_generos[genero_escolhido]
                    livro_atual = livro_escolhido
                    progresso['livro_atual'] = livro_atual             
                    if livro_atual:
                        livro_info = genero_info['livros_info'][livro_atual]
                        capitulos_livro = livro_info['capitulos']
                        idx_proximo = livro_info['proximo_capitulo']
                        tempo_restante = capacidade_tempo_hoje
                         # Alocar capítulos enquanto houver tempo
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
                total_palavras_lidas += palavras_hoje
                tempo_total_utilizado += tempo_usado_hoje
                if genero_escolhido and capitulos_agendados_hoje:
                    # Formatação
                    livro_nome = DADOS_LEITURA[capitulos_agendados_hoje[0]][2]
                    capitulos_abreviados = []
                    for cap in capitulos_agendados_hoje:
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
                # Adiciona ao plano final
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
# Finalização da Rota
        return render_template('index.html', 
                               plano_gerado=True,
                               status_solucao=status_solucao,
                               total_palavras=total_palavras_lidas,
                               tempo_utilizado=tempo_total_utilizado,
                               plano_diario=plano_diario_final, 
                               user_inputs=request.form) 
    else:
        return render_template('index.html', plano_gerado=False)
# Rodar a aplicação
if __name__ == '__main__':
    app.run(debug=True)