import streamlit as st
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from motor_financiero import analisis_completo, sugerir_inversiones
import anthropic
import json
import requests
import yfinance as yf
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE LA APP
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Asesor Financiero Estudiantil",
    page_icon="💰",
    layout="wide"
)

# ─────────────────────────────────────────────
# TASAS EN TIEMPO REAL
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600)
def obtener_tasas_cetes():
    series = {
        "28 días":  "SF43936",
        "91 días":  "SF43939",
        "182 días": "SF43942",
        "364 días": "SF43945",
    }
    token = "db3a7d16d18e41d9ee98d36fbab7a9e785d74b1e0c3b47eabe4c7c96b4adae5a"
    tasas = {}
    fecha_fin = datetime.today().strftime("%Y-%m-%d")
    fecha_ini = (datetime.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    try:
        for plazo, serie in series.items():
            url = f"https://www.banxico.org.mx/SieAPIRest/service/v1/series/{serie}/datos/{fecha_ini}/{fecha_fin}?token={token}"
            r = requests.get(url, timeout=8)
            datos = r.json()
            valores = datos["bmx"]["series"][0]["datos"]
            ultimo = [v for v in valores if v["dato"] != "N/E"][-1]
            tasas[plazo] = {"tasa": float(ultimo["dato"]), "fecha": ultimo["fecha"]}
    except:
        tasas = {
            "28 días":  {"tasa": 6.54, "fecha": "dato de respaldo"},
            "91 días":  {"tasa": 6.49, "fecha": "dato de respaldo"},
            "182 días": {"tasa": 6.74, "fecha": "dato de respaldo"},
            "364 días": {"tasa": 7.17, "fecha": "dato de respaldo"},
        }
    return tasas

@st.cache_data(ttl=86400)
def obtener_inflacion():
    try:
        token = "db3a7d16d18e41d9ee98d36fbab7a9e785d74b1e0c3b47eabe4c7c96b4adae5a"
        url = f"https://www.banxico.org.mx/SieAPIRest/service/v1/series/SP74625/datos/oportuno?token={token}"
        r = requests.get(url, timeout=8)
        datos = r.json()
        valores = datos["bmx"]["series"][0]["datos"]
        ultimo = [v for v in valores if v["dato"] != "N/E"][-1]
        return {"inflacion": float(ultimo["dato"]), "fecha": ultimo["fecha"]}
    except:
        return {"inflacion": 3.55, "fecha": "dato de respaldo"}

@st.cache_data(ttl=3600)
def obtener_rendimientos_etfs():
    etfs = {
        "VOO":        "Vanguard S&P 500",
        "QQQ":        "Invesco Nasdaq-100",
        "NAFTRAC.MX": "NAFTRAC (IPC México)"
    }
    resultados = {}
    try:
        for ticker, nombre in etfs.items():
            datos = yf.download(ticker, period="3y", progress=False, auto_adjust=True)
            if datos.empty:
                raise ValueError(f"Sin datos para {ticker}")
            precio_inicial = float(datos["Close"].iloc[0])
            precio_final   = float(datos["Close"].iloc[-1])
            rendimiento_anual = ((precio_final / precio_inicial) ** (1/3) - 1) * 100
            resultados[ticker] = {
                "nombre": nombre,
                "rendimiento_anual": round(rendimiento_anual, 2),
                "precio_actual": round(precio_final, 2),
                "fecha": datos.index[-1].strftime("%d/%m/%Y")
            }
    except:
        resultados = {
            "VOO":        {"nombre": "Vanguard S&P 500",    "rendimiento_anual": 13.5, "precio_actual": None, "fecha": "dato de respaldo"},
            "QQQ":        {"nombre": "Invesco Nasdaq-100",  "rendimiento_anual": 15.0, "precio_actual": None, "fecha": "dato de respaldo"},
            "NAFTRAC.MX": {"nombre": "NAFTRAC (IPC México)","rendimiento_anual": 10.5, "precio_actual": None, "fecha": "dato de respaldo"},
        }
    return resultados

# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────
MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
         "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

MESES_VACACIONALES = {
    "Diciembre": "🏖️ Vacaciones decembrinas — considera gastos extra de temporada",
    "Enero":     "📚 Inicio de semestre — gastos escolares altos (inscripción, libros)",
    "Julio":     "🏖️ Vacaciones de verano — posible reducción de ingresos variables",
    "Agosto":    "📚 Inicio de semestre — gastos escolares altos (inscripción, materiales)",
}

CATEGORIAS_EGRESO = [
    "Renta", "Comida (despensa)", "Comida (cafetería/salidas)",
    "Transporte", "Colegiatura / inscripción", "Libros y papelería",
    "Material escolar", "Salud", "Servicios (internet, celular)",
    "Entretenimiento", "Ropa", "Otros"
]

CATEGORIAS_NECESARIAS = {
    "Renta", "Comida (despensa)", "Transporte",
    "Colegiatura / inscripción", "Libros y papelería",
    "Material escolar", "Salud", "Servicios (internet, celular)"
}

# ─────────────────────────────────────────────
# ESTILO OSCURO PARA GRÁFICAS
# ─────────────────────────────────────────────
BG_GRAFICA  = "#0D3A1C"   # fondo de figura — verde muy oscuro
BG_EJE      = "#114722"   # fondo de ejes — verde oscuro (igual al fondo de la app)
TEXT_COLOR  = "#F0F0F0"   # blanco hueso para todo el texto
GRID_COLOR  = "#1E6B35"   # verde medio para la grilla

def estilo_oscuro(fig, *axes):
    """Aplica tema oscuro consistente a una figura y sus ejes."""
    fig.patch.set_facecolor(BG_GRAFICA)
    for ax in axes:
        ax.set_facecolor(BG_EJE)
        ax.tick_params(colors=TEXT_COLOR)
        ax.xaxis.label.set_color(TEXT_COLOR)
        ax.yaxis.label.set_color(TEXT_COLOR)
        ax.title.set_color(TEXT_COLOR)
        for spine in ax.spines.values():
            spine.set_edgecolor(GRID_COLOR)
        ax.tick_params(axis="both", colors=TEXT_COLOR)
        legend = ax.get_legend()
        if legend:
            legend.get_frame().set_facecolor(BG_GRAFICA)
            legend.get_frame().set_edgecolor(GRID_COLOR)
            for text in legend.get_texts():
                text.set_color(TEXT_COLOR)

SYSTEM_PROMPT = """
Eres un asesor financiero educativo para estudiantes universitarios en México.
El estudiante ya llenó su plantilla financiera y el sistema generó su análisis completo.
Tu rol ahora es responder preguntas adicionales sobre su situación financiera de forma
clara, amigable y sin tecnicismos. Usa los datos del análisis que ya se mostró para
dar respuestas personalizadas. Siempre termina con:
'Recuerda que esto es orientación educativa, no asesoría financiera profesional.'
"""

# ─────────────────────────────────────────────
# ESTADO DE SESIÓN
# ─────────────────────────────────────────────
if "etapa" not in st.session_state:
    st.session_state.etapa = "plantilla"  # "plantilla" o "analisis"
if "resultado" not in st.session_state:
    st.session_state.resultado = None
if "historial_chat" not in st.session_state:
    st.session_state.historial_chat = []
if "mensajes_chat" not in st.session_state:
    st.session_state.mensajes_chat = []

client = anthropic.Anthropic(api_key="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")

# ══════════════════════════════════════════════════════════
# ETAPA 1 — PLANTILLA
# ══════════════════════════════════════════════════════════
if st.session_state.etapa == "plantilla":

    st.title("💰 Asesor Financiero para Estudiantes")
    st.caption("Llena tu plantilla financiera y obtén un análisis personalizado.")

    st.divider()

    # ── SECCIÓN 1: Horizonte de planeación ──
    st.subheader("📅 Horizonte de planeación")
    col1, col2 = st.columns(2)
    with col1:
        anios_planeacion = st.selectbox(
            "¿Para cuánto tiempo quieres planear?",
            options=[1, 2, 3, 4],
            format_func=lambda x: f"{x} año{'s' if x > 1 else ''}"
        )
    with col2:
        mes_inicio = st.selectbox("Mes de inicio", options=MESES, index=datetime.today().month - 1)

    # Advertencia si el mes es vacacional
    if mes_inicio in MESES_VACACIONALES:
        st.info(f"ℹ️ {MESES_VACACIONALES[mes_inicio]}")

    st.divider()

    # ── SECCIÓN 2: Ingresos ──
    st.subheader("📥 Ingresos mensuales")
    st.caption("Agrega todas tus fuentes de ingreso. Cada una puede tener su propio día de cobro.")

    if "filas_ingreso" not in st.session_state:
        st.session_state.filas_ingreso = [
            {"fuente": "Beca", "tipo": "fijo", "monto": 0.0, "dia_cobro": 1},
            {"fuente": "Apoyo familiar", "tipo": "fijo", "monto": 0.0, "dia_cobro": 1},
        ]

    ingresos_validos = []
    filas_a_eliminar = []

    # Headers
    hc1, hc2, hc3, hc4, hc5 = st.columns([3, 2, 2, 1, 1])
    hc1.caption("**Fuente de ingreso**")
    hc2.caption("**Tipo**")
    hc3.caption("**Monto mensual ($)**")
    hc4.caption("**Día de cobro**")
    hc5.caption("")

    for i, fila in enumerate(st.session_state.filas_ingreso):
        col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 1])
        with col1:
            fuente = st.text_input("Fuente", value=fila["fuente"],
                                   key=f"ing_fuente_{i}", label_visibility="collapsed")
        with col2:
            tipo = st.selectbox("Tipo", ["fijo", "variable"],
                                index=0 if fila["tipo"] == "fijo" else 1,
                                key=f"ing_tipo_{i}", label_visibility="collapsed")
        with col3:
            monto = st.number_input("Monto ($)", min_value=0.0, value=fila["monto"], step=100.0,
                                    key=f"ing_monto_{i}", label_visibility="collapsed")
        with col4:
            dia_cobro_fila = st.number_input("Día", min_value=1, max_value=31,
                                             value=fila.get("dia_cobro", 1),
                                             key=f"ing_dia_{i}", label_visibility="collapsed")
        with col5:
            if st.button("🗑️", key=f"del_ing_{i}", help="Eliminar fila"):
                filas_a_eliminar.append(i)

        if fuente and monto > 0:
            ingresos_validos.append({
                "fuente":    fuente,
                "tipo":      tipo,
                "monto":     monto,
                "dia_cobro": int(dia_cobro_fila)
            })

    for i in sorted(filas_a_eliminar, reverse=True):
        st.session_state.filas_ingreso.pop(i)
        st.rerun()

    if st.button("➕ Agregar ingreso"):
        st.session_state.filas_ingreso.append({"fuente": "", "tipo": "fijo", "monto": 0.0, "dia_cobro": 1})
        st.rerun()

    # Indicador de meses vacacionales para ingresos
    st.caption("💡 Si tus ingresos cambian en meses vacacionales (julio, agosto, diciembre, enero), usa el tipo 'variable' y refleja el promedio mensual.")

    st.divider()

    # ── SECCIÓN 3: Egresos ──
    st.subheader("📤 Egresos mensuales")
    st.caption("Registra todos tus gastos. Los gastos escolares y de papelería ya están incluidos como sugerencia.")

    if "filas_egreso" not in st.session_state:
        st.session_state.filas_egreso = [
            {"categoria": "Renta",                   "descripcion": "", "monto": 0.0},
            {"categoria": "Comida (despensa)",        "descripcion": "", "monto": 0.0},
            {"categoria": "Comida (cafetería/salidas)","descripcion": "", "monto": 0.0},
            {"categoria": "Transporte",               "descripcion": "", "monto": 0.0},
            {"categoria": "Colegiatura / inscripción","descripcion": "Por semestre dividido entre 6 meses", "monto": 0.0},
            {"categoria": "Libros y papelería",       "descripcion": "Cuadernos, bolígrafos, impresiones", "monto": 0.0},
            {"categoria": "Material escolar",         "descripcion": "Calculadora, USB, folders, etc.", "monto": 0.0},
            {"categoria": "Servicios (internet, celular)", "descripcion": "", "monto": 0.0},
            {"categoria": "Entretenimiento",          "descripcion": "", "monto": 0.0},
        ]

    egresos_validos = []
    filas_egreso_eliminar = []

    # Headers
    hc1, hc2, hc3, hc4, hc5 = st.columns([2, 2, 2, 1, 1])
    hc1.caption("**Categoría**")
    hc2.caption("**Descripción (opcional)**")
    hc3.caption("**Monto mensual ($)**")
    hc4.caption("**¿Necesario?**")
    hc5.caption("")

    for i, fila in enumerate(st.session_state.filas_egreso):
        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])
        with col1:
            cat = st.selectbox("Cat", CATEGORIAS_EGRESO,
                              index=CATEGORIAS_EGRESO.index(fila["categoria"]) if fila["categoria"] in CATEGORIAS_EGRESO else 0,
                              key=f"eg_cat_{i}", label_visibility="collapsed")
        with col2:
            desc = st.text_input("Desc", value=fila["descripcion"],
                                key=f"eg_desc_{i}", label_visibility="collapsed",
                                placeholder="Detalle opcional")
        with col3:
            monto = st.number_input("Monto", min_value=0.0, value=fila["monto"], step=50.0,
                                   key=f"eg_monto_{i}", label_visibility="collapsed")
        with col4:
            necesario = st.checkbox("", value=cat in CATEGORIAS_NECESARIAS,
                                   key=f"eg_nec_{i}")
        with col5:
            if st.button("🗑️", key=f"del_eg_{i}"):
                filas_egreso_eliminar.append(i)

        if monto > 0:
            # Mapear categoría al formato del motor
            cat_motor = cat.lower().split("(")[0].strip().replace(" ", "_").replace("/","_").replace("ó","o")
            egresos_validos.append({
                "categoria": cat_motor,
                "descripcion": desc if desc else cat,
                "monto": monto,
                "es_necesario": necesario
            })

    for i in sorted(filas_egreso_eliminar, reverse=True):
        st.session_state.filas_egreso.pop(i)
        st.rerun()

    if st.button("➕ Agregar gasto"):
        st.session_state.filas_egreso.append({"categoria": "Otros", "descripcion": "", "monto": 0.0})
        st.rerun()

    # ── Ingresos extraordinarios ──
    st.divider()
    st.subheader("🎁 Ingresos extraordinarios")
    st.caption("Agrega pagos que recibes una o pocas veces al año, como aguinaldo o bonos. Se promediarán entre los 12 meses.")

    if "filas_extra" not in st.session_state:
        st.session_state.filas_extra = []

    ingresos_extra_validos = []
    filas_extra_eliminar = []

    if st.session_state.filas_extra:
        he1, he2, he3, he4 = st.columns([3, 3, 2, 1])
        he1.caption("**Concepto**")
        he2.caption("**Tipo**")
        he3.caption("**Monto total ($)**")
        he4.caption("")

        for i, fila in enumerate(st.session_state.filas_extra):
            col1, col2, col3, col4 = st.columns([3, 3, 2, 1])
            with col1:
                concepto = st.text_input("Concepto", value=fila.get("concepto", ""),
                                         key=f"ext_concepto_{i}", label_visibility="collapsed",
                                         placeholder="Ej: Aguinaldo, Bono semestral")
            with col2:
                tipo_extra = st.selectbox("Tipo", ["Aguinaldo (anual)", "Bono semestral", "Bono trimestral", "Otro (anual)"],
                                          index=0, key=f"ext_tipo_{i}", label_visibility="collapsed")
            with col3:
                monto_extra = st.number_input("Monto", min_value=0.0, value=fila.get("monto", 0.0),
                                              step=100.0, key=f"ext_monto_{i}", label_visibility="collapsed")
            with col4:
                if st.button("🗑️", key=f"del_ext_{i}"):
                    filas_extra_eliminar.append(i)

            if concepto and monto_extra > 0:
                divisor = {"Aguinaldo (anual)": 12, "Bono semestral": 6,
                           "Bono trimestral": 3, "Otro (anual)": 12}.get(tipo_extra, 12)
                mensual = round(monto_extra / divisor, 2)
                ingresos_extra_validos.append({
                    "concepto": concepto, "tipo": tipo_extra,
                    "monto_total": monto_extra, "mensual_promedio": mensual
                })

    for i in sorted(filas_extra_eliminar, reverse=True):
        st.session_state.filas_extra.pop(i)
        st.rerun()

    if st.button("➕ Agregar aguinaldo / bono"):
        st.session_state.filas_extra.append({"concepto": "", "monto": 0.0})
        st.rerun()

    if ingresos_extra_validos:
        total_extra_mensual = sum(e["mensual_promedio"] for e in ingresos_extra_validos)
        st.info(f"📊 Promedio mensual de ingresos extraordinarios: **${total_extra_mensual:,.2f}**")
        for e in ingresos_extra_validos:
            ingresos_validos.append({
                "fuente": f"{e['concepto']} (promedio mensual)",
                "tipo": "variable",
                "monto": e["mensual_promedio"],
                "dia_cobro": 1
            })

    # ── Vacaciones personalizadas ──
    st.divider()
    st.subheader("🏖️ Periodos vacacionales")
    st.caption("Indica tus periodos de vacaciones y el gasto extra que implican. Se distribuirá proporcionalmente entre los 12 meses.")

    if "filas_vacaciones" not in st.session_state:
        st.session_state.filas_vacaciones = []

    filas_vac_eliminar = []
    gasto_vacacional_mensual = 0.0

    # Sugerencias rápidas
    col_sug1, col_sug2, col_sug3 = st.columns(3)
    with col_sug1:
        if st.button("+ Agregar vacaciones de verano (jul-ago)"):
            st.session_state.filas_vacaciones.append({
                "nombre": "Vacaciones de verano", "mes_inicio": "Julio",
                "mes_fin": "Agosto", "gasto": 0.0
            })
            st.rerun()
    with col_sug2:
        if st.button("+ Agregar vacaciones decembrinas (dic-ene)"):
            st.session_state.filas_vacaciones.append({
                "nombre": "Vacaciones decembrinas", "mes_inicio": "Diciembre",
                "mes_fin": "Enero", "gasto": 0.0
            })
            st.rerun()
    with col_sug3:
        if st.button("+ Agregar otro periodo vacacional"):
            st.session_state.filas_vacaciones.append({
                "nombre": "", "mes_inicio": "Enero",
                "mes_fin": "Enero", "gasto": 0.0
            })
            st.rerun()

    if st.session_state.filas_vacaciones:
        hv1, hv2, hv3, hv4, hv5 = st.columns([2, 2, 2, 2, 1])
        hv1.caption("**Nombre del periodo**")
        hv2.caption("**Mes inicio**")
        hv3.caption("**Mes fin**")
        hv4.caption("**Gasto extra total ($)**")
        hv5.caption("")

        for i, fila in enumerate(st.session_state.filas_vacaciones):
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
            with col1:
                nombre_vac = st.text_input("Nombre", value=fila.get("nombre", ""),
                                           key=f"vac_nom_{i}", label_visibility="collapsed",
                                           placeholder="Ej: Semana Santa")
            with col2:
                mes_ini_vac = st.selectbox("Inicio", MESES,
                                           index=MESES.index(fila.get("mes_inicio", "Enero")),
                                           key=f"vac_ini_{i}", label_visibility="collapsed")
            with col3:
                mes_fin_vac = st.selectbox("Fin", MESES,
                                           index=MESES.index(fila.get("mes_fin", "Enero")),
                                           key=f"vac_fin_{i}", label_visibility="collapsed")
            with col4:
                gasto_vac = st.number_input("Gasto $", min_value=0.0,
                                            value=fila.get("gasto", 0.0), step=100.0,
                                            key=f"vac_gasto_{i}", label_visibility="collapsed")
            with col5:
                if st.button("🗑️", key=f"del_vac_{i}"):
                    filas_vac_eliminar.append(i)

            # Calcular duración en meses y promedio mensual
            idx_ini = MESES.index(mes_ini_vac)
            idx_fin = MESES.index(mes_fin_vac)
            duracion = (idx_fin - idx_ini) % 12 + 1
            promedio_mes = round(gasto_vac / 12, 2)
            gasto_vacacional_mensual += promedio_mes

            if nombre_vac or gasto_vac > 0:
                st.caption(f"   📅 {nombre_vac or 'Periodo'}: {mes_ini_vac} → {mes_fin_vac} ({duracion} mes{'es' if duracion > 1 else ''}) | Gasto extra promediado: ${promedio_mes:,.2f}/mes")

    for i in sorted(filas_vac_eliminar, reverse=True):
        st.session_state.filas_vacaciones.pop(i)
        st.rerun()

    gasto_vacacional_mensual = round(gasto_vacacional_mensual, 2)
    if gasto_vacacional_mensual > 0:
        st.info(f"📊 Total gasto vacacional promediado: **${gasto_vacacional_mensual:,.2f}/mes**")
        egresos_validos.append({
            "categoria": "otros",
            "descripcion": "Gastos vacacionales promediados",
            "monto": gasto_vacacional_mensual,
            "es_necesario": False
        })

    st.divider()

    # ── Resumen previo y botón de análisis ──
    total_ing = sum(i["monto"] for i in ingresos_validos)
    total_eg  = sum(e["monto"] for e in egresos_validos)
    balance_previo = total_ing - total_eg

    col1, col2, col3 = st.columns(3)
    col1.metric("Total ingresos", f"${total_ing:,.0f}")
    col2.metric("Total egresos",  f"${total_eg:,.0f}")
    col3.metric("Balance estimado",
                f"${balance_previo:,.0f}",
                delta="Excedente" if balance_previo >= 0 else "Déficit",
                delta_color="normal" if balance_previo >= 0 else "inverse")

    st.caption(f"📅 Planeación a {anios_planeacion} año{'s' if anios_planeacion > 1 else ''} | Inicio: {mes_inicio}")

    st.divider()

    if st.button("📊 Generar mi análisis financiero", type="primary", use_container_width=True):
        if not ingresos_validos:
            st.error("Agrega al menos un ingreso con monto mayor a $0.")
        elif not egresos_validos:
            st.error("Agrega al menos un egreso con monto mayor a $0.")
        else:
            with st.spinner("Calculando tu análisis..."):
                rendimientos_etfs = obtener_rendimientos_etfs()
                resultado = analisis_completo(ingresos_validos, egresos_validos, dia_cobro=1)

                # Recalcular inversiones con rendimientos reales de ETFs
                if resultado["balance"]["balance_mensual"] > 0:
                    resultado["inversiones"] = sugerir_inversiones(
                        resultado["balance"]["balance_mensual"],
                        rendimientos_etfs=rendimientos_etfs
                    )

                resultado["meta"] = {
                    "anios_planeacion": anios_planeacion,
                    "mes_inicio": mes_inicio,
                    "gasto_vacacional_mensual": gasto_vacacional_mensual
                }
                st.session_state.resultado = resultado
                st.session_state.etapa = "analisis"
                st.session_state.mensajes_chat = [{
                    "role": "assistant",
                    "content": f"¡Tu análisis está listo! 🎉 Puedes ver tu reporte arriba. ¿Tienes alguna pregunta sobre tu situación financiera o quieres explorar alguna opción de inversión en más detalle?"
                }]
            st.rerun()

# ══════════════════════════════════════════════════════════
# ETAPA 2 — ANÁLISIS + CHAT
# ══════════════════════════════════════════════════════════
else:
    r   = st.session_state.resultado
    bal = r["balance"]
    ing = r["ingresos"]
    eg  = r["egresos"]
    aho = r["ahorro"]
    meta = r.get("meta", {})

    # Obtener tasas en tiempo real
    tasas_cetes    = obtener_tasas_cetes()
    datos_inflacion = obtener_inflacion()
    inflacion_actual = datos_inflacion["inflacion"]
    fecha_inflacion  = datos_inflacion["fecha"]
    fecha_cetes      = list(tasas_cetes.values())[0]["fecha"]

    st.title("📊 Tu análisis financiero")
    st.caption(f"📅 Planeación a {meta.get('anios_planeacion',1)} año(s) | Inicio: {meta.get('mes_inicio','')} | "
               f"Tasas CETES al {fecha_cetes} | Inflación: {inflacion_actual}% al {fecha_inflacion}")

    if st.button("✏️ Editar mi plantilla", type="secondary"):
        st.session_state.etapa = "plantilla"
        st.rerun()

    st.info(f"📡 Tasas en tiempo real — CETES al {fecha_cetes} | Inflación anual: {inflacion_actual}%")

    st.divider()

    # ── Métricas principales ──
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ingresos mensuales", f"${ing['total_ingresos']:,.0f}")
    col2.metric("Egresos mensuales",  f"${eg['total_egresos']:,.0f}")
    col3.metric("Balance mensual",
                f"${bal['balance_mensual']:,.0f}",
                delta="Excedente" if bal["balance_mensual"] >= 0 else "Déficit",
                delta_color="normal" if bal["balance_mensual"] >= 0 else "inverse")
    anios = meta.get("anios_planeacion", 1)
    ahorro_proyectado = bal["balance_mensual"] * 12 * anios if bal["balance_mensual"] > 0 else 0
    col4.metric(f"Ahorro potencial a {anios} año(s)", f"${ahorro_proyectado:,.0f}")

    if bal["dia_queda_sin_dinero"]:
        st.warning(f"⚠️ Simulando tu flujo día a día, aproximadamente el día {bal['dia_queda_sin_dinero']} del mes tu saldo llega a cero.")

    if bal.get("dias_cobro_texto"):
        st.info(f"📅 Días de cobro registrados: {bal['dias_cobro_texto']}")

    if meta.get("gasto_vacacional_mensual", 0) > 0:
        st.info(f"🏖️ Se incluyó un promedio de ${meta['gasto_vacacional_mensual']:,.2f}/mes por gastos vacacionales.")

    # ── Gráficas ──
    col_a, col_b = st.columns(2)
    with col_a:
        fig1, ax1 = plt.subplots(figsize=(5, 4))
        if bal["balance_mensual"] >= 0:
            valores  = [eg["total_egresos"], bal["balance_mensual"]]
            etiquetas = [f"Gastos\n${eg['total_egresos']:,.0f}", f"Excedente\n${bal['balance_mensual']:,.0f}"]
            colores  = ["#E74C3C", "#2ECC71"]
        else:
            valores  = [ing["total_ingresos"], abs(bal["balance_mensual"])]
            etiquetas = [f"Ingresos\n${ing['total_ingresos']:,.0f}", f"Déficit\n${abs(bal['balance_mensual']):,.0f}"]
            colores  = ["#3498DB", "#E74C3C"]
        ax1.pie(valores, labels=etiquetas, colors=colores, autopct="%1.1f%%", startangle=90,
               wedgeprops={"edgecolor": "white", "linewidth": 2},
               textprops={"color": TEXT_COLOR})
        ax1.set_title("Balance mensual", fontsize=13, fontweight="bold", color=TEXT_COLOR)
        estilo_oscuro(fig1, ax1)
        st.pyplot(fig1)

    with col_b:
        categorias = [c[0] for c in eg["categorias_ordenadas"]]
        montos_eg  = [c[1] for c in eg["categorias_ordenadas"]]
        necesarios = {e["categoria"] for e in eg["detalle"] if e["es_necesario"]}
        colores_eg = ["#E74C3C" if c in necesarios else "#F39C12" for c in categorias]
        fig2, ax2  = plt.subplots(figsize=(6, 4))
        bars = ax2.barh(categorias, montos_eg, color=colores_eg, edgecolor="white", height=0.6)
        ax2.bar_label(bars, labels=[f"${m:,.0f}" for m in montos_eg], padding=5, fontsize=9, color=TEXT_COLOR)
        ax2.set_title("Gastos por categoría", fontsize=13, fontweight="bold")
        ax2.invert_yaxis()
        ax2.set_xlim(0, max(montos_eg) * 1.25)
        from matplotlib.patches import Patch
        ax2.legend(handles=[Patch(color="#E74C3C", label="Necesario"),
                            Patch(color="#F39C12", label="Prescindible")], fontsize=9)
        estilo_oscuro(fig2, ax2)
        plt.tight_layout()
        st.pyplot(fig2)

    # ── Proyección a N años ──
    if bal["balance_mensual"] > 0:
        meses_total  = anios * 12
        meses_eje    = np.arange(0, meses_total + 1)
        inflacion_m  = inflacion_actual / 100 / 12

        tasas_plot = {f"CETES {p} ({info['tasa']}%)": info["tasa"]
                      for p, info in tasas_cetes.items()}
        tasas_plot["Sin invertir"] = 0.0
        colores_plot = ["#27AE60","#2ECC71","#82E0AA","#A9DFBF","#95A5A6"]
        estilos_plot = ["-","-","-","-","--"]

        fig3, axes = plt.subplots(1, 2, figsize=(13, 5))
        saldos_finales = {}
        for (nombre, tasa), color, estilo in zip(tasas_plot.items(), colores_plot, estilos_plot):
            tm = tasa / 100 / 12
            if tm > 0:
                saldos = [bal["balance_mensual"] * (((1+tm)**m - 1)/tm) if m > 0 else 0 for m in meses_eje]
            else:
                saldos = [bal["balance_mensual"] * m for m in meses_eje]
            saldos_reales = [s / ((1+inflacion_m)**m) if m > 0 else 0 for m, s in zip(meses_eje, saldos)]
            axes[0].plot(meses_eje, saldos, color=color, linewidth=2, linestyle=estilo, label=nombre)
            axes[1].plot(meses_eje, saldos_reales, color=color, linewidth=2, linestyle=estilo, label=nombre)
            # Etiqueta valor final
            axes[0].annotate(f"${saldos[-1]:,.0f}", xy=(meses_eje[-1], saldos[-1]),
                            xytext=(4, 0), textcoords="offset points",
                            fontsize=7, color=color, va="center", fontweight="bold")
            axes[1].annotate(f"${saldos_reales[-1]:,.0f}", xy=(meses_eje[-1], saldos_reales[-1]),
                            xytext=(4, 0), textcoords="offset points",
                            fontsize=7, color=color, va="center", fontweight="bold")

        for ax, titulo in zip(axes, ["Proyección nominal", f"Proyección real\n(ajustada por inflación {inflacion_actual}%)"]):
            ax.set_title(titulo, fontsize=11, fontweight="bold")
            ax.set_xlabel("Meses", fontsize=10)
            ax.set_ylabel("Saldo acumulado ($MXN)", fontsize=10)
            ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
            ax.legend(fontsize=8)

        estilo_oscuro(fig3, *axes)
        fig3.suptitle(f"Proyección de ahorro a {anios} año(s)", fontsize=13, fontweight="bold", color=TEXT_COLOR)
        plt.tight_layout()
        st.pyplot(fig3)
        st.caption(f"📌 Inflación: {inflacion_actual}% anual (Banxico/INEGI, {fecha_inflacion})")

        # ── Proyección Apps de ahorro ──
        opciones_apps = [op for op in inv.get("opciones", []) if op.get("es_app")]
        if opciones_apps:
            st.subheader("📱 Proyección — Apps de ahorro digital")
            colores_apps = ["#8E44AD","#9B59B6","#A569BD","#BB8FCE"]
            fig_apps, axes_apps = plt.subplots(1, 2, figsize=(13, 5))
            for op, color in zip(opciones_apps, colores_apps):
                tasa  = op["rendimiento_anual_pct"]
                tm    = tasa / 100 / 12
                nombre_corto = op["instrumento"].split("—")[0].strip()
                saldos = [bal["balance_mensual"] * (((1+tm)**m - 1)/tm) if m > 0 else 0 for m in meses_eje]
                saldos_reales = [s / ((1+inflacion_m)**m) if m > 0 else 0 for m, s in zip(meses_eje, saldos)]
                axes_apps[0].plot(meses_eje, saldos,        color=color, linewidth=2, label=f"{nombre_corto} ({tasa}%)")
                axes_apps[1].plot(meses_eje, saldos_reales, color=color, linewidth=2, label=f"{nombre_corto} ({tasa}%)")
                axes_apps[0].annotate(f"${saldos[-1]:,.0f}", xy=(meses_eje[-1], saldos[-1]),
                                     xytext=(4, 0), textcoords="offset points",
                                     fontsize=7, color=color, va="center", fontweight="bold")
                axes_apps[1].annotate(f"${saldos_reales[-1]:,.0f}", xy=(meses_eje[-1], saldos_reales[-1]),
                                     xytext=(4, 0), textcoords="offset points",
                                     fontsize=7, color=color, va="center", fontweight="bold")
            # Línea de referencia sin invertir
            saldos_ref = [bal["balance_mensual"] * m for m in meses_eje]
            saldos_ref_reales = [s / ((1+inflacion_m)**m) if m > 0 else 0 for m, s in zip(meses_eje, saldos_ref)]
            axes_apps[0].plot(meses_eje, saldos_ref,       color="#95A5A6", linewidth=1.5, linestyle="--", label="Sin invertir")
            axes_apps[1].plot(meses_eje, saldos_ref_reales, color="#95A5A6", linewidth=1.5, linestyle="--", label="Sin invertir")
            for ax, titulo in zip(axes_apps, ["Proyección nominal", f"Proyección real (inflación {inflacion_actual}%)"]):
                ax.set_title(titulo, fontsize=11, fontweight="bold")
                ax.set_xlabel("Meses", fontsize=10)
                ax.set_ylabel("Saldo acumulado ($MXN)", fontsize=10)
                ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
                ax.legend(fontsize=8)

            estilo_oscuro(fig_apps, *axes_apps)
            fig_apps.suptitle(f"Proyección apps de ahorro a {anios} año(s)", fontsize=13, fontweight="bold", color=TEXT_COLOR)
            plt.tight_layout()
            st.pyplot(fig_apps)
            st.caption("📱 Las tasas de apps son referenciales y pueden cambiar — verifica en cada app antes de invertir.")

            # Tabla comparativa apps
            st.markdown("**Tabla comparativa — Apps de ahorro**")
            import pandas as pd
            filas_apps = []
            for op in opciones_apps:
                tasa  = op["rendimiento_anual_pct"]
                tr    = round(tasa - inflacion_actual, 2)
                tm    = tasa / 100 / 12
                saldo_final = bal["balance_mensual"] * (((1+tm)**(anios*12) - 1)/tm)
                filas_apps.append({
                    "Instrumento":         op["instrumento"].split("—")[0].strip(),
                    "Tasa nominal":        f"{tasa}%",
                    "Tasa real":           f"{tr}%",
                    "Ganancia/mes":        f"${op['ganancia_mensual_estimada']:,.2f}",
                    f"Saldo a {anios} año(s)": f"${saldo_final:,.0f}",
                    "Liquidez":            op.get("plazo","—"),
                })
            st.dataframe(pd.DataFrame(filas_apps), use_container_width=True, hide_index=True)

        # ── Proyección ETFs ──
        opciones_etfs = [op for op in inv.get("opciones", []) if op.get("es_etf")]
        if opciones_etfs:
            st.subheader("📊 Proyección — ETFs")
            colores_etfs = ["#E67E22","#F39C12","#F8C471"]
            fig_etfs, axes_etfs = plt.subplots(1, 2, figsize=(13, 5))
            for op, color in zip(opciones_etfs, colores_etfs):
                tasa  = op["rendimiento_anual_pct"]
                tm    = tasa / 100 / 12
                nombre_corto = op["instrumento"].split("—")[0].strip()
                saldos = [bal["balance_mensual"] * (((1+tm)**m - 1)/tm) if m > 0 else 0 for m in meses_eje]
                saldos_reales = [s / ((1+inflacion_m)**m) if m > 0 else 0 for m, s in zip(meses_eje, saldos)]
                axes_etfs[0].plot(meses_eje, saldos,        color=color, linewidth=2, label=f"{nombre_corto} ({tasa}%)")
                axes_etfs[1].plot(meses_eje, saldos_reales, color=color, linewidth=2, label=f"{nombre_corto} ({tasa}%)")
                axes_etfs[0].annotate(f"${saldos[-1]:,.0f}", xy=(meses_eje[-1], saldos[-1]),
                                     xytext=(4, 0), textcoords="offset points",
                                     fontsize=7, color=color, va="center", fontweight="bold")
                axes_etfs[1].annotate(f"${saldos_reales[-1]:,.0f}", xy=(meses_eje[-1], saldos_reales[-1]),
                                     xytext=(4, 0), textcoords="offset points",
                                     fontsize=7, color=color, va="center", fontweight="bold")
            axes_etfs[0].plot(meses_eje, saldos_ref,       color="#95A5A6", linewidth=1.5, linestyle="--", label="Sin invertir")
            axes_etfs[1].plot(meses_eje, saldos_ref_reales, color="#95A5A6", linewidth=1.5, linestyle="--", label="Sin invertir")
            for ax, titulo in zip(axes_etfs, ["Proyección nominal", f"Proyección real (inflación {inflacion_actual}%)"]):
                ax.set_title(titulo, fontsize=11, fontweight="bold")
                ax.set_xlabel("Meses", fontsize=10)
                ax.set_ylabel("Saldo acumulado ($MXN)", fontsize=10)
                ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
                ax.legend(fontsize=8)

            estilo_oscuro(fig_etfs, *axes_etfs)
            fig_etfs.suptitle(f"Proyección ETFs a {anios} año(s)", fontsize=13, fontweight="bold", color=TEXT_COLOR)
            plt.tight_layout()
            st.pyplot(fig_etfs)
            st.warning("⚠️ Los rendimientos de ETFs son históricos y no garantizan resultados futuros. Pueden perder valor en el corto plazo.")

            # Tabla comparativa ETFs
            st.markdown("**Tabla comparativa — ETFs**")
            filas_etfs = []
            for op in opciones_etfs:
                tasa  = op["rendimiento_anual_pct"]
                tr    = round(tasa - inflacion_actual, 2)
                tm    = tasa / 100 / 12
                saldo_final = bal["balance_mensual"] * (((1+tm)**(anios*12) - 1)/tm)
                filas_etfs.append({
                    "Instrumento":         op["instrumento"].split("—")[0].strip(),
                    "Fuente del dato":     op.get("fuente_rendimiento","histórico"),
                    "Tasa nominal":        f"{tasa}%",
                    "Tasa real":           f"{tr}%",
                    "Ganancia/mes":        f"${op['ganancia_mensual_estimada']:,.2f}",
                    f"Saldo a {anios} año(s)": f"${saldo_final:,.0f}",
                    "Riesgo":             op.get("riesgo","—"),
                })
            st.dataframe(pd.DataFrame(filas_etfs), use_container_width=True, hide_index=True)

    # ── Recomendación de ahorro ──
    st.subheader("🏦 Recomendación de ahorro")
    st.info(aho["recomendacion"])

    # ── Opciones de inversión ──
    inv = r.get("inversiones", {})
    if inv and inv.get("opciones"):
        st.subheader("📈 Opciones de inversión")
        st.caption(f"CETES al {fecha_cetes} (Banxico) | Inflación: {inflacion_actual}% al {fecha_inflacion}")
        for op in inv["opciones"]:
            tasa_real = round(op["rendimiento_anual_pct"] - inflacion_actual, 2)
            with st.expander(f"{op['instrumento']} — {op['rendimiento_anual_pct']}% nominal / {tasa_real}% real"):
                col1, col2 = st.columns(2)
                col1.metric("Ganancia mensual estimada", f"${op['ganancia_mensual_estimada']:,.2f}")
                col2.metric("Tasa real (vs inflación)", f"{tasa_real}%",
                           delta="Gana poder adquisitivo" if tasa_real > 0 else "Pierde poder adquisitivo",
                           delta_color="normal" if tasa_real > 0 else "inverse")

                detalle = op.get("detalle", {})
                if detalle:
                    st.divider()
                    for clave, valor in detalle.items():
                        if clave not in ("nombre", "ticker"):
                            st.write(f"**{clave.replace('_',' ').capitalize()}:** {valor}")
                else:
                    st.write(f"**Riesgo:** {op['riesgo']}")
                    st.write(f"**Plazo:** {op['plazo']}")
                    st.write(op["comentario"])

                if op.get("es_etf"):
                    st.warning(
                        f"⚠️ **Rendimiento histórico, no garantizado.** "
                        f"El {op['rendimiento_anual_pct']}% es el rendimiento anualizado real "
                        f"de los últimos 3 años ({op.get('fuente_rendimiento','')})."
                        f" Los rendimientos pasados no garantizan rendimientos futuros. "
                        f"Este instrumento puede perder valor en el corto plazo."
                    )
                    if op.get("precio_actual"):
                        st.caption(f"Precio actual: ${op['precio_actual']:,.2f} USD")
                elif any(x in op["instrumento"] for x in ["Nu","Flink","Mercado Pago","GBM"]):
                    st.info(
                        "📱 Tasa referencial. Las apps actualizan sus rendimientos libremente — "
                        "verifica la tasa vigente directamente en cada app antes de invertir."
                    )

    st.caption("⚠️ Esto es orientación educativa, no asesoría financiera profesional.")
    st.divider()

    # ── CHAT de preguntas adicionales ──
    st.subheader("💬 ¿Tienes preguntas sobre tu análisis?")

    for msg in st.session_state.mensajes_chat:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("Escribe tu pregunta aquí..."):
        st.session_state.mensajes_chat.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        contexto = (
            f"El estudiante tiene ingresos de ${ing['total_ingresos']:,.2f}/mes, "
            f"egresos de ${eg['total_egresos']:,.2f}/mes y un balance de ${bal['balance_mensual']:,.2f}/mes. "
            f"Situación: {bal['situacion']}. Planeación a {meta.get('anios_planeacion',1)} año(s)."
        )
        st.session_state.historial_chat.append({
            "role": "user",
            "content": f"[Contexto del análisis: {contexto}]\n\nPregunta del estudiante: {prompt}"
        })

        with st.spinner("El asesor está respondiendo..."):
            respuesta = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=800,
                system=SYSTEM_PROMPT,
                messages=st.session_state.historial_chat
            )
            texto = respuesta.content[0].text
            st.session_state.historial_chat.append({"role": "assistant", "content": texto})
            st.session_state.mensajes_chat.append({"role": "assistant", "content": texto})

        with st.chat_message("assistant"):
            st.write(texto)
