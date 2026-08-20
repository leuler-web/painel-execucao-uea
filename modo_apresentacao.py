import time
import streamlit as st

def iniciar_modo_apresentacao(lista_abas, tempo_segundos=5):
    """
    Alterna automaticamente entre as abas na nuvem e no localhost sem usar JavaScript.
    """
    if "aba_ativa_idx" not in st.session_state:
        st.session_state.aba_ativa_idx = 0

    # Cria o seletor visual no topo em vez de st.tabs
    aba_selecionada = st.segmented_control(
        "Navegação do Painel",
        options=lista_abas,
        default=lista_abas[st.session_state.aba_ativa_idx],
        key="navegacao_apresentacao"
    )

    # Atualiza o índice caso o usuário clique manualmente
    if aba_selecionada in lista_abas:
        st.session_state.aba_ativa_idx = lista_abas.index(aba_selecionada)

    # Temporizador de rotação automática
    time.sleep(tempo_segundos)
    st.session_state.aba_ativa_idx = (st.session_state.aba_ativa_idx + 1) % len(lista_abas)
    st.rerun()

    return aba_selecionada