# %%
!pip install --upgrade google-genai
# %%
from google import genai
from google.genai import types

# 1. Initialize the client (automatically picks up GEMINI_API_KEY from your .env)
client = genai.Client()
# %%
# 2. Read the local .jfif file into raw bytes
file_path = '../testcases/test-client_00.jfif'
with open(file_path, 'rb') as f:
    image_bytes = f.read()
# %%
# 3. Call the API using types.Part.from_bytes
response = client.models.generate_content(
    model="gemini-3.1-pro", 
    contents=[
        "Client wants Scandi blonde. Assess the starting level in this photo.",
        types.Part.from_bytes(
            data=image_bytes,
            mime_type='image/jpeg' 
        )
    ]
)
# %%
print(response.text)
# %%
dir(response)
# %%
