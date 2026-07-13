# ─────────────────────────────────────────────
# MOTOR FINANCIERO — Asesor Estudiantil México
# Versión completa con CETES, apps y ETFs
# ─────────────────────────────────────────────

def analizar_ingresos(ingresos: list[dict]) -> dict:
    total     = sum(i["monto"] for i in ingresos)
    fijos     = sum(i["monto"] for i in ingresos if i["tipo"] == "fijo")
    variables = sum(i["monto"] for i in ingresos if i["tipo"] == "variable")
    return {
        "total_ingresos":    round(total, 2),
        "ingresos_fijos":    round(fijos, 2),
        "ingresos_variables":round(variables, 2),
        "porcentaje_fijo":   round((fijos / total * 100), 1) if total > 0 else 0,
        "fuentes": ingresos
    }


def analizar_egresos(egresos: list[dict]) -> dict:
    total        = sum(e["monto"] for e in egresos)
    necesarios   = sum(e["monto"] for e in egresos if e["es_necesario"])
    prescindibles= sum(e["monto"] for e in egresos if not e["es_necesario"])
    por_categoria = {}
    for e in egresos:
        cat = e["categoria"]
        por_categoria[cat] = por_categoria.get(cat, 0) + e["monto"]
    categorias_ordenadas = sorted(por_categoria.items(), key=lambda x: x[1], reverse=True)
    return {
        "total_egresos":       round(total, 2),
        "gastos_necesarios":   round(necesarios, 2),
        "gastos_prescindibles":round(prescindibles, 2),
        "categorias_ordenadas":categorias_ordenadas,
        "detalle": egresos
    }


def calcular_balance(total_ingresos: float, total_egresos: float, dia_cobro: int = 1,
                     ingresos_detalle: list = None) -> dict:
    balance      = total_ingresos - total_egresos
    gasto_diario = total_egresos / 30
    dias_que_dura= total_ingresos / gasto_diario if gasto_diario > 0 else 30

    # Calcular días de cobro: si hay detalle por fuente, simular el flujo mensual
    if ingresos_detalle:
        # Construir flujo día a día del mes
        flujo_diario = [0.0] * 32  # índice = día del mes
        for ing in ingresos_detalle:
            dia = ing.get("dia_cobro", 1)
            flujo_diario[dia] += ing["monto"]

        # Simular saldo día a día
        saldo = 0.0
        gasto_dia = total_egresos / 30
        dia_queda_sin_dinero = None
        for dia in range(1, 31):
            saldo += flujo_diario[dia]
            saldo -= gasto_dia
            if saldo < 0 and dia_queda_sin_dinero is None:
                dia_queda_sin_dinero = dia

        # Resumen de días de cobro para mostrar al usuario
        dias_cobro_resumen = sorted(set(
            ing.get("dia_cobro", 1) for ing in ingresos_detalle if ing["monto"] > 0
        ))
    else:
        # Comportamiento original si no hay detalle
        if balance >= 0:
            dia_queda_sin_dinero = None
        else:
            dia_queda_sin_dinero = dia_cobro + int(dias_que_dura)
            if dia_queda_sin_dinero > 30:
                dia_queda_sin_dinero = None
        dias_cobro_resumen = [dia_cobro]

    if balance >= 0:
        situacion = "EXCEDENTE"
        mensaje = f"Tienes un excedente de ${balance:,.2f} al mes."
    else:
        situacion = "DEFICIT"
        mensaje = f"Tus gastos superan tus ingresos por ${abs(balance):,.2f} al mes."

    dias_str = ", ".join([f"día {d}" for d in dias_cobro_resumen])
    return {
        "balance_mensual":         round(balance, 2),
        "situacion":               situacion,
        "gasto_diario_promedio":   round(gasto_diario, 2),
        "dias_que_dura_el_dinero": round(dias_que_dura, 1),
        "dia_queda_sin_dinero":    dia_queda_sin_dinero,
        "dias_cobro":              dias_cobro_resumen,
        "dias_cobro_texto":        dias_str,
        "mensaje": mensaje
    }


def calcular_potencial_ahorro(balance: float, gastos_prescindibles: float) -> dict:
    if balance <= 0:
        recorte_minimo      = abs(balance)
        puede_cubrir_deficit= recorte_minimo <= gastos_prescindibles
        return {
            "ahorro_posible": 0,
            "recorte_minimo_necesario": round(recorte_minimo, 2),
            "puede_cubrir_con_prescindibles": puede_cubrir_deficit,
            "recomendacion": (
                f"Necesitas recortar al menos ${recorte_minimo:,.2f} de tus gastos prescindibles "
                f"(tienes ${gastos_prescindibles:,.2f} en gastos no esenciales)."
                if puede_cubrir_deficit
                else "Tus gastos esenciales ya superan tus ingresos. Necesitas aumentar ingresos o reducir gastos fijos."
            )
        }
    else:
        ahorro_20 = balance * 0.20
        ahorro_50 = balance * 0.50
        return {
            "ahorro_posible":                 round(balance, 2),
            "ahorro_recomendado_conservador": round(ahorro_20, 2),
            "ahorro_recomendado_agresivo":    round(ahorro_50, 2),
            "recomendacion": (
                f"Podrías ahorrar entre ${ahorro_20:,.2f} (20%) "
                f"y ${ahorro_50:,.2f} (50%) de tu excedente mensual."
            )
        }


def sugerir_inversiones(excedente_mensual: float, rendimientos_etfs: dict = None) -> dict:
    """
    Sugiere opciones de inversión según el monto disponible.
    Tasas CETES: se actualizan en tiempo real desde Banxico vía app.py.
    Los valores aquí son de respaldo; la app siempre intenta jalar los datos reales.
    """
    opciones = []

    # ── CETES: 4 plazos (tasas de respaldo — Banxico las actualiza semanalmente) ──
    if excedente_mensual >= 100:
        plazos_cetes = [
            {"plazo": "28 días (1 mes)",    "tasa": 6.54},
            {"plazo": "91 días (3 meses)",  "tasa": 6.49},
            {"plazo": "182 días (6 meses)", "tasa": 6.74},
            {"plazo": "364 días (1 año)",   "tasa": 7.17},
        ]
        for p in plazos_cetes:
            opciones.append({
                "instrumento": f"CETES {p['plazo']} — cetesdirecto.com.mx",
                "rendimiento_anual_pct":     p["tasa"],
                "minimo":  100,
                "plazo":   p["plazo"],
                "riesgo":  "Muy bajo (gobierno federal)",
                "ganancia_mensual_estimada": round(excedente_mensual * (p["tasa"] / 100) / 12, 2),
                "es_etf":  False,
                "es_app":  False,
                "comentario": (
                    f"Tasa vigente: {p['tasa']}% anual (actualizada semanalmente por Banxico). "
                    f"Sin comisiones, 100% respaldado por el gobierno federal. "
                    f"Disponible desde $100 MXN en cetesdirecto.com.mx sin necesidad de banco."
                ),
                "detalle": {
                    "plazo": p["plazo"],
                    "tasa_anual": f"{p['tasa']}%",
                    "minimo_inversion": "$100 MXN",
                    "donde_comprar": "cetesdirecto.com.mx (gratuito, solo necesitas INE y CURP)",
                    "liquidez": "Al vencimiento del plazo elegido",
                    "riesgo": "Muy bajo — respaldado por el Gobierno Federal",
                    "isr_2026": "Retención provisional de 0.90% anual sobre el capital (subió de 0.50% en 2025)",
                    "ventaja": "La inversión más segura de México; ideal para empezar sin experiencia previa"
                }
            })

    # ── Apps de ahorro digital ──
    if excedente_mensual >= 100:
        apps_ahorro = [
            {
                "nombre":      "Nu (Nubank)",
                "tasa":        11.5,
                "minimo":      1,
                "liquidez":    "Inmediata (mismo día)",
                "regulacion":  "CNBV e IPAB — depósitos asegurados hasta 25 UDIs (~$200,000 MXN)",
                "como_abrir":  "App Nu en iOS o Android — solo necesitas INE y CURP, proceso en minutos",
                "ventaja":     "Sin comisiones, sin monto mínimo, rendimiento diario visible en la app",
                "advertencia": "Tasa referencial — Nu puede modificarla. Verifica en la app antes de invertir."
            },
            {
                "nombre":      "Mercado Pago",
                "tasa":        11.0,
                "minimo":      1,
                "liquidez":    "Inmediata",
                "regulacion":  "CNBV",
                "como_abrir":  "App Mercado Pago — vinculada a tu cuenta de Mercado Libre",
                "ventaja":     "Ideal si ya usas Mercado Libre; el dinero rinde mientras lo tienes guardado",
                "advertencia": "Tasa referencial — puede cambiar. Verifica en la app antes de invertir."
            },
            {
                "nombre":      "Flink",
                "tasa":        10.8,
                "minimo":      1,
                "liquidez":    "1-2 días hábiles",
                "regulacion":  "CNBV",
                "como_abrir":  "App Flink en iOS o Android — proceso 100% digital",
                "ventaja":     "Interfaz muy sencilla, diseñada para jóvenes que inician a invertir",
                "advertencia": "Tasa referencial — puede cambiar. Verifica en la app antes de invertir."
            },
            {
                "nombre":      "GBM+ (Cuenta Cash)",
                "tasa":        11.2,
                "minimo":      100,
                "liquidez":    "Inmediata dentro de la plataforma",
                "regulacion":  "CNBV y BMV",
                "como_abrir":  "App GBM+ — requiere INE y comprobante de domicilio",
                "ventaja":     "Desde la misma app puedes dar el salto a ETFs cuando quieras crecer",
                "advertencia": "Tasa referencial — puede cambiar. Verifica en la app antes de invertir."
            },
        ]
        for app in apps_ahorro:
            if excedente_mensual >= app["minimo"]:
                ganancia = round(excedente_mensual * (app["tasa"] / 100) / 12, 2)
                opciones.append({
                    "instrumento": f"{app['nombre']} — Cuenta de ahorro digital",
                    "rendimiento_anual_pct":     app["tasa"],
                    "minimo":  app["minimo"],
                    "plazo":   app["liquidez"],
                    "riesgo":  "Bajo",
                    "ganancia_mensual_estimada": ganancia,
                    "es_etf":  False,
                    "es_app":  True,
                    "comentario": app["advertencia"],
                    "detalle": {
                        "tasa_referencial":   f"{app['tasa']}% anual",
                        "minimo_inversion":   f"${app['minimo']} MXN",
                        "liquidez":           app["liquidez"],
                        "regulacion":         app["regulacion"],
                        "como_abrir":         app["como_abrir"],
                        "ventaja_principal":  app["ventaja"],
                        "advertencia":        app["advertencia"]
                    }
                })

    # ── ETFs con rendimiento real de yfinance ──
    if excedente_mensual >= 1000:
        etfs_info = [
            {
                "ticker":       "NAFTRAC.MX",
                "nombre":       "NAFTRAC",
                "descripcion":  "Replica las 35 empresas más grandes de México (IPC de la BMV)",
                "donde_comprar":"GBM+, BIVA, cualquier casa de bolsa mexicana",
                "moneda":       "Pesos mexicanos — sin riesgo cambiario",
                "horizonte":    "Mínimo 1-3 años recomendado",
                "ventaja":      "Diversificación instantánea en México sin exposición a dólares",
                "riesgo_detalle":"Sigue al mercado mexicano — puede bajar en periodos de volatilidad"
            },
            {
                "ticker":       "VOO",
                "nombre":       "VOO (Vanguard S&P 500)",
                "descripcion":  "Replica las 500 empresas más grandes de EE.UU.",
                "donde_comprar":"GBM+ (requiere cuenta en USD)",
                "moneda":       "Dólares — incluye riesgo de tipo de cambio MXN/USD",
                "horizonte":    "Mínimo 3-5 años recomendado",
                "ventaja":      "El índice más diversificado y con mayor historial de largo plazo en el mundo",
                "riesgo_detalle":"Exposición al mercado americano y al tipo de cambio"
            },
            {
                "ticker":       "QQQ",
                "nombre":       "QQQ (Invesco Nasdaq-100)",
                "descripcion":  "Replica las 100 empresas tecnológicas más grandes (Apple, Google, Nvidia, Meta)",
                "donde_comprar":"GBM+ (requiere cuenta en USD)",
                "moneda":       "Dólares — incluye riesgo de tipo de cambio MXN/USD",
                "horizonte":    "Mínimo 3-5 años recomendado",
                "ventaja":      "Mayor rendimiento histórico pero con más volatilidad que el S&P 500",
                "riesgo_detalle":"Alta concentración en tecnología — más volátil en correcciones de mercado"
            },
        ]
        for etf in etfs_info:
            if rendimientos_etfs and etf["ticker"] in rendimientos_etfs:
                info          = rendimientos_etfs[etf["ticker"]]
                tasa          = info["rendimiento_anual"]
                fecha_dato    = info["fecha"]
                precio_actual = info["precio_actual"]
                fuente_dato   = f"Rendimiento anualizado real a 3 años (al {fecha_dato})"
            else:
                tasa          = 12.0
                fecha_dato    = "dato de respaldo"
                precio_actual = None
                fuente_dato   = "Rendimiento histórico referencial (3 años)"

            opciones.append({
                "instrumento": f"{etf['nombre']} — ETF",
                "rendimiento_anual_pct":     tasa,
                "minimo":  1000,
                "plazo":   etf["horizonte"],
                "riesgo":  "Medio" if "NAFTRAC" in etf["nombre"] else "Medio-alto",
                "ganancia_mensual_estimada": round(excedente_mensual * (tasa / 100) / 12, 2),
                "es_etf":           True,
                "es_app":           False,
                "fuente_rendimiento": fuente_dato,
                "precio_actual":    precio_actual,
                "comentario": (
                    f"{etf['descripcion']} | "
                    f"Dónde comprar: {etf['donde_comprar']} | "
                    f"Moneda: {etf['moneda']} | "
                    f"Ventaja: {etf['ventaja']}"
                ),
                "detalle": {
                    "descripcion":      etf["descripcion"],
                    "donde_comprar":    etf["donde_comprar"],
                    "moneda":           etf["moneda"],
                    "horizonte_recomendado": etf["horizonte"],
                    "ventaja_principal":etf["ventaja"],
                    "riesgo_detalle":   etf["riesgo_detalle"],
                    "fuente_rendimiento": fuente_dato,
                    "advertencia":      (
                        "⚠️ Rendimiento histórico — no garantiza rendimientos futuros. "
                        "Este instrumento puede perder valor en el corto plazo."
                    )
                }
            })

    if not opciones:
        return {
            "opciones": [],
            "mensaje": (
                "Con menos de $100 de excedente es difícil invertir formalmente. "
                "Primero enfócate en reducir gastos o buscar fuentes adicionales de ingreso."
            )
        }

    return {
        "excedente_analizado": excedente_mensual,
        "opciones": opciones,
        "mensaje": f"Con ${excedente_mensual:,.2f} de excedente mensual tienes {len(opciones)} opción(es) de inversión."
    }


def analisis_completo(ingresos: list[dict], egresos: list[dict], dia_cobro: int = 1) -> dict:
    res_ingresos = analizar_ingresos(ingresos)
    res_egresos  = analizar_egresos(egresos)
    res_balance  = calcular_balance(
        res_ingresos["total_ingresos"],
        res_egresos["total_egresos"],
        dia_cobro,
        ingresos_detalle=ingresos   # pasar detalle para múltiples días de cobro
    )
    res_ahorro = calcular_potencial_ahorro(
        res_balance["balance_mensual"],
        res_egresos["gastos_prescindibles"]
    )
    inversiones = {}
    if res_balance["balance_mensual"] > 0:
        inversiones = sugerir_inversiones(res_balance["balance_mensual"])
    return {
        "ingresos":   res_ingresos,
        "egresos":    res_egresos,
        "balance":    res_balance,
        "ahorro":     res_ahorro,
        "inversiones":inversiones
    }


# ─────────────────────────────────────────────
# PRUEBA
# ─────────────────────────────────────────────
if __name__ == "__main__":
    ingresos_ejemplo = [
        {"fuente": "Beca",            "tipo": "fijo",     "monto": 3000},
        {"fuente": "Trabajo part-time","tipo": "variable", "monto": 2500},
        {"fuente": "Apoyo familiar",  "tipo": "fijo",     "monto": 1000},
    ]
    egresos_ejemplo = [
        {"categoria": "renta",           "descripcion": "Cuarto cerca de la universidad", "monto": 2000, "es_necesario": True},
        {"categoria": "comida",          "descripcion": "Despensa y comida diaria",        "monto": 1500, "es_necesario": True},
        {"categoria": "transporte",      "descripcion": "Camión/metro",                    "monto": 400,  "es_necesario": True},
        {"categoria": "educacion",       "descripcion": "Libros y papelería",              "monto": 300,  "es_necesario": True},
        {"categoria": "entretenimiento", "descripcion": "Salidas, streaming",              "monto": 600,  "es_necesario": False},
        {"categoria": "ropa",            "descripcion": "Ropa y accesorios",               "monto": 400,  "es_necesario": False},
    ]
    resultado = analisis_completo(ingresos_ejemplo, egresos_ejemplo, dia_cobro=1)
    ing = resultado["ingresos"]
    eg  = resultado["egresos"]
    bal = resultado["balance"]
    aho = resultado["ahorro"]
    print("=" * 55)
    print("    ANÁLISIS FINANCIERO PERSONAL - ESTUDIANTE")
    print("=" * 55)
    print(f"\n📥 INGRESOS:  ${ing['total_ingresos']:,.2f}/mes")
    print(f"📤 EGRESOS:   ${eg['total_egresos']:,.2f}/mes")
    print(f"💰 BALANCE:   ${bal['balance_mensual']:,.2f} ({bal['situacion']})")
    print(f"\n🏦 AHORRO: {aho['recomendacion']}")
    if resultado["inversiones"]:
        inv = resultado["inversiones"]
        print(f"\n📈 {inv['mensaje']}")
        for op in inv["opciones"]:
            print(f"   → {op['instrumento']}: {op['rendimiento_anual_pct']}% anual")
    print("\n⚠️  Orientación educativa, no asesoría financiera profesional.")
