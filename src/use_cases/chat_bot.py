import logging

from fastapi import APIRouter
from pydantic import BaseModel
from src.llm.chatgpt import chat_with_gpt4


router = APIRouter()


# Data model for the message structure
class Message(BaseModel):
    text: str


# Endpoint for chatbot communication
@router.post("/chat")
async def chat(message: Message):
    return {"response": chat_with_gpt4(message.text)}
