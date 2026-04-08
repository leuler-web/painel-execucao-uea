import streamlit as st
import pandas as pd
import plotly.express as px
import os
from io import BytesIO

# 1. CONFIGURAÇÃO VISUAL E CSS (O "ROSTO" DO PAINEL)
st.set_page_config(page_title="PAINEL ORÇAMENTÁRIO - UEA", layout="wide", page_icon="📈")

st.markdown(
    """
    <style>
    [data-testid="stMetricValue"] { color: #2E7D32 !important; }
    .block-container { padding-top: 2rem !important; padding-bottom: 1rem !important; max-width: 100% !important; }
    [data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E5E7EB !important; }
    [data-testid="stTabs"] > div:first-of-type {
        position: sticky !important; top: 0px !important; background-color: white !important;
        z-index: 9999 !important; padding-bottom: 10px !important; padding-top: 15px !important;
        border-bottom: 2px solid #2E7D32 !important;
    }
    h1 { font-size: 44px !important; font-weight: 900 !important; color: #878787 !important; margin-top: -20px !important;}
    h3 { font-size: 26px !important; font-weight: 800 !important; color: #111827 !important; padding-bottom: 10px; }
    .destaque-ano { font-size: 26px; color: #2E7D32; font-weight: 900; text-align: center; margin-bottom: 15px; border-bottom: 3px solid #2E7D32; padding-bottom: 5px; }
    
    /* CSS DA TABELA HTML CUSTOMIZADA */
    .tabela-container { max-height: 480px; overflow-y: auto; overflow-x: auto; border: 1px solid #D1D5DB; border-radius: 8px; background-color: white; margin-bottom: 20px; }
    .tabela-customizada table { width: 100%; border-collapse: collapse; font-family: sans-serif; }
    .tabela-customizada thead th { background-color: #1E3A8A !important; color: #FFFFFF !important; font-weight: 900 !important; font-size: 14px !important; text-align: center !important; position: sticky; top: 0; z-index: 10; padding: 10px 8px; border-bottom: 2px solid #0F172A; }
    .tabela-customizada tbody td { padding: 8px 8px; border-bottom: 1px solid #E5E7EB; font-size: 13px; vertical-align: middle; white-space: nowrap; }
    </style>
    """, unsafe_allow_html=True)

# 2. DICIONÁRIOS E AUXILIARES
ordem_meses_robusto = {
    'JANEIRO': 1, 'FEVEREIRO': 2, 'MARCO': 3, 'MARÇO': 3, 'ABRIL': 4, 'MAIO': 5, 'JUNHO': 6,
    'JULHO': 7, 'AGOSTO': 8, 'SETEMBRO': 9, 'OUTUBRO': 10, 'NOVEMBRO': 11, 'DEZEMBRO': 12,
    'JAN': 1, 'FEV': 2, 'MAR': 3, 'ABR': 4, 'MAI': 5, 'JUN': 6, 'JUL': 7, 'AGO': 8, 'SET': 9, 'OUT': 10, 'NOV': 11, 'DEZ': 12
}

# 3. FUNÇÕES DE LIMPEZA (EXTREMAMENTE IMPORTANTES)
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
    except: return 0.0

def formata_moeda_sem_decimal(valor):
    try: return f"R$ {extrair_numero(valor):,.0f}".replace(',', '.')
    except: return "R$ 0"

def formata_numero_duas_casas(valor):
    try: 
        val_formatado = f"{extrair_numero(valor):,.2f}"
        return val_formatado.replace(',', 'X').replace('.', ',').replace('X', '.')
    except: return "0,00"

def formata_abreviado(valor):
    try:
        val_num = extrair_numero(valor)
        if val_num == 0: return "R$ 0"
        sinal = "-" if val_num < 0 else ""
        abs_val = abs(val_num)
        if abs_val >= 1_000_000: return f"{sinal}R$ {abs_val/1_000_000:.1f} Mi".replace('.', ',')
        elif abs_val >= 1_000: return f"{sinal}R$ {abs_val/1_000:.1f} mil".replace('.', ',')
        return f"{sinal}R$ {abs_val:,.0f}".replace(',', '.')
    except: return "0"

def destacar_linhas_com_variacao(row):
    cols_var = [c for c in row.index if 'Varia' in str(c)]
    for c in cols_var:
        if abs(extrair_numero(row[c])) > 0.001:
            return ['background-color: #FFFF00; color: #000000; font-weight: bold;'] * len(row)
    return [''] * len(row)

# 4. LEITORES DE ARQUIVOS (AUXILIARES + SIAFI)
@st.cache_data(ttl=3600)
def carregar_dicionarios():
    dict_acoes, dict_naturezas = {}, {}
    caminho_aux = r"Tabelas_Auxiliares.xlsx"
    if os.path.exists(caminho_aux):
        try:
            xls = pd.ExcelFile(caminho_aux)
            for aba in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=aba)
                if 'AÇ' in aba.upper() or 'AC' in aba.upper():
                    df.columns = [str(c).upper().strip() for c in df.columns]
                    col_acao = next((c for c in df.columns if 'AÇ' in c or 'AC' in c), None)
                    col_nome = next((c for c in df.columns if 'IDENTIFICA' in c), None)
                    if col_acao and col_nome:
                        for _, row in df.iterrows():
                            cod = str(row[col_acao]).split('.')[0].strip().zfill(4)
                            dict_acoes[cod] = str(row[col_nome]).strip()
        except: pass
    return dict_acoes, dict_naturezas

@st.cache_data(ttl=60)
def carregar_dados_completos():
    path = r"Base_Consolidada_SIAFI.xlsx"
    df_base = pd.read_excel(path, sheet_name='Base_Consolidada')
    df_var = pd.read_excel(path, sheet_name='Variacoes_Recentes')
    
    for df in [df_base, df_var]:
        df.columns = [str(c).strip() for c in df.columns]
        # Identificação de Ação e Natureza
        if 'Programa de Trabalho' in df.columns:
            df['Ação'] = df['Programa de Trabalho'].astype(str).str.replace(r'\D', '', regex=True).str[9:13]
        if 'Natureza da Despesa' in df.columns:
            df['Natureza_ID'] = df['Natureza da Despesa'].astype(str).str.replace(r'\D', '', regex=True).str[:6]
        
        # Conversão de valores financeiros
        palavras_fin = ['Autorizado', 'Empenhado', 'Liquidado', 'Pago', 'Dotação', 'Reduções', 'Variação', 'Disponível']
        colunas_fin = [col for col in df.columns if any(p in col for p in palavras_fin)]
        for col in colunas_fin:
            df[col] = df[col].apply(extrair_numero)

    # TRATAMENTO ROBUSTO DO MÊS (BARRA OU ESPAÇO)
    if 'Mês Referência' in df_base.columns:
        # Aqui está a correção: trocamos / por espaço e cortamos
        df_base['Mes_Extraido'] = df_base['Mês Referência'].astype(str).str.replace('/', ' ').str.split(' ').str[0].str.upper().str.strip()
        df_base['Mes_Num'] = df_base['Mes_Extraido'].map(ordem_meses_robusto)
        df_base['Mes_Nome'] = df_base['Mes_Extraido'].str.capitalize()
        df_base['Ano_Ref'] = df_base['Mês Referência'].astype(str).str.extract(r'(\d{4})').fillna("2026")
    
    return df_base, df_var

# 5. EXECUÇÃO DO CARREGAMENTO
try:
    df_base, df_var = carregar_dados_completos()
    dict_acoes, dict_naturezas = carregar_dicionarios()
except Exception as e:
    st.error(f"Erro fatal ao ler arquivos: {e}")
    st.stop()

# 6. LÓGICA DE NAVEGAÇÃO (CAPA / DASHBOARD)
if 'pagina_ativa' not in st.session_state: st.session_state.pagina_ativa = 'capa'

if st.session_state.pagina_ativa == 'capa':
    try: st.image("LogoPainelOrcamento.jpeg", use_container_width=True)
    except: st.title("PAINEL ORÇAMENTÁRIO - UEA")
    if st.button("🚀 ACESSAR PAINEL DE EXECUÇÃO ORÇAMENTÁRIA", use_container_width=True):
        st.session_state.pagina_ativa = 'dashboard'; st.rerun()

elif st.session_state.pagina_ativa == 'dashboard':
    st.sidebar.button("⬅️ Voltar", on_click=lambda: st.session_state.update(pagina_ativa='capa'))
    
    # Filtros SideBar
    lista_meses = df_base[['Mes_Nome', 'Mes_Num']].dropna().drop_duplicates().sort_values('Mes_Num')['Mes_Nome'].tolist()
    var_mes = st.sidebar.selectbox("Mês de Referência", ["Todos"] + lista_meses)
    
    tipos_mov = sorted([t for t in df_base['Tipo Movimento'].unique() if pd.notna(t)])
    var_mov = st.sidebar.selectbox("Tipo de Movimento", tipos_mov, index=tipos_mov.index('Acumulado') if 'Acumulado' in tipos_mov else 0)

    acoes_validas = sorted(df_base['Ação'].unique())
    var_acao_str = st.sidebar.selectbox("Ação", ["Todas"] + [f"{a} - {dict_acoes.get(a, 'N/I')}" for a in acoes_validas])
    var_acao_cod = var_acao_str.split(' - ')[0]

    # Máscaras de Dados
    mask_view = (df_base['Tipo Movimento'] == var_mov)
    if var_mes != "Todos": mask_view &= (df_base['Mes_Nome'] == var_mes)
    if var_acao_cod != "Todas": mask_view &= (df_base['Ação'] == var_acao_cod)
    df_latest = df_base[mask_view]

    st.title("📊 Painel Orçamentário - UEA")
    
    tab_visao, tab_evolucao, tab_var = st.tabs(["🎯 Visão Estratégica", "📈 Evolução Mensal", "🔍 Tabela de Variações"])

    with tab_visao:
        st.markdown(f"<div class='destaque-ano'>Posição: {var_mes if var_mes != 'Todos' else 'Consolidado'}</div>", unsafe_allow_html=True)
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("AUTORIZADO", formata_moeda_sem_decimal(df_latest['Autorizado'].sum()))
        c2.metric("EMPENHADO", formata_moeda_sem_decimal(df_latest['Empenhado'].sum()))
        c3.metric("LIQUIDADO", formata_moeda_sem_decimal(df_latest['Liquidado'].sum()))
        c4.metric("PAGO", formata_moeda_sem_decimal(df_latest['Pago'].sum()))
        c5.metric("DISPONÍVEL", formata_moeda_sem_decimal(df_latest['Disponível'].sum()))
        
        # Gráfico Top 10 Ações
        st.subheader("Top 10 Ações por Volume Empenhado")
        df_top = df_latest.groupby('Ação')['Empenhado'].sum().nlargest(10).reset_index()
        df_top['Nome'] = df_top['Ação'].apply(lambda x: dict_acoes.get(x, x))
        fig_bar = px.bar(df_top, x='Empenhado', y='Nome', orientation='h', color_discrete_sequence=['#2E7D32'])
        st.plotly_chart(fig_bar, use_container_width=True)

    with tab_evolucao:
        st.subheader("Evolução Mensal da Execução")
        # Ignora o filtro de mês para mostrar a linha do tempo
        mask_evo = (df_base['Tipo Movimento'] == var_mov)
        if var_acao_cod != "Todas": mask_evo &= (df_base['Ação'] == var_acao_cod)
        
        df_m = df_base[mask_evo].groupby(['Mes_Num', 'Mes_Nome'])[['Autorizado', 'Empenhado', 'Liquidado']].sum().reset_index().sort_values('Mes_Num')
        
        if not df_m.empty:
            df_melt = df_m.melt(id_vars=['Mes_Nome'], value_vars=['Autorizado', 'Empenhado', 'Liquidado'], var_name='Fase', value_name='Valor')
            fig_line = px.line(df_melt, x='Mes_Nome', y='Valor', color='Fase', markers=True, text=df_melt['Valor'].apply(formata_abreviado))
            fig_line.update_traces(textposition="top center")
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Sem dados históricos para os filtros selecionados.")

    with tab_var:
        st.subheader("🔍 Detalhamento de Variações Recentes")
        mask_v = pd.Series(True, index=df_var.index)
        if var_acao_cod != "Todas": mask_v &= (df_var['Ação'] == var_acao_cod)
        df_v_show = df_var[mask_v].copy()
        
        # Aplicar o realce amarelo se houver variação
        st.dataframe(df_v_show.style.apply(destacar_linhas_com_variacao, axis=1), use_container_width=True)

st.sidebar.markdown("<br><hr><center>Versão 4.5 - Full & Fixed 🚀</center>", unsafe_allow_html=True)