
import streamlit as st
import gspread
from google.oauth2 import service_account
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Registro de Cuotas", layout="centered")

st.title("📋 Registro de Compras en Cuotas")

# Autenticación con Google Sheets desde st.secrets
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file",
         "https://www.googleapis.com/auth/drive"]

credentials = service_account.Credentials.from_service_account_info(
    st.secrets["google"], scopes=scope
)
client = gspread.authorize(credentials)

# Abrir la hoja de cálculo
sheet = client.open("Registro_Cuotas_Tarjetas").sheet1

# Formulario de carga
with st.form("cuotas_form"):
    fecha = st.date_input("Fecha de compra", value=datetime.today())
    comercio = st.text_input("Comercio")
    descripcion = st.text_input("Descripción (opcional)")
    monto_total = st.number_input("Monto total", min_value=0.0, step=100.0)
    cuotas = st.number_input("Cantidad de cuotas", min_value=1, step=1)
    tarjeta = st.selectbox("Tarjeta", ["Naranja", "Macro"])
    cuota_pagada = st.number_input("Cuota pagada (si ya abonaste alguna)", min_value=0, step=1)
    observaciones = st.text_area("Observaciones (opcional)")

    # Cálculo del monto por cuota y saldo restante
    monto_por_cuota = monto_total / cuotas
    saldo_pendiente = monto_total - (monto_por_cuota * cuota_pagada)

    st.markdown(f"💸 **Monto por cuota:** ${monto_por_cuota:.2f}")
    st.markdown(f"📉 **Saldo restante por pagar:** ${saldo_pendiente:.2f}")

    enviar = st.form_submit_button("Registrar")

    if enviar:
        nueva_fila = [
            fecha.strftime("%d/%m/%Y"),
            comercio,
            descripcion,
            f"{monto_total:.2f}",
            cuotas,
            tarjeta,
            cuota_pagada,
            observaciones
        ]
        sheet.append_row(nueva_fila)
        st.success("✅ Compra registrada con éxito.")

# Mostrar registros
st.subheader("🧾 Historial de compras")

data = sheet.get_all_records()
df = pd.DataFrame(data)

if not df.empty:
    def convertir_monto(valor):
        if isinstance(valor, str):
            valor = valor.replace(",", "").replace(".", ".")
        try:
            return float(valor)
        except:
            return 0.0

    df["Monto Total"] = df["Monto Total"].apply(convertir_monto)
    df["Cantidad de Cuotas"] = pd.to_numeric(df["Cantidad de Cuotas"], errors="coerce").fillna(1).astype(int)
    df["Cuota Pagada (N°)"] = pd.to_numeric(df["Cuota Pagada (N°)"], errors="coerce").fillna(0).astype(int)

    # Calcular columnas adicionales
    df["Monto por Cuota"] = df["Monto Total"] / df["Cantidad de Cuotas"]
    df["Saldo Restante"] = df["Monto Total"] - (df["Monto por Cuota"] * df["Cuota Pagada (N°)"])

    df["Fecha de Compra"] = pd.to_datetime(df["Fecha de Compra"], format="%d/%m/%Y", errors="coerce")

    # Filtros
    st.sidebar.header("🔍 Filtros")

    tarjeta_filtro = st.sidebar.selectbox("Filtrar por tarjeta", ["Todas"] + sorted(df["Tarjeta"].unique().tolist()))
    meses_disponibles = sorted(df["Fecha de Compra"].dropna().dt.to_period("M").astype(str).unique())
    mes_filtro = st.sidebar.selectbox("Filtrar por mes", ["Todos"] + meses_disponibles)

    if tarjeta_filtro != "Todas":
        df = df[df["Tarjeta"] == tarjeta_filtro]

    if mes_filtro != "Todos":
        periodo = pd.Period(mes_filtro, freq='M')
        df = df[df["Fecha de Compra"].dt.to_period("M") == periodo]

    # Mostrar resultados filtrados
    st.dataframe(df)

    # Mostrar totales
    total_saldo = df["Saldo Restante"].sum()
    st.markdown(f"### 💰 Total general pendiente: **${total_saldo:,.2f}**")

    st.markdown("### 💳 Total pendiente por tarjeta:")
    for tarjeta in df["Tarjeta"].unique():
        total_por_tarjeta = df[df["Tarjeta"] == tarjeta]["Saldo Restante"].sum()
        st.markdown(f"- **{tarjeta}**: ${total_por_tarjeta:,.2f}")

else:
    st.info("No hay registros cargados aún.")
