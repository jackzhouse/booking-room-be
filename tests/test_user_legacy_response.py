from datetime import datetime, timezone

from app.schemas.auth import UserResponse


def test_user_response_keeps_legacy_telegram_shape():
    response = UserResponse(
        _id="699d573746c590dad4a737ab",
        telegram_id=293871670,
        full_name="Joko Makruf",
        username="jokomakruf",
        role="ROLE_SUPER_ADMIN",
        user_type="TELEGRAM",
        account_id=None,
        company_id=None,
        avatar_url=None,
        division=None,
        email=None,
        telegram_username=None,
        external_user_id=None,
        external_company_id=None,
        external_producer=None,
        attendance_user_id=None,
        employee_no=None,
        department_id=None,
        department_name=None,
        job_title=None,
        manager_external_id=None,
        created_by=None,
        updated_by=None,
        deleted_by=None,
        gender=None,
        nip=None,
        phone=None,
        deleted_at=None,
        is_deleted=False,
        is_admin=True,
        is_active=True,
        created_at=datetime(2026, 2, 24, 7, 45, 59, 451000, tzinfo=timezone.utc),
        updated_at=datetime(2026, 2, 24, 7, 45, 59, 451000, tzinfo=timezone.utc),
        last_login_at=datetime(2026, 4, 27, 4, 21, 2, 901000, tzinfo=timezone.utc),
    )

    assert response.id == "699d573746c590dad4a737ab"
    assert response.role == "ROLE_SUPER_ADMIN"
    assert response.user_type == "TELEGRAM"


def test_user_response_derives_legacy_external_defaults():
    response = UserResponse(
        _id="6a4dca3004cc862c258c7304",
        telegram_id=None,
        full_name="DEMO QA - ADMIN",
        username=None,
        role=None,
        user_type=None,
        account_id=None,
        company_id=None,
        avatar_url=None,
        division=None,
        email="demoqa@gmail.com",
        telegram_username=None,
        external_user_id="6740422e74739c67c2a1d711",
        external_company_id=None,
        external_producer="katalis",
        attendance_user_id=None,
        employee_no=None,
        department_id=None,
        department_name=None,
        job_title=None,
        manager_external_id=None,
        created_by=None,
        updated_by=None,
        deleted_by=None,
        gender=None,
        nip=None,
        phone=None,
        deleted_at=None,
        is_deleted=False,
        is_admin=False,
        is_active=True,
        created_at=datetime(2026, 7, 8, 3, 55, 28, 687000, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 8, 4, 3, 1, 349000, tzinfo=timezone.utc),
        last_synced_at=datetime(2026, 7, 8, 4, 3, 1, 349000, tzinfo=timezone.utc),
        last_login_at=datetime(2026, 7, 8, 4, 3, 1, 349000, tzinfo=timezone.utc),
    )

    assert response.id == "6a4dca3004cc862c258c7304"
    assert response.role == "ROLE_USER"
    assert response.user_type == "KATALIS"
