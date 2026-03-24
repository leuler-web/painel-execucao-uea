import streamlit as st
import pandas as pd
import plotly.express as px
import os
from io import BytesIO

# Código para forçar o valor da métrica a ser verde
st.markdown(
    """
    <style>
    [data-testid="stMetricValue"] {
        color: #2E7D32 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 1. CONFIGURAÇÃO DA PÁGINA E FONTES
st.set_page_config(page_title="PAINEL ORÇAMENTÁRIO - UEA", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    /* 1. OTIMIZAÇÃO DE ESPAÇO E BORDAS (RESPONSIVIDADE MÁXIMA) */
    .block-container { 
        padding-top: 2rem !important; 
        padding-bottom: 1rem !important; 
        max-width: 100% !important; 
    }
    
    /* 2. DEIXAR O MENU LATERAL 100% BRANCO */
    [data-testid="stSidebar"] { 
        background-color: #FFFFFF !important; 
        border-right: 1px solid #E5E7EB !important; 
    }
    
    /* 3. CONGELAR AS ABAS NO TOPO DA TELA (EFEITO STICKY) */
    [data-testid="stTabs"] > div:first-of-type {
        position: sticky !important;
        top: 0px !important;
        background-color: white !important;
        z-index: 9999 !important;
        padding-bottom: 10px !important;
        padding-top: 15px !important;
        border-bottom: 2px solid #2E7D32 !important;
    }
    
    /* Fontes e Textos Ajustados para caberem bem em Laptops e Telas Grandes */
    h1 { font-size: 44px !important; font-weight: 900 !important; color: #878787 !important; margin-top: -20px !important;}
    h3 { font-size: 26px !important; font-weight: 800 !important; color: #111827 !important; padding-bottom: 10px; }
    .stTabs [data-baseweb="tab-list"] button { font-size: 22px !important; font-weight: 900 !important; color: #374151 !important; }
    [data-testid="stMetricValue"] { font-size: 26px !important; font-weight: 900 !important; color: #4B5563 !important; }
    [data-testid="stMetricLabel"] * { font-size: 16px !important; font-weight: 900 !important; color: #111827 !important; }
    .periodo-destaque { font-size: 18px; color: #DC2626; font-weight: 900; margin-bottom: 10px; }
    .caixa-destaque { padding: 12px; background-color: #E0F2FE; border-left: 5px solid #0284C7; border-radius: 5px; margin-bottom: 15px; font-size: 15px; color: #0C4A6E; line-height: 1.5; }
    
    /* Destaque do Ano Dinâmico nas Abas */
    .destaque-ano { font-size: 26px; color: #2E7D32; font-weight: 900; text-align: center; margin-bottom: 15px; border-bottom: 3px solid #2E7D32; padding-bottom: 5px; }
    
    /* Destaque para os Filtros do Menu Lateral */
    [data-testid="stSidebar"] label p { font-size: 16px !important; font-weight: 900 !important; color: #0F172A !important; margin-bottom: 4px; }
    
    /* CSS DA TABELA HTML CUSTOMIZADA */
    .tabela-container { max-height: 480px; overflow-y: auto; overflow-x: auto; border: 1px solid #D1D5DB; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); background-color: white; margin-bottom: 20px; }
    .tabela-customizada table { width: 100%; border-collapse: collapse; font-family: sans-serif; }
    .tabela-customizada thead th { background-color: #1E3A8A !important; color: #FFFFFF !important; font-weight: 900 !important; font-size: 14px !important; text-align: center !important; position: sticky; top: 0; z-index: 10; padding: 10px 8px; border-bottom: 2px solid #0F172A; line-height: 1.2; }
    .tabela-customizada tbody td { padding: 8px 8px; border-bottom: 1px solid #E5E7EB; font-size: 13px; vertical-align: middle; white-space: nowrap;  }
    .tabela-customizada tbody tr:hover { background-color: #F3F4F6 !important; }
    .tabela-customizada tbody td div[title] { cursor: help; border-bottom: 1px dotted #9CA3AF; display: inline-block; }
    </style>
    """, unsafe_allow_html=True)

# GESTÃO DE ESTADO (Capa)
if 'pagina_ativa' not in st.session_state:
    st.session_state.pagina_ativa = 'capa'

# 2. DICIONÁRIO MANUAL DAS FONTES
dict_fontes_global = {
    '201': 'Recursos Diretamente Arrecadados', '280': 'Convênios ou transferências',
    '116': 'Fonte do Tesouro', '285': 'Outras Fontes', '243': 'Transferências vinculadas/fundos'
}

# 3. FUNÇÕES DE LIMPEZA E FORMATAÇÃO
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

def destacar_linhas_com_variacao(row):
    cols_var = [c for c in row.index if 'Varia' in str(c)]
    for c in cols_var:
        if abs(extrair_numero(row[c])) > 0.001:
            return ['background-color: #FFFF00; color: #000000; font-weight: bold;'] * len(row)
    return [''] * len(row)

# 4. LEITOR DAS TABELAS AUXILIARES
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

# 5. CARREGAMENTO DOS DADOS PRINCIPAIS
PATH_SIAFI = r"Base_Consolidada_SIAFI.xlsx"

@st.cache_data(ttl=60)
def carregar_dados_v181(path):
    tipos_forçados = {'Programa de Trabalho': str, 'Fonte de Recurso': str, 'Natureza da Despesa': str}
    df_base = pd.read_excel(path, sheet_name='Base_Consolidada', dtype=tipos_forçados)
    df_var = pd.read_excel(path, sheet_name='Variacoes_Recentes', dtype=tipos_forçados)
    palavras_fin = ['Autorizado', 'Empenhado', 'Liquidado', 'Pago', 'Dotação', 'Reduções', 'Variação', 'Disponível']
    
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
        mascara = df['Programa de Trabalho'].astype(str).str.lower().str.strip().isin(['', 'nan', 'none', 'null'])
        return df[~mascara].copy()
        
    df_base = remover_fantasmas(df_base)
    df_var = remover_fantasmas(df_var)
    
    for df in [df_base, df_var]:
        colunas_fin = [col for col in df.columns if any(p in col for p in palavras_fin)]
        for col in colunas_fin: df[col] = df[col].apply(extrair_numero)
            
    colunas_texto = ['Programa de Trabalho', 'Fonte de Recurso', 'Natureza da Despesa', 'Mês Referência', 'Tipo Movimento']
    for df in [df_base, df_var]:
        for col in colunas_texto:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().replace('nan', '')
        if 'Tipo Movimento' in df.columns:
            df['Tipo Movimento'] = df['Tipo Movimento'].apply(lambda x: 'Acumulado' if 'Acumulado' in str(x) else ('Mês' if str(x).lower() not in ['nan', 'none', '', '0', '0.0'] else x))
        
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

try: df_base, df_var = carregar_dados_v181(PATH_SIAFI)
except Exception as e: st.error(f"Erro ao acessar o arquivo SIAFI: {e}"); st.stop()

dict_acoes, dict_naturezas, status_dic = carregar_dicionarios()
ordem_meses = {'Janeiro': 1, 'Fevereiro': 2, 'Março': 3, 'Abril': 4, 'Maio': 5, 'Junho': 6, 'Julho': 7, 'Agosto': 8, 'Setembro': 9, 'Outubro': 10, 'Novembro': 11, 'Dezembro': 12}
abrev_meses = {'Janeiro': 'Jan', 'Fevereiro': 'Fev', 'Março': 'Mar', 'Abril': 'Abr', 'Maio': 'Mai', 'Junho': 'Jun', 'Julho': 'Jul', 'Agosto': 'Ago', 'Setembro': 'Set', 'Outubro': 'Out', 'Novembro': 'Nov', 'Dezembro': 'Dez'}

try:
    val_ant = df_var['Data_Extracao_Anterior'].dropna().iloc[0]
    val_atual = df_var['Data_Extracao_Atual'].dropna().iloc[0]
    dt_ant = pd.to_datetime(val_ant, errors='coerce').strftime('%d/%m/%Y')
    dt_atual = pd.to_datetime(val_atual, errors='coerce').strftime('%d/%m/%Y')
    texto_periodo = f"Posição Consolidada da Base: {dt_atual}" if dt_ant == dt_atual else f"Comparativo Automático: Extrato de {dt_ant} até {dt_atual}"
except Exception: 
    dt_atual = "N/D"
    texto_periodo = "Aguardando atualização da base de dados."

# LÓGICA DA DATA E ANO DINÂMICO
if 'Mês Referência' in df_base.columns:
    df_base['Mes_Nome'] = df_base['Mês Referência'].astype(str).str.split(' ').str[0].str.capitalize()
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
# TELA 1: CAPA
# ==========================================
if st.session_state.pagina_ativa == 'capa':
    try:
        st.image("LogoPainelOrcamento.jpeg", use_container_width=True)
    except:
        st.warning("Imagem da capa não encontrada.")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("")
        if st.button("🚀 ACESSAR PAINEL DE EXECUÇÃO ORÇAMENTÁRIA", use_container_width=True):
            st.session_state.pagina_ativa = 'dashboard'
            st.rerun()


# ==========================================
# TELA 2: DASHBOARD
# ==========================================
elif st.session_state.pagina_ativa == 'dashboard':

    if 'botao_reset' not in st.session_state: st.session_state.botao_reset = 0
    def forcar_limpeza_total():
        st.session_state.botao_reset += 1
        for chave in list(st.session_state.keys()):
            if chave.startswith('filtro_'): del st.session_state[chave]

    img_logos = r"Logos_Execução.jpeg"
    if os.path.exists(img_logos):
        st.sidebar.image(img_logos, use_container_width=True)
        st.sidebar.markdown("---")

    st.sidebar.button("⬅️ Voltar para a Capa", on_click=lambda: st.session_state.update(pagina_ativa='capa'))
    st.sidebar.header("FILTROS GLOBAIS")
    st.sidebar.button("🧹 Limpar Todos os Filtros", on_click=forcar_limpeza_total, use_container_width=True)

    lista_meses = df_base[['Mes_Nome', 'Mes_Num']].dropna().drop_duplicates().sort_values('Mes_Num')['Mes_Nome'].tolist()
    if len(lista_meses) > 1: lista_meses = lista_meses[:-1] 
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

    st.title(f"📊 PAINEL ORÇAMENTÁRIO - UEA {f'- {var_mes_str}' if var_mes_str != 'Todos' else ''}")
    
    tags = []
    if var_acao_codigo != "Todas": tags.append(f"<b>🎯 Ação:</b> {var_acao_str}")
    if var_fonte_codigo != "Todas": tags.append(f"<b>🏦 Fonte de Recurso:</b> {var_fonte_str}")
    if var_natureza_codigo != "Todas": tags.append(f"<b>🏷️ Natureza da Despesa:</b> {var_natureza_str}")
    if tags: st.markdown(f"<div class='caixa-destaque'>{' &nbsp;&nbsp;|&nbsp;&nbsp; '.join(tags)}</div>", unsafe_allow_html=True)

    tab_visao, tab_evolucao, tab_tabela = st.tabs(["🎯 Visão Estratégica", "📈 Evolução Mensal", "🔍 Tabela de Variações"])

    with tab_visao:
        st.markdown(f"<div class='destaque-ano'>Exercício Orçamentário: {ano_dinamico}</div>", unsafe_allow_html=True)
        
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
            st.subheader("Top 10 Maiores Despesas por Ação")
            
            df_top = df_latest.groupby('Ação')['Empenhado'].sum().nlargest(10).reset_index()
            df_top = df_top[df_top['Empenhado'] > 0]
            
            if not df_top.empty:
                df_top['Rotulo'] = df_top['Empenhado'].apply(formata_abreviado)
                df_top['Nome_Acao'] = df_top['Ação'].map(dict_acoes).fillna('Não Identificada')
                df_top['Eixo_Y_Negrito'] = '<b>' + df_top['Ação'] + '</b>'
                
                fig_bar = px.bar(df_top, x='Empenhado', y='Eixo_Y_Negrito', orientation='h', text='Rotulo', custom_data=['Ação', 'Nome_Acao'])
                
                fig_bar.update_layout(
                    yaxis=dict(categoryorder='total ascending', tickfont=dict(size=24, color="#111827"), automargin=True), 
                    font=dict(size=18, color="black"), 
                    xaxis=dict(showticklabels=False, title="", showgrid=False, zeroline=False), 
                    yaxis_title="", 
                    margin=dict(l=10, r=120, t=10, b=10),
                    plot_bgcolor='white'
                )
                
                fig_bar.update_traces(
                    marker_color='#4f8868', 
                    textposition="outside", 
                    textfont=dict(size=18, color="black"), 
                    cliponaxis=False, 
                    hovertemplate="<b>Ação: %{customdata[0]} - %{customdata[1]}</b><br>Valor: %{text}<extra></extra>"
                )
                
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
                fig_tree = px.treemap(df_tree, path=[px.Constant(f"Ação {var_acao_codigo}"), 'Rotulo_Display'], values='Empenhado', color='Empenhado', color_continuous_scale='Greens', custom_data=['Valor_Abreviado'])
                fig_tree.update_traces(texttemplate="<b>%{label}</b><br>%{customdata[0]}", textfont=dict(size=18), hovertemplate="<b>%{label}</b><br>Empenhado: %{customdata[0]}<extra></extra>")
                # Altura ajustada para caber melhor na tela
                fig_tree.update_layout(margin=dict(t=20, l=10, r=10, b=10), height=450)
                st.plotly_chart(fig_tree, use_container_width=True)
            else:
                st.info("Não há valores empenhados para detalhar nesta Ação.")

    with tab_evolucao:
        st.markdown(f"<div class='destaque-ano'>Evolução Mensal da Execução - Ano {ano_dinamico}</div>", unsafe_allow_html=True)
        
        colunas_ex = [col for col in ['Autorizado', 'Empenhado', 'Liquidado', 'Pago', 'Disponível'] if col in df_base.columns]
        df_m = df_base[mask_evo].groupby(['Mês Referência', 'Mes_Nome', 'Ano_Ref', 'Mes_Num'])[colunas_ex].sum().reset_index()
        
        if not df_m.empty:
            df_m = df_m.sort_values('Mes_Num')
            df_m['Mes_F'] = df_m['Mes_Nome'].map(abrev_meses) + '/' + df_m['Ano_Ref'].astype(str)
            
            df_melt = df_m.melt(id_vars=['Mes_F', 'Mes_Num'], value_vars=colunas_ex, var_name='Fase', value_name='Valor')
            df_melt['Rotulo_F'] = df_melt['Valor'].apply(formata_abreviado)
            
            fig_line = px.line(df_melt, x='Mes_F', y='Valor', color='Fase', markers=True, text='Rotulo_F', color_discrete_sequence=['#64748B', '#1E3A8A', '#3B82F6', '#10B981', '#F59E0B'])
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
        
        df_var_visual = df_var_filtrada.copy()
        df_var_visual_tela = df_var_visual.copy()
        
        df_var_visual_tela['AÇÃO'] = df_var_visual['Ação'].apply(lambda x: f'<div title="{x} - {dict_acoes.get(x, "N/I")}">{x}</div>' if x else "")
        df_var_visual_tela['FONTE'] = df_var_visual['Fonte_3'].apply(lambda x: f'<div title="{x} - {dict_fontes_global.get(x, "Outras Fontes")}">{x}</div>' if x else "")
        df_var_visual_tela['NATUREZA'] = df_var_visual['Natureza_ID'].apply(lambda x: f'<div title="{x} - {dict_naturezas.get(x, "N/I")}">{x}</div>' if x else "")
        
        colunas_identificacao = ['AÇÃO', 'FONTE', 'NATUREZA']
        categorias_alvo = ['Dotação Suplementar', 'Reduções', 'Autorizado', 'Empenhado', 'Disponível']
        
        colunas_financeiras_originais = []
        for col in df_var_visual.columns:
            if any(cat.lower() in col.lower() for cat in categorias_alvo) and col not in colunas_identificacao:
                if not any(x in col for x in ['Data_', 'Mês', 'Tipo', 'Programa']):
                    colunas_financeiras_originais.append(col)
                    
        df_var_visual_tela = df_var_visual_tela[colunas_identificacao + colunas_financeiras_originais]
        
        mapeamento_colunas = {}
        for col in colunas_financeiras_originais:
            nome_seguro = col.replace('Ant.', 'A\u200Bnt.') 
            novo_nome = nome_seguro.replace('_', '<br>').replace(' ', '<br>').replace('<br><br>', '<br>')
            mapeamento_colunas[col] = f'<span translate="no" class="notranslate">{novo_nome}</span>'
            
        df_var_visual_tela = df_var_visual_tela.rename(columns=mapeamento_colunas)
        colunas_financeiras_tela = list(mapeamento_colunas.values())
        
        tabela_estilizada = (df_var_visual_tela.style
            .apply(destacar_linhas_com_variacao, axis=1)
            .format({col: formata_numero_duas_casas for col in colunas_financeiras_tela})
            .set_properties(**{'text-align': 'right'}, subset=colunas_financeiras_tela)
            .set_properties(**{'text-align': 'center'}, subset=colunas_identificacao)
        )
        
        try: html_tabela = tabela_estilizada.hide(axis="index").to_html(escape=False)
        except AttributeError: html_tabela = tabela_estilizada.hide_index().render()
            
        st.markdown(f'<div class="tabela-container tabela-customizada">{html_tabela}</div>', unsafe_allow_html=True)
        
        df_excel = df_var_visual.copy()
        df_excel['AÇÃO'] = df_excel['Ação'].apply(lambda x: f"{x} - {dict_acoes.get(x, 'N/I')}" if x else "")
        df_excel['FONTE'] = df_excel['Fonte_3'].apply(lambda x: f"{x} - {dict_fontes_global.get(x, 'Outras Fontes')}" if x else "")
        df_excel['NATUREZA'] = df_excel['Natureza_ID'].apply(lambda x: f"{x} - {dict_naturezas.get(x, 'N/I')}" if x else "")
        df_excel = df_excel[colunas_identificacao + colunas_financeiras_originais]
        df_excel.columns = [c.replace('_Ant.', '_Anterior').replace('_Ant', '_Anterior').replace(' Ant.', ' Anterior').replace(' Ant', ' Anterior') for c in df_excel.columns]
        
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_excel.to_excel(writer, index=False, sheet_name='Variações')
        
        st.download_button(label="📥 Descarregar Relatório Excel (.xlsx)", data=buffer.getvalue(), file_name=f"Execucao_UEA_Variacoes_{dt_atual.replace('/', '-')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.sidebar.markdown("""
        <br><hr>
        <div style='text-align: center; color: #6B7280; font-size: 11px; line-height: 1.4;'>
            <b>Desenvolvido com ajuda da IA</b><br>
            em parceria com o Centro de Gerenciamento Operacional - CGO da CDM/PROPLAN<br>
            e CPI - Coordenação de Planejamento Institucional
        </div>
    """, unsafe_allow_html=True)