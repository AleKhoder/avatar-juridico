import os
import time
import uuid
import tempfile
import requests
import streamlit as st
import openai
from dotenv import load_dotenv

# ---------------------------------------------------------
# Cargar claves desde .env (local) o "Secrets" (Streamlit)
# ---------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------
# Lectura de claves de configuración
#
# En Streamlit Community Cloud las variables definidas en la sección
# "Secrets" están disponibles vía st.secrets. Para facilitar el uso tanto
# local (con .env) como en la nube, intentamos leer primero desde el
# entorno y, si no existe, desde st.secrets. Esto evita que claves
# definidas en secrets sean ignoradas por os.getenv().
# ---------------------------------------------------------
def _get_secret(name: str, default: str = "") -> str:
    """Devuelve una clave desde el entorno o st.secrets."""
    value = os.getenv(name)
    if value:
        return value
    # st.secrets podría no existir en ejecución local; usamos getattr
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default

OPENAI_API_KEY = _get_secret("OPENAI_API_KEY")
ELEVEN_KEY     = _get_secret("ELEVEN_KEY")
HEYGEN_KEY     = _get_secret("HEYGEN_KEY")
VOICE_ID       = _get_secret("ELEVEN_VOICE_ID")   # Mariana – v3 u otra
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
            # 1️⃣ Consulta a OpenAI
            chat = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": (
                        "Eres Abogada Virtual. Responde en español rioplatense, claro y sintético (≤200 palabras). "
                        "Cita artículo y ley argentina pertinente, y cierra con: 'Esto es orientación general, consulte a un/a abogado/a matriculado/a'.")},
                    {"role": "user", "content": prompt}
                ]
            )
            answer = chat.choices[0].message.content.strip()
            st.markdown("### Respuesta")
            st.write(answer)

            # 2️⃣ Texto → voz (ElevenLabs v3 ‑ streaming)
            tts_headers = {
                "xi-api-key": ELEVEN_KEY,
                "Content-Type": "application/json",
            }
            tts_payload = {
                "text": answer,
                "model_id": "eleven_v3",
            }
            tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
            r = requests.post(tts_url, headers=tts_headers, json=tts_payload, timeout=60)
            r.raise_for_status()

            # Guardar MP3 temporal
            tmp_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.mp3")
            with open(tmp_path, "wb") as f:
                f.write(r.content)
            st.audio(tmp_path)

            # 3️⃣ Video del avatar (HeyGen)
            vid_req = {
                "avatar_id": AVATAR_ID,
                "script": {"type": "text", "input": answer}
            }
            vid_headers = {
                "x-api-key": HEYGEN_KEY,
                "Content-Type": "application/json",
            }
            vid_json = requests.post("https://api.heygen.com/v1/video.generate",
                                     headers=vid_headers, json=vid_req, timeout=30).json()
            vid_id = vid_json["data"]["video_id"]

            # Poll de estado
            status_url = f"https://api.heygen.com/v1/video.status?video_id={vid_id}"
            start = time.time()
            status = "processing"
            while status != "done" and time.time() - start < 90:
                time.sleep(8)
                status = requests.get(status_url, headers=vid_headers, timeout=20).json()["data"]["status"]

            if status == "done":
                vid_url = requests.get(status_url, headers=vid_headers, timeout=20).json()["data"]["video_url"]
                st.video(vid_url)
            else:
                st.warning("El video tarda más de lo esperado; refrescá la página en un momento para verlo.")

        except Exception as e:
            st.error(f"Ocurrió un error: {e}")
