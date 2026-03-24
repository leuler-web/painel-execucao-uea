import streamlit as st
import pandas as pd
import plotly.express as px
import os
from io import BytesIO
import locale
from streamlit_plotly_events import plotly_events

# Configuração de idioma para meses em Português
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.utf8')
except:
    pass

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="PAINEL ORÇAMENTÁRIO - UEA", layout="wide", page_icon="📈")

# --- ESTILIZAÇÃO CSS CUSTOMIZADA ---
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #2E7D32 !important; font-size: 28px !important; font-weight: 900 !important; }
    .block-container { padding-top: 1.5rem !important; }
    [data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E5E7EB !important; }
    h1 { font-size: 54px !important; font-weight: 900 !important; color: #878787 !important; }
    .periodo-tecnico { font-size: 20px; color: #DC2626; font-weight: 900; margin-bottom: 15px; }
    .destaque-ano { font-size: 34px; color: #2E7D32; font-weight: 900; text-align: center; margin-bottom: 20px; border-bottom: 3px solid #2E7D32; padding-bottom: 10px; }
    
    /* Estilo da Tabela */
    .tabela-container { max-height: 600px; overflow: auto; border: 1px solid #D1D5DB; border-radius: 8px; background-color: white; }
    .tabela-customizada table { width: 100%; border-collapse: collapse; }
    .tabela-customizada thead th { background-color: #1E3A8A !important; color: white !important; position: sticky; top: 0; z-index: 10; padding: 12px; }
    </style>
    """, unsafe_allow_html=True)

# 2. GESTÃO DE ESTADO (NAVEGAÇÃO E CLIQUE)
if 'pagina_ativa' not in st.session_state:
    st.session_state.pagina_ativa = 'capa'
if 'acao_drilldown' not in st.session_state:
    st.session_state.acao_drilldown = None

# --- FUNÇÕES DE CARREGAMENTO ---
@st.cache_data(ttl=60)
def carregar_dados_completos():
    PATH_SIAFI = "Base_Consolidada_SIAFI.xlsx"
    df_b = pd.read_excel(PATH_SIAFI, sheet_name='Base_Consolidada')
    df_v = pd.read_excel(PATH_SIAFI, sheet_name='Variacoes_Recentes')
    
    # Criar coluna Mes/Ano cronológica
    df_b['DATA_DT'] = pd.to_datetime(df_b['Mês Referência'], errors='coerce')
    df_b = df_b.sort_values('DATA_DT')
    df_b['Mes_Ano'] = df_b['DATA_DT'].dt.strftime('%b/%Y').str.capitalize()
    
    # Limpeza básica de valores
    colunas_fin = [c for c in df_b.columns if any(p in c for p in ['Autorizado', 'Empenhado', 'Liquidado', 'Pago', 'Disponível'])]
    for col in colunas_fin:
        df_b[col] = pd.to_numeric(df_b[col], errors='coerce').fillna(0)
    
    return df_b, df_v

df_base, df_var = carregar_dados_completos()

# ==========================================
# TELA 1: CAPA
# ==========================================
if st.session_state.pagina_ativa == 'capa':
    st.image("LogoPainelOrcamento.jpeg", use_container_width=True) # Nome do arquivo que você confirmou
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 ACESSAR PAINEL DE EXECUÇÃO ORÇAMENTÁRIA", use_container_width=True):
            st.session_state.pagina_ativa = 'dashboard'
            st.rerun()

# ==========================================
# TELA 2: DASHBOARD
# ==========================================
elif st.session_state.pagina_ativa == 'dashboard':
    
    # Sidebar
    if st.sidebar.button("⬅️ Voltar para Capa"):
        st.session_state.pagina_ativa = 'capa'
        st.rerun()

    st.sidebar.header("FILTROS GLOBAIS")
    lista_meses = df_base['Mes_Ano'].unique().tolist()
    sel_mes = st.sidebar.selectbox("Mês de Referência", ["Todos"] + lista_meses)
    
    df_f = df_base.copy()
    if sel_mes != "Todos":
        df_f = df_f[df_f['Mes_Ano'] == sel_mes]

    # Abas
    tab1, tab2, tab3 = st.tabs(["🎯 Visão Estratégica", "📈 Evolução Mensal", "🔍 Tabela de Variações"])

    with tab1:
        ano_ref = df_base['DATA_DT'].dt.year.max()
        st.markdown(f"<div class='destaque-ano'>Exercício Orçamentário: {ano_ref}</div>", unsafe_allow_html=True)
        
        # KPIs Rápidos
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("AUTORIZADO", f"R$ {df_f['Autorizado'].sum():,.0f}".replace(',', '.'))
        c2.metric("EMPENHADO", f"R$ {df_f['Empenhado'].sum():,.0f}".replace(',', '.'))
        c3.metric("LIQUIDADO", f"R$ {df_f['Liquidado'].sum():,.0f}".replace(',', '.'))
        c4.metric("PAGO", f"R$ {df_f['Pago'].sum():,.0f}".replace(',', '.'))
        
        st.divider()
        st.subheader("Top 10 Ações (Clique na barra para ver o detalhamento por Natureza)")
        
        # Gráfico de Barras Interativo
        df_top = df_f.groupby('Ação')['Empenhado'].sum().nlargest(10).reset_index()
        fig_bar = px.bar(df_top, x='Empenhado', y='Ação', orientation='h', color_discrete_sequence=['#4f8868'])
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(l=20, r=20, t=20, b=20))
        
        # Captura do Clique
        clique = plotly_events(fig_bar, click_event=True)
        
        if clique:
            idx = clique[0]['pointNumber']
            st.session_state.acao_drilldown = df_top.iloc[idx]['Ação']
            
        if st.session_state.acao_drilldown:
            st.info(f"Detalhamento da Ação: {st.session_state.acao_drilldown}")
            if st.button("✖️ Fechar Detalhamento"):
                st.session_state.acao_drilldown = None
                st.rerun()
            
            df_tree = df_f[df_f['Ação'] == st.session_state.acao_drilldown]
            fig_tree = px.treemap(df_tree, path=['Natureza da Despesa'], values='Empenhado', color='Empenhado', color_continuous_scale='Greens')
            st.plotly_chart(fig_tree, use_container_width=True)

    with tab2:
        st.markdown(f"<div class='destaque-ano'>Evolução da Execução - Ano {ano_ref}</div>", unsafe_allow_html=True)
        df_evo = df_base.groupby('Mes_Ano')[['Empenhado', 'Liquidado', 'Pago']].sum().reset_index()
        fig_evo = px.line(df_evo, x='Mes_Ano', y=['Empenhado', 'Liquidado', 'Pago'], markers=True)
        st.plotly_chart(fig_evo, use_container_width=True)

    with tab3:
        # Texto técnico movido para cá conforme solicitado
        st.markdown(f"<div class='periodo-tecnico'>🗓️ Data de Extração / Comparativo Automático (SIAFI)</div>", unsafe_allow_html=True)
        st.write("Abaixo, a tabela detalhada com as variações entre os períodos de extração:")
        st.dataframe(df_var, use_container_width=True)

st.sidebar.markdown("<br><hr><center><small>PROPLAN / CPI / CGO - UEA</small></center>", unsafe_allow_html=True)