import os
import time
import uuid
import tempfile
import requests
import streamlit as st
import openai
from dotenv import load_dotenv

# ------------------------------------------------------------------
# Cargar variables de entorno (.env local) o Secrets (Streamlit Cloud)
# ------------------------------------------------------------------
load_dotenv()

OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY")
ELEVEN_KEY       = os.getenv("ELEVEN_KEY")
HEYGEN_KEY       = os.getenv("HEYGEN_KEY")
AVATAR_ID        = os.getenv("HEYGEN_AVATAR_ID")
VOICE_ID         = os.getenv("ELEVEN_VOICE_ID")  # Mariana – v3
OPENAI_MODEL     = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
MAX_WAIT_SECONDS = 90

openai.api_key = OPENAI_API_KEY

# ------------------------------------------------------------------
# Streamlit UI
# ------------------------------------------------------------------
st.set_page_config(page_title="Asesor Jurídico Virtual", page_icon="⚖️")
st.title("⚖️ Asesor Jurídico Virtual")

query = st.text_input("Escribí tu consulta legal:")
if st.button("Responder") and query:
    with st.spinner("Pensando…"):
        try:
            # 1) Generar respuesta con OpenAI
            chat = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": (
                        "Eres Abogada Virtual. Responde en español rioplatense, ≤200 palabras, "
                        "citando la norma argentina exacta y finaliza con: 'Esto es orientación general, "
                        "consulte a un/a abogado/a matriculado/a'.")},
                    {"role": "user", "content": query}
                ]
            )
            answer = chat.choices[0].message.content.strip()
            st.markdown("### Respuesta")
            st.write(answer)

            # 2) Texto → voz (ElevenLabs v3 devuelve bytes)
            tts_headers = {
                "xi-api-key": ELEVEN_KEY,
                "Content-Type": "application/json",
            }
            tts_payload = {
                "text": answer,
                "model_id": "eleven_v3",
            }
            res = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
                headers=tts_headers,
                json=tts_payload,
                timeout=45,
            )
            res.raise_for_status()

            # Guardar MP3 temporal
            tmp_mp3 = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.mp3")
            with open(tmp_mp3, "wb") as f:
                f.write(res.content)
            st.audio(tmp_mp3)

            # 3) Generar video del avatar (sin source_url)
            video_req = {
                "avatar_id": AVATAR_ID,
                "script": {"type": "text", "input": answer}
            }
            video_headers = {
                "x-api-key": HEYGEN_KEY,
                "Content-Type": "application/json",
            }
            v_json = requests.post(
                "https://api.heygen.com/v1/video.generate",
                headers=video_headers,
                json=video_req,
                timeout=30,
            ).json()
            vid_id = v_json["data"]["video_id"]
            status_url = f"https://api.heygen.com/v1/video.status?video_id={vid_id}"

            start = time.time()
            status = "processing"
            while status != "done" and (time.time() - start) < MAX_WAIT_SECONDS:
                time.sleep(8)
                status = requests.get(status_url, headers=video_headers, timeout=30).json()["data"]["status"]

            if status == "done":
                vid_url = requests.get(status_url, headers=video_headers, timeout=30).json()["data"]["video_url"]
                st.video(vid_url)
            else:
                st.warning("El video tardó demasiado en generarse; intentá de nuevo más tarde.")

        except Exception as e:
            st.error(f"Ocurrió un error: {e}")
