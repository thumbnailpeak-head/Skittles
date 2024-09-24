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
    user_input = message.text

    return chat_with_gpt4(user_input)
