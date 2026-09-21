from datetime import datetime, date
from urllib.parse import urlparse
from flask import Flask, redirect, render_template, request, url_for, flash, abort, send_file, session
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
import atexit

from employees import get_employees, get_employee, add_employee, update_employee, delete_employee
from payroll import calculate_payroll, current_ist_str
from tax_engine import calculate_annual_tax
from payroll_history import get_month_record, record_month, get_fy_summary, fy_label
from auth import verify_login, login_required, role_required
from playwright.sync_api import sync_playwright


app = Flask(__name__)
app.secret_key = "justarandomsecretkey"

COMPANY_NAME = "5Gen Educon Private Limited"


# ============================================================
# REUSABLE PLAYWRIGHT BROWSER FOR PDF DOWNLOADS
# ============================================================

# Playwright's sync API is thread-pinned. Keep the entire Playwright
# lifecycle on one permanent worker thread so Flask request threads
# never touch the browser directly.
_pdf_executor = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="pdf-worker",
)

_pdf_playwright = None
_pdf_browser = None


def _get_pdf_browser():
    """Runs ONLY inside the _pdf_executor worker thread."""
    global _pdf_playwright, _pdf_browser

    if _pdf_browser is None:
        _pdf_playwright = sync_playwright().start()
        _pdf_browser = _pdf_playwright.chromium.launch(
            headless=True
        )

    return _pdf_browser


def _render_payslip_pdf(payslip_url, auth_cookie):
    """Render one payslip PDF entirely on the dedicated worker thread.

    auth_cookie: dict with the Flask session cookie (name/value/domain/path)
    so the headless browser is authenticated as the requesting user.
    Without this, Playwright hits the login-protected payslip route as an
    anonymous visitor and gets redirected to /login, producing a PDF of
    the login page instead of the payslip.
    """
    browser = _get_pdf_browser()

    context = browser.new_context(
        viewport={"width": 1180, "height": 900},
        device_scale_factor=1,
    )

    if auth_cookie:
        context.add_cookies([auth_cookie])

    page = context.new_page()

    try:
        page.goto(payslip_url, wait_until="networkidle")

        # If the cookie didn't authenticate us for any reason, fail loudly
        # instead of silently returning a PDF of the login screen.
        if "/login" in page.url:
            raise RuntimeError(
                "Payslip PDF render was redirected to the login page "
                "(session cookie was missing or invalid)."
            )

        page.evaluate(
            """
            async () => {
                if (document.fonts) {
                    await document.fonts.ready;
                }
            }
            """
        )

        page.wait_for_timeout(200)

        page.add_style_tag(
            content="""
            @page {
                size: A4;
                margin: 10mm;
            }

            html, body {
                margin: 0 !important;
                padding: 0 !important;
                background: #ffffff !important;
            }

            /* Chrome section headers/footers never belong in a payslip */
            .navbar, .site-footer, .no-print {
                display: none !important;
            }

            *, *::before, *::after {
                animation: none !important;
                transition: none !important;
            }

            .payslip {
                width: 100% !important;
                max-width: none !important;
                margin: 0 !important;
                padding: 0 !important;
                border: none !important;
                box-shadow: none !important;
                font-size: 11px !important;
                line-height: 1.35 !important;
            }

            /* HEADER — real class is .payslip-head */
            .payslip-head {
                margin-bottom: 14px !important;
                padding-bottom: 10px !important;
            }

            .payslip-head h1 {
                font-size: 22px !important;
                margin: 0 !important;
            }

            .payslip-head .muted.small {
                font-size: 10px !important;
                margin: 3px 0 !important;
            }

            /* EMPLOYEE META — real classes are .payslip-meta / .meta-item */
            .payslip-meta {
                gap: 10px !important;
                margin-bottom: 12px !important;
            }

            .meta-item {
                padding: 10px !important;
            }

            /* DETAIL PANELS */
            .detail-panel {
                margin-bottom: 12px !important;
                break-inside: avoid !important;
                page-break-inside: avoid !important;
            }

            .detail-panel-heading {
                padding-bottom: 9px !important;
                font-size: 12px !important;
            }

            .details-list {
                padding: 5px 0 !important;
            }

            .detail-row {
                padding: 7px 0 !important;
                min-height: 0 !important;
            }

            .detail-label {
                font-size: 10px !important;
            }

            .detail-value {
                font-size: 11px !important;
            }

            /* Page break before "Tax for FY" — real icon is fa-file-invoice */
            .detail-panel:has(.detail-panel-heading .fa-file-invoice) {
                break-before: page !important;
                page-break-before: always !important;
            }

            /* SALARY SECTION */
            .salary-grid {
                gap: 12px !important;
                margin-top: 12px !important;
                margin-bottom: 12px !important;
                break-inside: avoid !important;
                page-break-inside: avoid !important;
            }

            .salary-box {
                padding: 12px !important;
                break-inside: avoid !important;
                page-break-inside: avoid !important;
            }

            .salary-heading {
                font-size: 11px !important;
                margin-bottom: 8px !important;
            }

            .salary-line {
                padding: 6px 0 !important;
                font-size: 10px !important;
            }

            .salary-line strong {
                font-size: 11px !important;
            }

            .salary-total {
                font-size: 11px !important;
            }

            /* NET SALARY */
            .net-pay {
                padding: 13px 15px !important;
                margin-top: 10px !important;
                break-inside: avoid !important;
                page-break-inside: avoid !important;
            }

            .net-label {
                font-size: 12px !important;
            }

            .net-pay small {
                font-size: 10px !important;
            }

            .net-value {
                font-size: 22px !important;
            }
            """
        )

        page.emulate_media(media="print")

        return page.pdf(
            format="A4",
            print_background=True,
            margin={
                "top": "10mm",
                "right": "10mm",
                "bottom": "10mm",
                "left": "10mm",
            },
            scale=0.90,
            prefer_css_page_size=False,
        )

    finally:
        page.close()
        context.close()


def _shutdown_pdf_browser():
    """Runs on the worker thread because it touches Playwright objects."""
    global _pdf_playwright, _pdf_browser

    try:
        if _pdf_browser is not None:
            _pdf_browser.close()
            _pdf_browser = None
    except Exception:
        pass

    try:
        if _pdf_playwright is not None:
            _pdf_playwright.stop()
            _pdf_playwright = None
    except Exception:
        pass


@atexit.register
def close_pdf_browser():
    try:
        _pdf_executor.submit(_shutdown_pdf_browser).result(timeout=5)
    except Exception:
        pass

    _pdf_executor.shutdown(wait=False)


@app.context_processor
def inject_company_name():
    return {"company_name": COMPANY_NAME}
@app.template_filter("inr")
def inr_filter(value):
    """Format a number as Indian Rupees with Indian digit grouping (1,23,456.78)."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return value
    negative = value < 0
    value = abs(value)
    whole, _, decimal = f"{value:.2f}".partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        head = ",".join([head[max(i - 2, 0):i] for i in range(len(head), 0, -2)][::-1])
        whole = f"{head},{tail}"
    result = f"₹{whole}.{decimal}"
    return f"-{result}" if negative else result


def _parse_employee_form(form):
    """Shared validation for both the add and edit forms."""
    full_name = (form.get("full_name") or "").strip()
    department = (form.get("department") or "").strip()
    designation = (form.get("designation") or "").strip()
    joining_date_raw = (form.get("joining_date") or "").strip()
    ctc_raw = form.get("ctc")
    pan = (form.get("pan") or "").strip().upper()
    pf_uan = (form.get("pf_uan") or "").strip()
    account_number = (form.get("account_number") or "").strip()
    ifsc_code = (form.get("ifsc_code") or "").strip().upper()
    regime_opted = (form.get("regime_opted") or "New").strip()
    working_days_raw = (form.get("working_days") or "").strip()

    if not full_name or not ctc_raw or not joining_date_raw or not working_days_raw:
        return None, "Full Name, Joining Date, CTC, and Working Days are required."

    try:
        ctc = float(ctc_raw)
    except ValueError:
        return None, "CTC must be a valid number."

    if ctc <= 0:
        return None, "CTC must be greater than zero."

    try:
        joining_date = datetime.strptime(joining_date_raw, "%Y-%m-%d").date()
    except ValueError:
        return None, "Joining Date must be a valid date (YYYY-MM-DD)."

    try:
        working_days = int(working_days_raw)
    except ValueError:
        return None, "Working Days must be a whole number."

    if working_days < 0 or working_days > 31:
        return None, "Working Days must be between 0 and 31."

    if regime_opted not in ("New", "Old"):
        regime_opted = "New"

    return {
        "full_name": full_name,
        "department": department or None,
        "designation": designation or None,
        "joining_date": joining_date,
        "ctc": ctc,
        "pan": pan or None,
        "pf_uan": pf_uan or None,
        "account_number": account_number or None,
        "ifsc_code": ifsc_code or None,
        "regime_opted": regime_opted,
        "working_days": working_days,
    }, None


# ============================================================
# AUTH
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        user = verify_login(username, password)

        if not user:
            flash("Invalid username or password.", "error")
            return redirect(url_for("login"))

        session.clear()
        session["user_id"] = user.UserId
        session["username"] = user.Username
        session["role"] = user.Role
        session["employee_code"] = user.EmployeeCode

        flash(f"Welcome back, {user.Username}.", "success")
        next_url = request.args.get("next") or url_for("index")
        return redirect(next_url)

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You've been signed out.", "success")
    return redirect(url_for("login"))


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/")
@login_required
def index():
    if session.get("role") == "client" and session.get("employee_code"):
        # This client account is restricted to a single employee record.
        employee = get_employee(session["employee_code"])
        employees = [employee] if employee else []
    else:
        # Admins, and "shared" client accounts with no EmployeeCode,
        # see every active employee.
        employees = get_employees()

    return render_template("index.html", employees=employees)


def _client_can_view(employee_code):
    """True unless this session is a client restricted to a different employee."""
    if session.get("role") != "client":
        return True
    restricted_to = session.get("employee_code")
    return not restricted_to or restricted_to == employee_code


@app.route("/generate-payroll/<EmployeeCode>")
@login_required
def generate_payroll(EmployeeCode):
    if not _client_can_view(EmployeeCode):
        abort(403)

    employee = get_employee(EmployeeCode)
    if not employee:
        abort(404)

    payroll = calculate_payroll(employee)
    generated_at = current_ist_str()

    today = date.today()
    month, year = today.month, today.year

    annual_gross = payroll["gross_earnings"] * 12
    regime = getattr(employee, "RegimeOpted", None) or "New"
    tax = calculate_annual_tax(annual_gross, regime)

    existing_tds = get_month_record(EmployeeCode, month, year)
    if existing_tds is not None:
        monthly_tds = existing_tds
    else:
        tax_deducted_before, _, executions_left_before = get_fy_summary(EmployeeCode, today)
        remaining_including_this = max(executions_left_before, 1)
        monthly_tds = round(
            max(tax["net_tax"] - tax_deducted_before, 0) / remaining_including_this, 2
        )
        record_month(EmployeeCode, month, year, monthly_tds)

    tax_deducted_till_date, executions_done, executions_left = get_fy_summary(EmployeeCode, today)

    payroll["tds"] = monthly_tds
    payroll["total_deductions"] = payroll["professional_tax"] + payroll["epf"] + monthly_tds
    payroll["net_salary"] = payroll["gross_earnings"] - payroll["total_deductions"]

    return render_template(
        "payroll.html",
        employee=employee,
        payroll=payroll,
        tax=tax,
        generated_at=generated_at,
        fy_label=fy_label(today),
        tax_deducted_till_date=tax_deducted_till_date,
        executions_left=executions_left,
    )


@app.route("/download-payslip/<EmployeeCode>")
@login_required
def download_payslip(EmployeeCode):
    if not _client_can_view(EmployeeCode):
        abort(403)

    employee = get_employee(EmployeeCode)

    if not employee:
        abort(404)

    payslip_url = url_for(
        "generate_payroll",
        EmployeeCode=EmployeeCode,
        pdf=1,
        _external=True,
    )

    # Hand the current Flask session cookie to the headless browser so it
    # renders the payslip as the logged-in user instead of as a guest
    # (who would just get redirected to /login).
    cookie_name = app.config["SESSION_COOKIE_NAME"]
    cookie_value = request.cookies.get(cookie_name)

    auth_cookie = None
    if cookie_value:
        parsed_url = urlparse(payslip_url)
        auth_cookie = {
            "name": cookie_name,
            "value": cookie_value,
            "domain": parsed_url.hostname,
            "path": "/",
        }

    # The Flask request thread only waits for the result. Every Playwright
    # operation itself executes on the dedicated worker thread.
    pdf_bytes = _pdf_executor.submit(
        _render_payslip_pdf,
        payslip_url,
        auth_cookie,
    ).result()

    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"Payslip-{EmployeeCode}.pdf",
    )


# ============================================================
# ADMIN-ONLY: EMPLOYEE MANAGEMENT
# ============================================================

@app.route("/add-employee", methods=["POST"])
@role_required("admin")
def add_employee_route():
    data, error = _parse_employee_form(request.form)
    if error:
        flash(error, "error")
        return redirect(url_for("index", show_add=1))

    add_employee(
        data["full_name"], data["department"], data["designation"],
        data["joining_date"], data["ctc"], data["pan"], data["pf_uan"],
        data["account_number"], data["ifsc_code"], data["regime_opted"],
        data["working_days"],
    )
    flash(f"Employee \u201c{data['full_name']}\u201d added successfully.", "success")
    return redirect(url_for("index"))


@app.route("/edit-employee/<EmployeeCode>", methods=["GET", "POST"])
@role_required("admin")
def edit_employee_route(EmployeeCode):
    employee = get_employee(EmployeeCode)
    if not employee:
        abort(404)

    if request.method == "POST":
        data, error = _parse_employee_form(request.form)
        if error:
            flash(error, "error")
            return redirect(url_for("edit_employee_route", EmployeeCode=EmployeeCode))

        update_employee(
            EmployeeCode, data["full_name"], data["department"], data["designation"],
            data["joining_date"], data["ctc"], data["pan"], data["pf_uan"],
            data["account_number"], data["ifsc_code"], data["regime_opted"],
            data["working_days"],
        )
        flash(f"Employee \u201c{data['full_name']}\u201d updated successfully.", "success")
        return redirect(url_for("index"))

    return render_template("edit_employee.html", employee=employee)


@app.route("/delete-employee/<EmployeeCode>", methods=["POST"])
@role_required("admin")
def delete_employee_route(EmployeeCode):
    employee = get_employee(EmployeeCode)
    if not employee:
        abort(404)

    delete_employee(EmployeeCode)
    flash(f"Employee \u201c{employee.FullName}\u201d deleted.", "success")
    return redirect(url_for("index"))


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)