
import streamlit as st
import gspread
from google.oauth2 import service_account
import pandas as pd

st.set_page_config(page_title="Gestión de cuotas", layout="wide")
st.title("💳 Gestión de cuotas con tarjeta")

# Autenticación
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file",
         "https://www.googleapis.com/auth/drive"]

credentials = service_account.Credentials.from_service_account_info(
    st.secrets["google"], scopes=scope
)
client = gspread.authorize(credentials)
sheet = client.open("Registro_Cuotas_Tarjetas").sheet1

# Obtener datos
data = sheet.get_all_records()
df = pd.DataFrame(data)

# Conversión de columnas
df["Monto Total"] = pd.to_numeric(df["Monto Total"], errors="coerce").fillna(0.0)
df["Cantidad de Cuotas"] = pd.to_numeric(df["Cantidad de Cuotas"], errors="coerce").fillna(1).astype(int)
df["Cuota Pagada (N°)"] = pd.to_numeric(df.get("Cuota Pagada (N°)", 0), errors="coerce").fillna(0).astype(int)

# Selección de modo
modo = st.sidebar.radio("Seleccionar vista", ["📋 Ver cuotas", "✅ Marcar cuota como pagada", "✏️ Editar compra", "🗑️ Eliminar compra", "📊 Resumen mensual y gráficos"])

if modo == "📋 Ver cuotas":
    st.subheader("📋 Cuotas registradas")
    st.dataframe(df)

elif modo == "✅ Marcar cuota como pagada":
    st.subheader("✅ Marcar cuotas como pagadas")

    # Filtro por tarjeta
    st.sidebar.header("🎴 Filtro de tarjeta")
    tarjetas = df["Tarjeta"].unique().tolist()
    tarjeta_sel = st.sidebar.selectbox("Seleccioná la tarjeta", tarjetas)

    df_filtrado = df[df["Tarjeta"] == tarjeta_sel].copy()
    df_filtrado.reset_index(drop=True, inplace=True)

    df_filtrado["Monto por Cuota"] = df_filtrado["Monto Total"] / df_filtrado["Cantidad de Cuotas"]
    df_filtrado["Saldo Restante"] = df_filtrado["Monto Total"] - df_filtrado["Monto por Cuota"] * df_filtrado["Cuota Pagada (N°)"]

    st.write(f"💳 Cuotas registradas con **{tarjeta_sel}**")

    for idx, row in df_filtrado.iterrows():
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"📅 **{row['Fecha de Compra']}** – 🏪 *{row['Comercio']}*")
            st.write(f"💵 Total: ${row['Monto Total']:.2f} – Cuotas: {row['Cantidad de Cuotas']}")
            st.write(f"✅ Cuotas pagadas: {row['Cuota Pagada (N°)']} / {row['Cantidad de Cuotas']}")
            st.write(f"📉 Saldo restante: ${row['Saldo Restante']:.2f}")
        with col2:
            if row["Cuota Pagada (N°)"] < row["Cantidad de Cuotas"]:
                if st.button(f"➕ Marcar cuota pagada #{idx}", key=idx):
                    nueva_cuota = int(row["Cuota Pagada (N°)"]) + 1
                    sheet.update_cell(idx + 2, df.columns.get_loc("Cuota Pagada (N°)") + 1, nueva_cuota)
                    st.success(f"✔ Se marcó 1 cuota más como pagada para '{row['Comercio']}'")
                    st.experimental_rerun()
            else:
                st.success("✅ Compra completamente pagada")

elif modo == "✏️ Editar compra":
    st.subheader("✏️ Editar una compra existente")

    if df.empty:
        st.warning("No hay compras para editar.")
        st.stop()

    df.reset_index(drop=True, inplace=True)
    opciones = [f"{i+1}. {row['Fecha de Compra']} - {row['Comercio']} (${row['Monto Total']})" for i, row in df.iterrows()]
    seleccion = st.selectbox("Seleccioná una compra para editar:", opciones)
    idx = int(seleccion.split(".")[0]) - 1
    row = df.loc[idx]

    with st.form("form_editar"):
        fecha = st.text_input("Fecha de Compra", row["Fecha de Compra"])
        comercio = st.text_input("Comercio", row["Comercio"])
        monto_total = st.number_input("Monto Total", value=row["Monto Total"], step=100.0)
        tarjeta = st.selectbox("Tarjeta", df["Tarjeta"].unique().tolist(), index=df["Tarjeta"].tolist().index(row["Tarjeta"]))
        cant_cuotas = st.number_input("Cantidad de Cuotas", value=row["Cantidad de Cuotas"], step=1, min_value=1)
        cuotas_pagadas = st.number_input("Cuotas Pagadas", value=row["Cuota Pagada (N°)"], step=1, min_value=0)

        submitted = st.form_submit_button("💾 Guardar cambios")

        if submitted:
            errores = []
            if cuotas_pagadas > cant_cuotas:
                errores.append("❌ Las cuotas pagadas no pueden superar la cantidad de cuotas.")
            if comercio.strip() == "":
                errores.append("❌ El comercio no puede estar vacío.")
            if fecha.strip() == "":
                errores.append("❌ La fecha no puede estar vacía.")

            if errores:
                for e in errores:
                    st.error(e)
            else:
                sheet.update_cell(idx + 2, df.columns.get_loc("Fecha de Compra") + 1, fecha)
                sheet.update_cell(idx + 2, df.columns.get_loc("Comercio") + 1, comercio)
                sheet.update_cell(idx + 2, df.columns.get_loc("Monto Total") + 1, monto_total)
                sheet.update_cell(idx + 2, df.columns.get_loc("Tarjeta") + 1, tarjeta)
                sheet.update_cell(idx + 2, df.columns.get_loc("Cantidad de Cuotas") + 1, cant_cuotas)
                sheet.update_cell(idx + 2, df.columns.get_loc("Cuota Pagada (N°)") + 1, cuotas_pagadas)
                st.success("✔ Compra actualizada correctamente")
                st.experimental_rerun()

elif modo == "🗑️ Eliminar compra":
    st.subheader("🗑️ Eliminar una compra")

    if df.empty:
        st.warning("No hay compras para eliminar.")
        st.stop()

    df.reset_index(drop=True, inplace=True)
    opciones = [f"{i+1}. {row['Fecha de Compra']} - {row['Comercio']} (${row['Monto Total']})" for i, row in df.iterrows()]
    seleccion = st.selectbox("Seleccioná una compra para eliminar:", opciones)
    idx = int(seleccion.split(".")[0]) - 1
    row = df.loc[idx]

    st.warning(f"¿Estás seguro que querés eliminar la compra del {row['Fecha de Compra']} en {row['Comercio']}?")
    if st.button("❌ Confirmar eliminación"):
        sheet.delete_rows(idx + 2)
        st.success("✔ Compra eliminada correctamente")
        st.experimental_rerun()

elif modo == "📊 Resumen mensual y gráficos":
    st.subheader("📊 Resumen mensual de cuotas")

    df["Fecha de Compra"] = pd.to_datetime(df["Fecha de Compra"], errors="coerce", dayfirst=True)
    df["Mes"] = df["Fecha de Compra"].dt.to_period("M").astype(str)

    resumen = df.groupby(["Mes", "Tarjeta"]).agg({
        "Monto Total": "sum",
        "Cantidad de Cuotas": "sum",
        "Cuota Pagada (N°)": "sum"
    }).reset_index()

    resumen["Saldo Pendiente"] = (resumen["Cantidad de Cuotas"] - resumen["Cuota Pagada (N°)"])
    resumen = resumen.sort_values("Mes", ascending=False)

    st.dataframe(resumen)

    st.markdown("### 📈 Monto Total por Mes")
    chart_data = resumen.groupby("Mes")["Monto Total"].sum().reset_index()
    st.bar_chart(chart_data.set_index("Mes"))

    st.markdown("### 🟠 Cuotas pagadas vs totales por Mes")
    cuotas_chart = resumen.groupby("Mes")[["Cantidad de Cuotas", "Cuota Pagada (N°)"]].sum()
    st.line_chart(cuotas_chart)
