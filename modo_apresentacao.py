import streamlit as st
import streamlit.components.v1 as components
from contextlib import contextmanager

@contextmanager
def modo_apresentacao(lista_abas, tempo_segundos=5):
    """
    Gerenciador de contexto adaptado para stlite: renderiza os gráficos
    sem bloquear o navegador e agenda a troca automática de aba via JS.
    """
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
        aba_selecionada = st.radio(
            "Navegação do Painel",
            options=lista_abas,
            key="navegacao_apresentacao",
            horizontal=True
        )

    # Entrega a aba selecionada para o app_stlite.py desenhar os gráficos
    yield aba_selecionada

    # Após desenhar os gráficos, agenda o clique na próxima aba no navegador
    if st.session_state.modo_auto_play and len(lista_abas) > 1:
        aba_atual = st.session_state.navegacao_apresentacao
        idx_atual = lista_abas.index(aba_atual) if aba_atual in lista_abas else 0
        proximo_idx = (idx_atual + 1) % len(lista_abas)

        components.html(
            f"""
            <script>
            setTimeout(function() {{
                try {{
                    const doc = window.parent.document;
                    const grupos = doc.querySelectorAll('[data-testid="stRadio"]');
                    for (const grupo of grupos) {{
                        if (grupo.innerText.includes("Navegação do Painel")) {{
                            const opcoes = grupo.querySelectorAll('input[type="radio"]');
                            if (opcoes.length > {proximo_idx}) {{
                                opcoes[{proximo_idx}].click();
                            }}
                            break;
                        }}
                    }}
                }} catch (e) {{
                    console.error("Erro na rotação automática:", e);
                }}
            }}, {tempo_segundos * 1000});
            </script>
            """,
            height=0,
            width=0,
        )