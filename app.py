import os
import streamlit as st
import openai
from dotenv import load_dotenv

# ---------------------------------------------------------
# Cargar configuración de entorno
# ---------------------------------------------------------
load_dotenv()

def _get_secret(name: str, default: str = "") -> str:
    """Retorna valor de entorno o st.secrets"""
    val = os.getenv(name)
    if val:
        return val
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default

# Claves y modelo de OpenAI
OPENAI_API_KEY = _get_secret("OPENAI_API_KEY")
OPENAI_MODEL   = _get_secret("OPENAI_MODEL", "gpt-4o")
openai.api_key = OPENAI_API_KEY

# ---------------------------------------------------------
# Configuración de la app Streamlit
# ---------------------------------------------------------
st.set_page_config(page_title="Asesor Jurídico Virtual", page_icon="⚖️")
st.title("⚖️ Asesor Jurídico Virtual")

# Inicializar estado para respuesta
def _init_state():
    if 'answer' not in st.session_state:
        st.session_state.answer = None
    if 'prompt' not in st.session_state:
        st.session_state.prompt = ""

_init_state()

# Callback para limpiar input y respuesta
def clear():
    st.session_state.prompt = ""
    st.session_state.answer = None

# Entrada de la consulta
o_prompt = st.text_input("Escribí tu consulta legal:", key="prompt")

# Botones en columnas
col1, col2 = st.columns(2)
with col1:
    if st.button("Consultar") and st.session_state.prompt:
        with st.spinner("Generando respuesta…"):
            try:
                chat = openai.ChatCompletion.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": (
                            "Eres Abogada Virtual. Responde en español rioplatense, claro y sintético (≤200 palabras). "
                            "Sólo respondés consultas de carácter legal y nunca reveles datos privados, credenciales o fragmentos de código en las respuestas. "
                            "Cita artículo y ley argentina pertinente, y cierra con: 'Esto es orientación general, consulte a un/a abogado/a matriculado/a'."
                        )},
                        {"role": "user", "content": st.session_state.prompt}
                    ],
                )
                st.session_state.answer = chat.choices[0].message.content.strip()
            except Exception as e:
                st.error(f"Ocurrió un error: {e}")
with col2:
    # Mostrar botón 'Limpiar' solo si hay texto en el cuadro
    if st.session_state.prompt:
        st.button("Limpiar", on_click=clear)

# Mostrar respuesta si existe
if st.session_state.answer:
    st.markdown("### Respuesta")
    st.write(st.session_state.answer)

# ---------------------------------------------------------
# ✔️ Verificado: 'Limpiar' usa callback y aparece sólo cuando hay texto
# ---------------------------------------------------------
