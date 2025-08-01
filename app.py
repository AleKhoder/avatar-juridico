import os
import time
import requests
import streamlit as st
import openai
from dotenv import load_dotenv

# ---------------------------------------------------------
# Cargar claves desde .env (local) o "Secrets" (Streamlit)
# ---------------------------------------------------------
load_dotenv()

# Utilidad para leer variables primero del entorno y luego de st.secrets

def _get_secret(name: str, default: str = "") -> str:
    val = os.getenv(name)
    if val:
        return val
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default

OPENAI_API_KEY = _get_secret("OPENAI_API_KEY")
HEYGEN_KEY     = _get_secret("HEYGEN_KEY")
AVATAR_ID      = _get_secret("HEYGEN_AVATAR_ID")
OPENAI_MODEL   = _get_secret("OPENAI_MODEL", "gpt-3.5-turbo")

openai.api_key = OPENAI_API_KEY

# ---------------------------------------------------------
# Configuración de Streamlit
# ---------------------------------------------------------
st.set_page_config(page_title="Asesor Jurídico Virtual", page_icon="⚖️")
st.title("⚖️ Asesor Jurídico Virtual")

prompt = st.text_input("Escribí tu consulta legal:")

if st.button("Responder") and prompt:
    with st.spinner("Generando respuesta…"):
        try:
            # 1️⃣ Obtener respuesta de ChatGPT
            response = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres Abogada Virtual. Responde en español rioplatense, claro y sintético (≤200 palabras). "
                            "Cita artículo y ley argentina pertinente, y cierra con: 'Esto es orientación general, consulte a un/a abogado/a matriculado/a'."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            answer = response.choices[0].message.content.strip()

            st.markdown("### Respuesta")
            st.write(answer)

            # 2️⃣ Generar vídeo con voz incorporada usando HeyGen (sin ElevenLabs)
            heygen_headers = {
                "x-api-key": HEYGEN_KEY,
                "Content-Type": "application/json",
            }
            vid_request = {
                "avatar_id": AVATAR_ID,
                "script": {"type": "text", "input": answer},
            }

            vid_resp = requests.post(
                "https://api.heygen.com/v1/video.generate",
                headers=heygen_headers,
                json=vid_request,
                timeout=30,
            )
            vid_resp.raise_for_status()
            vid_id = vid_resp.json()["data"]["video_id"]

            # Poll de estado hasta 90 s
            status_url = f"https://api.heygen.com/v1/video.status?video_id={vid_id}"
            status = "processing"
            start = time.time()
            while status != "done" and time.time() - start < 90:
                time.sleep(8)
                status_resp = requests.get(status_url, headers=heygen_headers, timeout=20)
                status_resp.raise_for_status()
                status = status_resp.json()["data"]["status"]

            if status == "done":
                vid_url = requests.get(status_url, headers=heygen_headers, timeout=20).json()["data"]["video_url"]
                st.video(vid_url)
            else:
                st.warning("El video tarda más de lo esperado; refrescá la página más tarde para verlo.")

        except Exception as e:
            st.error(f"Ocurrió un error: {e}")
