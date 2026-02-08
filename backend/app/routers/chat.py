from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel
from app.database import get_db
from app.services.yandex_api import YandexMarketAPI

router = APIRouter()


class MessageRequest(BaseModel):
    text: str


@router.get("/orders/{order_id}/unread-count", response_model=Dict)
def get_order_chat_unread_count(
    order_id: str,
    db: Session = Depends(get_db)
):
    """Get unread message count for an order
    
    Returns count of unread messages based on chat status.
    If chat status is WAITING_FOR_PARTNER, there are unread messages from customer/market.
    """
    try:
        yandex_api = YandexMarketAPI()
        
        # Get chat info to check status
        if not yandex_api.business_id:
            return {"unread_count": 0}
        
        url = f"{yandex_api.base_url}/v2/businesses/{yandex_api.business_id}/chats"
        import httpx
        
        with httpx.Client() as client:
            payload = {"orderIds": [int(order_id)]}
            response = client.post(
                url,
                json=payload,
                headers=yandex_api._get_headers(),
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                chats = data.get("result", {}).get("chats", [])
                if chats:
                    chat = chats[0]
                    # If status is WAITING_FOR_PARTNER, there are unread messages
                    status = chat.get("status", "")
                    if status == "WAITING_FOR_PARTNER":
                        # Get raw messages to count unread ones
                        # We need to get the chat history directly to count messages
                        chat_id = chat.get("chatId")
                        if chat_id:
                            history_url = f"{yandex_api.base_url}/v2/businesses/{yandex_api.business_id}/chats/history"
                            history_response = client.post(
                                history_url,
                                params={"chatId": chat_id},
                                json={},
                                headers=yandex_api._get_headers(),
                                timeout=30.0
                            )
                            if history_response.status_code == 200:
                                history_data = history_response.json()
                                messages = history_data.get("result", {}).get("messages", [])
                                # Count messages from CUSTOMER, MARKET, or SUPPORT (not from PARTNER)
                                unread_count = sum(1 for msg in messages 
                                                 if msg.get("sender", "").upper() in ["CUSTOMER", "MARKET", "SUPPORT"])
                                return {"unread_count": unread_count}
                        # If we can't get messages, but status is WAITING_FOR_PARTNER, return 1
                        return {"unread_count": 1}
            
            return {"unread_count": 0}
    except Exception as e:
        # Return 0 on error to prevent UI issues
        print(f"⚠️  Error getting unread count for order {order_id}: {str(e)}")
        return {"unread_count": 0}


@router.get("/orders/{order_id}/messages", response_model=List[Dict])
def get_order_chat_messages(
    order_id: str,
    db: Session = Depends(get_db)
):
    """Get chat messages for an order
    
    Transforms Yandex API message format to frontend format:
    - sender (PARTNER/CUSTOMER/MARKET/SUPPORT) -> author (SELLER/CUSTOMER/SYSTEM)
    - message -> text
    - messageId -> id
    - createdAt -> created_at
    """
    try:
        yandex_api = YandexMarketAPI()
        raw_messages = yandex_api.get_order_chat_messages(order_id)
        
        if not raw_messages:
            return []
        
        # Transform messages to match frontend interface
        transformed_messages = []
        for msg in raw_messages:
            # Map sender to author
            sender = msg.get("sender", "").upper()
            if sender == "PARTNER":
                author = "SELLER"
            elif sender == "CUSTOMER":
                author = "CUSTOMER"
            else:  # MARKET, SUPPORT, or unknown
                author = "SYSTEM"
            
            transformed_msg = {
                "id": str(msg.get("messageId", "")),
                "text": msg.get("message", ""),
                "author": author,
                "created_at": msg.get("createdAt", ""),
                "order_id": order_id
            }
            transformed_messages.append(transformed_msg)
        
        return transformed_messages
    except ValueError as e:
        # Configuration errors (missing business_id, etc.)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log the error but return empty list instead of 500 to prevent frontend errors
        import traceback
        print(f"⚠️  Error getting chat messages for order {order_id}: {str(e)}")
        print(traceback.format_exc())
        return []  # Return empty list instead of raising 500 error


@router.post("/orders/{order_id}/messages", response_model=Dict)
def send_order_chat_message(
    order_id: str,
    message: MessageRequest,
    db: Session = Depends(get_db)
):
    """Send a message in order chat"""
    try:
        yandex_api = YandexMarketAPI()
        
        # Send message
        result = yandex_api.send_order_chat_message(order_id, message.text)
        
        return {"success": True, "message": "Message sent successfully", "data": result}
    except Exception as e:
        import traceback
        print(f"⚠️  Error sending chat message: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to send order chat message: {str(e)}")
