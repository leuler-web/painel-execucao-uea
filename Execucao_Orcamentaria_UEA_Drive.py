import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import re
import tempfile
from io import BytesIO
import matplotlib.pyplot as plt
from modo_apresentacao import modo_apresentacao
from fpdf import FPDF
from datetime import datetime

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="PAINEL ORÇAMENTÁRIO - UEA", 
    layout="wide", 
    page_icon="📈",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.uea.edu.br',
        'Report a bug': None, 
        'About': "Painel de Execução Orçamentária UEA. Versão 2.0 (Blindada)"
    }
)

# ==========================================
# 2. BLOCO ÚNICO DE ESTILOS CSS
# ==========================================
st.markdown("""
<style>
.topo-congelado{position:sticky;top:0;background-color:white;z-index:1000;padding-top:10px;padding-bottom:5px;border-bottom:2px solid #e5e7eb;margin-bottom:15px;}
h1{font-size:2rem !important;margin-top:0 !important;line-height:1.2 !important;color:#111827 !important;font-weight:800 !important;}
.stTabs{margin-top:-20px !important;}
.tabela-container{max-height:520px;overflow:auto;border:1px solid #e5e7eb;border-radius:8px;position:relative;}
table{width:100%;min-width:800px;border-collapse:separate;border-spacing:0;font-family:sans-serif;table-layout:auto;}
thead th{position:sticky;top:0;background-color:#1E3A8A !important;color:white !important;padding:14px 10px;text-align:center;font-size:16px !important;font-weight:bold;border-bottom:2px solid #D1D5DB;white-space:nowrap;z-index:20;}
thead th:nth-child(1){position:sticky;left:0;z-index:25;background-color:#1E3A8A !important;}
tbody td:nth-child(1){position:sticky;left:0;z-index:15;background-color:white;}
thead th:nth-child(2){position:sticky;left:60px;z-index:25;background-color:#1E3A8A !important;}
tbody td:nth-child(2){position:sticky;left:60px;z-index:15;background-color:white;}
thead th:nth-child(3){position:sticky;left:120px;z-index:25;background-color:#1E3A8A !important;box-shadow:2px 0 5px -2px rgba(0,0,0,0.15);}
tbody td:nth-child(3){position:sticky;left:120px;z-index:15;background-color:white;box-shadow:2px 0 5px -2px rgba(0,0,0,0.15);}
tbody td{padding:12px 10px;border-bottom:1px solid #F3F4F6;font-size:16px !important;color:#1F2937;white-space:nowrap;background-color:white;text-align:right;font-weight:600;}
tbody td:nth-child(1),tbody td:nth-child(2),tbody td:nth-child(3){text-align:center;}
tr:hover td{background-color:#F9FAFB !important;}
tr:hover td:nth-child(1),tr:hover td:nth-child(2),tr:hover td:nth-child(3){background-color:#F9FAFB !important;}
.pos{color:#059669;font-weight:bold;}
.neg{color:#DC2626;font-weight:bold;}
.zero{color:#6B7280;}
#MainMenu{visibility:hidden !important;}
footer{visibility:hidden !important;}
header[data-testid=stHeader]{display:none !important;}
div[data-testid=stToolbar]{display:none !important;}
div[data-testid=stDecoration]{display:none !important;}
.st-emotion-cache-1f3f2m8{display:none !important;}
.stApp{margin-top:0 !important;}
.stMain{padding-top:0 !important;}
button[kind=header]{display:none !important;}
.st-emotion-cache-1q3nhyv{display:none !important;}
[data-testid=baseButton-header]{display:none !important;}
[data-testid=stMetricValue]{color:#2E7D32 !important;font-size:1.5rem !important;}
.destaque-ano{font-size: 20px !important; font-weight: 800 !important; color: #1E3A8A;}
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

def criar_grafico_tendencia_global(caminho_planilha_proj):
    """Gera o gráfico de tendência interativo (Plotly) e a tabela HTML com tema claro executivo."""
    try:
        df_proj_raw = pd.read_excel(caminho_planilha_proj)
        meses_eixo = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']
        
        primeira_coluna = df_proj_raw.iloc[:,0].astype(str).str.upper()
        
        mask_loa = primeira_coluna.str.contains("LOA", na=False)
        mask_emp = primeira_coluna.str.contains("EMPENHO", na=False)
        mask_prj = primeira_coluna.str.contains("PROJE", na=False)
        mask_disp = primeira_coluna.str.contains("DISPON", na=False)
        mask_saldo = primeira_coluna.str.contains("SALDO", na=False)
        
        if not (mask_loa.any() and mask_emp.any() and mask_prj.any()):
            return None, None, None
        
        row_loa = df_proj_raw[mask_loa].iloc[0]
        row_emp = df_proj_raw[mask_emp].iloc[0]
        row_prj = df_proj_raw[mask_prj].iloc[0]
        row_disp = df_proj_raw[mask_disp].iloc[0] if mask_disp.any() else None
        row_saldo = df_proj_raw[mask_saldo].iloc[0] if mask_saldo.any() else None
        
        def converter_br_para_float(valor):
            if pd.isna(valor) or valor == '-': return 0.0
            if isinstance(valor, (int, float)): return float(valor)
            v_str = str(valor).strip()
            if v_str == '' or v_str == '-': return 0.0
            v_str = v_str.replace('.', '').replace(',', '.')
            try: return float(v_str)
            except: return 0.0
        
        def formatar_moeda_curta(valor):
            if pd.isna(valor) or valor == 0: return "-"
            abs_v = abs(valor)
            sinal = "-" if valor < 0 else ""
            if abs_v >= 1_000_000_000:
                return f"{sinal}R$ {abs_v/1_000_000_000:,.1f} Bi".replace(",", "X").replace(".", ",").replace("X", ".")
            elif abs_v >= 1_000_000:
                return f"{sinal}R$ {abs_v/1_000_000:,.1f} Mi".replace(",", "X").replace(".", ",").replace("X", ".")
            elif abs_v >= 1_000:
                return f"{sinal}R$ {abs_v/1_000:,.1f} mil".replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                return f"{sinal}R$ {abs_v:,.0f}".replace(",", ".")

        loa = [converter_br_para_float(row_loa[m]) if m in row_loa.index else 0.0 for m in meses_eixo]
        executado = [converter_br_para_float(row_emp[m]) if m in row_emp.index else 0.0 for m in meses_eixo]
        projetado = [converter_br_para_float(row_prj[m]) if m in row_prj.index else 0.0 for m in meses_eixo]
        disponivel = [converter_br_para_float(row_disp[m]) if (row_disp is not None and m in row_disp.index) else 0.0 for m in meses_eixo]
        saldo = [converter_br_para_float(row_saldo[m]) if (row_saldo is not None and m in row_saldo.index) else 0.0 for m in meses_eixo]
        
        final_exec = 0
        for i, v in enumerate(executado):
            if v > 0: final_exec = i
        
        projetado_display = [None]*12
        projetado_display[final_exec] = executado[final_exec]
        for i in range(final_exec + 1, 12):
            projetado_display[i] = projetado[i]
        
        executado_display = [v if v > 0 else None for v in executado[:final_exec+1]] + [None]*(12 - final_exec - 1)
        disponivel_display = [v if v > 0 else None for v in disponivel[:final_exec+1]] + [None]*(12 - final_exec - 1)
        saldo_display = [v if v != 0 else None for v in saldo[:final_exec+1]] + [None]*(12 - final_exec - 1)

        col_total = next((c for c in df_proj_raw.columns if 'TOTAL' in str(c).upper()), None)
        def obter_total(row, lst):
            if row is None: return 0.0
            if col_total and col_total in row.index:
                return converter_br_para_float(row[col_total])
            return sum(lst)

        tot_loa = obter_total(row_loa, loa)
        tot_emp = obter_total(row_emp, executado)
        tot_prj = obter_total(row_prj, projetado)
        disp_atual = disponivel[final_exec] if final_exec < len(disponivel) else obter_total(row_disp, disponivel)

        kpis = {
            'tot_loa': formatar_moeda_curta(tot_loa),
            'tot_emp': formatar_moeda_curta(tot_emp),
            'disp_atual': formatar_moeda_curta(disp_atual),
            'tot_prj': formatar_moeda_curta(tot_prj)
        }

        loa_mi = [v/1e6 for v in loa]
        exec_mi = [v/1e6 if v is not None else None for v in executado_display]
        proj_mi = [v/1e6 if v is not None else None for v in projetado_display]
        disp_mi = [v/1e6 if v is not None else None for v in disponivel_display]
        saldo_mi = [v/1e6 if v is not None else None for v in saldo_display]

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=meses_eixo, y=loa_mi, name='LOA (A)',
            mode='lines+markers',
            line=dict(color='#8B5CF6', width=2.5, dash='dot'),
            marker=dict(size=7, symbol='triangle-up'),
            hovertemplate="<b>LOA (A)</b><br>Mês: %{x}<br>Valor: R$ %{y:.1f} Mi<extra></extra>"
        ))

        fig.add_trace(go.Scatter(
            x=meses_eixo, y=exec_mi, name='Empenhado (B)',
            mode='lines+markers',
            line=dict(color='#1E3A8A', width=3.5, shape='spline'),
            fill='tozeroy', fillcolor='rgba(30, 58, 138, 0.07)',
            marker=dict(size=8, symbol='circle'),
            hovertemplate="<b>Empenhado (B)</b><br>Mês: %{x}<br>Valor: R$ %{y:.1f} Mi<extra></extra>"
        ))

        fig.add_trace(go.Scatter(
            x=meses_eixo, y=proj_mi, name='Projetado (C)',
            mode='lines+markers',
            line=dict(color='#D97706', width=3, dash='dash', shape='spline'),
            marker=dict(size=8, symbol='square'),
            hovertemplate="<b>Projetado (C)</b><br>Mês: %{x}<br>Valor: R$ %{y:.1f} Mi<extra></extra>"
        ))

        fig.add_trace(go.Scatter(
            x=meses_eixo, y=disp_mi, name='Disponível (D)',
            mode='lines+markers',
            line=dict(color='#10B981', width=3, shape='spline'),
            fill='tozeroy', fillcolor='rgba(16, 185, 129, 0.05)',
            marker=dict(size=8, symbol='diamond'),
            hovertemplate="<b>Disponível (D)</b><br>Mês: %{x}<br>Valor: R$ %{y:.1f} Mi<extra></extra>"
        ))

        if row_saldo is not None:
            fig.add_trace(go.Scatter(
                x=meses_eixo, y=saldo_mi, name='Saldo (D-C)',
                mode='lines+markers',
                line=dict(color='#EF4444', width=2.5, dash='dashdot', shape='spline'),
                marker=dict(size=7, symbol='x'),
                hovertemplate="<b>Saldo (D-C)</b><br>Mês: %{x}<br>Valor: R$ %{y:.1f} Mi<extra></extra>"
            ))

        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            height=250,
            margin=dict(l=40, r=40, t=30, b=30),
            font=dict(size=14, color='#1E293B'),
            legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center", font=dict(size=14, color="#1E3A8A"))
        )
        fig.update_xaxes(tickfont=dict(size=14, color="#111827"), showgrid=True, gridcolor='#E2E8F0')
        fig.update_yaxes(
            tickprefix="R$ ", ticksuffix=" Mi",
            tickfont=dict(size=13, color="#111827"), 
            showgrid=True, gridcolor='#E2E8F0', griddash='dash'
        )

        rows_info = [
            ("LOA (A)", row_loa),
            ("Empenho (B)", row_emp),
            ("Projeção (C)", row_prj),
            ("Disponível (D)", row_disp),
            ("Saldo(D-C)", row_saldo)
        ]

        html_tabela = """<style>
.tabela-proj-container {
    margin-top: 15px;
    border: 2px solid #CBD5E1;
    border-radius: 10px;
    overflow-x: auto;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    background: #FFFFFF;
}
.tabela-proj {
    width: 100%;
    border-collapse: collapse;
    font-family: sans-serif;
}
.tabela-proj th {
    background-color: #F8FAFC;
    color: #1E3A8A;
    font-weight: 800;
    font-size: 14px;
    padding: 12px 10px;
    text-align: center;
    border-bottom: 2px solid #CBD5E1;
    border-right: 1px solid #E2E8F0;
}
.tabela-proj td {
    padding: 11px 10px;
    text-align: center;
    border-bottom: 1px solid #E2E8F0;
    border-right: 1px solid #F1F5F9;
    font-size: 14px;
    font-weight: 600;
    color: #334155;
}
.tabela-proj td.col-hdr-label {
    text-align: left;
    font-weight: 800;
    color: #0F172A;
    background-color: #F8FAFC;
    min-width: 130px;
}
.tabela-proj td.col-total-val, .tabela-proj th.col-total-hdr {
    border-right: none;
    font-weight: 800;
    background-color: #F1F5F9;
    color: #0F172A;
}
.tabela-proj tr:hover td {
    background-color: #F8FAFC;
}
</style>
<div class="tabela-proj-container">
<table class="tabela-proj">
<thead>
<tr>
<th style="text-align:left;">Fase / Item</th>"""

        for m in meses_eixo:
            html_tabela += f"<th>{m}</th>"
        html_tabela += "<th class='col-total-hdr'>TOTAL</th></tr></thead><tbody>"

        for label, row in rows_info:
            if row is None: continue
            html_tabela += f"<tr><td class='col-hdr-label'>{label}</td>"
            vals_m = [converter_br_para_float(row[m]) if m in row.index else 0.0 for m in meses_eixo]
            for v in vals_m:
                txt_v = formatar_moeda_curta(v) if v != 0 else "-"
                html_tabela += f"<td>{txt_v}</td>"
            
            tot_val = obter_total(row, vals_m)
            txt_tot = formatar_moeda_curta(tot_val) if tot_val != 0 else "-"
            html_tabela += f"<td class='col-total-val'>{txt_tot}</td></tr>"

        html_tabela += "</tbody></table></div>"

        return fig, html_tabela, kpis

    except Exception as e:
        return None, None, None

def criar_grafico_arrecadacao_fonte116(df_base=None, caminho_arquivo=None, meses_limite=12):
    """
    Gera o gráfico de Arrecadação da Fonte 116 permitindo a renderização animada mês a mês.
    """
    try:
        meses_eixo = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        
        # 1. Dados completos
        projecao_loa_full = [63000, 77000, 81000, 87000, 80000, 87000, 75000, 79000, 99000, 91000, 98000, 91000]
        realizado_2026_full = [62500, 71000, 75000, 91000, 77000, 75000, 71000, 76000, 87000, None, None, None]

        # 2. Corta os dados até o mês limite do frame animado
        projecao_loa = projecao_loa_full[:meses_limite] + [None] * (12 - meses_limite)
        realizado_2026 = realizado_2026_full[:meses_limite] + [None] * (12 - meses_limite)

        # 3. Cálculos do Período
        idx_realizados = [i for i, v in enumerate(realizado_2026_full) if v is not None]
        qtd_meses = len(idx_realizados)

        tot_proj_periodo = sum(projecao_loa_full[:qtd_meses])
        tot_real_periodo = sum([v for v in realizado_2026_full if v is not None])
        diferenca_abs = tot_real_periodo - tot_proj_periodo
        diferenca_pct = (diferenca_abs / tot_proj_periodo) * 100 if tot_proj_periodo > 0 else 0.0

        tot_proj_anual = sum(projecao_loa_full)
        proj_fechamento = (tot_real_periodo / tot_proj_periodo) * tot_proj_anual if tot_proj_periodo > 0 else tot_proj_anual
        dif_fechamento_abs = proj_fechamento - tot_proj_anual
        dif_fechamento_pct = (dif_fechamento_abs / tot_proj_anual) * 100 if tot_proj_anual > 0 else 0.0

        def fmt_br(v):
            if v is None: return "-"
            sinal = "-" if v < 0 else ""
            abs_v = abs(v)
            return f"{sinal}R$ {abs_v:,.0f}".replace(",", ".")

        kpis = {
            'proj_periodo': fmt_br(tot_proj_periodo),
            'real_periodo': fmt_br(tot_real_periodo),
            'dif_abs': fmt_br(diferenca_abs),
            'dif_pct': f"{diferenca_pct:.2f}%".replace(".", ","),
            'proj_fechamento_abs': fmt_br(dif_fechamento_abs),
            'proj_fechamento_pct': f"{dif_fechamento_pct:.2f}%".replace(".", ","),
            'qtd_meses_str': f"jan-{meses_eixo[qtd_meses-1].lower()}" if qtd_meses > 0 else "período"
        }

        # Rótulos e posições dinâmicas
        labels_proj = [f"<b>{v:,.0f}</b>".replace(",", ".") if v is not None else "" for v in projecao_loa]
        labels_real = [f"<b>{v:,.0f}</b>".replace(",", ".") if v is not None else "" for v in realizado_2026]

        pos_proj, pos_real = [], []
        for p, r in zip(projecao_loa, realizado_2026):
            if r is not None and p is not None and r > p:
                pos_proj.append('bottom center')
                pos_real.append('top center')
            else:
                pos_proj.append('top center')
                pos_real.append('bottom center')

        fig = go.Figure()

        # Linha Projeção LOA (Verde)
        fig.add_trace(go.Scatter(
            x=meses_eixo, y=projecao_loa,
            name='Receita Arrecadada',
            mode='lines+markers+text',
            text=labels_proj,
            textposition=pos_proj,
            textfont=dict(size=11, color='#15803D'),
            line=dict(color='#15803D', width=3, shape='spline'),
            marker=dict(size=7, color='#15803D'),
            hovertemplate="<b>Receita Arrecadada</b><br>Mês: %{x}<br>Valor: R$ %{y:,.0f}<extra></extra>"
        ))

        # Linha Realizado 2026 (Azul)
        fig.add_trace(go.Scatter(
            x=meses_eixo, y=realizado_2026,
            name='Realizado 2026',
            mode='lines+markers+text',
            text=labels_real,
            textposition=pos_real,
            textfont=dict(size=11, color='#0284C7'),
            line=dict(color='#0284C7', width=3.5, shape='spline'),
            marker=dict(size=8, color='#0284C7'),
            hovertemplate="<b>Realizado 2026</b><br>Mês: %{x}<br>Valor: R$ %{y:,.0f}<extra></extra>"
        ))

        fig.update_layout(
            title=dict(text="Acompanhamento da Arrecadação - Fonte 116 (Tesouro)", font=dict(size=18, color="#1E3A8A")),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            height=270,
            margin=dict(l=40, r=40, t=50, b=30),
            font=dict(size=13, color='#1E293B'),
            legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center", font=dict(size=13, color="#1E3A8A"))
        )
        fig.update_xaxes(showgrid=True, gridcolor='#E2E8F0', tickfont=dict(size=13, color="#111827"))
        fig.update_yaxes(showgrid=True, gridcolor='#E2E8F0', griddash='dash', tickprefix="R$ ", tickfont=dict(size=12, color="#111827"), range=[0, 120000])

        cor_dif = "f116-neg" if diferenca_abs < 0 else "f116-pos"
        cor_fech = "f116-neg" if dif_fechamento_abs < 0 else "f116-pos"
        bg_dif = "#FEF2F2" if diferenca_abs < 0 else "#F0FDF4"
        bg_fech = "#FEF2F2" if dif_fechamento_abs < 0 else "#F0FDF4"

        html_tabela_resumo = f"""<style>
.card-f116-tbl {{
    margin-top: 15px;
    background: #FFFFFF;
    border: 2px solid #CBD5E1;
    border-radius: 10px;
    padding: 15px;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
}}
.tbl-f116 {{
    width: 100%;
    border-collapse: collapse;
    font-family: sans-serif;
    font-size: 15px;
}}
.tbl-f116 td {{
    padding: 10px 14px;
    border-bottom: 1px solid #E2E8F0;
}}
.tbl-f116 tr:last-child td {{
    border-bottom: none;
}}
.f116-label {{
    font-weight: 700;
    color: #1E293B;
}}
.f116-val {{
    text-align: right;
    font-weight: 800;
    color: #0F172A;
}}
.f116-neg {{
    color: #DC2626 !important;
}}
.f116-pos {{
    color: #16A34A !important;
}}
</style>
<div class="card-f116-tbl">
<table class="tbl-f116">
<tr>
    <td class="f116-label">Receita Arrecadada ({kpis['qtd_meses_str']})</td>
    <td class="f116-val">{kpis['proj_periodo']}</td>
    <td class="f116-val"></td>
</tr>
<tr>
    <td class="f116-label">Realizado 2026 ({kpis['qtd_meses_str']})</td>
    <td class="f116-val">{kpis['real_periodo']}</td>
    <td class="f116-val"></td>
</tr>
<tr style="background-color: {bg_dif};">
    <td class="f116-label {cor_dif}">Diferença</td>
    <td class="f116-val {cor_dif}">{kpis['dif_abs']}</td>
    <td class="f116-val {cor_dif}">{kpis['dif_pct']}</td>
</tr>
<tr style="background-color: {bg_fech};">
    <td class="f116-label {cor_fech}">Projeção superávit/déficit 2026</td>
    <td class="f116-val {cor_fech}">{kpis['proj_fechamento_abs']}</td>
    <td class="f116-val {cor_fech}">{kpis['proj_fechamento_pct']}</td>
</tr>
</table>
</div>"""

        return fig, html_tabela_resumo, kpis
    except Exception as e:
        return None, None, None

def criar_grafico_grupo_despesa(df_filtrado):
    """Cria o gráfico interativo com Plotly e Tabela HTML com fontes grandes e números destacados."""
    try:
        col_grupo = next((c for c in df_filtrado.columns if 'GRUPO' in c.upper() and 'DESPESA' in c.upper()), None)
        if not col_grupo:
            if 'Grupo de Despesas' in df_filtrado.columns: col_grupo = 'Grupo de Despesas'
            else: return None, None

        col_loa = next((c for c in df_filtrado.columns if 'DOTAÇÃO' in c.upper() or 'LOA' in c.upper()), None)
        col_aut = next((c for c in df_filtrado.columns if 'AUTORIZADO' in c.upper()), None)
        col_emp = next((c for c in df_filtrado.columns if 'EMPENHADO' in c.upper()), None)
        col_bloq = next((c for c in df_filtrado.columns if 'BLOQUEADO' in c.upper()), None)
        col_disp = next((c for c in df_filtrado.columns if 'DISPONÍVEL' in c.upper()), None)

        fases_labels = ['LOA', 'AUTORIZADO', 'EMPENHADO', 'BLOQUEADO', 'DISPONÍVEL']
        cols_reais = [col_loa, col_aut, col_emp, col_bloq, col_disp]
        
        grupos_alvo = ['Pessoal', 'Custeio', 'Investimento']
        
        def padronizar_grupo(val):
            v = str(val).upper()
            if 'PESSOAL' in v: return 'Pessoal'
            if 'CUSTEIO' in v or 'CORRENTE' in v or 'OUTRAS' in v: return 'Custeio'
            if 'INVESTIMENTO' in v or 'CAPITAL' in v: return 'Investimento'
            return 'Outros'
            
        df_temp = df_filtrado.copy()
        df_temp['Grupo_Padrao'] = df_temp[col_grupo].apply(padronizar_grupo)
        
        dados_resumo = []
        for g in grupos_alvo:
            df_g = df_temp[df_temp['Grupo_Padrao'] == g]
            linha = {'Grupo': g}
            for label, c in zip(fases_labels, cols_reais):
                if c and c in df_g.columns:
                    linha[label] = int(round(df_g[c].sum() / 1_000_000))
                else:
                    linha[label] = 0
            dados_resumo.append(linha)
            
        df_grafico = pd.DataFrame(dados_resumo)

        cores = {
            'Pessoal': '#3B82F6',      # Azul
            'Custeio': '#DC2626',      # Vermelho
            'Investimento': '#000000'  # Preto
        }

        emojis_grupo = {
            'Pessoal': '👥',
            'Custeio': '💸',
            'Investimento': '🏗️'
        }

        fig = go.Figure()

        for index, row in df_grafico.iterrows():
            grupo = row['Grupo']
            emoji = emojis_grupo.get(grupo, '')
            
            hover_texts = [
                f"<b>{grupo} - {col}</b><br>Valor: R$ {row[col]} milhões"
                for col in fases_labels
            ]
            
            text_labels = [f"{emoji} {row[col]}" if row[col] > 0 else f"{row[col]}" for col in fases_labels]

            fig.add_trace(go.Bar(
                name=grupo,
                x=fases_labels,
                y=[row[col] for col in fases_labels],
                text=text_labels,
                textposition='outside',
                textfont=dict(size=16, color="black", family="sans-serif"),
                marker_color=cores.get(grupo, '#6B7280'),
                hovertemplate="%{customdata}<extra></extra>",
                customdata=hover_texts
            ))

        fig.update_layout(
            title=dict(text='Execução Orçamentária por Grupo de Despesa (em R$ milhões)', font=dict(size=16, color='#111827')),
            yaxis_title='R$ (Em milhões)',
            barmode='group',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=14)),
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(t=35, b=0, l=10, r=10),
            height=260
        )

        fig.update_xaxes(tickfont=dict(size=15, color='#111827'))
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#E5E7EB', griddash='dash', tickfont=dict(size=14))

        dicas = {
            'LOA': 'LOA (Lei Orçamentária Anual) é o instrumento legal que estima as receitas e fixa as despesas da UEA para o período de um ano.',
            'AUTORIZADO': 'Dotação Inicial acrescida ou reduzida por créditos adicionais durante o exercício financeiro.',
            'EMPENHADO': 'Valor do orçamento reservado para garantir o pagamento dos compromissos assumidos.',
            'BLOQUEADO': 'Valores orçamentários indisponíveis temporariamente por determinação legal ou administrativa.',
            'DISPONÍVEL': 'Saldo orçamentário livre que ainda pode ser utilizado para novas contratações.'
        }

        html_tabela = f"""<style>
.tabela-despesas-container {{
    margin-top: -20px;
    border: 2px solid #CBD5E1;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
}}
.tabela-despesas {{
    width: 100%;
    border-collapse: collapse;
    font-family: sans-serif;
}}
.tabela-despesas th {{
    background-color: #1E3A8A;
    color: white;
    font-weight: 800;
    font-size: 16px;
    padding: 14px 14px;
    text-align: center;
    border-right: 1px solid #3B82F6;
    cursor: help;
}}
.tabela-despesas th:last-child {{
    border-right: none;
}}
.tabela-despesas td {{
    padding: 14px 14px;
    text-align: center;
    border-bottom: 1px solid #E2E8F0;
    font-size: 18px;
    font-weight: 800;
    color: #1E3A8A;
}}
.tabela-despesas tr:nth-child(even) td {{
    background-color: #F8FAFC;
}}
.tabela-despesas tr:hover td {{
    background-color: #F1F5F9;
}}
.col-grupo-hdr {{
    text-align: left !important;
    background-color: #1E3A8A !important;
}}
.col-grupo-cell {{
    text-align: left !important;
    font-weight: 800 !important;
    font-size: 16px !important;
    color: #0F172A !important;
}}
</style>
<div class="tabela-despesas-container">
<table class="tabela-despesas">
<thead>
<tr>
<th class="col-grupo-hdr">Grupo Despesa</th>
<th title="{dicas['LOA']}">LOA 🛈</th>
<th title="{dicas['AUTORIZADO']}">AUTORIZADO 🛈</th>
<th title="{dicas['EMPENHADO']}">EMPENHADO 🛈</th>
<th title="{dicas['BLOQUEADO']}">BLOQUEADO 🛈</th>
<th title="{dicas['DISPONÍVEL']}">DISPONÍVEL 🛈</th>
</tr>
</thead>
<tbody>"""
        for index, row in df_grafico.iterrows():
            g_nome = f"{row['Grupo']} (em R$ milhões)"
            html_tabela += f"""<tr>
<td class="col-grupo-cell">{g_nome}</td>
<td>{row['LOA']}</td>
<td>{row['AUTORIZADO']}</td>
<td>{row['EMPENHADO']}</td>
<td>{row['BLOQUEADO']}</td>
<td>{row['DISPONÍVEL']}</td>
</tr>"""

        html_tabela += """</tbody>
</table>
</div>"""

        return fig, html_tabela
    except Exception as e:
        return None, None

def criar_grafico_receita_x_despesa_dinamico(df_filtrado_evo):
    """
    Gera o gráfico e a tabela comparativa de LOA, Receita Arrecadada, Despesa Realizada e Saldo
    de forma 100% dinâmica a partir do SIAFI (df_filtrado_evo).
    """
    try:
        def safe_num(v):
            if v is None or pd.isna(v):
                return 0.0
            if isinstance(v, (int, float)):
                return float(v)
            try:
                s = str(v).replace('R$', '').strip()
                if ',' in s and '.' in s:
                    s = s.replace('.', '').replace(',', '.')
                elif ',' in s:
                    s = s.replace(',', '.')
                return float(s)
            except Exception:
                return 0.0

        meses_ordem = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        
        loa_m = [0.0] * 12
        rec_m = [0.0] * 12
        desp_m = [0.0] * 12
        
        if df_filtrado_evo is not None and not df_filtrado_evo.empty:
            cols_agrupar = [c for c in ['Autorizado', 'Empenhado', 'Liquidado', 'Pago'] if c in df_filtrado_evo.columns]
            if 'Mes_Num' in df_filtrado_evo.columns and cols_agrupar:
                df_m = df_filtrado_evo.groupby('Mes_Num')[cols_agrupar].sum().reset_index()
                
                for _, row in df_m.iterrows():
                    try:
                        m_idx = int(safe_num(row['Mes_Num'])) - 1
                        if 0 <= m_idx < 12:
                            loa_m[m_idx] = safe_num(row.get('Autorizado', 0.0)) / 1_000_000
                            rec_m[m_idx] = safe_num(row.get('Liquidado', row.get('Pago', 0.0))) / 1_000_000
                            desp_m[m_idx] = safe_num(row.get('Empenhado', 0.0)) / 1_000_000
                    except Exception:
                        continue

        saldo_m = [r - d for r, d in zip(rec_m, desp_m)]

        ultimo_mes_idx = 0
        for i in range(11, -1, -1):
            if loa_m[i] > 0 or rec_m[i] > 0 or desp_m[i] > 0:
                ultimo_mes_idx = i
                break

        loa_disp = loa_m[:ultimo_mes_idx+1] + [None]*(11 - ultimo_mes_idx)
        rec_disp = rec_m[:ultimo_mes_idx+1] + [None]*(11 - ultimo_mes_idx)
        desp_disp = desp_m[:ultimo_mes_idx+1] + [None]*(11 - ultimo_mes_idx)
        saldo_disp = saldo_m[:ultimo_mes_idx+1] + [None]*(11 - ultimo_mes_idx)

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=meses_ordem, y=loa_disp, name='LOA (A)',
            mode='lines+markers',
            line=dict(color='#000000', width=2.5),
            marker=dict(size=7, symbol='circle'),
            hovertemplate="<b>LOA (A)</b><br>Mês: %{x}<br>Valor: R$ %{y:,.2f} Mi<extra></extra>"
        ))

        fig.add_trace(go.Scatter(
            x=meses_ordem, y=rec_disp, name='Receita Arrecadada (B)',
            mode='lines+markers',
            line=dict(color='#16A34A', width=3, shape='spline'),
            marker=dict(size=8, symbol='circle'),
            hovertemplate="<b>Receita Arrecadada (B)</b><br>Mês: %{x}<br>Valor: R$ %{y:,.2f} Mi<extra></extra>"
        ))

        fig.add_trace(go.Scatter(
            x=meses_ordem, y=desp_disp, name='Despesa Realizada (C)',
            mode='lines+markers',
            line=dict(color='#DC2626', width=3, shape='spline'),
            marker=dict(size=8, symbol='circle'),
            hovertemplate="<b>Despesa Realizada (C)</b><br>Mês: %{x}<br>Valor: R$ %{y:,.2f} Mi<extra></extra>"
        ))

        fig.add_trace(go.Scatter(
            x=meses_ordem, y=saldo_disp, name='Saldo (B-C)',
            mode='lines+markers',
            line=dict(color='#9333EA', width=2.5, shape='spline'),
            marker=dict(size=8, symbol='x'),
            hovertemplate="<b>Saldo (B-C)</b><br>Mês: %{x}<br>Valor: R$ %{y:,.2f} Mi<extra></extra>"
        ))

        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            height=320,
            margin=dict(l=40, r=40, t=20, b=20),
            font=dict(size=13, color='#1E293B'),
            legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center", font=dict(size=13, color="#1E3A8A"))
        )
        fig.update_xaxes(tickfont=dict(size=14, color="#111827"), showgrid=True, gridcolor='#E2E8F0')
        fig.update_yaxes(
            tickprefix="R$ ", ticksuffix=" Mi",
            tickfont=dict(size=12, color="#111827"),
            showgrid=True, gridcolor='#E2E8F0', griddash='dash'
        )

        def fmt_tbl(v):
            if v is None or pd.isna(v): return "-"
            return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        tot_loa = sum(loa_m)
        tot_rec = sum(rec_m[:ultimo_mes_idx+1])
        tot_desp = sum(desp_m[:ultimo_mes_idx+1])
        tot_saldo = tot_rec - tot_desp

        html_tabela = f"""<style>
.tbl-rec-desp-container {{
    margin-top: 15px;
    border: 2px solid #CBD5E1;
    border-radius: 10px;
    overflow-x: auto;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    background: #FFFFFF;
}}
.tbl-rec-desp {{
    width: 100%;
    border-collapse: collapse;
    font-family: sans-serif;
}}
.tbl-rec-desp th {{
    background-color: #F8FAFC;
    color: #1E3A8A;
    font-weight: 800;
    font-size: 14px;
    padding: 10px;
    text-align: center;
    border-bottom: 2px solid #CBD5E1;
    border-right: 1px solid #E2E8F0;
}}
.tbl-rec-desp td {{
    padding: 9px 8px;
    text-align: center;
    border-bottom: 1px solid #E2E8F0;
    border-right: 1px solid #F1F5F9;
    font-size: 13px;
    font-weight: 600;
    color: #334155;
}}
.tbl-rec-desp td.col-hdr-label {{
    text-align: left;
    font-weight: 800;
    color: #0F172A;
    background-color: #F8FAFC;
    min-width: 220px;
}}
.tbl-rec-desp td.col-total-val, .tbl-rec-desp th.col-total-hdr {{
    border-right: none;
    font-weight: 800;
    background-color: #F1F5F9;
    color: #0F172A;
}}
.tbl-rec-desp tr:hover td {{
    background-color: #F8FAFC;
}}
</style>
<div class="tbl-rec-desp-container">
<table class="tbl-rec-desp">
<thead>
<tr>
<th style="text-align:left;">Item Orçamentário</th>"""

        for m in meses_ordem:
            html_tabela += f"<th>{m}</th>"
        html_tabela += "<th class='col-total-hdr'>Total</th></tr></thead><tbody>"

        html_tabela += "<tr><td class='col-hdr-label'>LOA (A) (milhões)</td>"
        for v in loa_m: html_tabela += f"<td>{fmt_tbl(v)}</td>"
        html_tabela += f"<td class='col-total-val'>{fmt_tbl(tot_loa)}</td></tr>"

        html_tabela += "<tr><td class='col-hdr-label'>Receita Arrecadada (B) (milhões)</td>"
        for i, v in enumerate(rec_m):
            txt = fmt_tbl(v) if i <= ultimo_mes_idx else "-"
            html_tabela += f"<td>{txt}</td>"
        html_tabela += f"<td class='col-total-val'>{fmt_tbl(tot_rec)}</td></tr>"

        html_tabela += "<tr><td class='col-hdr-label'>Despesa Realizada (C) (milhões)</td>"
        for i, v in enumerate(desp_m):
            txt = fmt_tbl(v) if i <= ultimo_mes_idx else "-"
            html_tabela += f"<td>{txt}</td>"
        html_tabela += f"<td class='col-total-val'>{fmt_tbl(tot_desp)}</td></tr>"

        html_tabela += "<tr><td class='col-hdr-label'>Saldo (B-C) (milhões)</td>"
        for i, v in enumerate(saldo_m):
            txt = fmt_tbl(v) if i <= ultimo_mes_idx else "-"
            html_tabela += f"<td>{txt}</td>"
        html_tabela += f"<td class='col-total-val'>{fmt_tbl(tot_saldo)}</td></tr>"

        html_tabela += "</tbody></table></div>"

        return fig, html_tabela

    except Exception:
        return None, None

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
        if col in df_base.columns: df_base[col] = df_base[col].replace(['nan', 'None', ''], np.nan).ffill()
        if col in df_var.columns: df_var[col] = df_var[col].replace(['nan', 'None', ''], np.nan).ffill()

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
        for col in colunas_fin: df[col] = df[col].apply(extrair_numero)
            
    colunas_texto = ['Programa de Trabalho', 'Fonte de Recurso', 'Natureza da Despesa', 'Mês Referência', 'Tipo Movimento']
    for df in [df_base, df_var]:
        for col in colunas_texto:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().replace('nan', '')
        
        if 'Tipo Movimento' in df.columns:
            def classificar_movimento(x):
                txt = str(x).upper().strip()
                if txt in ['NAN', 'NONE', '', '0', '0.0']: return x
                if 'ACUMULADO' in txt or 'ATÉ' in txt or 'ATE' in txt: return 'Acumulado'
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
# GERADOR DE RELATÓRIO ANALÍTICO EM PDF
# ==========================================

class PDFPainelUEA(FPDF):
    def __init__(self, titulo_secao=""):
        super().__init__(orientation='L', unit='mm', format='A4')
        self.titulo_secao = titulo_secao
        self.alias_nb_pages()

    def header(self):
        self.set_font('Arial', 'B', 9)
        self.set_text_color(30, 58, 138)
        self.cell(0, 5, 'UNIVERSIDADE DO ESTADO DO AMAZONAS - UEA | PAINEL DE EXECUÇÃO ORÇAMENTÁRIA', border=0, ln=1, align='L')
        self.set_font('Arial', 'B', 12)
        self.set_text_color(17, 24, 39)
        self.cell(0, 6, self.titulo_secao, border=0, ln=1, align='L')
        self.set_draw_color(209, 213, 219)
        self.line(10, 20, 287, 20)
        self.ln(4)

    def footer(self):
        self.set_y(-12)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(107, 114, 128)
        dt_geracao = datetime.now().strftime('%d/%m/%Y às %H:%M')
        self.cell(0, 8, f'Relatório Executivo Consolidado - Circulação Interna (CGO/PROPLAN - CPI) | Gerado em: {dt_geracao} | Página {self.page_no()} de {{nb}}', 0, 0, 'C')

def formatar_milhoes_pdf(valor):
    try:
        val = float(valor)
        if abs(val) >= 1_000_000:
            return f"R$ {val/1_000_000:,.1f} Mi".replace(',', 'X').replace('.', ',').replace('X', '.')
        elif abs(val) >= 1_000:
            return f"R$ {val/1_000:,.1f} mil".replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"R$ {val:,.0f}".replace(',', '.')
    except:
        return str(valor)

def gerar_pdf_8_paginas_dinamico(df_latest, df_base, df_var, caminho_projecao, caminho_grupo_despesa, dict_acoes, dict_naturezas):
    pdf = PDFPainelUEA()

    # PÁGINA 1
    pdf.titulo_secao = "Visão Estratégica - Panorama por Grupo de Despesa"
    pdf.add_page()
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(75, 85, 99)
    pdf.cell(0, 6, "Execução consolidada dos Grupos de Despesa (Pessoal, Custeio e Investimento) em R$ milhões.", ln=1)
    pdf.ln(3)

    cols_w = [85, 38, 38, 38, 38, 38]
    headers_p1 = ["Grupo de Despesa", "LOA", "AUTORIZADO", "EMPENHADO", "BLOQUEADO", "DISPONÍVEL"]
    
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(30, 58, 138)
    pdf.set_text_color(255, 255, 255)
    for w, h in zip(cols_w, headers_p1):
        pdf.cell(w, 8, h, border=1, fill=True, align='C')
    pdf.ln()

    grupos = [('Pessoal', 'Pessoal e Encargos Sociais (31)'), ('Custeio', 'Custeio / Outras Despesas Correntes (33)'), ('Investimento', 'Investimentos e Capital (44)')]
    
    col_grupo = next((c for c in df_latest.columns if 'GRUPO' in c.upper()), None)
    col_loa = next((c for c in df_latest.columns if 'LOA' in c.upper() or 'DOTAÇÃO' in c.upper()), None)
    col_aut = next((c for c in df_latest.columns if 'AUTORIZADO' in c.upper()), None)
    col_emp = next((c for c in df_latest.columns if 'EMPENHADO' in c.upper()), None)
    col_bloq = next((c for c in df_latest.columns if 'BLOQUEADO' in c.upper()), None)
    col_disp = next((c for c in df_latest.columns if 'DISPONÍVEL' in c.upper()), None)

    totais_p1 = [0.0]*5
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(17, 24, 39)
    
    for key_g, label_g in grupos:
        if col_grupo:
            mask_g = df_latest[col_grupo].astype(str).str.upper().str.contains(key_g.upper())
            df_g = df_latest[mask_g]
        else:
            df_g = pd.DataFrame()

        v_loa = df_g[col_loa].sum() if col_loa and not df_g.empty else 0
        v_aut = df_g[col_aut].sum() if col_aut and not df_g.empty else 0
        v_emp = df_g[col_emp].sum() if col_emp and not df_g.empty else 0
        v_bloq = df_g[col_bloq].sum() if col_bloq and not df_g.empty else 0
        v_disp = df_g[col_disp].sum() if col_disp and not df_g.empty else 0

        totais_p1[0] += v_loa; totais_p1[1] += v_aut; totais_p1[2] += v_emp; totais_p1[3] += v_bloq; totais_p1[4] += v_disp

        pdf.cell(cols_w[0], 8, label_g, border=1, align='L')
        pdf.cell(cols_w[1], 8, formatar_milhoes_pdf(v_loa), border=1, align='C')
        pdf.cell(cols_w[2], 8, formatar_milhoes_pdf(v_aut), border=1, align='C')
        pdf.cell(cols_w[3], 8, formatar_milhoes_pdf(v_emp), border=1, align='C')
        pdf.cell(cols_w[4], 8, formatar_milhoes_pdf(v_bloq), border=1, align='C')
        pdf.cell(cols_w[5], 8, formatar_milhoes_pdf(v_disp), border=1, align='C')
        pdf.ln()

    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(243, 244, 246)
    pdf.cell(cols_w[0], 8, "TOTAL GERAL CONSOLIDADO", border=1, fill=True, align='L')
    for i in range(5):
        pdf.cell(cols_w[i+1], 8, formatar_milhoes_pdf(totais_p1[i]), border=1, fill=True, align='C')

    # PÁGINA 2
    pdf.titulo_secao = "Top 10 - Maiores Despesas por Ação Orçamentária"
    pdf.add_page()
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, "Ranking das principais Ações Orçamentárias da UEA por volume financeiro de Empenho.", ln=1)
    pdf.ln(3)

    cols_w2 = [25, 160, 50, 42]
    headers_p2 = ["Ação", "Descrição da Ação Orçamentária", "Empenhado (R$)", "% do Total"]

    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(30, 58, 138)
    pdf.set_text_color(255, 255, 255)
    for w, h in zip(cols_w2, headers_p2):
        pdf.cell(w, 8, h, border=1, fill=True, align='C')
    pdf.ln()

    if 'Ação' in df_latest.columns and col_emp:
        df_top = df_latest.groupby('Ação')[col_emp].sum().nlargest(10).reset_index()
        tot_emp_geral = df_latest[col_emp].sum()
        
        pdf.set_font('Arial', '', 9)
        pdf.set_text_color(17, 24, 39)
        for _, row in df_top.iterrows():
            ac = str(row['Ação']).zfill(4)
            nome_ac = dict_acoes.get(ac, 'Ação Orçamentária')
            v_e = row[col_emp]
            pct = (v_e / tot_emp_geral * 100) if tot_emp_geral > 0 else 0
            
            pdf.cell(cols_w2[0], 7, ac, border=1, align='C')
            pdf.cell(cols_w2[1], 7, nome_ac[:70], border=1, align='L')
            pdf.cell(cols_w2[2], 7, f"R$ {v_e:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), border=1, align='R')
            pdf.cell(cols_w2[3], 7, f"{pct:.1f}%".replace('.', ','), border=1, align='C')
            pdf.ln()

    # PÁGINA 3
    pdf.titulo_secao = "Evolução Mensal da Execução Orçamentária (2026)"
    pdf.add_page()
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, "Acompanhamento estático dos saldos acumulados mês a mês em todas as fases orçamentárias (em R$ mil).", ln=1)
    pdf.ln(3)

    cols_w3 = [37, 48, 48, 48, 48, 48]
    headers_p3 = ["Mês", "Autorizado", "Empenhado", "Liquidado", "Pago", "Disponível"]

    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(30, 58, 138)
    pdf.set_text_color(255, 255, 255)
    for w, h in zip(cols_w3, headers_p3):
        pdf.cell(w, 8, h, border=1, fill=True, align='C')
    pdf.ln()

    if 'Mês Referência' in df_base.columns:
        colunas_ex = [c for c in ['Autorizado', 'Empenhado', 'Liquidado', 'Pago', 'Disponível'] if c in df_base.columns]
        df_m = df_base.groupby('Mês Referência')[colunas_ex].sum().reset_index()
        
        pdf.set_font('Arial', '', 9)
        pdf.set_text_color(17, 24, 39)
        for _, row in df_m.iterrows():
            pdf.cell(cols_w3[0], 7, str(row['Mês Referência']), border=1, align='C')
            for idx, col in enumerate(['Autorizado', 'Empenhado', 'Liquidado', 'Pago', 'Disponível']):
                val = row[col] if col in row else 0
                pdf.cell(cols_w3[idx+1], 7, f"R$ {val/1000:,.0f}".replace(',', '.'), border=1, align='C')
            pdf.ln()

    # PÁGINA 4
    pdf.titulo_secao = "Projeção vs. Realizado - (Ação 2003: Folha de Pagamento)"
    pdf.add_page()
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, "Comparativo mensal entre LOA, Empenho Realizado, Projeção de Fechamento e Saldo Disponível (em R$ mil).", ln=1)
    pdf.ln(3)

    if os.path.exists(caminho_projecao):
        df_p = pd.read_excel(caminho_projecao)
        meses_eixo = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']
        cols_w4 = [43] + [18]*12 + [28]

        pdf.set_font('Arial', 'B', 8)
        pdf.set_fill_color(30, 58, 138)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(cols_w4[0], 7, "Fase / Mês", border=1, fill=True, align='C')
        for m in meses_eixo: pdf.cell(18, 7, m, border=1, fill=True, align='C')
        pdf.cell(cols_w4[-1], 7, "TOTAL", border=1, fill=True, align='C')
        pdf.ln()

        pdf.set_font('Arial', '', 8)
        pdf.set_text_color(17, 24, 39)
        for idx_row, row_p in df_p.iterrows():
            label_fase = str(row_p.iloc[0])
            pdf.cell(cols_w4[0], 7, label_fase[:20], border=1, align='L')
            tot_row = 0
            for m in meses_eixo:
                v = row_p[m] if m in row_p else 0
                try: v_num = float(str(v).replace('.', '').replace(',', '.'))
                except: v_num = 0.0
                tot_row += v_num
                txt_v = f"{v_num/1000:,.0f}".replace(',', '.') if v_num != 0 else "-"
                pdf.cell(18, 7, txt_v, border=1, align='C')
            pdf.cell(cols_w4[-1], 7, f"{tot_row/1000:,.0f}".replace(',', '.'), border=1, align='C')
            pdf.ln()

    # PÁGINA 5
    pdf.titulo_secao = "Receita vs. Despesa - Análise de Fluxo Orçamentário"
    pdf.add_page()
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, "Comparação entre a Receita Arrecadada, Despesa Realizada e Saldo Financeiro Acumulado (em R$ milhões).", ln=1)
    pdf.ln(3)

    if os.path.exists(caminho_grupo_despesa):
        try:
            df_rd = pd.read_excel(caminho_grupo_despesa, sheet_name="ReceitaXDespesa")
            df_rd.columns = [str(c).strip() for c in df_rd.columns]
            df_rd["Valor"] = df_rd["Valor"].apply(extrair_numero)

            meses_ordem = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

            def padronizar_mes(val):
                if isinstance(val, pd.Timestamp) or hasattr(val, 'month'):
                    return meses_ordem[val.month - 1]
                v = str(val).strip()
                if '-' in v and len(v) >= 10:
                    try:
                        data = pd.to_datetime(v)
                        return meses_ordem[data.month - 1]
                    except: pass
                v_texto = v.capitalize()[:3]
                for m in meses_ordem:
                    if m.lower() in v_texto.lower(): return m
                return v_texto

            df_rd["Mes_Padrao"] = df_rd["Mês/Ano"].apply(padronizar_mes)
            df_pivot = df_rd.pivot(index="Item Orçamentário", columns="Mes_Padrao", values="Valor")

            for m in meses_ordem:
                if m not in df_pivot.columns: df_pivot[m] = np.nan
            df_pivot = df_pivot[meses_ordem]

            cols_w5 = [55] + [16]*12 + [29]

            pdf.set_font('Arial', 'B', 8)
            pdf.set_fill_color(30, 58, 138)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(cols_w5[0], 7, "Item Orçamentário", border=1, fill=True, align='C')
            for m in meses_ordem:
                pdf.cell(16, 7, m, border=1, fill=True, align='C')
            pdf.cell(cols_w5[-1], 7, "Total", border=1, fill=True, align='C')
            pdf.ln()

            pdf.set_font('Arial', '', 8)
            pdf.set_text_color(17, 24, 39)

            for item in df_pivot.index:
                pdf.cell(cols_w5[0], 7, str(item)[:28], border=1, align='L')
                tot_item = 0.0
                for m in meses_ordem:
                    val = df_pivot.loc[item, m] if m in df_pivot.columns else np.nan
                    if pd.notna(val) and val != 0:
                        tot_item += val
                        val_m = val / 1_000_000 if abs(val) > 100_000 else val
                        pdf.cell(16, 7, f"{val_m:,.1f}".replace('.', ','), border=1, align='C')
                    else:
                        pdf.cell(16, 7, "-", border=1, align='C')
                
                tot_m = tot_item / 1_000_000 if abs(tot_item) > 100_000 else tot_item
                pdf.cell(cols_w5[-1], 7, f"{tot_m:,.1f}".replace('.', ','), border=1, align='C')
                pdf.ln()
        except Exception:
            pass

    # PÁGINA 6
    pdf.titulo_secao = "Arrecadação Fonte 116 (Tesouro) - Projeção vs. Realizado"
    pdf.add_page()
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, "Diferencial entre os repasses projetados do Tesouro Estadual e os valores efetivamente realizados.", ln=1)
    pdf.ln(3)

    cols_w6 = [160, 60, 57]
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(30, 58, 138)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(cols_w6[0], 8, "Indicador Orçamentário / Métrica", border=1, fill=True, align='C')
    pdf.cell(cols_w6[1], 8, "Valor no Período", border=1, fill=True, align='C')
    pdf.cell(cols_w6[2], 8, "Variação % / Impacto", border=1, fill=True, align='C')
    pdf.ln()

    _, _, kpis_f116 = criar_grafico_arrecadacao_fonte116(df_base, caminho_grupo_despesa)

    if kpis_f116:
        indicadores_f116 = [
            (f"Projeção LOA 1,01 BI ({kpis_f116.get('qtd_meses_str', 'período')})", kpis_f116.get('proj_periodo', '-'), "-"),
            (f"Realizado 2026 ({kpis_f116.get('qtd_meses_str', 'período')})", kpis_f116.get('real_periodo', '-'), "-"),
            ("Diferença Acumulada no Período", kpis_f116.get('dif_abs', '-'), kpis_f116.get('dif_pct', '-')),
            ("Projeção Estimada de Superávit / Déficit (2026)", kpis_f116.get('proj_fechamento_abs', '-'), kpis_f116.get('proj_fechamento_pct', '-'))
        ]
    else:
        indicadores_f116 = []

    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(17, 24, 39)
    for ind, val, pct in indicadores_f116:
        pdf.cell(cols_w6[0], 8, ind, border=1, align='L')
        pdf.cell(cols_w6[1], 8, val, border=1, align='C')
        pdf.cell(cols_w6[2], 8, pct, border=1, align='C')
        pdf.ln()

    # PÁGINA 7
    pdf.titulo_secao = "Tabela de Variações Recentes (Comparativo Fechamento vs. Atual)"
    pdf.add_page()
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, "Acompanhamento das alterações de saldo registradas na base entre a posição de Fechamento e a última extração do SIAFI.", ln=1)
    pdf.ln(3)

    cols_w7 = [30, 30, 45, 55, 55, 62]
    headers_p7 = ["Ação", "Fonte", "Natureza", "Empenhado Ant.", "Empenhado Atual", "Variação (R$)"]
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(30, 58, 138)
    pdf.set_text_color(255, 255, 255)
    for w, h in zip(cols_w7, headers_p7): pdf.cell(w, 8, h, border=1, fill=True, align='C')
    pdf.ln()

    pdf.set_font('Arial', '', 8)
    pdf.set_text_color(17, 24, 39)
    if not df_var.empty:
        for _, r_v in df_var.head(10).iterrows():
            pdf.cell(cols_w7[0], 6, str(r_v.get('Ação', '')), border=1, align='C')
            pdf.cell(cols_w7[1], 6, str(r_v.get('Fonte_3', '')), border=1, align='C')
            pdf.cell(cols_w7[2], 6, str(r_v.get('Natureza_ID', '')), border=1, align='C')
            pdf.cell(cols_w7[3], 6, f"R$ {r_v.get('Empenhado Ant.', 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), border=1, align='R')
            pdf.cell(cols_w7[4], 6, f"R$ {r_v.get('Empenhado Atual.', 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), border=1, align='R')
            pdf.cell(cols_w7[5], 6, f"R$ {r_v.get('Variação_Empenhado', 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), border=1, align='R')
            pdf.ln()

    # PÁGINA 8
    pdf.titulo_secao = "Variação por Natureza da Despesa"
    pdf.add_page()
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, "Detalhamento das maiores variações de Empenho agrupadas pelo código do elemento de despesa.", ln=1)
    pdf.ln(3)

    cols_w8 = [35, 142, 60, 40]
    headers_p8 = ["Código", "Descrição da Natureza da Despesa", "Variação Absoluta (R$)", "Status"]
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(30, 58, 138)
    pdf.set_text_color(255, 255, 255)
    for w, h in zip(cols_w8, headers_p8): pdf.cell(w, 8, h, border=1, fill=True, align='C')
    pdf.ln()

    pdf.set_font('Arial', '', 8)
    pdf.set_text_color(17, 24, 39)
    if 'Natureza_ID' in df_var.columns:
        col_v_emp = next((c for c in df_var.columns if 'Variação' in c and 'Empen' in c), None)
        if col_v_emp:
            df_nat_var = df_var.groupby('Natureza_ID')[col_v_emp].sum().reset_index()
            for _, r_n in df_nat_var.head(10).iterrows():
                cod_n = str(r_n['Natureza_ID'])
                desc_n = dict_naturezas.get(cod_n, 'Não Identificada')
                v_var = r_n[col_v_emp]
                st_v = "Aumento" if v_var > 0 else ("Redução" if v_var < 0 else "Estável")
                
                pdf.cell(cols_w8[0], 6, cod_n, border=1, align='C')
                pdf.cell(cols_w8[1], 6, desc_n[:60], border=1, align='L')
                pdf.cell(cols_w8[2], 6, f"R$ {v_var:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), border=1, align='R')
                pdf.cell(cols_w8[3], 6, st_v, border=1, align='C')
                pdf.ln()

    # BLOCCO CORRIGIDO COM INDENTAÇÃO DO TEMPFILE
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        caminho_pdf_temp = tmp_file.name
        pdf.output(caminho_pdf_temp)

    with open(caminho_pdf_temp, "rb") as f:
        bytes_pdf = f.read()

    if os.path.exists(caminho_pdf_temp):
        os.remove(caminho_pdf_temp)

    return bytes_pdf

# ==========================================
# 6. EXECUÇÃO PRINCIPAL
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
        dt_ant = pd.to_datetime(val_ant, errors='coerce').strftime('%d/%m/%Y às %H:%M')
        dt_atual = pd.to_datetime(val_atual, errors='coerce').strftime('%d/%m/%Y às %H:%M')
        texto_periodo = f"Posição Consolidada da Base: {dt_atual}" if dt_ant == dt_atual else f"Comparativo Automático: Extrato de {dt_ant} até {dt_atual}"
    except Exception: 
        dt_atual = "N/D"
        texto_periodo = "Aguardando atualização da base de dados."

    if 'Mês Referência' in df_base.columns:
        def identifying_mes_streamlit(texto):
            t = str(texto).upper().strip()
            if 'JAN' in t: return 'Janeiro'
            if 'FEV' in t: return 'Fevereiro'
            if 'MA' in t and 'R' in t: return 'Março'
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

        df_base['Mes_Nome'] = df_base['Mês Referência'].apply(identifying_mes_streamlit)
        df_base['Mes_Num'] = df_base['Mes_Nome'].map(ordem_meses)
        df_base['Ano_Ref'] = df_base['Mês Referência'].astype(str).str.extract(r'(\d{4})')
    else:
        df_base['Mes_Nome'] = 'Desconhecido'; df_base['Mes_Num'] = 0; df_base['Ano_Ref'] = '2026'

    try:
        ano_dinamico = str(df_base['Ano_Ref'].dropna().max())
        if ano_dinamico in ['', 'nan', 'None']: ano_dinamico = '2026'
    except:
        ano_dinamico = '2026'

    # BARRA LATERAL
    img_logos = r"Logos_Execução.jpeg"
    if os.path.exists(img_logos):
        st.sidebar.image(img_logos, width="stretch")
        st.sidebar.markdown("---")

    if st.sidebar.button("🔄 Atualizar Dados da Rede", width="stretch"):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.markdown("---")

    if st.session_state.pagina_ativa == 'dashboard':
        st.sidebar.button("⬅️ Voltar para a Capa", on_click=lambda: st.session_state.update(pagina_ativa='capa'), width="stretch")

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

    # TELA 1 (CAPA)
    if st.session_state.pagina_ativa == 'capa':
        st.write("")
        st.write("")
        col_esq, col_centro, col_dir = st.columns([1, 3, 1])
        with col_centro:
            try: st.image("LogoPainelOrcamento.jpeg", width="stretch")
            except: st.warning("Imagem da capa não encontrada.")
            st.write("")
            if st.button("🚀 ACESSAR PAINEL DE EXECUÇÃO ORÇAMENTÁRIA", width="stretch"):
                st.session_state.pagina_ativa = 'dashboard'
                st.rerun()
        st.stop()  

    # TELA 2 (DASHBOARD)
    elif st.session_state.pagina_ativa == 'dashboard':
        st.title("📊 PAINEL ORÇAMENTÁRIO - UEA")
        
        with st.expander("🔍 CLIQUE AQUI PARA ABRIR/FECHAR OS FILTROS DO PAINEL", expanded=True):
            c1, c2, c3, c4, c5 = st.columns(5)
            
            with c1:
                lista_meses = df_base[['Mes_Nome', 'Mes_Num']].dropna().drop_duplicates().sort_values('Mes_Num')['Mes_Nome'].tolist()
                var_mes_str = st.selectbox("Mês de Referência", ["Todos"] + lista_meses, key=f"filtro_mes_{st.session_state.botao_reset}")
                
            with c2:
                if 'Tipo Movimento' in df_base.columns:
                    tipos_mov = [t for t in df_base['Tipo Movimento'].dropna().unique() if t]
                    idx_padrao = tipos_mov.index('Acumulado') if 'Acumulado' in tipos_mov else 0
                    var_mov_str = st.selectbox("Tipo de Movimento", tipos_mov, index=idx_padrao, key=f"filtro_mov_{st.session_state.botao_reset}")
                else: 
                    var_mov_str = None
                    st.write("Movimento N/D")
                    
            with c3:
                acoes_validas = [str(a) for a in df_base['Ação'].unique() if str(a).strip() != '' and str(a).isdigit() and len(str(a)) == 4]
                opcoes_acao = ["Todas"] + [f"{a} - {dict_acoes.get(a, 'NÃO IDENTIFICADA')}" for a in sorted(list(set(acoes_validas)))]
                var_acao_str = st.selectbox("Ação", opcoes_acao, key=f"filtro_acao_{st.session_state.botao_reset}")
                var_acao_codigo = var_acao_str.split(' - ')[0]
                
            with c4:
                fontes_3_validas = sorted([f for f in df_base['Fonte_3'].unique() if f and f != ''])
                opcoes_fonte = ["Todas"] + [f"{f} - {dict_fontes_global.get(f, 'Outras Fontes')}" for f in fontes_3_validas]
                var_fonte_str = st.selectbox("Fonte de Recurso", opcoes_fonte, key=f"filtro_fonte_{st.session_state.botao_reset}")
                var_fonte_codigo = var_fonte_str.split(' - ')[0]
                
            with c5:
                naturezas_validas = sorted([str(n) for n in df_base['Natureza_ID'].unique() if n and n != ''])
                opcoes_natureza = ["Todas"] + [f"{n} - {dict_naturezas.get(n, 'NÃO IDENTIFICADA')}" for n in naturezas_validas]
                var_natureza_str = st.selectbox("Natureza", opcoes_natureza, key=f"filtro_natureza_{st.session_state.botao_reset}")
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

            st.markdown("---")

            col_b1, col_b2 = st.columns([1, 1])
            
            with col_b1:
                st.button("🧹 Limpar Todos os Filtros", on_click=forcar_limpeza_total, use_container_width=True)
            
            with col_b2:
                try:
                    bytes_relatorio_pdf = gerar_pdf_8_paginas_dinamico(
                        df_latest=df_latest,
                        df_base=df_base,
                        df_var=df_var_filtrada,
                        caminho_projecao=r"Projecao_2026.xlsx",
                        caminho_grupo_despesa=r"Grafico_Grupo de Despesa.xlsx",
                        dict_acoes=dict_acoes,
                        dict_naturezas=dict_naturezas
                    )

                    st.download_button(
                        label="📄 Baixar Relatório Analítico (.PDF)",
                        data=bytes_relatorio_pdf,
                        file_name=f"Relatorio_Analitico_UEA_{datetime.now().strftime('%d%m%Y')}.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )
                except Exception as e_pdf:
                    st.error(f"Erro ao preparar o PDF: {e_pdf}")
        
    st.markdown("""
        <style>
        .kpi-container { 
            position: sticky; 
            top: 0; 
            background: white; 
            z-index: 999; 
            padding: 4px 0 6px 0; 
            border-bottom: 2px solid #e5e7eb; 
            margin-bottom: 8px; 
        }
        .kpi-card { 
            background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%); 
            border-radius: 8px; 
            padding: 6px 10px !important; 
            text-align: center; 
            color: white; 
            box-shadow: 0 2px 6px rgba(30, 58, 138, 0.2); 
            min-height: 72px !important; 
            display: flex; 
            flex-direction: column; 
            justify-content: center; 
        }
        .kpi-card-aut { background: linear-gradient(135deg, #475569 0%, #64748B 100%); }
        .kpi-card-emp { background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%); }
        .kpi-card-liq { background: linear-gradient(135deg, #0369A1 0%, #0284C7 100%); }
        .kpi-card-pago { background: linear-gradient(135deg, #047857 0%, #10B981 100%); }
        .kpi-card-bloq { background: linear-gradient(135deg, #991B1B 0%, #EF4444 100%); }
        .kpi-card-disp { background: linear-gradient(135deg, #B45309 0%, #D97706 100%); }
        .kpi-label { font-size: 12px !important; font-weight: 800 !important; letter-spacing: 0.5px; opacity: 0.95; margin-bottom: 2px !important; text-transform: uppercase; }
        .kpi-value { font-size: 22px !important; font-weight: 900 !important; line-height: 1.1; }
        .kpi-delta { font-size: 11px !important; font-weight: 700 !important; opacity: 0.95; margin-top: 2px !important; background: rgba(255,255,255,0.2); padding: 1px 6px; border-radius: 8px; display: inline-block; }
        .block-container { padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; }
        </style>
        """, unsafe_allow_html=True)
        
    st.markdown('<div class="kpi-container">', unsafe_allow_html=True)
    st.markdown(f"<div class='destaque-ano'>Exercício Orçamentário: {ano_dinamico} <span style='font-size: 18px; font-weight: bold; color: #6B7280;'>(última atualização: {dt_atual})</span></div>", unsafe_allow_html=True)
    
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    
    v_aut = df_latest['Autorizado'].sum() if 'Autorizado' in df_latest.columns else 0
    v_emp = df_latest['Empenhado'].sum() if 'Empenhado' in df_latest.columns else 0
    v_liq = df_latest['Liquidado'].sum() if 'Liquidado' in df_latest.columns else 0
    v_pago = df_latest['Pago'].sum() if 'Pago' in df_latest.columns else 0
    v_bloq = df_latest['Bloqueado'].sum() if 'Bloqueado' in df_latest.columns else 0
    v_disp = df_latest['Disponível'].sum() if 'Disponível' in df_latest.columns else 0

    with c1: st.markdown(f'<div class="kpi-card kpi-card-aut"><div class="kpi-label">📋 AUTORIZADO</div><div class="kpi-value">{formata_moeda_sem_decimal(v_aut)}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="kpi-card kpi-card-emp"><div class="kpi-label">💰 EMPENHADO</div><div class="kpi-value">{formata_moeda_sem_decimal(v_emp)}</div><div class="kpi-delta">{(v_emp/v_aut)*100 if v_aut>0 else 0:.1f}% do total</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="kpi-card kpi-card-liq"><div class="kpi-label">✅ LIQUIDADO</div><div class="kpi-value">{formata_moeda_sem_decimal(v_liq)}</div><div class="kpi-delta">{(v_liq/v_aut)*100 if v_aut>0 else 0:.1f}% do total</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="kpi-card kpi-card-pago"><div class="kpi-label">💳 PAGO</div><div class="kpi-value">{formata_moeda_sem_decimal(v_pago)}</div><div class="kpi-delta">{(v_pago/v_aut)*100 if v_aut>0 else 0:.1f}% do total</div></div>', unsafe_allow_html=True)
    with c5: st.markdown(f'<div class="kpi-card kpi-card-bloq"><div class="kpi-label">🔒 BLOQUEADO</div><div class="kpi-value">{formata_moeda_sem_decimal(v_bloq)}</div></div>', unsafe_allow_html=True)
    with c6: st.markdown(f'<div class="kpi-card kpi-card-disp"><div class="kpi-label">📊 DISPONÍVEL</div><div class="kpi-value">{formata_moeda_sem_decimal(v_disp)}</div></div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

    lista_abas = [
        "🎯 Visão Estratégica",
        "🏆 Top 10",
        "📈 Evolução Mensal",
        "📉 Projeção vs. Realizado",
        "⚖️ Receita vs. Despesa",
        "🏛️ Arrecadação Fonte 116",
        "🔍 Tabela de Variações",
        "📊 Variação por Natureza"
    ]

    with modo_apresentacao(lista_abas, tempo_segundos=5) as aba_atual:

        if aba_atual == "🎯 Visão Estratégica":
            st.subheader("📊 Panorama Geral por Grupo de Despesa")
            fig_grupo, html_tabela = criar_grafico_grupo_despesa(df_latest)
            if fig_grupo is not None:
                st.plotly_chart(fig_grupo, use_container_width=True)
                st.markdown(html_tabela, unsafe_allow_html=True)
            else:
                st.info("A coluna 'Grupo de Despesas' não foi identificada ou está vazia na base de dados atual.")
                
        elif aba_atual == "🏆 Top 10":
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
                        yaxis=dict(categoryorder='total ascending', tickfont=dict(size=16, color="#111827"), automargin=True), 
                        font=dict(size=15, color="black"), 
                        xaxis=dict(showticklabels=False, title="", range=[0, max_valor_bar * 1.25]), 
                        yaxis_title="", 
                        margin=dict(l=20, r=100, t=10, b=10)
                    )
                    fig_bar.update_traces(marker_color='#4f8868', textposition="outside", textfont=dict(size=15, color="black"), hovertemplate="<b>Ação: %{customdata[0]} - %{customdata[1]}</b><br>Valor: %{text}<extra></extra>")
                    st.plotly_chart(fig_bar, width="stretch")
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
                    fig_tree.update_traces(texttemplate="<b>%{label}</b><br>%{customdata[0]}", textfont=dict(size=16), hovertemplate="<b>%{label}</b><br>Empenhado: %{customdata[0]}<extra></extra>")
                    fig_tree.update_layout(margin=dict(t=20, l=10, r=10, b=10), height=480)
                    st.plotly_chart(fig_tree, width="stretch")
                else:
                    st.info("Não há valores empenhados para detalhar nesta Ação.")

        elif aba_atual == "📈 Evolução Mensal":
            import time

            st.markdown(f"<div class='destaque-ano'>Evolução Mensal da Execução - Ano {ano_dinamico} <span style='font-size: 18px; font-weight: normal; color: #6B7280;'>(última atualização: {dt_atual})</span></div>", unsafe_allow_html=True)
            colunas_ex = [col for col in ['Autorizado', 'Empenhado', 'Liquidado', 'Pago', 'Disponível'] if col in df_base.columns]
            df_m = df_base[mask_evo].groupby('Mês Referência')[colunas_ex].sum().reset_index()
            
            if not df_m.empty:
                df_m['Nome_Mes'] = df_m['Mês Referência'].apply(identifying_mes_streamlit)
                df_m['mes_num'] = df_m['Nome_Mes'].map(ordem_meses)
                df_m['Mês'] = df_m['Nome_Mes'].map(abrev_meses) + f'/{ano_dinamico}'
                df_m = df_m.sort_values('mes_num')

                estilos_fases = {
                    'Autorizado': {'cor': '#64748B', 'dash': 'dot', 'fill': None, 'fillcolor': 'rgba(0,0,0,0)', 'width': 2.5, 'pos': 'top center'},
                    'Empenhado': {'cor': '#1E3A8A', 'dash': 'solid', 'fill': 'tozeroy', 'fillcolor': 'rgba(30, 58, 138, 0.14)', 'width': 3.5, 'pos': 'top center'},
                    'Liquidado': {'cor': '#3B82F6', 'dash': 'solid', 'fill': 'tozeroy', 'fillcolor': 'rgba(59, 130, 246, 0.10)', 'width': 3, 'pos': 'top center'},
                    'Pago': {'cor': '#10B981', 'dash': 'solid', 'fill': 'tozeroy', 'fillcolor': 'rgba(16, 185, 129, 0.10)', 'width': 3, 'pos': 'bottom center'},
                    'Disponível': {'cor': '#D97706', 'dash': 'solid', 'fill': 'tozeroy', 'fillcolor': 'rgba(217, 119, 6, 0.08)', 'width': 3, 'pos': 'top center'}
                }

                max_val = max([df_m[col].max() for col in colunas_ex if col in df_m.columns])

                plot_spot = st.empty()
                fig_animated = go.Figure()

                fig_animated.update_layout(
                    font=dict(size=15, color="black"),
                    margin=dict(l=40, r=60, t=30, b=20),
                    yaxis_range=[0, max_val * 1.35],
                    yaxis=dict(showticklabels=False, title=""),
                    xaxis=dict(tickfont=dict(size=16, color="#111827")),
                    legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center", font=dict(size=15)),
                    plot_bgcolor='rgba(0,0,0,0)',
                    height=480
                )
                fig_animated.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#E5E7EB', griddash='dash')

                for fase in colunas_ex:
                    if fase in estilos_fases and fase in df_m.columns:
                        cfg = estilos_fases[fase]
                        y_vals = df_m[fase].values
                        rotulos = [f"<b>{formata_abreviado(v)}</b>" if v > 0 else "" for v in y_vals]
                        
                        fig_animated.add_trace(go.Scatter(
                            x=df_m['Mês'],
                            y=y_vals,
                            name=fase,
                            mode='lines+markers+text',
                            text=rotulos,
                            textposition=cfg['pos'],
                            textfont=dict(size=14, color=cfg['cor'], family="sans-serif"),
                            line=dict(color=cfg['cor'], width=cfg['width'], dash=cfg['dash']),
                            fill=cfg['fill'],
                            fillcolor=cfg['fillcolor'],
                            marker=dict(size=8, color=cfg['cor']),
                            hovertemplate=f"<b>{fase}</b><br>Mês: %{{x}}<br>Valor: R$ %{{y:,.2f}}<extra></extra>"
                        ))
                        
                        plot_spot.plotly_chart(fig_animated, use_container_width=True)
                        time.sleep(0.7)
            else:
                st.info("Não há dados de evolução mensal para os filtros selecionados.")

        elif aba_atual == "📉 Projeção vs. Realizado":
            st.markdown(f"<div class='destaque-ano'>Projeção Orçamentária - Ano {ano_dinamico} <span style='font-size: 18px; font-weight: normal; color: #6B7280;'>(última atualização: {dt_atual})</span></div>", unsafe_allow_html=True)
            caminho_projecao = r"Projecao_2026.xlsx"
            
            if os.path.exists(caminho_projecao):
                fig_tendencia, html_tabela_proj, kpis = criar_grafico_tendencia_global(caminho_projecao)
                if fig_tendencia is not None:
                    st.markdown("""
                    <style>
                    .kpi-row-proj { display: flex; gap: 15px; margin-top: 10px; margin-bottom: 15px; flex-wrap: wrap; }
                    .kpi-card-proj { flex: 1; min-width: 200px; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 14px 18px; box-shadow: 0 4px 10px rgba(0,0,0,0.04); display: flex; align-items: center; gap: 14px; }
                    .kpi-icon-box { width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: bold; }
                    .kpi-title-proj { font-size: 13px; font-weight: 700; color: #64748B; text-transform: uppercase; }
                    .kpi-value-proj { font-size: 24px; font-weight: 800; color: #0F172A; line-height: 1.1; }
                    </style>
                    """, unsafe_allow_html=True)

                    html_kpis = f"""
                    <div class="kpi-row-proj">
                        <div class="kpi-card-proj">
                            <div class="kpi-icon-box" style="background:#F3E8FF; color:#8B5CF6;">📊</div>
                            <div>
                                <div class="kpi-title-proj">Total LOA (A)</div>
                                <div class="kpi-value-proj" style="color:#6B21A8;">{kpis['tot_loa']}</div>
                            </div>
                        </div>
                        <div class="kpi-card-proj">
                            <div class="kpi-icon-box" style="background:#DBEAFE; color:#1E3A8A;">💰</div>
                            <div>
                                <div class="kpi-title-proj">Total Empenhado (B)</div>
                                <div class="kpi-value-proj" style="color:#1E3A8A;">{kpis['tot_emp']}</div>
                            </div>
                        </div>
                        <div class="kpi-card-proj">
                            <div class="kpi-icon-box" style="background:#D1FAE5; color:#059669;">🏦</div>
                            <div>
                                <div class="kpi-title-proj">Disponível Atual (D)</div>
                                <div class="kpi-value-proj" style="color:#047857;">{kpis['disp_atual']}</div>
                            </div>
                        </div>
                        <div class="kpi-card-proj">
                            <div class="kpi-icon-box" style="background:#FEF3C7; color:#D97706;">🎯</div>
                            <div>
                                <div class="kpi-title-proj">Total Projeção (C)</div>
                                <div class="kpi-value-proj" style="color:#B45309;">{kpis['tot_prj']}</div>
                            </div>
                        </div>
                    </div>
                    """
                    st.markdown(html_kpis, unsafe_allow_html=True)

                    st.markdown("### 📉 LOA vs. Empenhado vs. Projeção vs Disponível - (Ação 2003: Folha de Pagamento - UEA)")
                    st.plotly_chart(fig_tendencia, use_container_width=True)
                    st.markdown(html_tabela_proj, unsafe_allow_html=True)
                else: 
                    st.warning("⚠️ Planilha de projeção não encontrada ou com formato inválido.")
            else: 
                st.warning("⚠️ Arquivo de projeção não encontrado.")

        elif aba_atual == "⚖️ Receita vs. Despesa":
            # 1. Varredura garantida da data do arquivo "Grafico_Grupo de Despesa.xlsx"
            pasta_script = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
            nome_alvo = "Grafico_Grupo de Despesa.xlsx"
            
            candidatos_planilha = [
                os.path.join(pasta_script, nome_alvo),
                os.path.abspath(nome_alvo),
                r"\\Rei-1cpd003\coord_plan_institucional\DADOS CPI\Orçamento\2026\EXECUÇÃO ORÇAMENTÁRIA\RELEXORC_CSV\Saida_PowerBI\Grafico_Grupo de Despesa.xlsx"
            ]
            
            dt_atualizacao_gd = None
            for caminho_teste in candidatos_planilha:
                if os.path.exists(caminho_teste):
                    try:
                        mtime = os.path.getmtime(caminho_teste)
                        dt_atualizacao_gd = datetime.fromtimestamp(mtime).strftime('%d/%m/%Y às %H:%M')
                        break
                    except Exception:
                        pass

            # Caso o caminho exato varie, busca por variação do nome na pasta
            if not dt_atualizacao_gd:
                try:
                    for f in os.listdir(pasta_script):
                        if "grupo de despesa" in f.lower() and f.endswith((".xlsx", ".XLSX")):
                            caminho_f = os.path.join(pasta_script, f)
                            mtime = os.path.getmtime(caminho_f)
                            dt_atualizacao_gd = datetime.fromtimestamp(mtime).strftime('%d/%m/%Y às %H:%M')
                            break
                except Exception:
                    pass

            # Fallback final de segurança
            if not dt_atualizacao_gd:
                dt_atualizacao_gd = dt_atual

            st.markdown(f"<div class='destaque-ano'>Análise da Receita Arrecadada x Despesa Realizada <span style='font-size: 18px; font-weight: normal; color: #6B7280;'>(última atualização: {dt_atualizacao_gd})</span></div>", unsafe_allow_html=True)
            
            # 2. Filtragem segura (passa a base consolidada para a função)
            df_rec_desp_filtrado = df_base if df_base is not None else pd.DataFrame()
            
            fig_rec_desp, html_rec_desp = criar_grafico_receita_x_despesa_dinamico(df_rec_desp_filtrado)
            
            if fig_rec_desp is not None:
                st.plotly_chart(fig_rec_desp, use_container_width=True)
                if html_rec_desp:
                    st.markdown(html_rec_desp, unsafe_allow_html=True)
            else:
                st.warning("⚠️ Não foi possível calcular a relação Receita vs. Despesa.")
                
        elif aba_atual == "🏛️ Arrecadação Fonte 116":
            import time
            st.markdown(f"<div class='destaque-ano'>Arrecadação Fonte 116 (Tesouro) - Realizado vs. Projeção <span style='font-size: 18px; font-weight: normal; color: #6B7280;'>(última atualização: {dt_atual})</span></div>", unsafe_allow_html=True)
            caminho_grupo_despesa = r"Grafico_Grupo de Despesa.xlsx"

            plot_spot = st.empty()

            for m in range(1, 13):
                fig_f116, html_f116, kpis_f116 = criar_grafico_arrecadacao_fonte116(df_base, caminho_grupo_despesa, meses_limite=m)
                if fig_f116 is not None:
                    plot_spot.plotly_chart(fig_f116, use_container_width=True)
                    time.sleep(1.08)

            if html_f116 is not None:
                st.markdown(html_f116, unsafe_allow_html=True)
            else:
                st.info("Não foi possível carregar os dados da Fonte 116.")

        elif aba_atual == "🔍 Tabela de Variações":
            st.markdown(f"<div class='periodo-destaque'>📅 {texto_periodo}</div>", unsafe_allow_html=True)
            st.subheader("Tabela de Variações")
            
            df_var_visual = df_var_filtrada.copy()
            df_var_visual_tela = df_var_visual.copy()
            
            df_var_visual_tela['AÇÃO'] = df_var_visual['Ação'].apply(lambda x: f'<div title="{x} - {dict_acoes.get(x, "N/I")}">{x}</div>' if x else "")
            df_var_visual_tela['FONTE'] = df_var_visual['Fonte_3'].apply(lambda x: f'<div title="{x} - {dict_fontes_global.get(x, "Outras Fontes")}">{x}</div>' if x else "")
            df_var_visual_tela['NATUREZA'] = df_var_visual['Natureza_ID'].apply(lambda x: f'<div title="{x} - {dict_naturezas.get(x, "N/I")}">{x}</div>' if x else "")
            
            colunas_identificacao = ['AÇÃO', 'FONTE', 'NATUREZA']
            colunas_financeiras_originais = [
                'Autorizado Ant.', 'Autorizado Atual.', 'Variação_Autorizado',
                'Empenhado Ant.', 'Empenhado Atual.', 'Variação_Empenhado',
                'Liquidado Ant.', 'Liquidado Atual.', 'Variação_Liquidado',
                'Pago Ant.', 'Pago Atual.', 'Variação_Pago',
                'Bloqueado Ant.', 'Bloqueado Atual.', 'Variação_Bloqueado',
                'Disponível Ant.', 'Disponível Atual.', 'Variação_Disponível'
            ]
            colunas_financeiras_originais = [c for c in colunas_financeiras_originais if c in df_var_visual.columns]
            df_var_visual_tela = df_var_visual_tela[colunas_identificacao + colunas_financeiras_originais]
            
            linha_soma = df_var_visual_tela[colunas_financeiras_originais].sum()
            df_total = pd.DataFrame(linha_soma).T
            for col in colunas_identificacao: df_total[col] = ""
            df_total['AÇÃO'] = "<b>TOTAL GERAL</b>"
            df_var_visual_tela = pd.concat([df_var_visual_tela, df_total], ignore_index=True)
            
            mapeamento_colunas = {}
            for col in colunas_financeiras_originais:
                nome_seguro = col.replace('Ant.', 'A\u200Bnt.')
                novo_nome = nome_seguro.replace('_', '<br>').replace(' ', '<br>').replace('<br><br>', '<br>')
                mapeamento_colunas[col] = f'<span translate="no" class="notranslate">{novo_nome}</span>'
            
            df_var_visual_tela = df_var_visual_tela.rename(columns=mapeamento_colunas)
            colunas_financeiras_tela = list(mapeamento_colunas.values())
            
            tabela_estilizada = (df_var_visual_tela.style
                .apply(destacar_celulas_com_variacao, axis=None)
                .format({col: formata_numero_duas_casas for col in colunas_financeiras_tela})
                .set_properties(**{'text-align': 'right'}, subset=colunas_financeiras_tela)
                .set_properties(**{'text-align': 'center'}, subset=colunas_identificacao)
                .set_properties(subset=pd.IndexSlice[df_var_visual_tela.index[-1], :], **{'font-weight': 'bold', 'background-color': '#E5E7EB', 'color': '#0F172A'})
            )
            
            try: html_tabela = tabela_estilizada.hide(axis="index").to_html(escape=False)
            except AttributeError: html_tabela = tabela_estilizada.hide_index().render()
            
            st.markdown(f'<div class="tabela-container">{html_tabela}</div>', unsafe_allow_html=True)
            
            df_excel = df_var_visual.copy()
            df_excel['AÇÃO'] = df_excel['Ação'].apply(lambda x: f"{x} - {dict_acoes.get(x, 'N/I')}" if x else "")
            df_excel['FONTE'] = df_excel['Fonte_3'].apply(lambda x: f"{x} - {dict_fontes_global.get(x, 'Outras Fontes')}" if x else "")
            df_excel['NATUREZA'] = df_excel['Natureza_ID'].apply(lambda x: f"{x} - {dict_naturezas.get(x, 'N/I')}" if x else "")
            df_excel = df_excel[colunas_identificacao + colunas_financeiras_originais]
            
            df_total_excel = pd.DataFrame(df_excel[colunas_financeiras_originais].sum()).T
            for col in colunas_identificacao: df_total_excel[col] = ""
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

        elif aba_atual == "📊 Variação por Natureza":
            if var_acao_codigo != "Todas":
                titulo_dinamico = f"Detalhamento da variação do Empenhado<br><span style='font-size: 22px; color: #4B5563;'>da Ação: {var_acao_str}</span>"
            else:
                titulo_dinamico = "Detalhamento da variação do Empenhado<br><span style='font-size: 22px; color: #4B5563;'>(Panorama de Todas as Ações)</span>"
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

            if col_var_emp and not df_var_filtrada.empty:
                df_chart_var = df_var_filtrada.groupby('Natureza_ID')[col_var_emp].sum().reset_index()
                df_chart_var = df_chart_var[abs(df_chart_var[col_var_emp]) > 0.01]
                
                if not df_chart_var.empty:
                    df_chart_var['Nome_Natureza'] = df_chart_var['Natureza_ID'].map(dict_naturezas).fillna('Não Identificada')
                    df_chart_var['Rotulo_Eixo'] = "<b>" + df_chart_var['Natureza_ID'] + " - " + df_chart_var['Nome_Natureza'].str.slice(0, 50) + "</b>"
                    df_chart_var['Texto_Valor'] = df_chart_var[col_var_emp].apply(formata_abreviado)
                    df_chart_var['Cor'] = df_chart_var[col_var_emp].apply(lambda x: '#10B981' if x > 0 else '#EF4444')
                    df_chart_var = df_chart_var.sort_values(by=col_var_emp, ascending=True)
                    
                    fig_var = px.bar(df_chart_var, x=col_var_emp, y='Rotulo_Eixo', orientation='h', text='Texto_Valor', custom_data=['Natureza_ID', 'Nome_Natureza'])
                    fig_var.update_traces(marker_color=df_chart_var['Cor'], textposition="outside", textfont=dict(size=15, color="black"), hovertemplate="<b>Natureza: %{customdata[0]} - %{customdata[1]}</b><br>Variação no Período: %{text}<extra></extra>")
                    fig_var.add_vline(x=0, line_width=2, line_color="black")
                    max_abs = abs(df_chart_var[col_var_emp]).max()
                    fig_var.update_layout(font=dict(size=15, color="black"), yaxis=dict(tickfont=dict(size=14, color="#111827")), xaxis=dict(showticklabels=False, title="", range=[-max_abs * 1.35, max_abs * 1.35]), yaxis_title="", margin=dict(l=10, r=40, t=20, b=10), height=max(420, len(df_chart_var) * 48))
                    st.plotly_chart(fig_var, width="stretch")
                else: st.info("Não houve variação de Empenho para as naturezas neste período ou filtro selecionado.")
            else: st.warning("Coluna de variação de Empenhado não foi identificada na base de dados.")

except Exception as e:
    st.markdown(f"""
        <div style="background-color: #FEF2F2; border-left: 6px solid #DC2626; padding: 20px; border-radius: 5px; margin-top: 50px;">
            <h2 style="color: #991B1B; margin-top: 0;">⚠️ Ocorreu uma instabilidade no painel.</h2>
            <p style="color: #7F1D1D; font-size: 16px;">
                Não se preocupe! Isto geralmente ocorre devido a uma atualização recente nos dados do SIAFI ou conflito de memória.
            </p>
            <p style="color: #991B1B; font-size: 13px;"><b>Erro técnico detalhado:</b> {e}</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Reiniciar e Limpar Cache do Sistema", width="stretch"):
            st.cache_data.clear()
            st.session_state.clear()
            st.rerun()