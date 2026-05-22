# GardenCity Barbershop Management System

A high-end Barbershop Management System and website built with **Python + Flask**, styled using **Tailwind CSS** with a dark premium aesthetic.

## Highlights

- Public landing page with:
  - Hero section + Book Now CTA
  - Services grid with pricing
  - Meet the Team section
  - Appointment booking form
- Staff-only authentication and role-based access:
  - **Admin**: full CRUD for Staff, Services, Sales, Expenses, Payouts + full reporting
  - **Manager**: can log Sales and Expenses, can view dashboards/reports
  - **Staff**: personal dashboard with own sales, commission, upcoming appointments
- Dashboard analytics:
  - Today's sales
  - This month's sales
  - This month's expenses
  - Top Performing Staff leaderboard
  - Sales and expense category charts via Chart.js
- Reporting:
  - Sales by staff with dynamic commission calculations
  - Sales by category
  - Expenses by category
  - Date-range filtering (daily/weekly/monthly/custom)
  - CSV export

## Tech Stack

- Flask
- Flask-SQLAlchemy
- Flask-Login
- Tailwind CSS (CDN)
- Chart.js (CDN)
- SQLite (default dev DB)

## Run locally

1. Install dependencies:

   `pip install -r requirements.txt`

2. Seed sample data:

   `flask --app run.py seed`

3. Start app:

   `python run.py`

4. Open browser:

   `http://127.0.0.1:5000`

## Seeded users

- Admin: `admin@gardencitybarbers.com` / `admin123`
- Manager: `manager@gardencitybarbers.com` / `manager123`
- Staff: `jordan@gardencitybarbers.com` / `staff123`
- Staff: `dante@gardencitybarbers.com` / `staff123`

## Tests

Run:

`pytest -q`

