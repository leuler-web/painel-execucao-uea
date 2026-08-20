import time
import streamlit as st
from contextlib import contextmanager

@contextmanager
def modo_apresentacao(lista_abas, tempo_segundos=5):
    """
    Gerenciador de contexto que garante a renderização completa dos gráficos
    antes de realizar a pausa e transição de aba.
    """
    # 1. Aplica a transição de aba pendente
    if "proxima_aba" in st.session_state:
        st.session_state.navegacao_apresentacao = st.session_state.pop("proxima_aba")

    # 2. Inicializa os estados do Session State
    if "modo_auto_play" not in st.session_state:
        st.session_state.modo_auto_play = False

    if "navegacao_apresentacao" not in st.session_state or st.session_state.navegacao_apresentacao not in lista_abas:
        st.session_state.navegacao_apresentacao = lista_abas[0]

    col1, col2 = st.columns([4, 1])

    with col2:
        st.session_state.modo_auto_play = st.toggle(
            "🔄 Rotação Automática", 
            value=st.session_state.modo_auto_play,
            key="toggle_auto_play_key",
            help="Ative para alternar as abas automaticamente."
        )

    with col1:
        aba_selecionada = st.segmented_control(
            "Navegação do Painel",
            options=lista_abas,
            key="navegacao_apresentacao"
        )

    # 3. Entrega a aba selecionada para o app.py renderizar os gráficos
    yield aba_selecionada

    # 4. DEPOIS que a página foi desenhada, aguarda o tempo e agenda a próxima troca
    if st.session_state.modo_auto_play:
        time.sleep(tempo_segundos)
        
        aba_atual = st.session_state.navegacao_apresentacao
        idx_atual = lista_abas.index(aba_atual) if aba_atual in lista_abas else 0
        proximo_idx = (idx_atual + 1) % len(lista_abas)
        
        st.session_state.proxima_aba = lista_abas[proximo_idx]
        st.rerun()