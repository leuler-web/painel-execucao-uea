import time
import streamlit as st

def iniciar_modo_apresentacao(lista_abas, tempo_segundos=5):
    """
    Alterna automaticamente entre as abas atualizando diretamente a chave
    de estado do widget no Streamlit.
    """
    # 1. Inicializa o estado do Auto Play
    if "modo_auto_play" not in st.session_state:
        st.session_state.modo_auto_play = False

    # 2. Inicializa a aba ativa garantindo que seja um item válido da lista
    if "navegacao_apresentacao" not in st.session_state or st.session_state.navegacao_apresentacao not in lista_abas:
        st.session_state.navegacao_apresentacao = lista_abas[0]

    col1, col2 = st.columns([4, 1])

    with col2:
        st.session_state.modo_auto_play = st.toggle(
            "🔄 Rotação Automática", 
            value=st.session_state.modo_auto_play,
            key="toggle_auto_play_key",
            help="Ative para alternar as abas automaticamente a cada X segundos."
        )

    with col1:
        # Ao passar a key, o Streamlit sincroniza automaticamente com st.session_state.navegacao_apresentacao
        aba_selecionada = st.segmented_control(
            "Navegação do Painel",
            options=lista_abas,
            key="navegacao_apresentacao"
        )

    # 3. Executa a transição apenas se o botão estiver ligado
    if st.session_state.modo_auto_play:
        time.sleep(tempo_segundos)
        
        # Descobre qual é a aba atual e calcula o próximo índice
        aba_atual = st.session_state.navegacao_apresentacao
        idx_atual = lista_abas.index(aba_atual) if aba_atual in lista_abas else 0
        proximo_idx = (idx_atual + 1) % len(lista_abas)
        
        # Atualiza a chave diretamente no Session State e recarrega a tela
        st.session_state.navegacao_apresentacao = lista_abas[proximo_idx]
        st.rerun()

    return aba_selecionada