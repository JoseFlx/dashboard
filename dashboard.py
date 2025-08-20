import streamlit as st
import pandas as pd
import plotly.express as px
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io
import matplotlib.pyplot as plt

# ===============================
# Funções auxiliares
# ===============================
def format_timedelta(td):
    if pd.isnull(td):
        return "00:00:00"
    total_seconds = int(td.total_seconds())
    horas = total_seconds // 3600
    minutos = (total_seconds % 3600) // 60
    segundos = total_seconds % 60
    return f"{horas:02d}:{minutos:02d}:{segundos:02d}"

def calcular_metricas(df, agente=None):
    if agente:
        df = df[df['Agente'] == agente]
    tma = df["Tempo em Atendimento"].mean() if "Tempo em Atendimento" in df.columns else pd.Timedelta(0)
    tme = df["Tempo em Espera"].mean() if "Tempo em Espera" in df.columns else pd.Timedelta(0)
    qtd = len(df)
    return {"TMA": format_timedelta(tma), "TME": format_timedelta(tme), "Qtd_Atendimentos": qtd}

def gerar_pdf(df, metricas_gerais):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("RELATÓRIO DE ATENDIMENTO - CALL CENTER", styles['Title']))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Empresa: Nevoli Telecom", styles['Normal']))
    elements.append(Paragraph("Setor: Suporte Técnico / Atendimento", styles['Normal']))
    elements.append(Paragraph("Relatório referente ao desempenho dos agentes.", styles['Normal']))
    elements.append(Spacer(1, 20))

    # KPIs gerais
    elements.append(Paragraph("Indicadores Gerais", styles['Heading2']))
    data = [["Métrica", "Valor"],
            ["Tempo Médio de Atendimento (TMA)", metricas_gerais["TMA"]],
            ["Tempo Médio de Espera (TME)", metricas_gerais["TME"]],
            ["Quantidade de Atendimentos", metricas_gerais["Qtd_Atendimentos"]]]
    tabela = Table(data, hAlign="LEFT")
    tabela.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')]))
    elements.append(tabela)
    elements.append(Spacer(1, 20))

    # KPIs por agente
    elements.append(Paragraph("Indicadores por Agente", styles['Heading2']))
    data = [["Agente", "TMA", "TME", "Qtd. Atendimentos"]]
    for agente in df['Agente'].unique():
        if agente == "SYNTESIS - Olivia Bot":
            continue
        m = calcular_metricas(df, agente)
        data.append([agente, m["TMA"], m["TME"], m["Qtd_Atendimentos"]])
    tabela = Table(data, hAlign="LEFT")
    tabela.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')]))
    elements.append(tabela)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ===============================
# Interface Streamlit
# ===============================
st.set_page_config(page_title="Dashboard Call Center", layout="wide")
st.sidebar.title("📊 Navegação")

pagina = st.sidebar.radio("Ir para:", ["Geral", "Individual", "Ranking", "Relatório", "VOIP PABX"])
uploaded_file = st.sidebar.file_uploader("📂 Envie o arquivo CSV do Chat", type=["csv"])

# ===============================
# Dashboard Chat
# ===============================
if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=";", encoding="latin-1")

    # Mapear colunas
    col_map = {"Nome do Agente": "Agente",
               "Tempo em Atendimento": "Tempo em Atendimento",
               "Tempo em Espera na Fila": "Tempo em Espera",
               "Data Inicial": "Data Inicial",
               "Hora Inicial": "Hora Inicial"}
    df = df.rename(columns=col_map)

    # Converter tempos
    for col in ["Tempo em Atendimento", "Tempo em Espera"]:
        if col in df.columns:
            df[col] = pd.to_timedelta(df[col], errors='coerce')

    # Converter datas e hora
    if 'Data Inicial' in df.columns:
        df['Data Inicial'] = pd.to_datetime(df['Data Inicial'], errors='coerce')
    if 'Hora Inicial' in df.columns:
        df['Hora_Inicio'] = pd.to_datetime(df['Hora Inicial'], errors='coerce').dt.hour

    # -----------------------
    # Aba Geral
    # -----------------------
    if pagina == "Geral":
        st.title("📈 Dashboard Geral")
        metricas = calcular_metricas(df)
        col1, col2, col3 = st.columns(3)
        col1.metric("⏱️ TMA", metricas["TMA"])
        col2.metric("⌛ TME", metricas["TME"])
        col3.metric("📞 Atendimentos", metricas["Qtd_Atendimentos"])

        # Gráfico geral por agente
        df_geral = df.groupby("Agente").size().reset_index(name="Qtd_Atendimentos").sort_values("Qtd_Atendimentos", ascending=False)
        fig = px.bar(df_geral, x="Agente", y="Qtd_Atendimentos",
                     title="Distribuição de Atendimentos por Agente",
                     text="Qtd_Atendimentos", height=400, color="Qtd_Atendimentos")
        fig.update_traces(textposition='outside')
        fig.update_layout(xaxis_tickangle=-45, yaxis_title="Atendimentos", xaxis_title="Agente", coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

        # Atendimentos por horário
        if 'Hora_Inicio' in df.columns:
            df_hora = df.groupby('Hora_Inicio').size().reset_index(name='Qtd_Atendimentos')
            fig_hora = px.bar(df_hora, x='Hora_Inicio', y='Qtd_Atendimentos',
                              title="Atendimentos por Horário", text='Qtd_Atendimentos', height=350, color='Qtd_Atendimentos')
            fig_hora.update_traces(textposition='outside')
            fig_hora.update_layout(xaxis_title="Hora do Dia", yaxis_title="Qtd. Atendimentos", coloraxis_showscale=False)
            st.plotly_chart(fig_hora, use_container_width=True)

        st.write("### 📋 Detalhamento dos Atendimentos")
        st.dataframe(df[["Agente", "Data Inicial", "Hora Inicial", "Tempo em Atendimento", "Tempo em Espera"]])

    # -----------------------
    # Aba Individual
    # -----------------------
    elif pagina == "Individual":
        st.title("👤 Dashboard Individual por Agente")
        agente = st.selectbox("Selecione o Agente", df['Agente'].unique())
        df_agente = df[df["Agente"] == agente]
        metricas = calcular_metricas(df, agente)
        col1, col2, col3 = st.columns(3)
        col1.metric("⏱️ TMA", metricas["TMA"])
        col2.metric("⌛ TME", metricas["TME"])
        col3.metric("📞 Atendimentos", metricas["Qtd_Atendimentos"])

        st.write(f"### 📋 Detalhamento de {agente}")
        st.dataframe(df_agente[["Data Inicial", "Hora Inicial", "Tempo em Atendimento", "Tempo em Espera"]])

    # -----------------------
    # Aba Ranking
    # -----------------------
    elif pagina == "Ranking":
        st.title("🏆 Ranking dos Agentes")
        df_rank = df[df['Agente'] != "SYNTESIS - Olivia Bot"]
        df_rank = df_rank.groupby("Agente").agg({"Tempo em Atendimento": "mean", "Tempo em Espera": "mean"}).reset_index()
        df_rank["Qtd_Atendimentos"] = df.groupby("Agente").size().reindex(df_rank['Agente']).values
        df_rank["TMA"] = df_rank["Tempo em Atendimento"].apply(format_timedelta)
        df_rank["TME"] = df_rank["Tempo em Espera"].apply(format_timedelta)

        st.write("### 📞 Top 3 - Mais Atendimentos")
        st.dataframe(df_rank.sort_values("Qtd_Atendimentos", ascending=False).head(3)[["Agente", "Qtd_Atendimentos"]])
        st.write("### 📉 Top 3 - Menos Atendimentos")
        st.dataframe(df_rank.sort_values("Qtd_Atendimentos", ascending=True).head(3)[["Agente", "Qtd_Atendimentos"]])
        st.write("### ⏱️ Top 3 - Menor TMA")
        st.dataframe(df_rank.sort_values("Tempo em Atendimento", ascending=True).head(3)[["Agente", "TMA"]])
        st.write("### ⏱️ Top 3 - Maior TMA")
        st.dataframe(df_rank.sort_values("Tempo em Atendimento", ascending=False).head(3)[["Agente", "TMA"]])
        st.write("### ⌛ Top 3 - Menor TME")
        st.dataframe(df_rank.sort_values("Tempo em Espera", ascending=True).head(3)[["Agente", "TME"]])
        st.write("### ⌛ Top 3 - Maior TME")
        st.dataframe(df_rank.sort_values("Tempo em Espera", ascending=False).head(3)[["Agente", "TME"]])

    # -----------------------
    # Aba Relatório
    # -----------------------
    elif pagina == "Relatório":
        st.title("📄 Gerar Relatório PDF")
        metricas_gerais = calcular_metricas(df)
        if st.button("📥 Gerar PDF"):
            pdf_file = gerar_pdf(df, metricas_gerais)
            st.download_button("Download Relatório PDF", pdf_file, file_name="relatorio_atendimento.pdf")

# ===============================
# Aba VOIP PABX
# ===============================
elif pagina == "VOIP PABX":
    st.title("📞 Dashboard VOIP PABX")
    uploaded_pabx = st.file_uploader("📂 Envie o relatório do PABX", type=["csv"])

    if uploaded_pabx:
        # Leitura do CSV
        df_voip = pd.read_csv(uploaded_pabx, sep=";", encoding="latin-1")

        # Normalizar nomes de colunas (remove espaços extras)
        df_voip.columns = [col.strip().replace('"','').replace('ï»¿','') for col in df_voip.columns]



        # Verificação de coluna essencial
        if 'Agente' not in df_voip.columns:
            st.error(f"Coluna 'Agente' não encontrada. Colunas disponíveis: {df_voip.columns.tolist()}")
            st.stop()

        # Converter colunas de tempo
        tempo_cols = [
            "Tempo Total Trabalhado", "Tempo Total em Pausa", "Tempo Total Deslogado", 
            "Tempo Total Disponível", "Tempo Total Falado (Entrada)", "Tempo Total Falado (Saída)", 
            "Tempo Total Falado", "Tempo Total Ocioso", "Tempo Total Atendimento (Entrada)", 
            "Tempo Total Atendimento (Saída)", "Tempo Disponível Entre Chamadas", 
            "TMA (Entrada)", "TMA (Saída)"
        ]
        for col in tempo_cols:
            if col in df_voip.columns:
                df_voip[col] = pd.to_timedelta(df_voip[col], errors='coerce')

        # Garantir colunas de chamadas
        for col in ["Total Entrada (Atendidas)", "Total Entrada (Perdidas)", "Total Saida (Atendidas)"]:
           if col in df_voip.columns:
             df_voip[col] = pd.to_numeric(df_voip[col], errors='coerce').fillna(0)

        # Métricas principais
        metricas_voip = {
            "Total Agentes": df_voip['Agente'].nunique(),
            "Total Chamadas Atendidas": df_voip["Total Entrada (Atendidas)"].sum() + df_voip["Total Saida (Atendidas)"].sum(),
            "Total Chamadas Perdidas": df_voip["Total Entrada (Perdidas)"].sum(),
            "Média TMA Entrada": format_timedelta(df_voip["TMA (Entrada)"].mean() if "TMA (Entrada)" in df_voip.columns else pd.Timedelta(0)),
            "Média TMA Saída": format_timedelta(df_voip["TMA (Saída)"].mean() if "TMA (Saída)" in df_voip.columns else pd.Timedelta(0))
        }

        # Exibir KPIs
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("👥 Total Agentes", metricas_voip["Total Agentes"])
        col2.metric("📞 Chamadas Atendidas", metricas_voip["Total Chamadas Atendidas"])
        col3.metric("❌ Chamadas Perdidas", metricas_voip["Total Chamadas Perdidas"])
        col4.metric("⏱️ TMA Entrada", metricas_voip["Média TMA Entrada"])
        col5.metric("⏱️ TMA Saída", metricas_voip["Média TMA Saída"])

        # Detalhamento por agente
        display_cols = [
            "Agente", "Ramal", "Fila", "Tempo Total Trabalhado", "Tempo Total Disponível",
            "TOTAL ENTRADA (ATENDIDAS)", "TOTAL ENTRADA (PERDIDAS)", "TOTAL SAIDA (ATENDIDAS)",
            "TMA (Entrada)", "TMA (Saída)"
        ]
        df_display = df_voip[[col for col in display_cols if col in df_voip.columns]].sort_values("Agente")
        st.write("### 📋 Detalhamento por Agente")
        st.dataframe(df_display)

        # Gráficos: Chamadas atendidas
        df_plot = df_voip.groupby("Agente")[["Total Entrada (Atendidas)", "Total Saida (Atendidas)"]].sum().reset_index()
        df_plot["Total Atendidas"] = df_plot["Total Entrada (Atendidas)"] + df_plot["Total Saida (Atendidas)"]
        df_plot = df_plot.sort_values("Total Atendidas", ascending=True)
        plt.figure(figsize=(6,4))
        plt.barh(df_plot["Agente"], df_plot["Total Entrada (Atendidas)"], color="#4da6ff")
        plt.title("Chamadas Atendidas por Agente")
        plt.xlabel("Qtd. Atendidas")
        plt.tight_layout()
        st.pyplot(plt)
        plt.close()

        # Gráficos: TMA Entrada
        if "TMA (Entrada)" in df_voip.columns:
            

            plt.figure(figsize=(5,3))
            plt.barh(df_plot["Agente"], df_plot["Total Atendidas"], color="#4da6ff")
            plt.title("Chamadas Atendidas por Agente")
            plt.xlabel("Qtd. Atendidas")
            plt.tight_layout()
            st.pyplot(plt)
            plt.close()