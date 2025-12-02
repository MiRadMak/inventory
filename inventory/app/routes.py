from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from sqlalchemy import func, distinct, and_, or_
from datetime import datetime, timedelta
import json

from app.models import Equipment, db, User, Maintenance, Assignment, AuditLog

main_bp = Blueprint('main', __name__)


def log_audit(action, resource_type, resource_id=None, details=None):
    """Логирование действий пользователей"""
    audit = AuditLog(
        user_id=current_user.id if current_user.is_authenticated else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=request.remote_addr
    )
    db.session.add(audit)


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Расширенная панель управления"""
    total_equipment = Equipment.query.count()
    active_equipment = Equipment.query.filter_by(status='Активно').count()
    maintenance_equipment = Equipment.query.filter_by(status='На обслуживании').count()

    equipment_by_type = db.session.query(
        Equipment.type, func.count(Equipment.id)
    ).group_by(Equipment.type).all()

    upcoming_maintenance = Maintenance.query.filter(
        Maintenance.status.in_(['planned', 'in_progress']),
        Maintenance.scheduled_date >= datetime.utcnow()
    ).order_by(Maintenance.scheduled_date).limit(5).all()

    recent_equipment = Equipment.query.order_by(
        Equipment.created_at.desc()
    ).limit(5).all()

    total_value = db.session.query(func.sum(Equipment.price)).scalar() or 0

    expiring_warranty = Equipment.query.filter(
        Equipment.warranty_expiry.between(
            datetime.utcnow().date(),
            datetime.utcnow().date() + timedelta(days=30)
        )
    ).all()

    return render_template('dashboard.html',
                           total_equipment=total_equipment,
                           active_equipment=active_equipment,
                           maintenance_equipment=maintenance_equipment,
                           equipment_by_type=dict(equipment_by_type),
                           upcoming_maintenance=upcoming_maintenance,
                           recent_equipment=recent_equipment,
                           total_value=total_value,
                           expiring_warranty=expiring_warranty)


@main_bp.route('/equipment')
@login_required
def equipment():
    """Расширенный список оборудования с пагинацией"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = Equipment.query

    filters = {
        'type': request.args.get('type'),
        'status': request.args.get('status'),
        'location': request.args.get('location'),
        'name': request.args.get('name'),
        'category': request.args.get('category')
    }

    for field, value in filters.items():
        if value:
            query = query.filter(getattr(Equipment, field).ilike(f'%{value}%'))

    sort_by = request.args.get('sort', 'id')
    sort_order = request.args.get('order', 'desc')

    if hasattr(Equipment, sort_by):
        if sort_order == 'desc':
            query = query.order_by(getattr(Equipment, sort_by).desc())
        else:
            query = query.order_by(getattr(Equipment, sort_by))

    equipment_pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    categories = db.session.query(distinct(Equipment.category)).all()
    statuses = db.session.query(distinct(Equipment.status)).all()
    locations = db.session.query(distinct(Equipment.location)).all()

    log_audit('view_equipment_list', 'equipment')

    return render_template('equipment.html',
                           equipment=equipment_pagination.items,
                           pagination=equipment_pagination,
                           user=current_user,
                           categories=[c[0] for c in categories if c[0]],
                           statuses=[s[0] for s in statuses if s[0]],
                           locations=[l[0] for l in locations if l[0]])


@main_bp.route('/equipment/<int:id>')
@login_required
def equipment_detail(id):
    """Детальная страница оборудования"""
    eq = Equipment.query.get_or_404(id)
    maintenance_history = Maintenance.query.filter_by(equipment_id=id).order_by(
        Maintenance.scheduled_date.desc()
    ).all()

    assignment_history = Assignment.query.filter_by(equipment_id=id).order_by(
        Assignment.assignment_date.desc()
    ).all()

    log_audit('view_equipment_detail', 'equipment', id)

    return render_template('equipment_detail.html',
                           equipment=eq,
                           maintenance_history=maintenance_history,
                           assignment_history=assignment_history)


@main_bp.route('/equipment/add', methods=['GET', 'POST'])
@login_required
def add_equipment():
    if current_user.role != 'admin':
        flash('У вас нет прав на добавление оборудования', 'error')
        return redirect(url_for('main.equipment'))

    if request.method == 'POST':
        try:
            specs = {}
            for key in request.form:
                if key.startswith('spec_') and request.form[key]:
                    specs[key[5:]] = request.form[key]

            eq = Equipment(
                name=request.form['name'],
                model=request.form.get('model'),
                type=request.form.get('type'),
                category=request.form.get('category'),
                location=request.form.get('location'),
                status=request.form.get('status', 'Активно'),
                inventory_number=request.form.get('inventory_number'),
                ip_address=request.form.get('ip_address'),
                mac_address=request.form.get('mac_address'),
                serial_number=request.form.get('serial_number'),
                description=request.form.get('description'),
                specifications=specs,
                purchase_date=datetime.strptime(request.form['purchase_date'], '%Y-%m-%d').date() if request.form.get(
                    'purchase_date') else None,
                warranty_expiry=datetime.strptime(request.form['warranty_expiry'],
                                                  '%Y-%m-%d').date() if request.form.get('warranty_expiry') else None,
                price=request.form.get('price'),
                supplier=request.form.get('supplier'),
                created_by=current_user.id
            )

            db.session.add(eq)
            db.session.commit()

            log_audit('create_equipment', 'equipment', eq.id, {
                'name': eq.name,
                'model': eq.model,
                'type': eq.type
            })

            flash('Оборудование успешно добавлено!', 'success')
            return redirect(url_for('main.equipment'))

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении оборудования: {str(e)}', 'error')

    return render_template('add_equipment.html')


@main_bp.route('/equipment/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_equipment(id):
    if current_user.role != 'admin':
        flash('У вас нет прав на редактирование оборудования', 'error')
        return redirect(url_for('main.equipment'))

    eq = Equipment.query.get_or_404(id)

    if request.method == 'POST':
        try:
            old_data = {
                'name': eq.name,
                'status': eq.status,
                'location': eq.location
            }

            eq.name = request.form['name']
            eq.model = request.form.get('model')
            eq.type = request.form.get('type')
            eq.category = request.form.get('category')
            eq.location = request.form.get('location')
            eq.status = request.form.get('status')
            eq.inventory_number = request.form.get('inventory_number')
            eq.ip_address = request.form.get('ip_address')
            eq.mac_address = request.form.get('mac_address')
            eq.serial_number = request.form.get('serial_number')
            eq.description = request.form.get('description')
            eq.price = request.form.get('price')
            eq.supplier = request.form.get('supplier')
            eq.updated_at = datetime.utcnow()

            if request.form.get('purchase_date'):
                eq.purchase_date = datetime.strptime(request.form['purchase_date'], '%Y-%m-%d').date()
            if request.form.get('warranty_expiry'):
                eq.warranty_expiry = datetime.strptime(request.form['warranty_expiry'], '%Y-%m-%d').date()

            db.session.commit()

            log_audit('update_equipment', 'equipment', id, {
                'old_data': old_data,
                'new_data': {
                    'name': eq.name,
                    'status': eq.status,
                    'location': eq.location
                }
            })

            flash('Оборудование успешно обновлено!', 'success')
            return redirect(url_for('main.equipment_detail', id=id))

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении оборудования: {str(e)}', 'error')

    return render_template('edit_equipment.html', equipment=eq)


@main_bp.route('/equipment/delete/<int:id>')
@login_required
def delete_equipment(id):
    if current_user.role != 'admin':
        flash('У вас нет прав на удаление оборудования', 'error')
        return redirect(url_for('main.equipment'))

    eq = Equipment.query.get_or_404(id)

    try:
        log_audit('delete_equipment', 'equipment', id, {
            'name': eq.name,
            'model': eq.model
        })

        db.session.delete(eq)
        db.session.commit()
        flash('Оборудование успешно удалено!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении оборудования: {str(e)}', 'error')

    return redirect(url_for('main.equipment'))


@main_bp.route('/maintenance/add', methods=['GET', 'POST'])
@login_required
def add_maintenance():
    if request.method == 'POST':
        try:
            maintenance = Maintenance(
                equipment_id=request.form['equipment_id'],
                technician_id=current_user.id,
                type=request.form['type'],
                description=request.form['description'],
                status=request.form['status'],
                scheduled_date=datetime.strptime(request.form['scheduled_date'], '%Y-%m-%d'),
                cost=request.form.get('cost'),
                parts_used=request.form.get('parts_used')
            )

            equipment = Equipment.query.get(request.form['equipment_id'])
            equipment.status = 'На обслуживании'

            db.session.add(maintenance)
            db.session.commit()

            log_audit('create_maintenance', 'maintenance', maintenance.id)

            flash('Запланировано техническое обслуживание!', 'success')
            return redirect(url_for('main.maintenance'))

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при планировании обслуживания: {str(e)}', 'error')

    equipment_list = Equipment.query.filter_by(status='Активно').all()
    return render_template('add_maintenance.html', equipment=equipment_list)


@main_bp.route('/maintenance/complete/<int:id>')
@login_required
def complete_maintenance(id):
    maintenance = Maintenance.query.get_or_404(id)

    try:
        maintenance.status = 'completed'
        maintenance.completed_date = datetime.utcnow()

        equipment = maintenance.equipment
        equipment.status = 'Активно'

        db.session.commit()

        log_audit('complete_maintenance', 'maintenance', id)

        flash('Обслуживание завершено!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка: {str(e)}', 'error')

    return redirect(url_for('main.maintenance'))


@main_bp.route('/maintenance')
@login_required
def maintenance():
    """Управление техническим обслуживанием"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status')

    query = Maintenance.query

    if status_filter:
        query = query.filter_by(status=status_filter)

    maintenance_pagination = query.order_by(Maintenance.scheduled_date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    return render_template('maintenance.html',
                         maintenance=maintenance_pagination.items,
                         pagination=maintenance_pagination)

@main_bp.route('/assignments')
@login_required
def assignments():
    """Управление назначениями оборудования"""
    page = request.args.get('page', 1, type=int)

    assignments_pagination = Assignment.query.order_by(
        Assignment.assignment_date.desc()
    ).paginate(page=page, per_page=20, error_out=False)

    return render_template('assignments.html',
                         assignments=assignments_pagination.items,
                         pagination=assignments_pagination)


@main_bp.route('/assignments/add', methods=['GET', 'POST'])
@login_required
def add_assignment():
    if request.method == 'POST':
        try:
            assignment = Assignment(
                equipment_id=request.form['equipment_id'],
                assigned_to=request.form['assigned_to'],
                department=request.form['department'],
                purpose=request.form['purpose'],
                assignment_date=datetime.strptime(request.form['assignment_date'], '%Y-%m-%d'),
                created_by=current_user.id
            )

            db.session.add(assignment)
            db.session.commit()

            log_audit('create_assignment', 'assignment', assignment.id)

            flash('Оборудование назначено сотруднику!', 'success')
            return redirect(url_for('main.assignments'))

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при назначении оборудования: {str(e)}', 'error')

    available_equipment = Equipment.query.filter_by(status='Активно').all()
    return render_template('add_assignment.html', equipment=available_equipment)


@main_bp.route('/reports')
@login_required
def reports():
    """Отчеты и аналитика"""
    equipment_by_category = db.session.query(
        Equipment.category, func.count(Equipment.id)
    ).group_by(Equipment.category).all()

    equipment_by_status = db.session.query(
        Equipment.status, func.count(Equipment.id)
    ).group_by(Equipment.status).all()

    maintenance_stats = db.session.query(
        Maintenance.type, func.count(Maintenance.id)
    ).group_by(Maintenance.type).all()

    total_value = db.session.query(func.sum(Equipment.price)).scalar() or 0

    return render_template('reports.html',
                           equipment_by_category=dict(equipment_by_category),
                           equipment_by_status=dict(equipment_by_status),
                           maintenance_stats=dict(maintenance_stats),
                           total_value=total_value)


@main_bp.route('/api/equipment/chart-data')
@login_required
def equipment_chart_data():
    """API данные для графиков"""
    data = {
        'by_type': dict(db.session.query(Equipment.type, func.count(Equipment.id))
                        .group_by(Equipment.type).all()),
        'by_status': dict(db.session.query(Equipment.status, func.count(Equipment.id))
                          .group_by(Equipment.status).all()),
        'by_location': dict(db.session.query(Equipment.location, func.count(Equipment.id))
                            .group_by(Equipment.location).limit(10).all())
    }
    return jsonify(data)


@main_bp.route('/search')
@login_required
def search():
    """Расширенный поиск"""
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('main.equipment'))

    equipment_results = Equipment.query.filter(
        or_(
            Equipment.name.ilike(f'%{query}%'),
            Equipment.model.ilike(f'%{query}%'),
            Equipment.inventory_number.ilike(f'%{query}%'),
            Equipment.serial_number.ilike(f'%{query}%'),
            Equipment.ip_address.ilike(f'%{query}%'),
            Equipment.description.ilike(f'%{query}%')
        )
    ).all()

    log_audit('search', 'system', details={'query': query})

    return render_template('search_results.html',
                           query=query,
                           results=equipment_results,
                           results_count=len(equipment_results))


@main_bp.route('/profile')
@login_required
def profile():
    """Профиль пользователя"""
    user_activity = AuditLog.query.filter_by(user_id=current_user.id).order_by(
        AuditLog.timestamp.desc()
    ).limit(10).all()

    return render_template('profile.html', user_activity=user_activity)


@main_bp.route('/settings')
@login_required
def settings():
    """Настройки системы"""
    if current_user.role != 'admin':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('main.dashboard'))

    users_count = User.query.count()
    equipment_count = Equipment.query.count()
    total_storage = equipment_count * 0.5

    return render_template('settings.html',
                           users_count=users_count,
                           equipment_count=equipment_count,
                           total_storage=total_storage)