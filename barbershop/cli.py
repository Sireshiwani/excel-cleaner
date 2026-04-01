from datetime import datetime, timedelta

import click
from flask import Flask

from .extensions import db
from .models import Appointment, Expense, Sale, Service, User


def register_cli(app: Flask) -> None:
    @app.cli.command("seed")
    def seed() -> None:
        db.drop_all()
        db.create_all()

        admin = User(
            name="Marcus Steele",
            role="admin",
            email="admin@gardencitybarbers.com",
            commission_rate=0.5,
        )
        admin.set_password("admin123")

        manager = User(
            name="Elias Grant",
            role="manager",
            email="manager@gardencitybarbers.com",
            commission_rate=0.45,
        )
        manager.set_password("manager123")

        staff_1 = User(
            name="Jordan King",
            role="staff",
            email="jordan@gardencitybarbers.com",
            commission_rate=0.4,
        )
        staff_1.set_password("staff123")

        staff_2 = User(
            name="Dante Brooks",
            role="staff",
            email="dante@gardencitybarbers.com",
            commission_rate=0.35,
        )
        staff_2.set_password("staff123")

        db.session.add_all([admin, manager, staff_1, staff_2])
        db.session.flush()

        services = [
            Service(
                name="Signature Haircut",
                category="Haircuts",
                price=45.0,
                description="Precision cut with wash and style.",
            ),
            Service(
                name="Beard Sculpt",
                category="Beard Trims",
                price=30.0,
                description="Detailed beard trim with line-up and oil finish.",
            ),
            Service(
                name="Royal Grooming Package",
                category="Packages",
                price=85.0,
                description="Haircut, beard sculpt, hot towel and facial treatment.",
            ),
            Service(
                name="Premium Pomade",
                category="Products",
                price=22.0,
                description="Matte hold premium pomade.",
            ),
        ]
        db.session.add_all(services)

        now = datetime.utcnow()
        sales = [
            Sale(
                service_rendered="Signature Haircut",
                category="Haircuts",
                price=50.0,
                staff_id=staff_1.id,
                payment_method="Card",
                date=now - timedelta(days=1),
            ),
            Sale(
                service_rendered="Beard Sculpt",
                category="Beard Trims",
                price=35.0,
                staff_id=staff_1.id,
                payment_method="Cash",
                date=now - timedelta(days=2),
            ),
            Sale(
                service_rendered="Royal Grooming Package",
                category="Packages",
                price=90.0,
                staff_id=staff_2.id,
                payment_method="Card",
                date=now - timedelta(days=3),
            ),
            Sale(
                service_rendered="Premium Pomade",
                category="Products",
                price=22.0,
                staff_id=staff_2.id,
                payment_method="Card",
                date=now - timedelta(days=5),
            ),
        ]
        db.session.add_all(sales)

        expenses = [
            Expense(
                category="Supplies",
                amount=120.0,
                description="Clipper guards and sanitation liquids",
                date=now - timedelta(days=2),
            ),
            Expense(
                category="Utilities",
                amount=280.0,
                description="Power and water bill",
                date=now - timedelta(days=7),
            ),
        ]
        db.session.add_all(expenses)

        appointments = [
            Appointment(
                customer_name="Andre Porter",
                customer_email="andre@example.com",
                customer_phone="+1 555-1100",
                service_name="Signature Haircut",
                notes="Skin fade preference",
                appointment_datetime=now + timedelta(days=1, hours=2),
                staff_id=staff_1.id,
            ),
            Appointment(
                customer_name="Caleb Jones",
                customer_email="caleb@example.com",
                customer_phone="+1 555-1200",
                service_name="Royal Grooming Package",
                notes="Event prep",
                appointment_datetime=now + timedelta(days=2, hours=1),
                staff_id=staff_2.id,
            ),
        ]
        db.session.add_all(appointments)

        db.session.commit()
        click.echo("Database seeded.")
