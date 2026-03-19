import modal

app = modal.App("astroshade")

volume = modal.Volume.from_name("astroshade-logs", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "fastapi[standard]",
        "gradio~=5.7",
        "requests",
        "google-genai",
        "Pillow",
        "pydantic",
        "python-dotenv",
    )
    .add_local_file("app/app.py", "/root/app.py")
    .add_local_file("app/inference.py", "/root/inference.py")
    .add_local_dir("app/prompts", "/root/prompts")
)


@app.function(
    image=image,
    max_containers=1,
    volumes={"/root/logs": volume},
    secrets=[modal.Secret.from_name("gemini-secret")],
)
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def web():
    import sys
    sys.path.insert(0, "/root")
    from fastapi import FastAPI
    from gradio.routes import mount_gradio_app
    from app import create_demo
    demo = create_demo(log_dir="/root/logs")
    return mount_gradio_app(app=FastAPI(), blocks=demo, path="/")
