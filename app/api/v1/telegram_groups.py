from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from app.models.telegram_group import TelegramGroup
from app.schemas.telegram_group import (
    TelegramGroupCreate,
    TelegramGroupResponse,
    TelegramGroupListResponse
)
from app.services.telegram_service import (
    get_all_telegram_groups,
    add_telegram_group,
    delete_telegram_group,
    test_notification
)
from app.api.deps import get_current_active_user, get_current_admin_user
from app.models.user import User

router = APIRouter(prefix="/telegram-groups", tags=["telegram-groups"])


def convert_group_to_response(group: TelegramGroup) -> TelegramGroupResponse:
    """
    Convert a TelegramGroup model to TelegramGroupResponse by converting ObjectId to string.
    """
    group_dict = group.dict(by_alias=True)
    if "_id" in group_dict and group_dict["_id"] is not None:
        group_dict["_id"] = str(group_dict["_id"])
    return TelegramGroupResponse(**group_dict)


@router.get("", response_model=TelegramGroupListResponse)
async def get_telegram_groups_list(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get all active Telegram groups.
    
    Only admin can access this endpoint.
    """
    groups = await get_all_telegram_groups()
    return TelegramGroupListResponse(
        groups=[convert_group_to_response(group) for group in groups],
        total=len(groups)
    )


@router.post("", response_model=TelegramGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_telegram_group(
    group_data: TelegramGroupCreate,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Add a new Telegram group.
    
    Only admin can access this endpoint.
    
    Validation:
    - group_id must be unique
    - group_name is required
    """
    try:
        group = await add_telegram_group(
            group_id=group_data.group_id,
            group_name=group_data.group_name
        )
        
        return convert_group_to_response(group)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_telegram_group_endpoint(
    group_id: int,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Delete a Telegram group by ID.
    
    Only admin can access this endpoint.
    
    Note: This will not affect existing bookings that reference this group.
    """
    deleted = await delete_telegram_group(group_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Telegram group with ID {group_id} not found"
        )
    
    return None


@router.post("/{group_id}/test", status_code=status.HTTP_200_OK)
async def test_telegram_group_notification(
    group_id: int,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Send a test notification to a Telegram group.
    
    Only admin can access this endpoint.
    
    Useful for verifying that the bot can send messages to the group.
    """
    success = await test_notification(group_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to send test notification. Check if the bot is added to the group."
        )
    
    return {"message": "Test notification sent successfully"}