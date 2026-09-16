import gradio as gr
from app.main import app

with gr.Blocks(title="MUYU API - SONIK / BEAT") as demo:
    gr.Markdown("# 🎵 MUYU API Backend")
    gr.Markdown("Backend API untuk aplikasi **SONIK / BEAT** berjalan secara live!")
    gr.Markdown("""
### 📡 Quick Links:
- **Interactive OpenAPI / Swagger UI:** [/docs](/docs)
- **ReDoc Documentation:** [/redoc](/redoc)
- **Server Healthcheck:** [/health](/health)

### 🎧 Endpoint API:
- `GET /api/playlist/parse?url=...`
- `GET /api/track/{videoId}/stream`
- `GET /api/playlist/{playlistId}/sync`
- `GET /api/track/{videoId}/audio` (Audio Stream Proxy)
    """)

# Mount Gradio UI on the root of the FastAPI app
app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
