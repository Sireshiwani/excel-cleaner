from datetime import UTC, datetime

import pytest

from barbershop import create_app
from barbershop.extensions import db
from barbershop.models import Expense, Sale, Service, User


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-key",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }
    )
    with app.app_context():
        db.create_all()
        admin = User(
            name="Admin User",
            role="admin",
            email="admin@test.com",
            commission_rate=0.5,
        )
        admin.set_password("pass")
        manager = User(
            name="Manager User",
            role="manager",
            email="manager@test.com",
            commission_rate=0.4,
        )
        manager.set_password("pass")
        staff = User(
            name="Staff User",
            role="staff",
            email="staff@test.com",
            commission_rate=0.4,
        )
        staff.set_password("pass")
        db.session.add_all([admin, manager, staff])
        db.session.flush()

        db.session.add(
            Service(
                name="Cut",
                category="Haircuts",
                price=40.0,
                description="Classic cut",
            )
        )
        db.session.add(
            Sale(
                service_rendered="Cut",
                category="Haircuts",
                price=50.0,
                staff_id=staff.id,
                payment_method="Card",
                date=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        db.session.add(
            Expense(
                category="Supplies",
                amount=20.0,
                description="Clippers oil",
                date=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        db.session.commit()

    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email, password="pass"):
    return client.post(
        "/login", data={"email": email, "password": password}, follow_redirects=True
    )


def test_public_landing(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"GardenCity Barbers" in res.data


def test_staff_cannot_access_admin_dashboard(client):
    login(client, "staff@test.com")
    res = client.get("/dashboard/admin", follow_redirects=True)
    assert b"Staff Performance" in res.data


def test_manager_cannot_manage_staff(client):
    login(client, "manager@test.com")
    res = client.get("/manage/staff", follow_redirects=True)
    assert b"authorized" in res.data


def test_admin_reports_have_commission(client):
    login(client, "admin@test.com")
    res = client.get("/reports")
    assert res.status_code == 200
    assert b"Gross" in res.data
    assert b"Staff Earnings" in res.data
    assert b"Shop Net" in res.data


def test_export_csv(client):
    login(client, "admin@test.com")
    res = client.get("/reports/export")
    assert res.status_code == 200
    assert b"gross_sale" in res.data
    assert b"shop_net" in res.data
