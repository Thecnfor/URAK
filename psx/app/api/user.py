"""用户管理API路由"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.user import User, UserRepository, user_repository
from app.services.auth import get_current_user, require_admin
from app.core.security import verify_password, get_password_hash
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/users", tags=["用户管理"])


class UserResponse(BaseModel):
    """用户响应模型"""
    id: str
    username: str
    email: str
    role: str
    status: str
    created_at: str
    last_login: Optional[str] = None
    
    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """创建用户请求模型"""
    username: str
    email: EmailStr
    password: str
    role: str = "user"


class UserUpdate(BaseModel):
    """更新用户请求模型"""
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    status: Optional[str] = None


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session)
):
    """获取用户列表（仅管理员）"""
    users = await user_repository.list_users(skip=skip, limit=limit)
    return [UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        status=user.status,
        created_at=user.created_at.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None
    ) for user in users]


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """获取当前用户信息"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        status=current_user.status,
        created_at=current_user.created_at.isoformat(),
        last_login=current_user.last_login.isoformat() if current_user.last_login else None
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session)
):
    """获取指定用户信息（仅管理员）"""
    user = await user_repository.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        status=user.status,
        created_at=user.created_at.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None
    )


@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session)
):
    """创建新用户（仅管理员）"""
    try:
        user = await user_repository.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            role=user_data.role
        )
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            status=user.status,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session)
):
    """更新用户信息（仅管理员）"""
    user = await user_repository.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 更新用户信息
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.role is not None:
        user.role = user_data.role
    if user_data.status is not None:
        user.status = user_data.status
    
    await user_repository.update_user(user)
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        status=user.status,
        created_at=user.created_at.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session)
):
    """删除用户（仅管理员）"""
    success = await user_repository.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return {"message": "用户删除成功"}