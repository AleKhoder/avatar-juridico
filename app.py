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
            #
            # Comprobamos que exista la clave de HeyGen antes de continuar. Si
            # no está definida, mostramos un error y salimos.
            if not HEYGEN_KEY:
                st.error(
                    "No se encontró la clave de HeyGen (HEYGEN_KEY). Configúrala en tus secrets o variables de entorno."
                )
            else:
                vid_req = {
                    "avatar_id": AVATAR_ID,
                    "script": {"type": "text", "input": answer}
                }
                vid_headers = {
                    "x-api-key": HEYGEN_KEY,
                    "Content-Type": "application/json",
                }
                # Solicitar la generación del vídeo
                vid_resp = requests.post(
                    "https://api.heygen.com/v1/video.generate",
                    headers=vid_headers,
                    json=vid_req,
                    timeout=30,
                )
                try:
                    vid_resp.raise_for_status()
                    vid_json = vid_resp.json()
                except Exception as exc:
                    st.error(f"Error al generar el video con HeyGen: {exc}")
                    vid_json = None

                if vid_json and "data" in vid_json and "video_id" in vid_json["data"]:
                    vid_id = vid_json["data"]["video_id"]

                    # Poll de estado
                    status_url = f"https://api.heygen.com/v1/video.status?video_id={vid_id}"
                    start = time.time()
                    status = "processing"
                    while status != "done" and time.time() - start < 90:
                        time.sleep(8)
                        try:
                            status_data = requests.get(status_url, headers=vid_headers, timeout=20).json().get("data", {})
                            status = status_data.get("status", "processing")
                        except Exception:
                            status = "error"
                            break

                    if status == "done":
                        try:
                            vid_data = requests.get(status_url, headers=vid_headers, timeout=20).json().get("data", {})
                            vid_url = vid_data.get("video_url")
                            if vid_url:
                                st.video(vid_url)
                            else:
                                st.error("No se pudo obtener la URL del video.")
                        except Exception as exc:
                            st.error(f"Error al obtener la URL del video: {exc}")
                    else:
                        st.warning(
                            "El video tarda más de lo esperado o falló; refrescá la página en un momento para verlo."
                        )
                else:
                    msg = vid_json.get("message") if isinstance(vid_json, dict) else "Respuesta inesperada de HeyGen"
                    st.error(f"HeyGen no devolvió un video válido: {msg}")

        except Exception as e:
            st.error(f"Ocurrió un error: {e}")
