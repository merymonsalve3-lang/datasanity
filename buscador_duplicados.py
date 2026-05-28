import itertools
import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher

import pandas as pd


COLUMNAS_CLIENTE = [
    "ID_Cliente",
    "Nombre_Completo",
    "Email_Contacto",
    "Telefono",
    "Fecha_Registro",
    "Facturacion_Mensual",
]

VALORES_VACIOS = {"", "nan", "none", "null", "n/a", "na", "-", "--", "---", "sin datos", "pendiente"}


def es_vacio(valor):
    if pd.isna(valor):
        return True
    return str(valor).strip().lower() in VALORES_VACIOS


def texto_base(valor):
    if es_vacio(valor):
        return ""
    texto = str(valor).strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto.upper()


def normalizar_nombre(valor):
    texto = texto_base(valor)
    texto = texto.replace("_", " ").replace("-", " ")
    texto = re.sub(r"[^A-ZÑ ]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    if texto in {"", "SIN NOMBRE"}:
        return ""
    return texto


def nombre_compacto(valor):
    return re.sub(r"\s+", "", normalizar_nombre(valor))


def normalizar_email(valor):
    if es_vacio(valor):
        return ""
    email = str(valor).strip().lower()
    if email.count("@") != 1:
        return ""
    usuario, dominio = email.split("@")
    if not usuario or not dominio or "." not in dominio:
        return ""
    if usuario.startswith(".") or usuario.endswith(".") or ".." in usuario:
        return ""
    if ".." in dominio:
        return ""
    return email


def normalizar_telefono(valor):
    if es_vacio(valor):
        return ""

    numeros = re.sub(r"\D", "", str(valor))
    if numeros.startswith("0034") and len(numeros) >= 13:
        numeros = numeros[4:]
    elif numeros.startswith("34") and len(numeros) >= 11:
        numeros = numeros[2:]

    if len(numeros) == 9 and numeros[0] in {"6", "7", "8", "9"}:
        return numeros
    return ""


def similitud_nombre(nombre_a, nombre_b):
    if not nombre_a or not nombre_b:
        return 0.0

    compacto_a = re.sub(r"\s+", "", nombre_a)
    compacto_b = re.sub(r"\s+", "", nombre_b)
    ratio_compacto = SequenceMatcher(None, compacto_a, compacto_b).ratio()
    ratio_completo = SequenceMatcher(None, nombre_a, nombre_b).ratio()

    tokens_a = set(nombre_a.split())
    tokens_b = set(nombre_b.split())
    overlap = len(tokens_a & tokens_b) / max(len(tokens_a | tokens_b), 1)

    return max(ratio_compacto, ratio_completo, overlap)


def valor_util(valor):
    return not es_vacio(valor) and not str(valor).startswith("REVISAR:")


def contar_campos_utiles(fila):
    return sum(valor_util(valor) for valor in fila.values)


def generar_bloques(df_norm):
    bloques = defaultdict(set)

    for idx, fila in df_norm.iterrows():
        email = fila["_email_norm"]
        telefono = fila["_telefono_norm"]
        compacto = fila["_nombre_compacto"]

        if email:
            bloques[f"email:{email}"].add(idx)
        if telefono:
            bloques[f"telefono:{telefono}"].add(idx)
        if compacto and len(compacto) >= 8:
            bloques[f"nombre_compacto:{compacto[:10]}"].add(idx)

    pares = set()
    for indices in bloques.values():
        if 1 < len(indices) <= 80:
            for a, b in itertools.combinations(sorted(indices), 2):
                pares.add((a, b))

    return pares


def evaluar_par(df_norm, idx_a, idx_b):
    a = df_norm.loc[idx_a]
    b = df_norm.loc[idx_b]

    email_match = bool(a["_email_norm"] and a["_email_norm"] == b["_email_norm"])
    telefono_match = bool(a["_telefono_norm"] and a["_telefono_norm"] == b["_telefono_norm"])
    nombre_ratio = similitud_nombre(a["_nombre_norm"], b["_nombre_norm"])

    puntuacion = 0
    motivos = []

    if email_match:
        puntuacion += 55
        motivos.append("email exacto")
    if telefono_match:
        puntuacion += 45
        motivos.append("telefono exacto")

    if nombre_ratio >= 0.97:
        puntuacion += 35
        motivos.append("nombre casi igual")
    elif nombre_ratio >= 0.90:
        puntuacion += 28
        motivos.append("nombre muy parecido")
    elif nombre_ratio >= 0.82:
        puntuacion += 20
        motivos.append("nombre parecido")
    elif nombre_ratio >= 0.72:
        puntuacion += 12
        motivos.append("nombre algo parecido")

    if not email_match and not telefono_match and nombre_ratio < 0.90:
        return None

    if email_match and telefono_match:
        puntuacion = max(puntuacion, 98)
    elif email_match and nombre_ratio >= 0.72:
        puntuacion = max(puntuacion, 92)
    elif telefono_match and nombre_ratio >= 0.72:
        puntuacion = max(puntuacion, 90)
    elif email_match:
        puntuacion = max(puntuacion, 84)
    elif telefono_match:
        puntuacion = max(puntuacion, 82)

    puntuacion = min(puntuacion, 100)

    if puntuacion >= 90:
        nivel = "ALTA"
    elif puntuacion >= 78:
        nivel = "MEDIA"
    else:
        nivel = "BAJA"

    return {
        "Fila_A": int(a["_fila_original"]),
        "Fila_B": int(b["_fila_original"]),
        "ID_A": a.get("ID_Cliente", ""),
        "ID_B": b.get("ID_Cliente", ""),
        "Nombre_A": a.get("Nombre_Completo", ""),
        "Nombre_B": b.get("Nombre_Completo", ""),
        "Email_A": a.get("Email_Contacto", ""),
        "Email_B": b.get("Email_Contacto", ""),
        "Telefono_A": a.get("Telefono", ""),
        "Telefono_B": b.get("Telefono", ""),
        "Score": puntuacion,
        "Confianza": nivel,
        "Similitud_Nombre": round(nombre_ratio * 100, 1),
        "Motivos": ", ".join(motivos),
    }


def buscar_pares_duplicados(df, umbral=78):
    df_norm = df.copy().dropna(how="all").reset_index(drop=True)
    df_norm["_fila_original"] = df_norm.index + 2

    for columna in COLUMNAS_CLIENTE:
        if columna not in df_norm.columns:
            df_norm[columna] = ""

    df_norm["_nombre_norm"] = df_norm["Nombre_Completo"].apply(normalizar_nombre)
    df_norm["_nombre_compacto"] = df_norm["Nombre_Completo"].apply(nombre_compacto)
    df_norm["_email_norm"] = df_norm["Email_Contacto"].apply(normalizar_email)
    df_norm["_telefono_norm"] = df_norm["Telefono"].apply(normalizar_telefono)

    resultados = []
    for idx_a, idx_b in generar_bloques(df_norm):
        resultado = evaluar_par(df_norm, idx_a, idx_b)
        if resultado and resultado["Score"] >= umbral:
            resultados.append(resultado)

    pares = pd.DataFrame(resultados)
    if not pares.empty:
        pares = pares.sort_values(["Score", "Fila_A", "Fila_B"], ascending=[False, True, True]).reset_index(drop=True)

    return df_norm, pares


class UnionFind:
    def __init__(self, valores):
        self.parent = {valor: valor for valor in valores}

    def find(self, valor):
        if self.parent[valor] != valor:
            self.parent[valor] = self.find(self.parent[valor])
        return self.parent[valor]

    def union(self, a, b):
        raiz_a = self.find(a)
        raiz_b = self.find(b)
        if raiz_a != raiz_b:
            self.parent[raiz_b] = raiz_a


def construir_grupos(df_norm, pares):
    if pares.empty:
        return pd.DataFrame(), pd.DataFrame()

    filas = sorted(set(pares["Fila_A"]).union(set(pares["Fila_B"])))
    uf = UnionFind(filas)

    for _, par in pares.iterrows():
        if par["Confianza"] in {"ALTA", "MEDIA"}:
            uf.union(int(par["Fila_A"]), int(par["Fila_B"]))

    grupos_raw = defaultdict(list)
    for fila in filas:
        grupos_raw[uf.find(fila)].append(fila)

    grupos = []
    asignaciones = []
    for numero_grupo, filas_grupo in enumerate(grupos_raw.values(), start=1):
        if len(filas_grupo) < 2:
            continue

        filas_df = df_norm[df_norm["_fila_original"].isin(filas_grupo)].copy()
        indices = list(filas_df.index)
        maestro_idx = max(indices, key=lambda idx: contar_campos_utiles(df_norm.loc[idx, COLUMNAS_CLIENTE]))
        maestro = df_norm.loc[maestro_idx]

        max_score = int(
            pares[
                pares["Fila_A"].isin(filas_grupo) & pares["Fila_B"].isin(filas_grupo)
                | pares["Fila_A"].isin(filas_grupo) & pares["Fila_B"].isin(filas_grupo)
            ]["Score"].max()
        )

        grupos.append(
            {
                "Grupo_Duplicado": numero_grupo,
                "Registros_En_Grupo": len(filas_grupo),
                "Filas_Originales": ", ".join(map(str, sorted(filas_grupo))),
                "Fila_Maestra_Sugerida": int(maestro["_fila_original"]),
                "ID_Maestro": maestro.get("ID_Cliente", ""),
                "Nombre_Maestro": maestro.get("Nombre_Completo", ""),
                "Email_Maestro": maestro.get("Email_Contacto", ""),
                "Telefono_Maestro": maestro.get("Telefono", ""),
                "Score_Maximo": max_score,
            }
        )

        for fila in filas_grupo:
            asignaciones.append({"Fila_Original": fila, "Grupo_Duplicado": numero_grupo})

    return pd.DataFrame(grupos), pd.DataFrame(asignaciones)


def fusionar_valores(valores):
    utiles = [valor for valor in valores if valor_util(valor)]
    if not utiles:
        return ""

    primero = utiles[0]
    distintos = []
    vistos = set()
    for valor in utiles:
        clave = str(valor).strip().lower()
        if clave not in vistos:
            vistos.add(clave)
            distintos.append(valor)

    if len(distintos) == 1:
        return primero

    return " | ".join(str(valor) for valor in distintos)


def construir_fusion_sugerida(df_norm, grupos_df):
    if grupos_df.empty:
        return pd.DataFrame()

    filas_fusionadas = []
    columnas_usuario = [col for col in df_norm.columns if not col.startswith("_")]

    for _, grupo in grupos_df.iterrows():
        filas = [int(x.strip()) for x in grupo["Filas_Originales"].split(",")]
        bloque = df_norm[df_norm["_fila_original"].isin(filas)]

        fila_fusionada = {"Grupo_Duplicado": grupo["Grupo_Duplicado"]}
        for columna in columnas_usuario:
            fila_fusionada[columna] = fusionar_valores(bloque[columna].tolist())
        fila_fusionada["Filas_Fusionadas"] = grupo["Filas_Originales"]
        fila_fusionada["Revision_Necesaria"] = "SI" if any(" | " in str(v) for v in fila_fusionada.values()) else "NO"
        filas_fusionadas.append(fila_fusionada)

    return pd.DataFrame(filas_fusionadas)


def analizar_duplicados(df, umbral=78):
    df_norm, pares = buscar_pares_duplicados(df, umbral=umbral)
    grupos, asignaciones = construir_grupos(df_norm, pares)
    fusion = construir_fusion_sugerida(df_norm, grupos)

    df_marcado = df_norm[[col for col in df_norm.columns if not col.startswith("_")]].copy()
    if not asignaciones.empty:
        df_marcado = df_marcado.merge(
            asignaciones,
            how="left",
            left_on=df_norm["_fila_original"],
            right_on="Fila_Original",
        )
        df_marcado = df_marcado.drop(columns=["key_0", "Fila_Original"], errors="ignore")
    else:
        df_marcado["Grupo_Duplicado"] = ""

    resumen = {
        "registros_analizados": len(df_norm),
        "pares_detectados": len(pares),
        "grupos_detectados": len(grupos),
        "registros_implicados": int(df_marcado["Grupo_Duplicado"].notna().sum()) if "Grupo_Duplicado" in df_marcado else 0,
    }

    return {
        "resumen": resumen,
        "pares": pares,
        "grupos": grupos,
        "fusion_sugerida": fusion,
        "base_marcada": df_marcado,
    }
