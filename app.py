# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import streamlit.components.v1 as components
import html

# ---------------- CONFIGURAÇÃO ----------------
st.set_page_config(page_title="Relatório de Frequência",
                   page_icon="📊", layout="wide")

st.title("📊Frequência de Funcionários ID Logistícs Cajamar SP")

# ---------------- CARREGAR DADOS (AGORA NA SIDEBAR) ----------------
st.sidebar.header("📂 Upload de Arquivo")
uploaded_file = st.sidebar.file_uploader(
    "Carregue a planilha de frequência (CSV ou Excel)", type=["csv", "xlsx"]
)

if uploaded_file:
    # Detecta formato
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file, header=0, sep=";", encoding="utf-8")
    else:
        df = pd.read_excel(uploaded_file, header=0)

    # Ajuste de nomes de colunas
    df.columns = df.columns.str.upper().str.strip()

    # Remover as colunas de 'FUNÇÃO' até 'UNIDADE' (inclusive) — se existirem
    if "FUNÇÃO" in df.columns and "UNIDADE" in df.columns:
        idx_funcao = df.columns.get_loc("FUNÇÃO")
        idx_unidade = df.columns.get_loc("UNIDADE")
        cols_to_drop = df.columns[idx_funcao:idx_unidade + 1]
        df = df.drop(columns=cols_to_drop)

    # ---------------- DEFINIR A COLUNA DE NOME ----------------
    if "NOME" in df.columns:
        nome_col = "NOME"
    else:
        st.error(
            "❌ Não encontrei a coluna 'NOME' na planilha. Verifique se existe essa coluna.")
        st.stop()

    # Seleciona as colunas de datas (todas após a coluna 'NOME')
    colunas_datas = [col for col in df.columns if col != nome_col]

    # ---------------- CRIAÇÃO DA TABELA DE MÉTRICAS ----------------
    df_long = df.melt(id_vars=[nome_col], value_vars=colunas_datas,
                      var_name="DATA", value_name="STATUS")

    resumo = df_long.groupby([nome_col, "STATUS"]).size().unstack(
        fill_value=0).reset_index()

    # Garantir colunas
    for col in ["DSR", "FÉRIAS", "AFASTAMENTO MÉDICO", "SUSPENSO", "PRESENTE", "FALTA", "ATESTADO MÉDICO", "BANCO DE HORAS"]:
        if col not in resumo.columns:
            resumo[col] = 0

    resumo["TOTAL DIAS"] = resumo[["PRESENTE", "FALTA", "DSR", "FÉRIAS", "AFASTAMENTO MÉDICO", "SUSPENSO",
                                   "ATESTADO MÉDICO", "BANCO DE HORAS"]].sum(axis=1)
    resumo["% PRESENÇA"] = (
        (resumo["PRESENTE"] / resumo["TOTAL DIAS"]) * 100).round(2)

    # ---------------- CONTROLES DE EXIBIÇÃO ----------------
    st.sidebar.header("⚙️ Configurações de exibição")
    n_colunas = st.sidebar.slider(
        "Número de colunas (layout)", min_value=1, max_value=6, value=3)
    busca_nome = st.sidebar.text_input("🔎 Filtrar por nome")

    # Filtrar DataFrame conforme busca
    if busca_nome:
        resumo_display = resumo[resumo[nome_col].str.contains(
            busca_nome, case=False, na=False)].copy()
    else:
        resumo_display = resumo.copy()

    resumo_display = resumo_display.sort_values(
        "% PRESENÇA", ascending=False).reset_index(drop=True)

    # ---------------- HTML + CSS + JS PARA CARDS ----------------
    cards_html = """
    <style>
    .rt-dashboard { font-family: "Inter", "Segoe UI", Roboto, Arial, sans-serif; font-size:10pt; color:#222; }
    .cards-grid {
        display: grid;
        grid-template-columns: repeat(%d, 1fr);
        gap: 10px;
        align-items: start;
    }
    .card {
        border-radius: 8px;
        padding: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
        background: linear-gradient(180deg, #ffffff 0%%, #f7f9fc 100%%);
        border: 1px solid #e6eef6;
        transition: transform .12s ease, box-shadow .12s ease;
    }
    .card:hover {
        transform: translateY(-4px);
        box-shadow: 0 6px 18px rgba(0,0,0,0.12);
    }
    .card .nome { font-weight:700; font-size:10pt; margin-bottom:6px; color:#0b3d91; }
    .card .meta { display:flex; justify-content:space-between; margin:4px 0; }
    .meta .label { font-size:9pt; color:#555; }
    .meta .value { font-weight:700; font-size:10pt; }
    .badge { padding:4px 8px; border-radius:12px; font-size:9pt; color:white; display:inline-block; }
    .badge.green { background:#2ecc71; }
    .badge.yellow { background:#f1c40f; color:#222; }
    .badge.red { background:#e74c3c; }
    .small { font-size:9pt; color:#666; }
    .table-preview { width:100%%; border-collapse:collapse; margin-top:12px; font-size:9pt; }
    .table-preview th, .table-preview td { border:1px solid #e6eef6; padding:6px; text-align:center; }
    </style>

    <div class="rt-dashboard">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <div><strong>Relatório resumido</strong> — visual compacta</div>
        <div class="small">Font-size: 10pt · Colunas: %d · Registros: %d</div>
      </div>

      <div class="cards-grid">
    """ % (n_colunas, n_colunas, len(resumo_display))

    for _, r in resumo_display.iterrows():
        nome = html.escape(str(r[nome_col]))
        faltas = int(r["FALTA"])
        afastamento = int(r["AFASTAMENTO MÉDICO"])
        dsr = int(r["DSR"])
        ferias = int(r["FÉRIAS"])
        suspenso = int(r["SUSPENSO"])
        atestado = int(r["ATESTADO MÉDICO"])
        banco = int(r["BANCO DE HORAS"])
        presente = int(r["PRESENTE"])
        perc = float(r["% PRESENÇA"])

        if perc >= 85:
            badge = f'<span class="badge green">Presença: {perc}%</span>'
        elif perc >= 70:
            badge = f'<span class="badge yellow">Presença: {perc}%</span>'
        else:
            badge = f'<span class="badge red">Presença: {perc}%</span>'

        cards_html += f"""
        <div class="card" data-nome="{nome.lower()}">
            <div class="nome">{nome}</div>
            <div class="meta"><div class="label">Presentes</div><div class="value">{presente}</div></div>
            <div class="meta"><div class="label">DSR</div><div class="value">{dsr}</div></div>
            <div class="meta"><div class="label">Banco de Horas</div><div class="value">{banco}</div></div>
            <div class="meta"><div class="label">Atestados</div><div class="value">{atestado}</div></div>
            
            <div class="meta"><div class="label">Faltas</div><div class="value">{faltas}</div></div>
            
            <div class="meta"><div class="label">Férias</div><div class="value">{ferias}</div></div>
            <div class="meta"><div class="label">Afastamentos</div><div class="value">{afastamento}</div></div>
            <div class="meta"><div class="label">Suspensos</div><div class="value">{suspenso}</div></div>
            
           
            
            
            <div style="margin-top:8px;">{badge}</div>
        </div>
        """

    cards_html += "</div></div>"

    components.html(cards_html, height=520, scrolling=True)
    # ---------------- RESUMO GERAL AGREGADO ----------------
    total_faltas = resumo["FALTA"].sum()
    total_atestados = resumo["ATESTADO MÉDICO"].sum()
    total_banco = resumo["BANCO DE HORAS"].sum()
    media_presenca = resumo["% PRESENÇA"].mean().round(2)

    st.markdown(f"""
    <div style="background-color:#f0f4f8; padding:12px; border-radius:8px; margin-bottom:12px; font-size:11pt;">    
    📌 <strong>Resumo Geral dos Funcionários ID Logistics:</strong> &nbsp; 
    Faltas = <strong>{total_faltas}</strong> · 
    Atestados Médicos = <strong>{total_atestados}</strong> · 
    Banco de Horas = <strong>{total_banco}</strong> · 
    Presença Média = <strong>{media_presenca}%</strong>
    </div>
    """, unsafe_allow_html=True)
    # ---------------- EXPORTAÇÃO ----------------
    st.subheader("⬇️ Exportar Relatório")
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        resumo.to_excel(writer, index=False, sheet_name="Relatório")
    st.download_button(
        label="📥 Baixar em Excel",
        data=buffer.getvalue(),
        file_name="relatorio_frequencia.xlsx",
        mime="application/vnd.ms-excel"
    )

    def gerar_pdf(dataframe):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer)
        styles = getSampleStyleSheet()
        story = []
        story.append(Paragraph("Relatório de Frequência", styles["Title"]))
        story.append(Spacer(1, 12))
        tabela = [list(dataframe.columns)] + dataframe.values.tolist()
        t = Table(tabela, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b3d91")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dfeaf6")),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica")
        ]))
        story.append(t)
        doc.build(story)
        buffer.seek(0)
        return buffer

    pdf_buffer = gerar_pdf(resumo)
    st.download_button(
        label="📥 Baixar em PDF",
        data=pdf_buffer,
        file_name="relatorio_frequencia.pdf",
        mime="application/pdf"
    )
st.markdown(
    """
    <div style="text-align: center; font-size: 10px;">
        Copyright ©-2025 Direitos Autorais Desenvolvedor Rogério Ferreira
    </div>
    """,
    unsafe_allow_html=True
)
