import ssl
import httpx
from elevenlabs.client import ElevenLabs
from elevenlabs import play
from dotenv import load_dotenv

load_dotenv()

# Create an SSL context with the specified certificate path
context = ssl.create_default_context(cafile="C:/Program Files/OpenSSL-Win64/ssl/cacert.pem")

# Create a custom HTTP client with the SSL context
client = httpx.Client(verify=context)

# Use the custom HTTP client for the ElevenLabs client
elevenlabs_client = ElevenLabs()

# Monkey patch the httpx client used by ElevenLabs
elevenlabs_client._client = client

audio = elevenlabs_client.text_to_speech.convert(
    text="The first move is what sets everything in motion.",
    voice_id="cclclCaJslL1xziwefCeTNzHv",
    model_id="eleven_multilingual_v2",
    output_format="mp3_44100_128",
)

play(audio)