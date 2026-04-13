"""
User service for managing user operations with repository pattern.
"""
from datetime import datetime, timezone
from typing import Optional, List
from passlib.context import CryptContext
from bson import ObjectId

from app.models.user import User
from app.models.company import Company
from app.core.enums import RoleEnum, UserTypeEnum
from app.schemas.auth import TeacherCreateRequest, AdminCreateRequest, UserUpdateRequest


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


class UserRepository:
    """Repository for user operations."""
    
    @staticmethod
    async def find_by_id(user_id: str) -> Optional[User]:
        """Find user by ID."""
        try:
            return await User.get(user_id)
        except:
            return None
    
    @staticmethod
    async def find_by_telegram_id(telegram_id: int) -> Optional[User]:
        """Find user by Telegram ID."""
        return await User.find_one(User.telegram_id == telegram_id)
    
    @staticmethod
    async def find_by_external_user_id(external_user_id: str) -> Optional[User]:
        """Find user by external user ID."""
        return await User.find_one(User.external_user_id == external_user_id)
    
    @staticmethod
    async def find_by_username(username: str) -> Optional[User]:
        """Find user by username."""
        return await User.find_one(User.username == username, User.is_deleted == False)
    
    @staticmethod
    async def find_by_email(email: str) -> Optional[User]:
        """Find user by email."""
        return await User.find_one(User.email == email, User.is_deleted == False)
    
    @staticmethod
    async def find_by_username_or_email(username_or_email: str) -> Optional[User]:
        """Find user by username or email."""
        user = await User.find_one(
            (User.username == username_or_email) | (User.email == username_or_email),
            User.is_deleted == False
        )
        return user
    
    @staticmethod
    async def find_by_company(company_id: str, skip: int = 0, limit: int = 100) -> List[User]:
        """Find all users in a company."""
        users = await User.find(
            User.company_id == company_id,
            User.is_deleted == False
        ).skip(skip).limit(limit).to_list()
        return users
    
    @staticmethod
    async def find_by_role(role: RoleEnum, skip: int = 0, limit: int = 100) -> List[User]:
        """Find all users with a specific role."""
        users = await User.find(
            User.role == role,
            User.is_deleted == False
        ).skip(skip).limit(limit).to_list()
        return users
    
    @staticmethod
    async def create_teacher(request: TeacherCreateRequest, company_id: Optional[str] = None) -> User:
        """Create a new teacher user."""
        # Check if username/email already exists
        if await UserRepository.find_by_username(request.username):
            raise ValueError("Username already exists")
        if request.email and await UserRepository.find_by_email(request.email):
            raise ValueError("Email already exists")
        
        user = User(
            full_name=request.full_name,
            username=request.username,
            password=hash_password(request.password),
            email=request.email,
            phone=request.phone,
            gender=request.gender,
            nip=request.nip,
            role=RoleEnum.TEACHER,
            user_type=UserTypeEnum.INTERNAL,
            company_id=company_id,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        await user.create()
        return user
    
    @staticmethod
    async def create_admin(request: AdminCreateRequest, created_by: Optional[str] = None, company_id: Optional[str] = None) -> User:
        """Create a new admin user."""
        # Check if username/email already exists
        if await UserRepository.find_by_username(request.username):
            raise ValueError("Username already exists")
        if request.email and await UserRepository.find_by_email(request.email):
            raise ValueError("Email already exists")
        
        user = User(
            full_name=request.full_name,
            username=request.username,
            password=hash_password(request.password),
            email=request.email,
            phone=request.phone,
            gender=request.gender,
            role=request.role,
            user_type=UserTypeEnum.INTERNAL,
            company_id=company_id,
            created_by=created_by,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        await user.create()
        return user
    
    @staticmethod
    async def update_profile(user_id: str, request: UserUpdateRequest, updated_by: Optional[str] = None) -> User:
        """Update user profile."""
        user = await UserRepository.find_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        if request.full_name:
            user.full_name = request.full_name
        if request.email:
            user.email = request.email
        if request.phone:
            user.phone = request.phone
        if request.gender:
            user.gender = request.gender
        if request.division:
            user.division = request.division
        if request.avatar_url:
            user.avatar_url = request.avatar_url
        
        user.updated_at = datetime.now(timezone.utc)
        user.updated_by = updated_by
        
        await user.save()
        return user
    
    @staticmethod
    async def change_password(user_id: str, old_password: str, new_password: str) -> bool:
        """Change user password."""
        user = await UserRepository.find_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        if not user.password:
            raise ValueError("User has no password set")
        
        if not verify_password(old_password, user.password):
            raise ValueError("Incorrect old password")
        
        user.password = hash_password(new_password)
        user.updated_at = datetime.now(timezone.utc)
        await user.save()
        return True
    
    @staticmethod
    async def reset_password(user_id: str, new_password: str) -> bool:
        """Reset user password (admin action)."""
        user = await UserRepository.find_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        user.password = hash_password(new_password)
        user.updated_at = datetime.now(timezone.utc)
        await user.save()
        return True
    
    @staticmethod
    async def set_active_status(user_id: str, is_active: bool) -> User:
        """Set user active/inactive status."""
        user = await UserRepository.find_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        user.is_active = is_active
        user.updated_at = datetime.now(timezone.utc)
        await user.save()
        return user
    
    @staticmethod
    async def soft_delete(user_id: str, deleted_by: Optional[str] = None) -> User:
        """Soft delete a user."""
        user = await UserRepository.find_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        user.is_deleted = True
        user.deleted_at = datetime.now(timezone.utc)
        user.deleted_by = deleted_by
        await user.save()
        return user


class CompanyRepository:
    """Repository for company operations."""
    
    @staticmethod
    async def find_by_id(company_id: str) -> Optional[Company]:
        """Find company by ID."""
        try:
            return await Company.get(company_id)
        except:
            return None
    
    @staticmethod
    async def find_all(skip: int = 0, limit: int = 100) -> List[Company]:
        """Find all active companies."""
        companies = await Company.find(
            Company.is_deleted == False
        ).skip(skip).limit(limit).to_list()
        return companies
    
    @staticmethod
    async def create(name: str, initial: str, created_by: Optional[str] = None) -> Company:
        """Create a new company."""
        company = Company(
            name=name,
            initial=initial,
            is_active=True,
            created_by=created_by,
            created_at=datetime.now(timezone.utc)
        )
        await company.create()
        return company
    
    @staticmethod
    async def update(company_id: str, name: Optional[str] = None, initial: Optional[str] = None, is_active: Optional[bool] = None, updated_by: Optional[str] = None) -> Company:
        """Update company."""
        company = await CompanyRepository.find_by_id(company_id)
        if not company:
            raise ValueError("Company not found")
        
        if name:
            company.name = name
        if initial:
            company.initial = initial
        if is_active is not None:
            company.is_active = is_active
        
        company.updated_at = datetime.now(timezone.utc)
        company.updated_by = updated_by
        
        await company.save()
        return company
    
    @staticmethod
    async def soft_delete(company_id: str, deleted_by: Optional[str] = None) -> Company:
        """Soft delete a company."""
        company = await CompanyRepository.find_by_id(company_id)
        if not company:
            raise ValueError("Company not found")
        
        company.is_deleted = True
        company.deleted_at = datetime.now(timezone.utc)
        company.deleted_by = deleted_by
        await company.save()
        return company
