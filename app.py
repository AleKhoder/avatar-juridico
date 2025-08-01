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
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY")
ELEVEN_KEY       = os.getenv("ELEVEN_KEY")
HEYGEN_KEY       = os.getenv("HEYGEN_KEY")
VOICE_ID         = os.getenv("ELEVEN_VOICE_ID")   # Mariana – v3
AVATAR_ID        = os.getenv("HEYGEN_AVATAR_ID")
OPENAI_MODEL     = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

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

            # 2️⃣ Texto → voz (ElevenLabs v3)
            #
            # Usamos el endpoint sin streaming. Algunas voces o cuentas no
            # permiten el uso de /stream y devuelven un error 403. El endpoint
            # sin sufijo /stream devuelve el audio completo en el cuerpo de la
            # respuesta. Puedes ajustar ``model_id`` según tus necesidades.
            tts_headers = {
                "xi-api-key": ELEVEN_KEY,
                "Content-Type": "application/json",
            }
            tts_payload = {
                "text": answer,
                "model_id": "eleven_v3",
            }
            # Endpoint de ElevenLabs sin streaming
            tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
            tts_resp = requests.post(tts_url, headers=tts_headers, json=tts_payload, timeout=60)
            tts_resp.raise_for_status()

            # Guardar MP3 temporal
            tmp_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.mp3")
            with open(tmp_path, "wb") as f:
                f.write(tts_resp.content)
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
