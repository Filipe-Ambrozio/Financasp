import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
from datetime import datetime

CAMINHO_ARQUIVO = "dados_financeiros.json"

# Funções utilitárias

def carregar_dados():
    if os.path.exists(CAMINHO_ARQUIVO):
        with open(CAMINHO_ARQUIVO, "r") as f:
            return json.load(f)
    return []

def salvar_dados(dados):
    with open(CAMINHO_ARQUIVO, "w") as f:
        json.dump(dados, f, indent=2, default=str)

def adicionar_lancamento(lancamento):
    dados = carregar_dados()
    dados.append(lancamento)
    salvar_dados(dados)

def excluir_lancamento_por_indices(indices):
    dados = carregar_dados()
    novos_dados = [item for i, item in enumerate(dados) if i not in indices]
    salvar_dados(novos_dados)

def atualizar_credito(indice, novo_valor, nova_descricao):
    dados = carregar_dados()
    dados[indice]['valor'] = novo_valor
    dados[indice]['descricao'] = nova_descricao
    salvar_dados(dados)

def excluir_credito(indice):
    dados = carregar_dados()
    del dados[indice]
    salvar_dados(dados)

def obter_nome_mes(numero_mes):
    return datetime(1900, numero_mes, 1).strftime('%b')

# Interface principal
st.sidebar.title("Menu")
menu = st.sidebar.selectbox("Selecione a opção", [
    "Novo Lançamento", "Consulta por Categoria", "Resumo por Mês", "Controle de Créditos", "Gráficos"])

if menu == "Novo Lançamento":
    st.title("Novo Lançamento")
    tipo = st.selectbox("Tipo", ["Débito", "Crédito"])
    valor = st.number_input("Valor", min_value=0.0, format="%.2f")
    descricao = st.text_input("Descrição")
    categoria = st.text_input("Categoria")
    data = st.date_input("Data")
    pago = st.checkbox("Pago", value=False)

    if st.button("Salvar"):
        lancamento = {
            "tipo": tipo,
            "valor": valor,
            "descricao": descricao,
            "categoria": categoria,
            "data": str(data),
            "pago": pago
        }
        adicionar_lancamento(lancamento)
        st.success("Lançamento salvo com sucesso!")

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
            anos_unicos = sorted(df_debitos['ano'].unique())
            opcoes_ano = ["Todos"] + [str(a) for a in anos_unicos]
            ano_selecionado = st.selectbox("Ano", opcoes_ano, index=opcoes_ano.index(str(ano_atual)) if str(ano_atual) in opcoes_ano else 0)

            if ano_selecionado != "Todos":
                df_debitos = df_debitos[df_debitos['ano'] == int(ano_selecionado)]

            meses_disponiveis = sorted(df_debitos['mes'].unique())
            opcoes_mes = ["Todos os meses"] + [str(m) for m in meses_disponiveis]
            mes_selecionado = st.selectbox("Mês", opcoes_mes)

            df_filtrado = df_debitos[df_debitos['categoria'] == categoria]
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

elif menu == "Resumo por Mês":
    st.title("Resumo por Mês")
    dados = carregar_dados()

    if dados:
        df = pd.DataFrame(dados)
        df['data'] = pd.to_datetime(df['data'])
        df['ano'] = df['data'].dt.year
        df['mes'] = df['data'].dt.month

        ano_atual = datetime.today().year
        ano_sel = st.selectbox("Selecione o ano", sorted(df['ano'].unique()), index=list(df['ano'].unique()).index(ano_atual))

        df_ano = df[df['ano'] == ano_sel]
        total_mes = df_ano.groupby(['mes', 'tipo'])['valor'].sum().reset_index()
        total_mes['mes_nome'] = total_mes['mes'].apply(obter_nome_mes)

        fig = px.bar(total_mes, x='mes_nome', y='valor', color='tipo', barmode='group', title="Resumo Financeiro por Mês")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhum dado disponível.")

elif menu == "Controle de Créditos":
    st.title("Controle de Créditos")
    dados = carregar_dados()

    df_creditos = pd.DataFrame(dados)
    df_creditos = df_creditos[df_creditos['tipo'] == 'Crédito']

    if not df_creditos.empty:
        for i, row in df_creditos.iterrows():
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                novo_valor = st.number_input(f"Valor", value=row['valor'], key=f"valor_{i}")
            with col2:
                nova_desc = st.text_input("Descrição", value=row['descricao'], key=f"desc_{i}")
            with col3:
                if st.button("Salvar", key=f"salvar_{i}"):
                    atualizar_credito(i, novo_valor, nova_desc)
                    st.success("Crédito atualizado.")

            if st.button("Excluir", key=f"excluir_{i}"):
                excluir_credito(i)
                st.success("Crédito excluído.")
                st.experimental_rerun()
    else:
        st.info("Nenhum crédito cadastrado.")

elif menu == "Gráficos":
    st.title("Gráficos Financeiros")
    dados = carregar_dados()

    if dados:
        df = pd.DataFrame(dados)
        df['data'] = pd.to_datetime(df['data'])
        df['ano'] = df['data'].dt.year
        df['mes'] = df['data'].dt.month
        df['mes_nome'] = df['mes'].apply(obter_nome_mes)

        ano_sel = st.selectbox("Selecione o ano", sorted(df['ano'].unique()))
        df_ano = df[df['ano'] == ano_sel]

        st.subheader("Totais por Tipo (por Mês)")
        total_tipo = df_ano.groupby(['mes_nome', 'tipo'])['valor'].sum().reset_index()
        meses_ordem = [obter_nome_mes(i) for i in range(1, 13)]
        total_tipo['mes_nome'] = pd.Categorical(total_tipo['mes_nome'], categories=meses_ordem, ordered=True)
        total_tipo = total_tipo.sort_values("mes_nome")

        fig = px.bar(total_tipo, x='mes_nome', y='valor', color='tipo', barmode='group')
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Totais por Categoria (por Mês)")
        tipo = st.selectbox("Tipo", ["Débito", "Crédito"], key="tipo_graf")
        df_tipo = df[df['tipo'] == tipo]
        categorias = df_tipo['categoria'].unique()
        cat_sel = st.selectbox("Categoria", sorted(categorias))

        df_cat = df_tipo[(df_tipo['categoria'] == cat_sel) & (df_tipo['ano'] == ano_sel)]
        total_mes = df_cat.groupby('mes_nome')['valor'].sum().reindex(meses_ordem).fillna(0).reset_index(name="Total")

        fig2 = px.bar(total_mes, x='mes_nome', y='Total', text_auto='.2f', title=f"{cat_sel} - {tipo} por Mês ({ano_sel})")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Nenhum dado disponível para exibir gráficos.")
