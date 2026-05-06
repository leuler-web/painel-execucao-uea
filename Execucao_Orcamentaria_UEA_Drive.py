import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
from io import BytesIO
from st_aggrid import AgGrid, GridOptionsBuilder

# IMPORTANDO O AGGRID (A Mágica do Excel)
from st_aggrid import AgGrid, GridOptionsBuilder
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="PAINEL ORÇAMENTÁRIO - UEA", 
    layout="wide", 
    page_icon="📈",
    initial_sidebar_state="expanded"
)

if 'pagina_ativa' not in st.session_state:
    st.session_state.pagina_ativa = 'capa' 

# ==========================================
# 2. BLOCO ÚNICO DE ESTILOS CSS (LIMPO E SEGURO)
# ==========================================
st.markdown("""
    <style>
    /* Segurança: Esconde Deploy e GitHub */
    .stAppDeployButton { display: none !important; }
    footer { visibility: hidden !important; }
    [data-testid="stHeader"] > div:first-child { display: none !important; }
    
    /* Iframe UEA: Título não cortar */
    .block-container { 
        padding-top: 100px !important; 
        max-width: 100% !important; 
    }

    /* Cabeçalho fixo (Título e KPIs) */
    [data-testid="stVerticalBlock"] > div:has(div.unificar-header) {
        position: sticky; top: 0px; background-color: white; z-index: 99;
        padding-top: 10px !important; border-bottom: 2px solid #e5e7eb;
    }
    
    [data-testid="stMetricValue"] { color: #004587 !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. GESTÃO DE ESTADO
# ==========================================
if 'pagina_ativa' not in st.session_state:
    st.session_state.pagina_ativa = 'capa'

if 'botao_reset' not in st.session_state:
    st.session_state.botao_reset = 0

def forcar_limpeza_total():
    st.session_state.botao_reset += 1

# ==========================================
# 4. DICIONÁRIOS E FUNÇÕES DE FORMATAÇÃO
# ==========================================
dict_fontes_global = {
    '201': 'Recursos Diretamente Arrecadados', '280': 'Convênios ou transferências',
    '116': 'Fonte do Tesouro', '285': 'Outras Fontes', '243': 'Transferências vinculadas/fundos'
}

def extrair_numero(val):
    try:
        if pd.isna(val): return 0.0
        if isinstance(val, (int, float)): return float(val)
        txt = str(val).upper().replace('R$', '').replace(' ', '').strip()
        if txt == '' or txt == 'NAN': return 0.0
        if ',' in txt: txt = txt.replace('.', '').replace(',', '.')
        else:
            if txt.count('.') > 1: txt = txt.replace('.', '')
            elif txt.count('.') == 1:
                partes = txt.split('.')
                if len(partes[1]) == 3: txt = txt.replace('.', '')
        return float(txt)
    except Exception: return 0.0

def formata_moeda_sem_decimal(valor):
    if pd.isna(valor): return "R$ 0"
    try: return f"R$ {extrair_numero(valor):,.0f}".replace(',', '.')
    except Exception: return str(valor)

def formata_numero_duas_casas(valor):
    if pd.isna(valor): return "0,00"
    try: 
        val_formatado = f"{extrair_numero(valor):,.2f}"
        return val_formatado.replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception: return str(valor)

def formata_abreviado(valor):
    try:
        val_num = extrair_numero(valor)
        if val_num == 0: return "R$ 0"
        sinal = "-" if val_num < 0 else ""
        abs_val = abs(val_num)
        if abs_val >= 1_000_000_000: return f"{sinal}R$ {abs_val/1_000_000_000:.1f} Bi".replace('.', ',')
        elif abs_val >= 1_000_000: return f"{sinal}R$ {abs_val/1_000_000:.1f} Mi".replace('.', ',')
        elif abs_val >= 1_000: return f"{sinal}R$ {abs_val/1_000:.1f} mil".replace('.', ',')
        else: return f"{sinal}R$ {abs_val:,.0f}".replace(',', '.')
    except Exception: return str(valor)

def destacar_celulas_com_variacao(df):
    estilos = pd.DataFrame('', index=df.index, columns=df.columns)
    for col in df.columns:
        if 'Varia' in str(col) or 'Diferença' in str(col):
            mask = df[col].apply(extrair_numero).abs() > 0.001
            estilos.loc[mask, col] = 'background-color: #FFFF00; color: #000000; font-weight: bold;'
    return estilos

# ==========================================
# 5. CARREGAMENTO DOS DADOS E DICIONÁRIOS
# ==========================================
@st.cache_data(ttl=3600)
def carregar_dicionarios():
    dict_acoes, dict_naturezas, status_msg = {}, {}, ""
    caminho_aux = r"Tabelas_Auxiliares.xlsx"
    if os.path.exists(caminho_aux):
        try:
            xls = pd.ExcelFile(caminho_aux)
            for aba in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=aba)
                if 'AÇ' in aba.upper() or 'AC' in aba.upper():
                    df_acao = df.copy()
                    df_acao.columns = [str(c).upper().strip() for c in df_acao.columns]
                    col_acao = next((c for c in df_acao.columns if 'AÇ' in c or 'AC' in c), None)
                    if col_acao:
                        col_nome = next((c for c in df_acao.columns if 'IDENTIFICA' in c), None)
                        if not col_nome:
                            idx = df_acao.columns.get_loc(col_acao)
                            if idx + 2 < len(df_acao.columns): col_nome = df_acao.columns[idx + 2]
                            elif idx + 1 < len(df_acao.columns): col_nome = df_acao.columns[idx + 1]
                        if col_nome:
                            for _, row in df_acao.iterrows():
                                cod = str(row[col_acao]).split('.')[0].strip().zfill(4)
                                if cod.isdigit() and len(cod) == 4: dict_acoes[cod] = str(row[col_nome]).strip()
                if 'NAT' in aba.upper():
                    df_nat = df.copy()
                    if len(df_nat.columns) >= 2:
                        col_cod, col_nome = df_nat.columns[0], df_nat.columns[1]
                        for _, row in df_nat.iterrows():
                            cod_limpo = str(row[col_cod]).split('.')[0].strip().replace('-', '')
                            cod_numeros = ''.join([char for char in cod_limpo if char.isdigit()])
                            if cod_numeros: dict_naturezas[cod_numeros[:6]] = str(row[col_nome]).strip()
            status_msg = f"Dicionários OK! ({len(dict_acoes)} Ações)"
        except Exception as e: status_msg = f"Erro na leitura: {e}"
    else: status_msg = "Arquivo Tabelas_Auxiliares.xlsx não encontrado."
    return dict_acoes, dict_naturezas, status_msg

@st.cache_data(ttl=3600)
def carregar_dados_v181(path):
    tipos_forcados = {'Programa de Trabalho': str, 'Fonte de Recurso': str, 'Natureza da Despesa': str}
    df_base = pd.read_excel(path, sheet_name='Base_Consolidada', dtype=tipos_forcados)
    df_var = pd.read_excel(path, sheet_name='Variacoes_Recentes', dtype=tipos_forcados)

    colunas_preencher = ['Mês Referência', 'Programa de Trabalho', 'Fonte de Recurso', 'Natureza da Despesa', 'Tipo Movimento']
    for col in colunas_preencher:
        if col in df_base.columns:
            df_base[col] = df_base[col].replace(['nan', 'None', ''], np.nan).ffill()
        if col in df_var.columns:
            df_var[col] = df_var[col].replace(['nan', 'None', ''], np.nan).ffill()

    palavras_fin = ['Autorizado', 'Empenhado', 'Liquidado', 'Pago', 'Dotação', 'Reduções', 'Variação', 'Disponível', 'Bloqueado']
    
    def limpar_nomes_colunas(df):
        df.columns = [str(c).strip() for c in df.columns]
        novas_colunas = []
        for c in df.columns:
            if any(p.lower() in c.lower() for p in palavras_fin) and 'Data_' not in c:
                c = c.replace('_Ant.', ' Ant.').replace('_Ant', ' Ant.')
                if c.endswith(' Ant'): c = c[:-4] + ' Ant.'
                c = c.replace(' Ant ', ' Ant. ').replace('Ant..', 'Ant.')
                c = c.replace('_Atual.', ' Atual.').replace('_Atual', ' Atual.')
                if c.endswith(' Atual'): c = c[:-6] + ' Atual.'
                c = c.replace(' Atual ', ' Atual. ').replace('Atual..', 'Atual.')
            novas_colunas.append(c)
        df.columns = novas_colunas
        return df

    df_base = limpar_nomes_colunas(df_base)
    df_var = limpar_nomes_colunas(df_var)
    
    def remover_fantasmas(df):
        df['Programa de Trabalho'] = df['Programa de Trabalho'].astype(str).str.replace('nan', '', regex=False).str.strip()
        mascara_fantasma = (df['Programa de Trabalho'] == '') | (df['Programa de Trabalho'] == '0')
        return df[~mascara_fantasma].copy()
        
    df_base = remover_fantasmas(df_base)
    df_var = remover_fantasmas(df_var)
    
    for df in [df_base, df_var]:
        colunas_fin = [col for col in df.columns if any(p in col for p in palavras_fin)]
        for col in colunas_fin: 
            df[col] = df[col].apply(extrair_numero)
            
    colunas_texto = ['Programa de Trabalho', 'Fonte de Recurso', 'Natureza da Despesa', 'Mês Referência', 'Tipo Movimento']
    for df in [df_base, df_var]:
        for col in colunas_texto:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().replace('nan', '')
        
        # ========================================================================
        # 💡 CORREÇÃO 1: BLINDAGEM DO TIPO DE MOVIMENTO (SEPARA ACUMULADO E MÊS)
        # ========================================================================
        if 'Tipo Movimento' in df.columns:
            def classificar_movimento(x):
                txt = str(x).upper().strip()
                if txt in ['NAN', 'NONE', '', '0', '0.0']: return x
                # Se o SIAFI chamou de 'Até o Mês' ou 'Acumulado', vai para a caixa certa
                if 'ACUMULADO' in txt or 'ATÉ' in txt or 'ATE' in txt: 
                    return 'Acumulado'
                # Todo o resto (como 'No Mês') vira 'Mês'
                return 'Mês'
            
            df['Tipo Movimento'] = df['Tipo Movimento'].apply(classificar_movimento)
        
        if 'Programa de Trabalho' in df.columns:
            def extrair_acao(pt):
                pt_limpo = str(pt).replace('.', '').replace('-', '').replace(' ', '')
                if len(pt_limpo) >= 13: return pt_limpo[9:13]
                return ""
            df['Ação'] = df['Programa de Trabalho'].apply(extrair_acao)
            df['Ação'] = df['Ação'].apply(lambda x: str(x).strip() if str(x).strip().isdigit() and len(str(x).strip()) == 4 else "")
        
        if 'Natureza da Despesa' in df.columns:
            df['Natureza_ID'] = df['Natureza da Despesa'].astype(str).str.replace(r'\D', '', regex=True).str[:6]
        
        if 'Fonte de Recurso' in df.columns:
            df['Fonte_7'] = df['Fonte de Recurso'].astype(str).str.replace(r'\D', '', regex=True).str[:7]
            df['Fonte_3'] = df['Fonte_7'].str[-3:]
            
    return df_base, df_var

# ==========================================
# 6. O PLANO B: BLINDAGEM GLOBAL (TRY/EXCEPT)
# ==========================================
try:
    PATH_SIAFI = r"Base_Consolidada_SIAFI.xlsx"
    df_base, df_var = carregar_dados_v181(PATH_SIAFI)
    dict_acoes, dict_naturezas, status_dic = carregar_dicionarios()

    ordem_meses = {
        'Janeiro': 1, 'Fevereiro': 2, 'Março': 3, 'Marco': 3, 'Abril': 4, 'Maio': 5, 'Junho': 6, 
        'Julho': 7, 'Agosto': 8, 'Setembro': 9, 'Outubro': 10, 'Novembro': 11, 'Dezembro': 12,
        'Jan': 1, 'Fev': 2, 'Mar': 3, 'Abr': 4, 'Mai': 5, 'Jun': 6, 'Jul': 7, 'Ago': 8, 'Set': 9, 'Out': 10, 'Nov': 11, 'Dez': 12
    }
    abrev_meses = {
        'Janeiro': 'jan', 'Fevereiro': 'fev', 'Março': 'mar', 'Marco': 'mar', 'Abril': 'abr', 'Maio': 'mai', 'Junho': 'jun', 
        'Julho': 'jul', 'Agosto': 'ago', 'Setembro': 'set', 'Outubro': 'out', 'Novembro': 'nov', 'Dezembro': 'dez',
        'Jan': 'jan', 'Fev': 'fev', 'Mar': 'mar', 'Abr': 'abr', 'Mai': 'mai', 'Jun': 'jun'
    }

    try:
        val_ant = df_var['Data_Extracao_Anterior'].dropna().iloc[0]
        val_atual = df_var['Data_Extracao_Atual'].dropna().iloc[0]
        dt_ant = pd.to_datetime(val_ant, errors='coerce').strftime('%d/%m/%Y')
        dt_atual = pd.to_datetime(val_atual, errors='coerce').strftime('%d/%m/%Y')
        texto_periodo = f"Posição Consolidada da Base: {dt_atual}" if dt_ant == dt_atual else f"Comparativo Automático: Extrato de {dt_ant} até {dt_atual}"
    except Exception: 
        dt_atual = "N/D"
        texto_periodo = "Aguardando atualização da base de dados."

    # ========================================================================
    # 💡 CORREÇÃO 2: TRATAMENTO DE CHOQUE NO MÊS REFERÊNCIA (FUZZY MATCHING)
    # ========================================================================
    if 'Mês Referência' in df_base.columns:
        def identificar_mes_streamlit(texto):
            t = str(texto).upper().strip()
            if 'JAN' in t: return 'Janeiro'
            if 'FEV' in t: return 'Fevereiro'
            if 'MA' in t and 'R' in t: return 'Março' # O Exterminador de erros (Maro, Marco, Março)
            if 'ABR' in t: return 'Abril'
            if 'MAI' in t: return 'Maio'
            if 'JUN' in t: return 'Junho'
            if 'JUL' in t: return 'Julho'
            if 'AGO' in t: return 'Agosto'
            if 'SET' in t: return 'Setembro'
            if 'OUT' in t: return 'Outubro'
            if 'NOV' in t: return 'Novembro'
            if 'DEZ' in t: return 'Dezembro'
            return t.capitalize()

        df_base['Mes_Nome'] = df_base['Mês Referência'].apply(identificar_mes_streamlit)
        df_base['Mes_Num'] = df_base['Mes_Nome'].map(ordem_meses)
        df_base['Ano_Ref'] = df_base['Mês Referência'].astype(str).str.extract(r'(\d{4})')
    else:
        df_base['Mes_Nome'] = 'Desconhecido'; df_base['Mes_Num'] = 0; df_base['Ano_Ref'] = '2026'

    try:
        ano_dinamico = str(df_base['Ano_Ref'].dropna().max())
        if ano_dinamico in ['', 'nan', 'None']: ano_dinamico = '2026'
    except:
        ano_dinamico = '2026'

    # ==========================================
    # BARRA LATERAL (SIDEBAR)
    # ==========================================
    img_logos = r"Logos_Execução.jpeg"
    if os.path.exists(img_logos):
        st.sidebar.image(img_logos, use_container_width=True)
        st.sidebar.markdown("---")

    if st.sidebar.button("🔄 Atualizar Dados da Rede", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.markdown("---")

    if st.session_state.pagina_ativa == 'dashboard':
        st.sidebar.button("⬅️ Voltar para a Capa", on_click=lambda: st.session_state.update(pagina_ativa='capa'))
        
        st.sidebar.header("FILTROS GLOBAIS")
        st.sidebar.button("🧹 Limpar Todos os Filtros", on_click=forcar_limpeza_total, use_container_width=True)

        lista_meses = df_base[['Mes_Nome', 'Mes_Num']].dropna().drop_duplicates().sort_values('Mes_Num')['Mes_Nome'].tolist()
        
        # 💡 CORREÇÃO 3: REMOVIDA A LINHA QUE DELETAVA O ÚLTIMO MÊS DA LISTA!
        var_mes_str = st.sidebar.selectbox("Mês de Referência (Fechados)", ["Todos"] + lista_meses, key=f"filtro_mes_{st.session_state.botao_reset}")

        if 'Tipo Movimento' in df_base.columns:
            tipos_mov = [t for t in df_base['Tipo Movimento'].dropna().unique() if t]
            idx_padrao = tipos_mov.index('Acumulado') if 'Acumulado' in tipos_mov else 0
            var_mov_str = st.sidebar.selectbox("Tipo de Movimento", tipos_mov, index=idx_padrao, key=f"filtro_mov_{st.session_state.botao_reset}")
        else: var_mov_str = None

        acoes_validas = [str(a) for a in df_base['Ação'].unique() if str(a).strip() != '' and str(a).isdigit() and len(str(a)) == 4]
        opcoes_acao = ["Todas"] + [f"{a} - {dict_acoes.get(a, 'NÃO IDENTIFICADA')}" for a in sorted(list(set(acoes_validas)))]
        var_acao_str = st.sidebar.selectbox("Ação", opcoes_acao, key=f"filtro_acao_{st.session_state.botao_reset}")
        var_acao_codigo = var_acao_str.split(' - ')[0]

        fontes_3_validas = sorted([f for f in df_base['Fonte_3'].unique() if f and f != ''])
        opcoes_fonte = ["Todas"] + [f"{f} - {dict_fontes_global.get(f, 'Outras Fontes')}" for f in fontes_3_validas]
        var_fonte_str = st.sidebar.selectbox("Fonte de Recurso", opcoes_fonte, key=f"filtro_fonte_{st.session_state.botao_reset}")
        var_fonte_codigo = var_fonte_str.split(' - ')[0]

        naturezas_validas = sorted([str(n) for n in df_base['Natureza_ID'].unique() if n and n != ''])
        opcoes_natureza = ["Todas"] + [f"{n} - {dict_naturezas.get(n, 'NÃO IDENTIFICADA')}" for n in naturezas_validas]
        var_natureza_str = st.sidebar.selectbox("Natureza", opcoes_natureza, key=f"filtro_natureza_{st.session_state.botao_reset}")
        var_natureza_codigo = var_natureza_str.split(' - ')[0]

        mask_base = pd.Series(True, index=df_base.index)
        if var_mes_str != "Todos": mask_base &= (df_base['Mes_Nome'] == var_mes_str)
        if var_mov_str: mask_base &= (df_base['Tipo Movimento'] == var_mov_str)
        if var_acao_codigo != "Todas": mask_base &= (df_base['Ação'] == var_acao_codigo)
        if var_natureza_codigo != "Todas": mask_base &= (df_base['Natureza_ID'] == var_natureza_codigo)
        if var_fonte_codigo != "Todas": mask_base &= (df_base['Fonte_3'] == var_fonte_codigo)

        df_base_filtrada = df_base[mask_base]
        df_latest = df_base_filtrada[df_base_filtrada['Mes_Num'] == df_base_filtrada['Mes_Num'].max()] if (var_mes_str == "Todos" and not df_base_filtrada['Mes_Num'].isna().all()) else df_base_filtrada

        mask_evo = pd.Series(True, index=df_base.index)
        if var_mov_str: mask_evo &= (df_base['Tipo Movimento'] == var_mov_str)
        if var_acao_codigo != "Todas": mask_evo &= (df_base['Ação'] == var_acao_codigo)
        if var_natureza_codigo != "Todas": mask_evo &= (df_base['Natureza_ID'] == var_natureza_codigo)
        if var_fonte_codigo != "Todas": mask_evo &= (df_base['Fonte_3'] == var_fonte_codigo)

        mask_var = pd.Series(True, index=df_var.index)
        if var_acao_codigo != "Todas": mask_var &= (df_var['Ação'] == var_acao_codigo)
        if var_natureza_codigo != "Todas": mask_var &= (df_var['Natureza_ID'] == var_natureza_codigo)
        if var_fonte_codigo != "Todas": mask_var &= (df_var['Fonte_3'] == var_fonte_codigo)
        df_var_filtrada = df_var[mask_var]
    else:
        st.sidebar.info("Acesse o painel para habilitar os filtros de execução.")

    st.sidebar.markdown("""
        <br><hr>
        <div style='text-align: center; color: #6B7280; font-size: 11px; line-height: 1.4;'>
            <b>Desenvolvido com ajuda do Gemini Pro</b><br>
            em parceria com o Centro de Gerenciamento Operacional - CGO da CDM/PROPLAN<br>
            e CPI - Coordenação de Planejamento Institucional
        </div>
        <div style='text-align: center; color: #9CA3AF; font-size: 11px; margin-top: 10px;'>
            Versão de Rede - Atualização Automática 🚀<br>
            <b>Versão 2.0 (Blindada)</b>
        </div>
    """, unsafe_allow_html=True)

    # ==========================================
    # INTERFACE: TELA 1 (CAPA)
    # ==========================================
    if st.session_state.pagina_ativa == 'capa':
        st.write("") 
        st.write("")
        col_esq, col_centro, col_dir = st.columns([1, 3, 1])
        
        with col_centro:
            try:
                st.image("LogoPainelOrcamento.jpeg", use_container_width=True)
            except:
                st.warning("Imagem da capa não encontrada.")
                
            st.write("") 
            
            if st.button("🚀 ACESSAR PAINEL DE EXECUÇÃO ORÇAMENTÁRIA", use_container_width=True):
                st.session_state.pagina_ativa = 'dashboard'
                st.rerun()

    # ==========================================
    # INTERFACE: TELA 2 (DASHBOARD)
    # ==========================================
    elif st.session_state.pagina_ativa == 'dashboard':

        st.title(f"📊 PAINEL ORÇAMENTÁRIO - UEA {f'- {var_mes_str}' if var_mes_str != 'Todos' else ''}")
        
        tags = []
        if var_acao_codigo != "Todas": tags.append(f"<b>🎯 Ação:</b> {var_acao_str}")
        if var_fonte_codigo != "Todas": tags.append(f"<b>🏦 Fonte de Recurso:</b> {var_fonte_str}")
        if var_natureza_codigo != "Todas": tags.append(f"<b>🏷️ Natureza da Despesa:</b> {var_natureza_str}")
        if tags: st.markdown(f"<div class='caixa-destaque'>{' &nbsp;&nbsp;|&nbsp;&nbsp; '.join(tags)}</div>", unsafe_allow_html=True)

        tab_visao, tab_evolucao, tab_tabela, tab_var_natureza = st.tabs([
            "🎯 Visão Estratégica", 
            "📈 Evolução Mensal", 
            "🔍 Tabela de Variações",
            "📊 Variação do Empenhado por Natureza"
        ])

        with tab_visao:
            st.markdown(f"<div class='destaque-ano'>Exercício Orçamentário: {ano_dinamico} <span style='font-size: 16px; font-weight: bold; color: #6B7280;'>(última atualização: {dt_atual})</span></div>", unsafe_allow_html=True)
            
            c1, c2, c3, c4, c5 = st.columns(5)
            v_aut = df_latest['Autorizado'].sum() if 'Autorizado' in df_latest.columns else 0
            v_emp = df_latest['Empenhado'].sum() if 'Empenhado' in df_latest.columns else 0
            v_liq = df_latest['Liquidado'].sum() if 'Liquidado' in df_latest.columns else 0
            v_pago = df_latest['Pago'].sum() if 'Pago' in df_latest.columns else 0
            v_disp = df_latest['Disponível'].sum() if 'Disponível' in df_latest.columns else 0
            
            c1.metric("AUTORIZADO", formata_moeda_sem_decimal(v_aut))
            c2.metric("EMPENHADO", formata_moeda_sem_decimal(v_emp), delta=f"{(v_emp/v_aut)*100 if v_aut>0 else 0:.1f}% do total")
            c3.metric("LIQUIDADO", formata_moeda_sem_decimal(v_liq), delta=f"{(v_liq/v_aut)*100 if v_aut>0 else 0:.1f}% do total")
            c4.metric("PAGO", formata_moeda_sem_decimal(v_pago), delta=f"{(v_pago/v_aut)*100 if v_aut>0 else 0:.1f}% do total")
            c5.metric("DISPONÍVEL", formata_moeda_sem_decimal(v_disp))
            
            st.divider()
            
            if var_acao_codigo == "Todas":
                st.subheader("Top 10 Maiores Despesas por Ação (Empenhado)")
                df_top = df_latest.groupby('Ação')['Empenhado'].sum().nlargest(10).reset_index()
                df_top = df_top[df_top['Empenhado'] > 0]
                
                if not df_top.empty:
                    df_top['Rotulo'] = df_top['Empenhado'].apply(formata_abreviado)
                    df_top['Nome_Acao'] = df_top['Ação'].map(dict_acoes).fillna('Não Identificada')
                    df_top['Eixo_Y_Negrito'] = '<b>' + df_top['Ação'] + '</b>'
                    
                    fig_bar = px.bar(df_top, x='Empenhado', y='Eixo_Y_Negrito', orientation='h', text='Rotulo', custom_data=['Ação', 'Nome_Acao'])
                    max_valor_bar = df_top['Empenhado'].max()
                    
                    fig_bar.update_layout(
                        yaxis=dict(categoryorder='total ascending', tickfont=dict(size=24, color="#111827"), automargin=True), 
                        font=dict(size=18, color="black"), 
                        xaxis=dict(showticklabels=False, title="", range=[0, max_valor_bar * 1.25]), 
                        yaxis_title="", 
                        margin=dict(l=20, r=100, t=10, b=10)
                    )
                    fig_bar.update_traces(marker_color='#4f8868', textposition="outside", textfont=dict(size=18, color="black"), hovertemplate="<b>Ação: %{customdata[0]} - %{customdata[1]}</b><br>Valor: %{text}<extra></extra>")
                    st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.info("Não há valores empenhados para os filtros selecionados.")
                    
            else:
                st.subheader(f"Detalhamento da Ação {var_acao_codigo} por Natureza da Despesa")
                
                df_tree = df_latest.groupby('Natureza_ID')['Empenhado'].sum().reset_index()
                df_tree = df_tree[df_tree['Empenhado'] > 0]
                
                if not df_tree.empty:
                    df_tree['Nome_Natureza'] = df_tree['Natureza_ID'].map(dict_naturezas).fillna('Não Identificada')
                    df_tree['Rotulo_Display'] = df_tree['Natureza_ID'] + " - " + df_tree['Nome_Natureza']
                    df_tree['Valor_Abreviado'] = df_tree['Empenhado'].apply(formata_abreviado)
                    
                    fig_tree = px.treemap(
                        df_tree, 
                        path=[px.Constant(f"Ação {var_acao_codigo}"), 'Rotulo_Display'], 
                        values='Empenhado',
                        color='Empenhado',
                        color_continuous_scale='Greens',
                        custom_data=['Valor_Abreviado']
                    )
                    
                    fig_tree.update_traces(
                        texttemplate="<b>%{label}</b><br>%{customdata[0]}",
                        textfont=dict(size=18), 
                        hovertemplate="<b>%{label}</b><br>Empenhado: %{customdata[0]}<extra></extra>"
                    )
                    fig_tree.update_layout(margin=dict(t=20, l=10, r=10, b=10), height=450)
                    st.plotly_chart(fig_tree, use_container_width=True)
                else:
                    st.info("Não há valores empenhados para detalhar nesta Ação.")

        with tab_evolucao:
            st.markdown(f"<div class='destaque-ano'>Evolução Mensal da Execução - Ano {ano_dinamico} <span style='font-size: 16px; font-weight: normal; color: #6B7280;'>(última atualização: {dt_atual})</span></div>", unsafe_allow_html=True)
            
            colunas_ex = [col for col in ['Autorizado', 'Empenhado', 'Liquidado', 'Pago', 'Disponível'] if col in df_base.columns]
            
            df_m = df_base[mask_evo].groupby('Mês Referência')[colunas_ex].sum().reset_index()
            if not df_m.empty:
                df_m['Nome_Mes'] = df_m['Mês Referência'].apply(identificar_mes_streamlit)
                df_m['mes_num'] = df_m['Nome_Mes'].map(ordem_meses)
                df_m['Mês'] = df_m['Nome_Mes'].map(abrev_meses) + f'/{ano_dinamico}'
                df_m = df_m.sort_values('mes_num')
                df_melt = df_m.melt(id_vars=['Mês', 'mes_num'], value_vars=colunas_ex, var_name='Fase', value_name='Valor')
                df_melt['Rotulo_F'] = df_melt['Valor'].apply(formata_abreviado)
                
                fig_line = px.line(df_melt, x='Mês', y='Valor', color='Fase', markers=True, text='Rotulo_F', color_discrete_sequence=['#64748B', '#1E3A8A', '#3B82F6', '#10B981', '#F59E0B'])
                for trace in fig_line.data:
                    trace.textfont.color = trace.line.color
                    trace.textfont.size = 14
                    trace.textfont.weight = "bold"
                    trace.marker.size = 12
                    trace.line.width = 3
                    trace.textposition = "top center" 
                
                fig_line.update_layout(font=dict(size=18, color="black"), margin=dict(l=40, r=60, t=20, b=20), yaxis_range=[0, df_melt['Valor'].max() * 1.30], yaxis=dict(showticklabels=False), xaxis=dict(tickfont=dict(size=20, weight="bold")), legend=dict(orientation="h", y=1.05))
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("Não há dados de evolução mensal para os filtros selecionados.")

        with tab_tabela:
            st.markdown(f"<div class='periodo-destaque'>📅 {texto_periodo}</div>", unsafe_allow_html=True)
            st.subheader("Tabela de Variações")
            
            # --- 1. PREPARAÇÃO DOS DADOS PARA A PLANILHA (Excel interativo) ---
            df_aggrid = df_var_filtrada.copy()
            
            # Isolando as colunas financeiras originais
            categorias_alvo = ['Dotação Suplementar', 'Reduções', 'Autorizado', 'Empenhado', 'Disponível', 'Bloqueado']
            colunas_financeiras = []
            for col in df_aggrid.columns:
                if any(cat.lower() in col.lower() for cat in categorias_alvo):
                    if not any(x in col for x in ['Data_', 'Mês', 'Tipo', 'Programa']):
                        colunas_financeiras.append(col)
            
            # Trazendo os códigos para a tela e as descrições para os Tooltips (Hover)
            df_aggrid['AÇÃO'] = df_aggrid['Ação']
            df_aggrid['AÇÃO_DESC'] = df_aggrid['Ação'].apply(lambda x: f"{x} - {dict_acoes.get(x, 'N/I')}" if x else "")
            
            df_aggrid['FONTE'] = df_aggrid['Fonte_3']
            df_aggrid['FONTE_DESC'] = df_aggrid['Fonte_3'].apply(lambda x: f"{x} - {dict_fontes_global.get(x, 'Outras Fontes')}" if x else "")
            
            df_aggrid['NATUREZA'] = df_aggrid['Natureza_ID']
            df_aggrid['NATUREZA_DESC'] = df_aggrid['Natureza_ID'].apply(lambda x: f"{x} - {dict_naturezas.get(x, 'N/I')}" if x else "")
                        
            # Organizando as colunas da tela
            df_aggrid = df_aggrid[['AÇÃO', 'AÇÃO_DESC', 'FONTE', 'FONTE_DESC', 'NATUREZA', 'NATUREZA_DESC'] + colunas_financeiras]
            
            # Adicionando a linha de TOTAL GERAL no final
            linha_soma = df_aggrid[colunas_financeiras].sum()
            df_total = pd.DataFrame(linha_soma).T
            df_total['AÇÃO'] = "TOTAL"
            for col in ['AÇÃO_DESC', 'FONTE', 'FONTE_DESC', 'NATUREZA', 'NATUREZA_DESC']: 
                df_total[col] = ""
            df_aggrid = pd.concat([df_aggrid, df_total], ignore_index=True)
            
            # --- 2. CONFIGURAÇÃO DA PLANILHA AGGRID ---
            gb = GridOptionsBuilder.from_dataframe(df_aggrid)
            gb.configure_default_column(resizable=True, filter=True, sortable=True)
            
            # Escondendo colunas de descrição (vão aparecer apenas quando o usuário passar o mouse)
            gb.configure_column("AÇÃO_DESC", hide=True)
            gb.configure_column("FONTE_DESC", hide=True)
            gb.configure_column("NATUREZA_DESC", hide=True)
            
            # 💡 O SEGREDO AQUI: CONGELANDO AS 3 PRIMEIRAS E FORÇANDO A LARGURA EXATA
            gb.configure_column("AÇÃO", pinned='left', width=90, tooltipField="AÇÃO_DESC")
            gb.configure_column("FONTE", pinned='left', width=75, tooltipField="FONTE_DESC") # <--- AQUI A FONTE FICA PEQUENA!
            gb.configure_column("NATUREZA", pinned='left', width=100, tooltipField="NATUREZA_DESC")
            
            # Formatando as colunas de valor para formato financeiro Brasileiro (R$)
            js_moeda = JsCode('''
            function(params) { 
                if(params.value == null) return ''; 
                return params.value.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2}); 
            }
            ''')
            
            for col in colunas_financeiras:
                novo_nome = col.replace('_Ant.', ' Ant.').replace('_', ' ') 
                gb.configure_column(col, header_name=novo_nome, valueFormatter=js_moeda)
            
            gridOptions = gb.build()
            
            # --- 3. EXIBIÇÃO DA PLANILHA INTERATIVA ---
            AgGrid(
                df_aggrid,
                gridOptions=gridOptions,
                height=450,
                theme='balham',
                fit_columns_on_grid_load=False, # Impede o navegador de espremer as colunas
                allow_unsafe_jscode=True # Permite a formatação das moedas
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # --- 4. EXPORTAÇÃO PARA EXCEL (SEU CÓDIGO ORIGINAL FOI MANTIDO AQUI!) ---
            df_excel = df_var_filtrada.copy()
            df_excel['AÇÃO'] = df_excel['Ação'].apply(lambda x: f"{x} - {dict_acoes.get(x, 'N/I')}" if x else "")
            df_excel['FONTE'] = df_excel['Fonte_3'].apply(lambda x: f"{x} - {dict_fontes_global.get(x, 'Outras Fontes')}" if x else "")
            df_excel['NATUREZA'] = df_excel['Natureza_ID'].apply(lambda x: f"{x} - {dict_naturezas.get(x, 'N/I')}" if x else "")
            df_excel = df_excel[['AÇÃO', 'FONTE', 'NATUREZA'] + colunas_financeiras]
            
            df_total_excel = pd.DataFrame(df_excel[colunas_financeiras].sum()).T
            for col in ['AÇÃO', 'FONTE', 'NATUREZA']: df_total_excel[col] = ""
            df_total_excel['AÇÃO'] = "TOTAL GERAL"
            df_excel = pd.concat([df_excel, df_total_excel], ignore_index=True)
            
            df_excel.columns = [c.replace('_Ant.', '_Anterior').replace('_Ant', '_Anterior').replace(' Ant.', ' Anterior').replace(' Ant', ' Anterior') for c in df_excel.columns]
            
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_excel.to_excel(writer, index=False, sheet_name='Variações')
            
            st.download_button(
                label="📥 Descarregar Relatório Excel (.xlsx)",
                data=buffer.getvalue(),
                file_name=f"Execucao_UEA_Variacoes_{dt_atual.replace('/', '-')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            st.download_button(
                label="📥 Descarregar Relatório Excel (.xlsx)",
                data=buffer.getvalue(),
                file_name=f"Execucao_UEA_Variacoes_{dt_atual.replace('/', '-')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        with tab_var_natureza:
            if var_acao_codigo != "Todas":
                titulo_dinamico = f"Detalhamento da variação do Empenhado<br><span style='font-size: 20px; color: #4B5563;'>da Ação: {var_acao_str}</span>"
            else:
                titulo_dinamico = "Detalhamento da variação do Empenhado<br><span style='font-size: 20px; color: #4B5563;'>(Panorama de Todas as Ações)</span>"
                
            st.markdown(f"<div class='destaque-ano'>{titulo_dinamico}</div>", unsafe_allow_html=True)
            
            col_var_emp = None
            for col in df_var_filtrada.columns:
                if 'Empenhado' in col and ('Varia' in col or 'Diferença' in col):
                    col_var_emp = col
                    break
            
            if not col_var_emp:
                for col in df_var_filtrada.columns:
                    if 'Empenhado' in col and 'Ant' not in col and 'Atual' not in col:
                        col_var_emp = col
                        break
                        
            if not col_var_emp:
                col_var_emp = [c for c in df_var_filtrada.columns if 'Empenhado' in c][0] if [c for c in df_var_filtrada.columns if 'Empenhado' in c] else None

            if col_var_emp and not df_var_filtrada.empty:
                df_chart_var = df_var_filtrada.groupby('Natureza_ID')[col_var_emp].sum().reset_index()
                df_chart_var = df_chart_var[abs(df_chart_var[col_var_emp]) > 0.01]
                
                if not df_chart_var.empty:
                    df_chart_var['Nome_Natureza'] = df_chart_var['Natureza_ID'].map(dict_naturezas).fillna('Não Identificada')
                    df_chart_var['Rotulo_Eixo'] = "<b>" + df_chart_var['Natureza_ID'] + " - " + df_chart_var['Nome_Natureza'].str.slice(0, 50) + "</b>"
                    df_chart_var['Texto_Valor'] = df_chart_var[col_var_emp].apply(formata_abreviado)
                    df_chart_var['Cor'] = df_chart_var[col_var_emp].apply(lambda x: '#10B981' if x > 0 else '#EF4444')
                    df_chart_var = df_chart_var.sort_values(by=col_var_emp, ascending=True)
                    
                    fig_var = px.bar(
                        df_chart_var, 
                        x=col_var_emp, 
                        y='Rotulo_Eixo', 
                        orientation='h', 
                        text='Texto_Valor',
                        custom_data=['Natureza_ID', 'Nome_Natureza']
                    )
                    
                    fig_var.update_traces(
                        marker_color=df_chart_var['Cor'], 
                        textposition="outside", 
                        textfont=dict(size=14, color="black", weight="bold"),
                        hovertemplate="<b>Natureza: %{customdata[0]} - %{customdata[1]}</b><br>Variação no Período: %{text}<extra></extra>"
                    )
                    
                    fig_var.add_vline(x=0, line_width=2, line_color="black")
                    max_abs = abs(df_chart_var[col_var_emp]).max()
                    fig_var.update_layout(
                        font=dict(size=14, color="black"), 
                        yaxis=dict(tickfont=dict(size=15, color="#111827")), 
                        xaxis=dict(showticklabels=False, title="", range=[-max_abs * 1.35, max_abs * 1.35]), 
                        yaxis_title="", 
                        margin=dict(l=10, r=40, t=20, b=10),
                        height=max(400, len(df_chart_var) * 45) 
                    )
                    
                    st.plotly_chart(fig_var, use_container_width=True)
                else:
                    st.info("Não houve variação de Empenho para as naturezas neste período ou filtro selecionado.")
            else:
                st.warning("Coluna de variação de Empenhado não foi identificada na base de dados.")

# ==========================================
# 7. TRATAMENTO DE ERROS (PLANO B VISUAL)
# ==========================================
except Exception as e:
    st.markdown("""
        <div style="background-color: #FEF2F2; border-left: 6px solid #DC2626; padding: 20px; border-radius: 5px; margin-top: 50px;">
            <h2 style="color: #991B1B; margin-top: 0;">⚠️ Ocorreu uma instabilidade no painel.</h2>
            <p style="color: #7F1D1D; font-size: 16px;">
                Não se preocupe! Isto geralmente ocorre devido a uma atualização recente nos dados do SIAFI ou um conflito temporário na memória do seu navegador. O erro técnico foi recolhido em segurança.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.info("💡 Por favor, clique no botão abaixo para restaurar o sistema à sua operação normal:")
        if st.button("🔄 Reiniciar e Limpar Cache do Sistema", use_container_width=True):
            st.cache_data.clear()
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()