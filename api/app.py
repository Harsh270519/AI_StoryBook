# from dotenv import load_dotenv
# load_dotenv()

# import os
# import logging
# from typing import Optional, List
# import json
# from datetime import datetime

# from openai import OpenAI
# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from sqlmodel import SQLModel, Field, create_engine, Session

# # Configure logging
# logging.basicConfig(level=logging.INFO)

# # Initialize OpenAI client
# env_key = os.getenv("OPENAI_API_KEY")
# if not env_key:
#     raise RuntimeError("Missing OPENAI_API_KEY in environment")
# client = OpenAI(api_key=env_key)

# # Create FastAPI app and enable CORS
# app = FastAPI()
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:3000"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # SQLite DB setup
# DATABASE_URL = "sqlite:///./stories.db"
# engine = create_engine(DATABASE_URL, echo=False)

# class Story(SQLModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     prompt: str
#     pages: str  # JSON-encoded list of {"text", "image_url"}
#     created_at: datetime = Field(default_factory=datetime.utcnow)

# # Create tables
# SQLModel.metadata.create_all(engine)

# # Pydantic request models
# class TextRequest(BaseModel):
#     text: str

# class ImageRequest(BaseModel):
#     text: str

# class TranslateRequest(BaseModel):
#     text: str
#     target_lang: str

# class StoryRequest(BaseModel):
#     text: str
#     num_pages: int = 5

# @app.get("/health")
# def health():
#     return {"status": "ok"}

# @app.post("/generate")
# def generate_text(req: TextRequest):
#     try:
#         resp = client.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=[{"role": "user", "content": req.text}],
#             temperature=0.7,
#         )
#         return {"result": resp.choices[0].message.content}
#     except Exception as e:
#         logging.exception("Error in /generate")
#         raise HTTPException(status_code=502, detail=str(e))

# @app.post("/generate-image")
# def generate_image(req: ImageRequest):
#     try:
#         resp = client.images.generate(
#             prompt=req.text,
#             n=1,
#             size="512x512",
#         )
#         return {"image_url": resp.data[0].url}
#     except Exception as e:
#         logging.exception("Error in /generate-image")
#         raise HTTPException(status_code=502, detail=str(e))

# @app.post("/translate")
# def translate(req: TranslateRequest):
#     try:
#         messages = [
#             {"role": "system", "content": f"Translate to {req.target_lang}."},
#             {"role": "user", "content": req.text},
#         ]
#         resp = client.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=messages,
#             temperature=0.0,
#         )
#         return {"translation": resp.choices[0].message.content}
#     except Exception as e:
#         logging.exception("Error in /translate")
#         raise HTTPException(status_code=502, detail=str(e))

# @app.post("/stories")
# def create_story_endpoint(req: StoryRequest):
#     # 1. Split prompt into pages via GPT
#     try:
#         system_msg = (
#             "You are a creative storybook writer. "
#             f"Split the user's prompt into {req.num_pages} pages. "
#             "Output ONLY a JSON array (no explanation) of objects with keys 'text' and 'description'."
#         )
#         resp = client.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=[
#                 {"role": "system", "content": system_msg},
#                 {"role": "user",   "content": req.text}
#             ],
#             temperature=0.7,
#         )
#         raw = resp.choices[0].message.content
#         try:
#             page_data = json.loads(raw)
#         except json.JSONDecodeError:
#             logging.error(f"Failed to parse JSON from OpenAI: {raw}")
#             raise HTTPException(status_code=502, detail="Invalid JSON from OpenAI: " + raw)
#     except Exception as e:
#         logging.exception("Error splitting story into pages")
#         raise HTTPException(status_code=502, detail=str(e))

#     enriched = []
#     # 2. Generate image for each page
#     for page in page_data:
#         try:
#             img_resp = client.images.generate(
#                 prompt=page["description"],
#                 n=1,
#                 size="512x512"
#             )
#             image_url = img_resp.data[0].url
#         except Exception as e:
#             logging.exception("Error generating image for page")
#             raise HTTPException(status_code=502, detail=str(e))
#         enriched.append({"text": page["text"], "image_url": image_url})

#     # 3. Persist to SQLite
#     story = Story(prompt=req.text, pages=json.dumps(enriched))
#     with Session(engine) as session:
#         session.add(story)
#         session.commit()
#         session.refresh(story)

#     return {"story_id": story.id, "pages": enriched}

# @app.get("/stories/{story_id}")
# def get_story_endpoint(story_id: int):
#     with Session(engine) as session:
#         story = session.get(Story, story_id)
#         if not story:
#             raise HTTPException(status_code=404, detail="Story not found")
#         return {
#             "id": story.id,
#             "prompt": story.prompt,
#             "pages": json.loads(story.pages),
#             "created_at": story.created_at.isoformat()
#         }

from dotenv import load_dotenv
load_dotenv()

import os
import logging
import json
import re
from openai import OpenAI
import boto3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize OpenAI client
env_key = os.getenv("OPENAI_API_KEY")
if not env_key:
    raise RuntimeError("Missing OPENAI_API_KEY in environment")
client = OpenAI(api_key=env_key)

# Initialize AWS Polly for TTS
env_region = os.getenv("AWS_DEFAULT_REGION") or os.getenv("AWS_REGION")
if not env_region:
    raise RuntimeError("Missing AWS_DEFAULT_REGION in environment")
polly = boto3.client(
    "polly",
    region_name=env_region,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

# Create FastAPI app and enable CORS
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic request models
class StoryRequest(BaseModel):
    text: str
    num_pages: int = 5

class TranslateRequest(BaseModel):
    text: str
    target_lang: str

class TTSRequest(BaseModel):
    text: str

# Health check
default_prefix = "/api"
@app.get(f"{default_prefix}/health")
def health(): return {"status": "ok"}

@app.post(f"{default_prefix}/stories")
def create_story_endpoint(req: StoryRequest):
    # 1. Split prompt into pages via GPT
    try:
        system_msg = (
            "You are a creative storybook writer. "
            f"Split the user's prompt into {req.num_pages} pages. "
            "Respond with ONLY a JSON array of { 'text', 'description' } objects, no explanation."
        )
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user",   "content": req.text}
            ],
            temperature=0.7,
        )
        raw = resp.choices[0].message.content.strip()
        # strip markdown fences
        if raw.startswith("```"):
            raw = re.sub(r"^```.*?\n|```$", "", raw, flags=re.S)
        # extract JSON array
        match = re.search(r"(\[.*\])", raw, re.S)
        json_str = match.group(1) if match else raw
        page_data = json.loads(json_str)
    except Exception as e:
        logging.exception("Error parsing page JSON")
        raise HTTPException(status_code=502, detail=f"Invalid JSON from OpenAI: {e}")

    # 2. Generate images for each page
    enriched = []
    for page in page_data:
        try:
            img_resp = client.images.generate(prompt=page['description'], n=1, size="512x512")
            enriched.append({
                'text': page['text'],
                'image_url': img_resp.data[0].url
            })
        except Exception as e:
            logging.exception("Error generating page image")
            raise HTTPException(status_code=502, detail=str(e))

    return {"pages": enriched}

@app.post(f"{default_prefix}/translate")
def translate(req: TranslateRequest):
    try:
        messages = [
            {"role": "system", "content": f"Translate to {req.target_lang}."},
            {"role": "user", "content": req.text},
        ]
        resp = client.chat.completions.create(model="gpt-3.5-turbo", messages=messages, temperature=0.0)
        return {"translation": resp.choices[0].message.content}
    except Exception as e:
        logging.exception("Error in /translate")
        raise HTTPException(status_code=502, detail=str(e))

@app.post(f"{default_prefix}/tts")
def tts(req: TTSRequest):
    try:
        polly_resp = polly.synthesize_speech(Text=req.text, OutputFormat="mp3", VoiceId="Joanna")
        return StreamingResponse(polly_resp['AudioStream'], media_type="audio/mpeg")
    except Exception as e:
        logging.exception("Error in /tts")
        raise HTTPException(status_code=502, detail=str(e))

