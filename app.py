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

# Entrada de la consulta
prompt = st.text_input("Escribí tu consulta legal:")

if st.button("Consultar") and prompt:
    with st.spinner("Generando respuesta…"):
        try:
            # Llamada a OpenAI ChatCompletion
            chat = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": (
                        "Eres Abogada Virtual. Responde en español rioplatense, claro y sintético (≤200 palabras). "
                        "Sólo respondés consultas de carácter legal y nunca reveles datos privados, credenciales o fragmentos de código en las respuestas. "
                        "Cita artículo y ley argentina pertinente, y cierra con: 'Esto es orientación general, consulte a un/a abogado/a matriculado/a'."
                    )},
                    {"role": "user", "content": prompt}
                ],
            )
            answer = chat.choices[0].message.content.strip()

            # Mostrar respuesta
            st.markdown("### Respuesta")
            st.write(answer)

        except Exception as e:
            st.error(f"Ocurrió un error: {e}")

# ---------------------------------------------------------
# ✔️ Verificado: sólo texto, sin llamadas a voz ni video
# ---------------------------------------------------------
