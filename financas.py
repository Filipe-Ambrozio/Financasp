import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
import plotly.express as px

CAMINHO_ARQUIVO = "db_financas.json"

def carregar_dados():
    if not os.path.exists(CAMINHO_ARQUIVO):
        return []
    with open(CAMINHO_ARQUIVO, "r") as f:
        return json.load(f)

def salvar_dados(dados):
    with open(CAMINHO_ARQUIVO, "w") as f:
        json.dump(dados, f, indent=4)

def adicionar_lancamentos_repetidos(tipo, categoria, valor, data_inicial, repetir):
    dados = carregar_dados()
    for i in range(repetir):
        nova_data = (pd.to_datetime(data_inicial) + pd.DateOffset(months=i)).strftime("%Y-%m-%d")
        valor_final = -valor if tipo == "Débito" else valor
        dados.append({
            "tipo": tipo,
            "categoria": categoria,
            "valor": valor_final,
            "data": nova_data,
            "pago": False
        })
    salvar_dados(dados)

def excluir_lancamento_por_indices(indices):
    dados = carregar_dados()
    novos_dados = [item for i, item in enumerate(dados) if i not in indices]
    salvar_dados(novos_dados)

# --- Streamlit ---
st.set_page_config(layout="wide")
st.sidebar.title("Menu")
menu = st.sidebar.radio("", ["Cadastro", "Resumo Mensal", "Consulta por Categoria", "Gráfico"])

if menu == "Cadastro":
    st.title("Cadastro de Débito ou Crédito")
    tipo = st.selectbox("Tipo", ["Débito", "Crédito"])

    if tipo == "Débito":
        categoria = st.selectbox("Categoria", ["Internet", "Credcar", "Nubanck", "Escola", "Plano de Saúde", "Empréstimo", "Outro"])
    else:
        categoria = st.selectbox("Categoria", ["Salário1", "Salário2", "Férias", "Adicional"])

    valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
    data = st.date_input("Data")
    repetir = st.number_input("Repetir por quantos meses?", min_value=1, step=1, value=1)

    if st.button("Adicionar Lançamento"):
        adicionar_lancamentos_repetidos(tipo, categoria, valor, data, repetir)
        st.success("Lançamento(s) adicionado(s) com sucesso!")

elif menu == "Resumo Mensal":
    st.title("Resumo por Mês")
    dados = carregar_dados()
    if dados:
        df = pd.DataFrame(dados)
        df['data'] = pd.to_datetime(df['data'])
        df['ano_mes'] = df['data'].dt.to_period('M')

        mes_atual = datetime.today().strftime("%Y-%m")
        meses = df['ano_mes'].drop_duplicates().astype(str).sort_values(ascending=False)
        mes_escolhido = st.selectbox("Selecione o mês", meses, index=meses.tolist().index(mes_atual) if mes_atual in meses.tolist() else 0)

        df_mes = df[df['ano_mes'].astype(str) == mes_escolhido].copy()
        df_mes['data'] = df_mes['data'].dt.strftime('%d/%m/%Y')

        saldo = df_mes['valor'].sum()
        st.write(f"**Saldo no mês {mes_escolhido}: R$ {saldo:.2f}**")

        # --- Débitos ---
        st.subheader("Débitos")
        modificou = False
        for i, row in df_mes.iterrows():
            if row["tipo"] == "Débito":
                pago = row.get("pago", False)
                novo_pago = st.checkbox(f"✅ {row['data']} - {row['categoria']} - R$ {abs(row['valor']):.2f}", value=pago, key=f"chk_{i}")
                if novo_pago != pago:
                    dados[i]["pago"] = novo_pago
                    modificou = True
        if modificou:
            salvar_dados(dados)
            st.success("Status de pagamento atualizado.")

        # --- Créditos ---
        st.subheader("Créditos")
        indices_creditos = []
        for i, row in df_mes.iterrows():
            if row["tipo"] == "Crédito":
                st.markdown(f"💰 {row['data']} - {row['categoria']} - R$ {row['valor']:.2f}")
                if st.checkbox("Excluir", key=f"exc_{i}"):
                    indices_creditos.append(i)

        if indices_creditos:
            if st.button("Excluir Créditos Selecionados"):
                excluir_lancamento_por_indices(indices_creditos)
                st.success("Créditos excluídos com sucesso.")
                st.experimental_rerun()

        # --- Simulador ---
        sim = st.number_input("Simular crédito extra (R$)", min_value=0.0, format="%.2f")
        saldo_simulado = saldo + sim
        if saldo_simulado >= 0:
            st.success(f"Saldo simulado: R$ {saldo_simulado:.2f} — crédito suficiente.")
        else:
            st.error(f"Saldo simulado: R$ {saldo_simulado:.2f} — crédito insuficiente.")
    else:
        st.info("Nenhum dado cadastrado ainda.")

elif menu == "Consulta por Categoria":
    st.title("Consulta de Débitos por Categoria")
    dados = carregar_dados()

    if dados:
        df = pd.DataFrame(dados)
        df['data'] = pd.to_datetime(df['data'])
        df['ano'] = df['data'].dt.year
        df['mes'] = df['data'].dt.month

        df_debitos = df[df["tipo"] == "Débito"]
        categorias = sorted(df_debitos["categoria"].unique())

        if not categorias:
            st.warning("Nenhum lançamento de débito encontrado.")
        else:
            categoria = st.selectbox("Selecione a categoria", categorias)

            ano_atual = datetime.today().year
            anos = sorted(df_debitos['ano'].unique(), reverse=True)
            ano = st.selectbox("Ano", anos, index=anos.index(ano_atual) if ano_atual in anos else 0)

            meses_disponiveis = sorted(df_debitos[df_debitos['ano'] == ano]['mes'].unique())
            opcoes_mes = ["Todos os meses"] + [str(m) for m in meses_disponiveis]
            mes_selecionado = st.selectbox("Mês", opcoes_mes)

            df_filtrado = df_debitos[(df_debitos['categoria'] == categoria) & (df_debitos['ano'] == ano)]
            if mes_selecionado != "Todos os meses":
                df_filtrado = df_filtrado[df_filtrado['mes'] == int(mes_selecionado)]

            if df_filtrado.empty:
                st.info("Nenhum lançamento para essa combinação.")
            else:
                df_filtrado['data_str'] = df_filtrado['data'].dt.strftime('%d/%m/%Y')
                df_filtrado['pago'] = df_filtrado['pago'].fillna(False)
                total_restante = df_filtrado[~df_filtrado['pago']]['valor'].sum()
                st.info(f"🔔 Total a pagar (não pagos): R$ {abs(total_restante):.2f}")

                indices_selecionados = []
                selecionar_todos = st.checkbox("Selecionar todos")

                for i, (idx, row) in enumerate(df_filtrado.iterrows()):
                    label = f"{row['data_str']} | R$ {abs(row['valor']):.2f} | {'✅ Pago' if row['pago'] else '❌ Não pago'}"
                    if selecionar_todos or st.checkbox(label, key=f"sel_{idx}"):
                        indices_selecionados.append(idx)

                if indices_selecionados:
                    if st.button("Excluir selecionados"):
                        excluir_lancamento_por_indices(indices_selecionados)
                        st.success("Lançamentos excluídos com sucesso.")
                        st.experimental_rerun()
                else:
                    st.info("Selecione ao menos um lançamento para excluir.")
    else:
        st.info("Nenhum dado disponível.")

elif menu == "Gráfico":
    st.title("📊 Análise Gráfica")
    dados = carregar_dados()

    if dados:
        df = pd.DataFrame(dados)
        df['data'] = pd.to_datetime(df['data'])
        df['ano'] = df['data'].dt.year
        df['mes'] = df['data'].dt.strftime('%b')
        df['ano_mes'] = df['data'].dt.to_period('M').astype(str)

        # Gráfico 1: Saldo por mês no ano
        st.subheader("Saldo por Mês (Ano)")
        ano_sel = st.selectbox("Selecione o ano", sorted(df['ano'].unique(), reverse=True), key="ano_graf")
        df_ano = df[df['ano'] == ano_sel]
        saldo_mes = df_ano.groupby('mes')['valor'].sum().reindex(
            ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
        ).fillna(0).reset_index(name="Saldo")
        fig1 = px.bar(saldo_mes, x='mes', y='Saldo', text_auto='.2f', title=f"Saldo por Mês em {ano_sel}")
        st.plotly_chart(fig1, use_container_width=True)

        # Gráfico 2: Totais por Categoria por Mês
        st.subheader("Totais por Categoria (por Mês)")
        tipo = st.selectbox("Tipo", ["Débito", "Crédito"], key="tipo_graf")
        df_tipo = df[df['tipo'] == tipo]
        categorias = df_tipo['categoria'].unique()
        cat_sel = st.selectbox("Categoria", sorted(categorias))
        df_cat = df_tipo[df_tipo['categoria'] == cat_sel]
        total_mes = df_cat.groupby('mes')['valor'].sum().reindex(
            ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
        ).fillna(0).reset_index(name="Total")
        fig2 = px.bar(total_mes, x='mes', y='Total', text_auto='.2f', title=f"{cat_sel} - {tipo} por Mês")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Nenhum dado cadastrado ainda.")






#if __name__ == "__main__":
    #main()


#streamlit run financas.py
