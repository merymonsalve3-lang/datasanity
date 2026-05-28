# DataSanity

DataSanity es una herramienta web creada con Streamlit para auditar bases de datos, detectar duplicados y generar dashboards automáticos a partir de archivos Excel o CSV.

## Acceso a la aplicación

[Entrar en DataSanity](https://datasanity.streamlit.app)

> Nota: la aplicación está desplegada en Streamlit Cloud con acceso restringido. El acceso se habilita individualmente para usuarios autorizados.

## Contenido

- `app.py`: navegacion principal de la app 3 en 1.
- `pages/00_Auditoria_de_datos.py`: Auditoria de datos.
- `pages/01_Buscador_de_duplicados.py`: Buscador de duplicados.
- `pages/02_Generador_dashboard.py`: Generador de dashboards.
- `limpiador.py`, `buscador_duplicados.py`, `generador_dashboard.py`: logica interna usada por las apps.
- `requirements.txt`: dependencias necesarias para que Streamlit Cloud instale el entorno.
- `runtime.txt`: version recomendada de Python para el despliegue.

## Publicacion en Streamlit Community Cloud

1. Sube esta carpeta a un repositorio de GitHub.
2. En Streamlit Community Cloud, crea una app nueva desde ese repositorio.
3. Como archivo principal selecciona `app.py`.
4. Streamlit detectara automaticamente las otras herramientas dentro de `pages/`.

## Nota

No subas `venv`, `__pycache__`, archivos temporales ni bases de clientes reales al repositorio.
## Autores

DataSanity es un proyecto desarrollado conjuntamente por [Bruno Belón Madan](https://github.com/brunobelonmadan) y [María Monsalve Pérez](https://github.com/merymonsalve3-lang).
