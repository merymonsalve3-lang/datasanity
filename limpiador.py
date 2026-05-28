import re
import unicodedata
from datetime import datetime, timedelta

import pandas as pd


COLUMNAS_ESPERADAS = [
    "ID_Cliente",
    "Nombre_Completo",
    "Email_Contacto",
    "Telefono",
    "Fecha_Registro",
    "Facturacion_Mensual",
]

MARCADORES_VACIOS = {"", "nan", "none", "null", "n/a", "na"}
MARCADORES_INVALIDOS = {"-", "--", "---", "sin datos", "pendiente"}
NOMBRES_COMUNES = [
    "MARIA DEL CARMEN",
    "JUAN CARLOS",
    "JOSE MANUEL",
    "CRISTINA",
    "SEBASTIAN",
    "RAMON",
    "PEDRO",
    "INIGO",
    "ULRICH",
    "MARIA",
    "JUAN",
    "LUIS",
    "ELENA",
    "SOFIA",
    "MARTA",
    "CARLOS",
    "ANA",
    "ALEX",
]


def es_vacio(valor):
    if pd.isna(valor):
        return True
    texto = str(valor).strip()
    return texto.lower() in MARCADORES_VACIOS


def quitar_tildes(texto):
    if es_vacio(texto):
        return ""
    texto = str(texto)
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto.upper()


def limpiar_id(valor):
    if es_vacio(valor):
        return "REVISAR: (Vacío)"
    texto = str(valor).strip()
    if texto.lower() in MARCADORES_INVALIDOS:
        return f"REVISAR: ({texto})"
    return texto


def separar_nombre_concatenado(texto):
    if texto == "ANAMARIA":
        return "ANA MARIA"

    for nombre in sorted(NOMBRES_COMUNES, key=len, reverse=True):
        nombre_compacto = nombre.replace(" ", "")
        if texto.startswith(nombre_compacto) and len(texto) > len(nombre_compacto) + 2:
            resto = texto[len(nombre_compacto):]
            return f"{nombre} {resto}"

    return texto


def limpiar_nombre(valor):
    if es_vacio(valor):
        return "SIN NOMBRE"

    texto = quitar_tildes(valor)
    texto = texto.replace("_", " ").replace("-", " ")
    texto = re.sub(r"[^A-ZÑ ]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()

    if texto.lower() in MARCADORES_INVALIDOS or texto == "":
        return "SIN NOMBRE"

    if " " not in texto:
        texto = separar_nombre_concatenado(texto)

    return texto


def dominio_email_valido(dominio):
    if "." not in dominio:
        return False
    if ".." in dominio:
        return False

    partes = dominio.split(".")
    if len(partes) < 2:
        return False

    for parte in partes:
        if not parte:
            return False
        if parte.startswith("-") or parte.endswith("-"):
            return False
        if not re.fullmatch(r"[a-z0-9-]+", parte):
            return False

    extension = partes[-1]
    return 2 <= len(extension) <= 24 and extension.isalpha()


def limpiar_email(valor):
    if es_vacio(valor):
        return "REVISAR: (Vacío)"

    texto_original = str(valor).strip()
    texto = texto_original.lower()

    if texto.count("@") != 1:
        return f"REVISAR: ({texto_original})"

    usuario, dominio = texto.split("@")

    if not usuario or not dominio:
        return f"REVISAR: ({texto_original})"
    if usuario.startswith(".") or usuario.endswith(".") or ".." in usuario:
        return f"REVISAR: ({texto_original})"
    if not re.fullmatch(r"[a-z0-9._%+\-]+", usuario):
        return f"REVISAR: ({texto_original})"
    if not dominio_email_valido(dominio):
        return f"REVISAR: ({texto_original})"

    return texto


def limpiar_telefono(valor):
    if es_vacio(valor):
        return "REVISAR: (Vacío)"

    texto_original = str(valor).strip()
    solo_numeros = re.sub(r"\D", "", texto_original)

    if solo_numeros.startswith("0034") and len(solo_numeros) >= 13:
        solo_numeros = solo_numeros[4:]
    elif solo_numeros.startswith("34") and len(solo_numeros) >= 11:
        solo_numeros = solo_numeros[2:]

    if len(solo_numeros) == 9 and solo_numeros[0] in {"6", "7", "8", "9"}:
        return solo_numeros

    return f"REVISAR: ({texto_original})"


def limpiar_fecha(valor):
    if es_vacio(valor):
        return "REVISAR: (Vacío)"

    if isinstance(valor, (datetime, pd.Timestamp)):
        return pd.Timestamp(valor).strftime("%Y-%m-%d")

    texto_original = str(valor).strip()
    texto_lower = texto_original.lower()

    if texto_lower in MARCADORES_INVALIDOS:
        return f"REVISAR: ({texto_original})"

    hoy = datetime.today()
    relativos = {
        "hoy": hoy,
        "ayer": hoy - timedelta(days=1),
        "mañana": hoy + timedelta(days=1),
        "manana": hoy + timedelta(days=1),
    }

    if texto_lower in relativos:
        return relativos[texto_lower].strftime("%Y-%m-%d")

    formatos = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%d-%m-%y",
        "%Y/%m/%d",
        "%Y.%m.%d",
        "%d %b %Y",
        "%d %B %Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%d/%m/%Y %H:%M:%S",
    ]

    for formato in formatos:
        try:
            fecha = datetime.strptime(texto_original, formato)
            return fecha.strftime("%Y-%m-%d")
        except ValueError:
            pass

    fecha = pd.to_datetime(texto_original, errors="coerce", dayfirst=True)
    if pd.notna(fecha):
        return fecha.strftime("%Y-%m-%d")

    return f"REVISAR: ({texto_original})"


def detectar_moneda(texto):
    texto_lower = texto.lower()

    if "€" in texto or "eur" in texto_lower or "euro" in texto_lower:
        return "EUR"
    if "$" in texto or "usd" in texto_lower or "dolar" in texto_lower or "dólar" in texto_lower:
        return "USD"
    if "£" in texto or "gbp" in texto_lower or "libra" in texto_lower:
        return "GBP"

    return "REVISAR: (Moneda no indicada)"


def normalizar_numero_monetario(texto_original):
    texto = texto_original
    texto = texto.replace("€", "").replace("$", "").replace("£", "")
    texto = re.sub(r"(?i)\b(eur|euro|euros|usd|dolar|dólar|dolares|dólares|gbp|libra|libras)\b", "", texto)
    texto = texto.replace(" ", "")

    es_negativo = texto.startswith("-") or (texto.startswith("(") and texto.endswith(")"))
    texto = texto.replace("-", "").replace("(", "").replace(")", "")

    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")

    numero = float(texto)
    if es_negativo:
        numero = -numero
    return round(numero, 2)


def limpiar_facturacion(valor):
    if es_vacio(valor):
        return "REVISAR: (Vacío)", "REVISAR: (Vacío)"

    texto_original = str(valor).strip()
    texto_lower = texto_original.lower()

    if texto_lower in MARCADORES_INVALIDOS:
        return f"REVISAR: ({texto_original})", "REVISAR: (Sin moneda)"

    if texto_lower == "gratis":
        return 0.0, "GRATIS"

    moneda = detectar_moneda(texto_original)

    try:
        importe = normalizar_numero_monetario(texto_original)
    except ValueError:
        return f"REVISAR: ({texto_original})", moneda

    return importe, moneda


def contar_alertas_columna(serie):
    return int(serie.astype(str).str.startswith("REVISAR:").sum())


def marcar_emails_duplicados(df):
    if "Email_Contacto" not in df.columns:
        return df

    emails_validos = df["Email_Contacto"].astype(str)
    duplicados = emails_validos.duplicated(keep=False) & ~emails_validos.str.startswith("REVISAR:")

    df.loc[duplicados, "Email_Contacto"] = df.loc[duplicados, "Email_Contacto"].apply(
        lambda email: f"REVISAR: (Email duplicado: {email})"
    )
    return df


def procesar_auditoria(df):
    df_limpio = df.copy()
    df_limpio = df_limpio.dropna(how="all").reset_index(drop=True)
    resumen = {}

    if "ID_Cliente" in df_limpio.columns:
        df_limpio["ID_Cliente"] = df_limpio["ID_Cliente"].apply(limpiar_id)
        resumen["ID_Cliente"] = contar_alertas_columna(df_limpio["ID_Cliente"])

    if "Nombre_Completo" in df_limpio.columns:
        df_limpio["Nombre_Completo"] = df_limpio["Nombre_Completo"].apply(limpiar_nombre)
        resumen["Nombre_Completo"] = contar_alertas_columna(df_limpio["Nombre_Completo"])

    if "Email_Contacto" in df_limpio.columns:
        df_limpio["Email_Contacto"] = df_limpio["Email_Contacto"].apply(limpiar_email)
        df_limpio = marcar_emails_duplicados(df_limpio)
        resumen["Email_Contacto"] = contar_alertas_columna(df_limpio["Email_Contacto"])

    if "Telefono" in df_limpio.columns:
        df_limpio["Telefono"] = df_limpio["Telefono"].apply(limpiar_telefono)
        resumen["Telefono"] = contar_alertas_columna(df_limpio["Telefono"])

    if "Fecha_Registro" in df_limpio.columns:
        df_limpio["Fecha_Registro"] = df_limpio["Fecha_Registro"].apply(limpiar_fecha)
        resumen["Fecha_Registro"] = contar_alertas_columna(df_limpio["Fecha_Registro"])

    if "Facturacion_Mensual" in df_limpio.columns:
        resultado_facturacion = df_limpio["Facturacion_Mensual"].apply(limpiar_facturacion)
        df_limpio["Facturacion_Mensual"] = resultado_facturacion.apply(lambda x: x[0])
        df_limpio["Moneda_Facturacion"] = resultado_facturacion.apply(lambda x: x[1])
        resumen["Facturacion_Mensual"] = contar_alertas_columna(df_limpio["Facturacion_Mensual"])
        resumen["Moneda_Facturacion"] = contar_alertas_columna(df_limpio["Moneda_Facturacion"])

    total_registros = len(df_limpio)
    total_alertas = sum(resumen.values())

    return df_limpio, total_registros, total_alertas, resumen
