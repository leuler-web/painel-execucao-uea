import time
import streamlit as st

def iniciar_modo_apresentacao(lista_abas, tempo_segundos=5):
    """
    Alterna automaticamente entre as abas e permite pausar a rotação para interagir com os filtros.
    """
    # Chave para controlar se o modo apresentação (carrossel) está ligado ou desligado
    if "modo_auto_play" not in st.session_state:
        st.session_state.modo_auto_play = False

    if "aba_ativa_idx" not in st.session_state:
        st.session_state.aba_ativa_idx = 0

    col1, col2 = st.columns([4, 1])
    
    with col1:
        aba_selecionada = st.segmented_control(
            "Navegação do Painel",
            options=lista_abas,
            default=lista_abas[st.session_state.aba_ativa_idx],
            key="navegacao_apresentacao"
        )

    with col2:
        st.session_state.modo_auto_play = st.toggle(
            "🔄 Rotação Automática", 
            value=st.session_state.modo_auto_play,
            help="Ative para alternar as abas automaticamente a cada X segundos."
        )

    # Atualiza o índice caso o usuário clique manualmente em alguma aba
    if aba_selecionada in lista_abas:
        st.session_state.aba_ativa_idx = lista_abas.index(aba_selecionada)

    # Executa a rotação automática apenas se o Toggle estiver ATIVADO
    if st.session_state.modo_auto_play:
        time.sleep(tempo_segundos)
        st.session_state.aba_ativa_idx = (st.session_state.aba_ativa_idx + 1) % len(lista_abas)
        st.rerun()

    return aba_selecionada