from __future__ import annotations

from datetime import UTC, datetime, timedelta
from functools import wraps
from io import StringIO
import csv

from flask import (
    Blueprint,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from .extensions import db
from .models import Appointment, Expense, Payment, Sale, Service, User
from .reporting import (
    expenses_by_category,
    expenses_total_between,
    resolve_date_range,
    sales_by_category,
    sales_total_between,
    top_staff,
)

bp = Blueprint("main", __name__)


def roles_required(*allowed_roles):
    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("main.login"))
            if current_user.role not in allowed_roles:
                flash("You are not authorized to access that page.", "error")
                return redirect(url_for("main.dashboard"))
            return func(*args, **kwargs)

        return wrapped

    return decorator


def parse_dt(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M")


def parse_booking_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Invalid appointment time format.") from exc
    return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed


def check_membership(user_id: str | None, referral_code: str | None = None) -> bool:
    code = (referral_code or "").strip().upper()
    if code.startswith("VIP") or code.startswith("CLUB"):
        return True
    identifier = (user_id or "").strip().lower()
    return identifier.endswith("@finecuts.club") or identifier.startswith("member_")


def calculate_price(service_id: str, is_member: bool) -> tuple[float, Service]:
    service = None
    normalized = service_id.strip()
    if normalized.isdigit():
        service = db.session.get(Service, int(normalized))
    if not service:
        service = Service.query.filter(Service.name.ilike(normalized)).first()
    if not service:
        raise ValueError("Selected service was not found.")
    price = service.price * (0.9 if is_member else 1.0)
    return round(price, 2), service


@bp.route("/")
def index():
    services = Service.query.order_by(Service.price.asc()).all()
    team = User.query.filter(User.role.in_(["staff", "manager"])).all()
    return render_template("landing.html", services=services, team=team)


@bp.route("/book", methods=["POST"])
def book():
    default_staff = User.query.filter(User.role == "staff").order_by(User.id.asc()).first()
    appointment = Appointment(
        customer_name=request.form["customer_name"],
        customer_email=request.form["customer_email"],
        customer_phone=request.form["customer_phone"],
        service_name=request.form["service_name"],
        notes=request.form.get("notes", ""),
        appointment_datetime=parse_dt(request.form["appointment_datetime"]),
        staff_id=default_staff.id if default_staff else None,
    )
    db.session.add(appointment)
    db.session.commit()
    flash("Appointment request submitted. We will contact you soon.", "success")
    return redirect(url_for("main.index"))


@bp.route("/api/book", methods=["POST"])
def handle_booking():
    data = request.get_json(silent=True) or {}
    required = ["customer_name", "customer_email", "customer_phone", "service_id", "time"]
    missing = [field for field in required if not str(data.get(field, "")).strip()]
    if missing:
        return (
            jsonify(
                {
                    "status": "error",
                    "error": f"Missing required fields: {', '.join(missing)}",
                }
            ),
            400,
        )

    is_member = check_membership(data.get("user_id"), data.get("referral_code"))
    try:
        price, service = calculate_price(str(data["service_id"]), is_member)
        appointment_time = parse_booking_time(str(data["time"]))
    except ValueError as exc:
        return jsonify({"status": "error", "error": str(exc)}), 400

    default_staff = User.query.filter(User.role == "staff").order_by(User.id.asc()).first()
    notes = (data.get("notes") or "").strip()
    preferred_barber = (data.get("preferred_barber") or "").strip()
    metadata = f"Quoted Price: {price:.2f}; Member: {'yes' if is_member else 'no'}"
    if preferred_barber:
        metadata = f"{metadata}; Preferred Barber: {preferred_barber}"
    merged_notes = " | ".join(part for part in [notes, metadata] if part)[:250]

    appointment = Appointment(
        customer_name=str(data["customer_name"]).strip(),
        customer_email=str(data["customer_email"]).strip().lower(),
        customer_phone=str(data["customer_phone"]).strip(),
        service_name=service.name,
        notes=merged_notes,
        appointment_datetime=appointment_time,
        staff_id=default_staff.id if default_staff else None,
    )
    db.session.add(appointment)
    db.session.commit()

    return jsonify(
        {
            "status": "success",
            "booking_id": appointment.id,
            "price": price,
            "is_member": is_member,
        }
    )


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")
        login_user(user)
        return redirect(url_for("main.dashboard"))
    return render_template("login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "success")
    return redirect(url_for("main.index"))


@bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == "staff":
        return redirect(url_for("main.staff_dashboard"))
    return redirect(url_for("main.admin_dashboard"))


@bp.route("/dashboard/admin")
@login_required
@roles_required("admin", "manager")
def admin_dashboard():
    mode = request.args.get("mode", "monthly")
    start_raw = request.args.get("start")
    end_raw = request.args.get("end")
    start, end = resolve_date_range(mode, start_raw, end_raw)

    today_start = datetime.now(UTC).replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=None
    )
    today_end = today_start + timedelta(days=1)
    month_start, month_end = resolve_date_range("monthly", None, None)

    metrics = {
        "today_sales": sales_total_between(today_start, today_end),
        "month_sales": sales_total_between(month_start, month_end),
        "month_expenses": expenses_total_between(month_start, month_end),
    }

    leaderboard = top_staff(start, end)
    category_sales = sales_by_category(start, end)
    category_expenses = expenses_by_category(start, end)

    return render_template(
        "dashboard_admin.html",
        metrics=metrics,
        leaderboard=leaderboard,
        category_sales=category_sales,
        category_expenses=category_expenses,
        mode=mode,
        start=start,
        end=end,
    )


@bp.route("/dashboard/staff")
@login_required
@roles_required("staff")
def staff_dashboard():
    sales = (
        Sale.query.filter_by(staff_id=current_user.id)
        .order_by(Sale.date.desc())
        .limit(20)
        .all()
    )
    upcoming = (
        Appointment.query.filter(
            Appointment.staff_id == current_user.id,
            Appointment.appointment_datetime >= datetime.now(UTC).replace(tzinfo=None),
        )
        .order_by(Appointment.appointment_datetime.asc())
        .all()
    )
    total_sales = sum(s.price for s in sales)
    commission = total_sales * current_user.commission_rate
    return render_template(
        "dashboard_staff.html",
        sales=sales,
        upcoming=upcoming,
        total_sales=total_sales,
        commission=commission,
    )


@bp.route("/manage/staff", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def manage_staff():
    if request.method == "POST":
        user = User(
            name=request.form["name"],
            role=request.form["role"],
            email=request.form["email"].strip().lower(),
            commission_rate=float(request.form["commission_rate"]) / 100.0,
        )
        user.set_password(request.form["password"])
        db.session.add(user)
        db.session.commit()
        flash("Staff member created.", "success")
        return redirect(url_for("main.manage_staff"))

    users = User.query.order_by(User.role.asc(), User.name.asc()).all()
    return render_template("manage_staff.html", users=users)


@bp.route("/manage/staff/<int:user_id>/edit", methods=["POST"])
@login_required
@roles_required("admin")
def edit_staff(user_id):
    user = User.query.get_or_404(user_id)
    user.name = request.form["name"]
    user.role = request.form["role"]
    user.email = request.form["email"].strip().lower()
    user.commission_rate = float(request.form["commission_rate"]) / 100.0
    password = request.form.get("password", "").strip()
    if password:
        user.set_password(password)
    db.session.commit()
    flash("Staff member updated.", "success")
    return redirect(url_for("main.manage_staff"))


@bp.route("/manage/staff/<int:user_id>/delete", methods=["POST"])
@login_required
@roles_required("admin")
def delete_staff(user_id):
    if user_id == current_user.id:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("main.manage_staff"))
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("Staff member deleted.", "success")
    return redirect(url_for("main.manage_staff"))


@bp.route("/manage/services", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def manage_services():
    if request.method == "POST":
        service = Service(
            name=request.form["name"],
            category=request.form["category"],
            price=float(request.form["price"]),
            description=request.form.get("description", ""),
        )
        db.session.add(service)
        db.session.commit()
        flash("Service saved.", "success")
        return redirect(url_for("main.manage_services"))
    services = Service.query.order_by(Service.category.asc(), Service.price.asc()).all()
    return render_template("manage_services.html", services=services)


@bp.route("/manage/services/<int:service_id>/edit", methods=["POST"])
@login_required
@roles_required("admin")
def edit_service(service_id):
    service = Service.query.get_or_404(service_id)
    service.name = request.form["name"]
    service.category = request.form["category"]
    service.price = float(request.form["price"])
    service.description = request.form.get("description", "")
    db.session.commit()
    flash("Service updated.", "success")
    return redirect(url_for("main.manage_services"))


@bp.route("/manage/services/<int:service_id>/delete", methods=["POST"])
@login_required
@roles_required("admin")
def delete_service(service_id):
    service = Service.query.get_or_404(service_id)
    db.session.delete(service)
    db.session.commit()
    flash("Service deleted.", "success")
    return redirect(url_for("main.manage_services"))


@bp.route("/finance/sales", methods=["GET", "POST"])
@login_required
@roles_required("admin", "manager")
def sales_page():
    if request.method == "POST":
        sale = Sale(
            service_rendered=request.form["service_rendered"],
            category=request.form["category"],
            price=float(request.form["price"]),
            staff_id=int(request.form["staff_id"]),
            payment_method=request.form["payment_method"],
            date=datetime.fromisoformat(request.form["date"]),
        )
        db.session.add(sale)
        db.session.commit()
        flash("Sale logged.", "success")
        return redirect(url_for("main.sales_page"))
    sales = Sale.query.order_by(Sale.date.desc()).limit(50).all()
    staff = User.query.filter(User.role.in_(["admin", "manager", "staff"])).all()
    return render_template("sales.html", sales=sales, staff=staff)


@bp.route("/finance/sales/<int:sale_id>/edit", methods=["POST"])
@login_required
@roles_required("admin")
def edit_sale(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    sale.service_rendered = request.form["service_rendered"]
    sale.category = request.form["category"]
    sale.price = float(request.form["price"])
    sale.staff_id = int(request.form["staff_id"])
    sale.payment_method = request.form["payment_method"]
    sale.date = datetime.fromisoformat(request.form["date"])
    db.session.commit()
    flash("Sale updated.", "success")
    return redirect(url_for("main.sales_page"))


@bp.route("/finance/sales/<int:sale_id>/delete", methods=["POST"])
@login_required
@roles_required("admin")
def delete_sale(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    db.session.delete(sale)
    db.session.commit()
    flash("Sale deleted.", "success")
    return redirect(url_for("main.sales_page"))


@bp.route("/finance/expenses", methods=["GET", "POST"])
@login_required
@roles_required("admin", "manager")
def expenses_page():
    if request.method == "POST":
        expense = Expense(
            category=request.form["category"],
            amount=float(request.form["amount"]),
            description=request.form["description"],
            date=datetime.fromisoformat(request.form["date"]),
        )
        db.session.add(expense)
        db.session.commit()
        flash("Expense logged.", "success")
        return redirect(url_for("main.expenses_page"))
    expenses = Expense.query.order_by(Expense.date.desc()).limit(50).all()
    return render_template("expenses.html", expenses=expenses)


@bp.route("/finance/expenses/<int:expense_id>/edit", methods=["POST"])
@login_required
@roles_required("admin")
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    expense.category = request.form["category"]
    expense.amount = float(request.form["amount"])
    expense.description = request.form["description"]
    expense.date = datetime.fromisoformat(request.form["date"])
    db.session.commit()
    flash("Expense updated.", "success")
    return redirect(url_for("main.expenses_page"))


@bp.route("/finance/expenses/<int:expense_id>/delete", methods=["POST"])
@login_required
@roles_required("admin")
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    flash("Expense deleted.", "success")
    return redirect(url_for("main.expenses_page"))


@bp.route("/finance/payouts", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def payouts_page():
    if request.method == "POST":
        payout = Payment(
            staff_id=int(request.form["staff_id"]),
            amount=float(request.form["amount"]),
            date=datetime.fromisoformat(request.form["date"]),
            period_start=datetime.fromisoformat(request.form["period_start"]),
            period_end=datetime.fromisoformat(request.form["period_end"]),
        )
        db.session.add(payout)
        db.session.commit()
        flash("Payout recorded.", "success")
        return redirect(url_for("main.payouts_page"))
    payouts = Payment.query.order_by(Payment.date.desc()).limit(50).all()
    staff = User.query.filter(User.role.in_(["manager", "staff"])).all()
    return render_template("payouts.html", payouts=payouts, staff=staff)


@bp.route("/reports")
@login_required
@roles_required("admin", "manager")
def reports():
    mode = request.args.get("mode", "monthly")
    start_raw = request.args.get("start")
    end_raw = request.args.get("end")
    start, end = resolve_date_range(mode, start_raw, end_raw)

    sales = (
        Sale.query.join(User, Sale.staff_id == User.id)
        .filter(Sale.date >= start, Sale.date < end)
        .order_by(Sale.date.desc())
        .all()
    )
    expenses = (
        Expense.query.filter(Expense.date >= start, Expense.date < end)
        .order_by(Expense.date.desc())
        .all()
    )

    by_staff = []
    staff_totals = {}
    for sale in sales:
        key = sale.staff_id
        staff_totals.setdefault(
            key,
            {
                "name": sale.staff.name,
                "gross": 0.0,
                "commission_rate": sale.staff.commission_rate,
            },
        )
        staff_totals[key]["gross"] += sale.price

    for row in staff_totals.values():
        earnings = row["gross"] * row["commission_rate"]
        by_staff.append(
            {
                "name": row["name"],
                "gross": row["gross"],
                "staff_earnings": earnings,
                "shop_net": row["gross"] - earnings,
                "commission_rate": row["commission_rate"],
            }
        )
    by_staff.sort(key=lambda x: x["gross"], reverse=True)

    by_category = sales_by_category(start, end)
    expense_categories = expenses_by_category(start, end)

    return render_template(
        "reports.html",
        mode=mode,
        start=start,
        end=end,
        sales=sales,
        expenses=expenses,
        by_staff=by_staff,
        by_category=by_category,
        expense_categories=expense_categories,
    )


@bp.route("/reports/export")
@login_required
@roles_required("admin", "manager")
def export_reports():
    mode = request.args.get("mode", "monthly")
    start_raw = request.args.get("start")
    end_raw = request.args.get("end")
    start, end = resolve_date_range(mode, start_raw, end_raw)
    sales = (
        Sale.query.join(User, Sale.staff_id == User.id)
        .filter(Sale.date >= start, Sale.date < end)
        .order_by(Sale.date.desc())
        .all()
    )
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "date",
            "service",
            "category",
            "staff",
            "gross_sale",
            "commission_rate_percent",
            "staff_earnings",
            "shop_net",
            "payment_method",
        ]
    )
    for sale in sales:
        rate = sale.staff.commission_rate
        earnings = sale.price * rate
        writer.writerow(
            [
                sale.date.isoformat(),
                sale.service_rendered,
                sale.category,
                sale.staff.name,
                f"{sale.price:.2f}",
                f"{rate * 100:.2f}",
                f"{earnings:.2f}",
                f"{sale.price - earnings:.2f}",
                sale.payment_method,
            ]
        )
    output = buffer.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=report_sales.csv"},
    )
