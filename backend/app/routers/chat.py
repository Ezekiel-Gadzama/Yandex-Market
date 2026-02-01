from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel
from app.database import get_db
from app.services.yandex_api import YandexMarketAPI

router = APIRouter()


class MessageRequest(BaseModel):
    text: str


@router.get("/orders/{order_id}/messages", response_model=List[Dict])
def get_order_chat_messages(
    order_id: str,
    db: Session = Depends(get_db)
):
    """Get chat messages for an order"""
    try:
        yandex_api = YandexMarketAPI()
        messages = yandex_api.get_order_chat_messages(order_id)
        return messages
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get order chat messages: {str(e)}")


@router.post("/orders/{order_id}/messages", response_model=Dict)
def send_order_chat_message(
    order_id: str,
    message: MessageRequest,
    db: Session = Depends(get_db)
):
    """Send a message in order chat and send Telegram notification"""
    try:
        yandex_api = YandexMarketAPI()
        
        # Get order details and previous messages
        from app import models
        order = db.query(models.Order).filter(models.Order.yandex_order_id == order_id).first()
        messages = yandex_api.get_order_chat_messages(order_id)
        
        # Send message
        result = yandex_api.send_order_chat_message(order_id, message.text)
        
        # Send Telegram notification with message and reply
        from app.services.telegram_bot import telegram_bot
        import asyncio
        if telegram_bot and order:
            # Get the last customer message if any
            customer_message = None
            if messages:
                # Find last message from customer (not from seller)
                for msg in reversed(messages):
                    if msg.get("author") != "SELLER":
                        customer_message = msg.get("text", "")
                        break
            
            asyncio.create_task(
                telegram_bot.send_chat_message_notification(
                    order, customer_message, message.text
                )
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send order chat message: {str(e)}")
