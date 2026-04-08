import streamlit as st
import pandas as pd
import plotly.express as px
import os
from io import BytesIO

# 1. ESTILO E CONFIGURAÇÃO (O visual que você já conhece)
st.set_page_config(page_title="PAINEL ORÇAMENTÁRIO - UEA", layout="wide", page_icon="📈")

st.markdown(
    """
    <style>
    [data-testid="stMetricValue"] { color: #2E7D32 !important; font-size: 26px !important; font-weight: 900 !important; }
    .block-container { padding-top: 2rem !important; max-width: 100% !important; }
    [data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E5E7EB !important; }
    [data-testid="stTabs"] > div:first-of-type {
        position: sticky !important; top: 0px !important; background-color: white !important;
        z-index: 9999 !important; padding-bottom: 10px !important; border-bottom: 2px solid #2E7D32 !important;
    }
    h1 { font-size: 44px !important; font-weight: 900 !important; color: #878787 !important; margin-top: -20px !important;}
    .destaque-ano { font-size: 26px; color: #2E7D32; font-weight: 900; text-align: center; margin-bottom: 15px; border-bottom: 3px solid #2E7D32; padding-bottom: 5px; }
    /* Estilo da Tabela Customizada */
    .tabela-customizada table { width: 100%; border-collapse: collapse; }
    .tabela-customizada thead th { background-color: #1E3A8A !important; color: white !important; font-weight: 900 !important; position: sticky; top: 0; padding: 10px; }
    </style>
    """,
    unsafe_allow_html=True
)

# 2. DICIONÁRIOS DE APOIO
ordem_meses_robusto = {
    'JANEIRO': 1, 'FEVEREIRO': 2, 'MARCO': 3, 'MARÇO': 3, 'ABRIL': 4, 'MAIO': 5, 'JUNHO': 6,
    'JULHO': 7, 'AGOSTO': 8, 'SETEMBRO': 9, 'OUTUBRO': 10, 'NOVEMBRO': 11, 'DEZEMBRO': 12,
    'JAN': 1, 'FEV': 2, 'MAR': 3, 'ABR': 4, 'MAI': 5, 'JUN': 6, 'JUL': 7, 'AGO': 8, 'SET': 9, 'OUT': 10, 'NOV': 11, 'DEZ': 12
}

# 3. FUNÇÕES DE TRATAMENTO DE DADOS
def extrair_numero(val):
    try:
        if pd.isna(val): return 0.0
        if isinstance(val, (int, float)): return float(val)
        txt = str(val).upper().replace('R$', '').replace(' ', '').strip()
        if ',' in txt: txt = txt.replace('.', '').replace(',', '.')
        else:
            if txt.count('.') > 1: txt = txt.replace('.', '')
        return float(txt)
    except: return 0.0

def formata_moeda_sem_decimal(valor):
    return f"R$ {extrair_numero(valor):,.0f}".replace(',', '.')

def formata_abreviado(valor):
    val = extrair_numero(valor)
    if val >= 1_000_000: return f"R$ {val/1_000_000:.1f} Mi".replace('.', ',')
    return f"R$ {val:,.0f}".replace(',', '.')

# 4. CARREGAMENTO DOS DICIONÁRIOS (Ações e Naturezas)
@st.cache_data(ttl=3600)
def carregar_tabelas_auxiliares():
    dict_acoes = {}
    path_aux = "Tabelas_Auxiliares.xlsx"
    if os.path.exists(path_aux):
        try:
            df_aux = pd.read_excel(path_aux)
            # Lógica para mapear códigos de 4 dígitos para nomes
            for _, row in df_aux.iterrows():
                cod = str(row.iloc[0]).strip().zfill(4)
                dict_acoes[cod] = str(row.iloc[-1]).strip()
        except: pass
    return dict_acoes

dict_acoes = carregar_tabelas_auxiliares()

# 5. CARREGAMENTO DA BASE PRINCIPAL
@st.cache_data(ttl=60)
def carregar_dados_siafi():
    path = "Base_Consolidada_SIAFI.xlsx"
    df_b = pd.read_excel(path, sheet_name='Base_Consolidada')
    df_v = pd.read_excel(path, sheet_name='Variacoes_Recentes')
    
    # Limpeza de nomes e extração de códigos
    for df in [df_b, df_v]:
        df.columns = [str(c).strip() for c in df.columns]
        if 'Programa de Trabalho' in df.columns:
            df['Ação'] = df['Programa de Trabalho'].astype(str).str.replace(r'\D', '', regex=True).str[9:13]
        if 'Tipo Movimento' in df.columns:
            df['Tipo Movimento'] = df['Tipo Movimento'].fillna('Acumulado')
            
    # CORREÇÃO CRÍTICA DO MÊS (BARRA '/')
    if 'Mês Referência' in df_b.columns:
        # Pega o que vem antes da barra ou do espaço
        df_b['Mes_Extraido'] = df_b['Mês Referência'].astype(str).str.replace('/', ' ').str.split(' ').str[0].str.upper().str.strip()
        df_b['Mes_Num'] = df_b['Mes_Extraido'].map(ordem_meses_robusto)
        df_b['Mes_Nome'] = df_b['Mes_Extraido'].str.capitalize()
    
    # Conversão financeira
    cols_fin = ['Autorizado', 'Empenhado', 'Liquidado', 'Pago', 'Disponível']
    for col in cols_fin:
        if col in df_b.columns: df_b[col] = df_b[col].apply(extrair_numero)
            
    return df_b, df_v

df_base, df_var = carregar_dados_siafi()

# 6. LÓGICA DE NAVEGAÇÃO
if 'pagina' not in st.session_state: st.session_state.pagina = 'capa'

if st.session_state.pagina == 'capa':
    try: st.image("LogoPainelOrcamento.jpeg", use_container_width=True)
    except: st.title("PAINEL ORÇAMENTÁRIO - UEA")
    if st.button("🚀 ACESSAR SISTEMA", use_container_width=True):
        st.session_state.pagina = 'dash'; st.rerun()

else:
    # SIDEBAR
    st.sidebar.button("⬅️ Voltar à Capa", on_click=lambda: st.session_state.update(pagina='capa'))
    
    meses_disponiveis = sorted(df_base[['Mes_Nome', 'Mes_Num']].dropna().drop_duplicates().values, key=lambda x: x[1])
    nomes_meses = [m[0] for m in meses_disponiveis]
    
    filtro_mes = st.sidebar.selectbox("Mês de Referência", ["Todos"] + nomes_meses)
    filtro_mov = st.sidebar.selectbox("Tipo de Movimento", sorted(df_base['Tipo Movimento'].unique()))
    
    # Filtro de Ação com nomes do dicionário
    acoes_lista = sorted(df_base['Ação'].unique())
    filtro_acao = st.sidebar.selectbox("Filtrar por Ação", ["Todas"] + [f"{a} - {dict_acoes.get(a, 'N/I')}" for a in acoes_lista])
    acao_cod = filtro_acao.split(' - ')[0]

    # APLICAR FILTROS
    mask = (df_base['Tipo Movimento'] == filtro_mov)
    if filtro_mes != "Todos": mask &= (df_base['Mes_Nome'] == filtro_mes)
    if acao_cod != "Todas": mask &= (df_base['Ação'] == acao_cod)
    df_view = df_base[mask]

    st.title("📊 Painel de Execução")
    
    tab_resumo, tab_evo, tab_detalhes = st.tabs(["🎯 Resumo Geral", "📈 Evolução Temporal", "🔍 Detalhes de Variação"])

    with tab_resumo:
        st.markdown(f"<div class='destaque-ano'>Posição: {filtro_mes if filtro_mes != 'Todos' else 'Consolidado'}</div>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("AUTORIZADO", formata_moeda_sem_decimal(df_view['Autorizado'].sum()))
        c2.metric("EMPENHADO", formata_moeda_sem_decimal(df_view['Empenhado'].sum()))
        c3.metric("LIQUIDADO", formata_moeda_sem_decimal(df_view['Liquidado'].sum()))
        c4.metric("DISPONÍVEL", formata_moeda_sem_decimal(df_view['Disponível'].sum()))

        # Gráfico de Barras por Ação
        st.subheader("Execução por Unidade/Ação")
        resumo_acao = df_view.groupby('Ação')['Empenhado'].sum().nlargest(10).reset_index()
        resumo_acao['Nome'] = resumo_acao['Ação'].apply(lambda x: dict_acoes.get(x, x))
        fig_bar = px.bar(resumo_acao, x='Empenhado', y='Nome', orientation='h', color_discrete_sequence=['#2E7D32'])
        st.plotly_chart(fig_bar, use_container_width=True)

    with tab_evo:
        st.subheader("Evolução Mensal (Janeiro a Abril)")
        # Importante: para a evolução, ignoramos o filtro de mês individual
        mask_evo = (df_base['Tipo Movimento'] == filtro_mov)
        if acao_cod != "Todas": mask_evo &= (df_base['Ação'] == acao_cod)
        
        df_evolucao = df_base[mask_evo].groupby(['Mes_Num', 'Mes_Nome'])[['Autorizado', 'Empenhado', 'Liquidado']].sum().reset_index().sort_values('Mes_Num')
        
        if not df_evolucao.empty:
            fig_line = px.line(df_evolucao, x='Mes_Nome', y=['Autorizado', 'Empenhado', 'Liquidado'], markers=True,
                               color_discrete_map={'Autorizado': '#878787', 'Empenhado': '#2E7D32', 'Liquidado': '#1E3A8A'})
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.warning("Selecione um Tipo de Movimento que contenha dados históricos.")

    with tab_detalhes:
        st.subheader("Comparativo de Variações Recentes")
        mask_v = pd.Series(True, index=df_var.index)
        if acao_cod != "Todas": mask_v &= (df_var['Ação'] == acao_cod)
        st.dataframe(df_var[mask_v], use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.caption("Versão 4.4 - Full Restored")