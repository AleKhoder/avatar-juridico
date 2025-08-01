import os
import time
import requests
import streamlit as st
import openai
from dotenv import load_dotenv

# ------------------------------------------------------------
# Carga de variables de entorno
# ------------------------------------------------------------
# En desarrollo local se leen del archivo .env; en Streamlit Cloud
# se toman de la sección “Secrets”.
load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
ELEVEN_KEY       = os.getenv("ELEVEN_KEY")
HEYGEN_KEY       = os.getenv("HEYGEN_KEY")
AVATAR_ID        = os.getenv("HEYGEN_AVATAR_ID")
VOICE_ID         = os.getenv("ELEVEN_VOICE_ID")
MODEL            = os.getenv("OPENAI_MODEL", "gpt-4o")  # fallback a este modelo
MAX_WAIT_SECONDS = 90  # tiempo máximo para que HeyGen renderice el video

# ------------------------------------------------------------
# Interfaz de usuario con Streamlit
# ------------------------------------------------------------
st.set_page_config(page_title="Asesor Jurídico Virtual", page_icon="⚖️")
st.title("⚖️ Asesor Jurídico Virtual")

question = st.text_input("Escribí tu consulta legal:")

if st.button("Responder") and question:
    with st.spinner("Pensando tu respuesta…"):
        try:
            # ------------------------------------------------
            # 1) Generar respuesta con OpenAI
            # ------------------------------------------------
            chat = openai.ChatCompletion.create(
                model=MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres Abogada Virtual. Responde en español rioplatense, "
                            "en \u2264 200 palabras, citando la norma argentina exacta. "
                            "Finaliza con: 'Esto es orientación general, consulte a un/a abogado/a matriculado/a'."
                        ),
                    },
                    {"role": "user", "content": question},
                ],
            )
            answer = chat.choices[0].message.content.strip()
            st.markdown("### Respuesta")
            st.write(answer)

            # ------------------------------------------------
            # 2) Texto a voz con ElevenLabs
            # ------------------------------------------------
            tts_headers = {
                "xi-api-key": ELEVEN_KEY,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            tts_payload = {
                "text": answer,
                "model_id": "eleven_multilingual_v2",
            }
            tts_url  = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
            tts_json = requests.post(tts_url, headers=tts_headers, json=tts_payload, timeout=30).json()
            audio_url = tts_json["audio_url"]

            # ------------------------------------------------
            # 3) Crear video del avatar con HeyGen
            # ------------------------------------------------
            video_req = {
                "avatar_id": AVATAR_ID,
                "source_url": audio_url,
                "script": {"type": "text", "input": answer},
            }
            video_headers = {
                "x-api-key": HEYGEN_KEY,
                "Content-Type": "application/json",
            }
            video_json = requests.post(
                "https://api.heygen.com/v1/video.generate",
                headers=video_headers,
                json=video_req,
                timeout=30,
            ).json()

            video_id = video_json["data"]["video_id"]
            status_url = f"https://api.heygen.com/v1/video.status?video_id={video_id}"

            # ------------------------------------------------
            # 4) Esperar a que termine el render (polling)
            # ------------------------------------------------
            start = time.time()
            status = "processing"
            while status != "done" and (time.time() - start) < MAX_WAIT_SECONDS:
                time.sleep(8)
                status = requests.get(status_url, headers=video_headers, timeout=30).json()["data"]["status"]

            if status == "done":
                video_url = requests.get(status_url, headers=video_headers, timeout=30).json()["data"]["video_url"]
                st.video(video_url)
            else:
                st.error("La generación de video demoró demasiado. Intentalo de nuevo en unos minutos.")

            # ------------------------------------------------
            # 5) Audio opcional
            # ------------------------------------------------
            if st.checkbox("Escuchar respuesta"):
                st.audio(audio_url)

        except Exception as err:
            st.error(f"Ocurrió un error: {err}")
