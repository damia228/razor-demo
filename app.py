import os
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, or_

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def database_url():
    url = os.getenv("DATABASE_URL") or os.getenv("SETTINGS_DATABASE_URL")
    if not url:
        return "sqlite:///" + os.path.join(BASE_DIR, "razor.db")
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url

app = Flask(__name__)
app.config.update(
    SQLALCHEMY_DATABASE_URI=database_url(),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-change-me"),
)
db = SQLAlchemy(app)

STATUSES = ["new", "contacted", "estimate", "won", "lost"]
STATUS_LABELS = {
    "new": "Новый",
    "contacted": "Связались",
    "estimate": "Расчёт",
    "won": "Сделка",
    "lost": "Отказ",
}

class Lead(db.Model):
    __tablename__ = "leads"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(60), nullable=False, index=True)
    service = db.Column(db.String(120), nullable=False, index=True)
    width = db.Column(db.String(120), default="")
    budget = db.Column(db.String(120), default="")
    details = db.Column(db.Text, default="")
    source = db.Column(db.String(180), default="site", index=True)
    status = db.Column(db.String(30), default="new", nullable=False, index=True)
    notes = db.Column(db.Text, default="")
    deal_value = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "service": self.service,
            "width": self.width or "",
            "budget": self.budget or "",
            "details": self.details or "",
            "source": self.source or "site",
            "status": self.status,
            "status_label": STATUS_LABELS.get(self.status, self.status),
            "notes": self.notes or "",
            "deal_value": self.deal_value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


def clean(value, limit=1000):
    return str(value or "").strip()[:limit]


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        configured = os.getenv("ADMIN_PASSWORD")
        if not configured:
            # Local development stays frictionless; deployed environments should set ADMIN_PASSWORD.
            if request.remote_addr in {"127.0.0.1", "::1"}:
                return view(*args, **kwargs)
            return render_template("admin_login.html", setup_required=True), 503
        if not session.get("admin_ok"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@app.before_request
def ensure_tables():
    if not getattr(app, "_tables_ready", False):
        db.create_all()
        app._tables_ready = True


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/healthz")
def healthz():
    return jsonify({"ok": True, "database": db.engine.url.get_backend_name(), "lead_mode": True})


@app.post("/api/lead")
def create_lead():
    data = request.get_json(silent=True) or request.form.to_dict()
    if clean(data.get("website"), 120):
        return jsonify({"ok": True, "message": "Заявка принята"}), 201
    name = clean(data.get("name"), 120)
    phone = clean(data.get("phone"), 60)
    service = clean(data.get("service"), 120)

    if len(name) < 2:
        return jsonify({"error": "Укажите имя"}), 400
    if len(phone) < 6:
        return jsonify({"error": "Укажите корректный телефон"}), 400
    if not service:
        return jsonify({"error": "Выберите тип мебели"}), 400

    recent = Lead.query.filter(Lead.phone == phone, Lead.service == service, Lead.created_at >= datetime.now(timezone.utc) - timedelta(minutes=2)).first()
    if recent:
        return jsonify({"ok": True, "lead_id": recent.id, "message": "Заявка уже принята"}), 200

    lead = Lead(
        name=name,
        phone=phone,
        service=service,
        width=clean(data.get("width"), 120),
        budget=clean(data.get("budget"), 120),
        details=clean(data.get("details"), 2500),
        source=clean(data.get("source") or "site", 180),
        status="new",
    )
    db.session.add(lead)
    db.session.commit()
    return jsonify({"ok": True, "lead_id": lead.id, "message": "Заявка принята"}), 201


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    configured = os.getenv("ADMIN_PASSWORD")
    if not configured:
        return render_template("admin_login.html", setup_required=True), 503
    error = None
    if request.method == "POST":
        if request.form.get("password") == configured:
            session["admin_ok"] = True
            return redirect(request.args.get("next") or url_for("admin_dashboard"))
        error = "Неверный пароль"
    return render_template("admin_login.html", error=error, setup_required=False)


@app.post("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.get("/admin")
@admin_required
def admin_dashboard():
    status = clean(request.args.get("status"), 30)
    service = clean(request.args.get("service"), 120)
    q = clean(request.args.get("q"), 120)

    query = Lead.query
    if status in STATUSES:
        query = query.filter(Lead.status == status)
    if service:
        query = query.filter(Lead.service == service)
    if q:
        pattern = f"%{q}%"
        query = query.filter(or_(Lead.name.ilike(pattern), Lead.phone.ilike(pattern), Lead.details.ilike(pattern)))

    leads = query.order_by(Lead.created_at.desc()).limit(300).all()
    services = [r[0] for r in db.session.query(Lead.service).distinct().order_by(Lead.service).all() if r[0]]

    counts = {s: Lead.query.filter_by(status=s).count() for s in STATUSES}
    total = Lead.query.count()
    won = counts["won"]
    conversion = round((won / total * 100), 1) if total else 0
    pipeline_value = db.session.query(func.coalesce(func.sum(Lead.deal_value), 0)).filter(Lead.status.in_(["estimate", "won"])).scalar() or 0

    return render_template(
        "admin.html",
        leads=leads,
        statuses=STATUSES,
        labels=STATUS_LABELS,
        counts=counts,
        total=total,
        conversion=conversion,
        pipeline_value=pipeline_value,
        services=services,
        filters={"status": status, "service": service, "q": q},
    )


@app.get("/admin/api/lead/<int:lead_id>")
@admin_required
def get_lead(lead_id):
    lead = db.get_or_404(Lead, lead_id)
    return jsonify(lead.to_dict())


@app.patch("/admin/api/lead/<int:lead_id>")
@admin_required
def update_lead(lead_id):
    lead = db.get_or_404(Lead, lead_id)
    data = request.get_json(silent=True) or {}

    if "status" in data:
        status = clean(data.get("status"), 30)
        if status not in STATUSES:
            return jsonify({"error": "Неизвестный статус"}), 400
        lead.status = status
    if "notes" in data:
        lead.notes = clean(data.get("notes"), 5000)
    if "deal_value" in data:
        raw = data.get("deal_value")
        if raw in (None, ""):
            lead.deal_value = None
        else:
            try:
                lead.deal_value = max(0, int(raw))
            except (TypeError, ValueError):
                return jsonify({"error": "Сумма сделки должна быть числом"}), 400

    lead.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({"ok": True, "lead": lead.to_dict()})


@app.get("/admin/api/analytics")
@admin_required
def analytics():
    since = datetime.now(timezone.utc) - timedelta(days=13)
    rows = (
        db.session.query(func.date(Lead.created_at), func.count(Lead.id))
        .filter(Lead.created_at >= since)
        .group_by(func.date(Lead.created_at))
        .all()
    )
    daily_map = {str(day): count for day, count in rows}
    days = []
    for i in range(14):
        day = (datetime.now(timezone.utc).date() - timedelta(days=13-i)).isoformat()
        days.append({"date": day, "count": daily_map.get(day, 0)})

    service_rows = (
        db.session.query(Lead.service, func.count(Lead.id))
        .group_by(Lead.service)
        .order_by(func.count(Lead.id).desc())
        .limit(8)
        .all()
    )
    return jsonify({
        "daily": days,
        "services": [{"name": name, "count": count} for name, count in service_rows],
    })


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")

@app.post('/admin/api/demo-seed')
@admin_required
def demo_seed():
    if Lead.query.filter(Lead.source == 'demo').count():
        return jsonify({'ok': True, 'message': 'Демо-лиды уже добавлены'})
    samples = [
        Lead(name='Алия', phone='+7 700 555 14 20', service='Кухня', width='4.1 м', budget='600 000–1 000 000 ₸', details='Светлая кухня до потолка, встроенная техника.', source='demo', status='estimate', notes='Демо-заявка для презентации', deal_value=850000),
        Lead(name='Марат', phone='+7 701 222 63 11', service='Шкаф', width='2.8 м', budget='300 000–600 000 ₸', details='Встроенный шкаф в спальню.', source='demo', status='contacted', notes='Демо-заявка для презентации', deal_value=430000),
        Lead(name='Диана', phone='+7 707 330 91 04', service='Гардеробная', width='6 м²', budget='от 1 000 000 ₸', details='Гардеробная с подсветкой и островом.', source='demo', status='won', notes='Демо-заявка для презентации', deal_value=1200000),
    ]
    db.session.add_all(samples); db.session.commit()
    return jsonify({'ok': True, 'message': 'Добавлено 3 демонстрационных лида'})

@app.delete('/admin/api/demo-seed')
@admin_required
def demo_clear():
    Lead.query.filter(Lead.source == 'demo').delete(synchronize_session=False); db.session.commit()
    return jsonify({'ok': True})
