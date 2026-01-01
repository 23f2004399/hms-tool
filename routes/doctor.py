"""
Doctor Routes for MediFriend
"""
from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify, make_response
from routes.auth import role_required
from database import (
    get_doctor_appointments, update_appointment_status, get_doctor_patients,
    get_patient_details, create_prescription, create_notification, execute_query,
    get_user_notifications, get_unread_notification_count, mark_notifications_as_read,
    delete_read_notifications, get_doctor_stats, search_patients, mark_follow_up_required,
    mark_follow_up_complete, generate_ics_calendar, get_doctor_today_appointments
)
import json

doctor_bp = Blueprint('doctor', __name__, url_prefix='/doctor')


@doctor_bp.route('/dashboard')
@role_required('DOCTOR')
def dashboard():
    """
    Doctor dashboard - main hub
    """
    user_id = session.get('user_id')
    full_name = session.get('full_name')
    
    # Get statistics
    stats = get_doctor_stats(user_id)
    
    # Get today's appointments
    today_appointments = get_doctor_today_appointments(user_id)
    
    return render_template('doctor_dashboard.html',
                         doctor_name=full_name,
                         doctor_id=user_id,
                         stats=stats,
                         today_appointments=today_appointments)


@doctor_bp.route('/appointments')
@role_required('DOCTOR')
def appointments():
    """
    View doctor's appointments
    """
    user_id = session.get('user_id')
    appointments_list = get_doctor_appointments(user_id)
    
    return render_template('doctor_appointments.html', appointments=appointments_list)


@doctor_bp.route('/appointment/accept/<int:appointment_id>', methods=['POST'])
@role_required('DOCTOR')
def accept_appointment(appointment_id):
    """
    Accept/confirm an appointment
    """
    try:
        # Get appointment details to notify patient
        query = "SELECT patient_id, date, time FROM appointments WHERE id = ?"
        appointment = execute_query(query, (appointment_id,), fetchone=True)
        
        update_appointment_status(appointment_id, 'CONFIRMED')
        
        # Create notification for patient
        doctor_name = session.get('full_name', 'Doctor')
        message = f"Dr. {doctor_name} accepted your appointment for {appointment['date']} at {appointment['time']}"
        create_notification(
            user_id=appointment['patient_id'],
            notification_type='APPOINTMENT_ACCEPTED',
            message=message,
            link='/patient/appointments',
            appointment_id=appointment_id
        )
        
        flash('Appointment confirmed successfully!', 'success')
    except Exception as e:
        flash(f'Error confirming appointment: {str(e)}', 'danger')
    
    return redirect(url_for('doctor.appointments'))


@doctor_bp.route('/appointment/reject/<int:appointment_id>', methods=['POST'])
@role_required('DOCTOR')
def reject_appointment(appointment_id):
    """
    Reject an appointment
    """
    try:
        # Get appointment details to notify patient
        query = "SELECT patient_id, date, time FROM appointments WHERE id = ?"
        appointment = execute_query(query, (appointment_id,), fetchone=True)
        
        update_appointment_status(appointment_id, 'REJECTED')
        
        # Create notification for patient (no link for rejected appointments)
        doctor_name = session.get('full_name', 'Doctor')
        message = f"Dr. {doctor_name} declined your appointment request for {appointment['date']} at {appointment['time']}"
        create_notification(
            user_id=appointment['patient_id'],
            notification_type='APPOINTMENT_REJECTED',
            message=message,
            link=None,
            appointment_id=appointment_id
        )
        
        flash('Appointment rejected.', 'info')
    except Exception as e:
        flash(f'Error rejecting appointment: {str(e)}', 'danger')
    
    return redirect(url_for('doctor.appointments'))


@doctor_bp.route('/appointment/complete/<int:appointment_id>', methods=['POST'])
@role_required('DOCTOR')
def complete_appointment(appointment_id):
    """
    Mark appointment as completed
    """
    try:
        update_appointment_status(appointment_id, 'COMPLETED')
        flash('Appointment marked as completed!', 'success')
    except Exception as e:
        flash(f'Error completing appointment: {str(e)}', 'danger')
    
    return redirect(url_for('doctor.appointments'))


@doctor_bp.route('/patients')
@role_required('DOCTOR')
def patients():
    """
    View doctor's patients
    """
    user_id = session.get('user_id')
    patients_list = get_doctor_patients(user_id)
    
    return render_template('doctor_patients.html', patients=patients_list)


@doctor_bp.route('/write-prescription/<int:patient_id>/<int:appointment_id>', methods=['GET', 'POST'])
@role_required('DOCTOR')
def write_prescription(patient_id, appointment_id):
    """
    Write prescription for patient
    """
    doctor_id = session.get('user_id')
    
    if request.method == 'POST':
        diagnosis = request.form.get('diagnosis', '').strip()
        notes = request.form.get('notes', '').strip()
        
        # Collect medicines from dynamic form fields
        medicines = []
        medicine_names = request.form.getlist('medicine_name[]')
        medicine_dosages = request.form.getlist('medicine_dosage[]')
        medicine_durations = request.form.getlist('medicine_duration[]')
        
        for name, dosage, duration in zip(medicine_names, medicine_dosages, medicine_durations):
            if name.strip() and dosage.strip() and duration.strip():
                medicines.append({
                    'name': name.strip(),
                    'dosage': dosage.strip(),
                    'duration': duration.strip()
                })
        
        if not diagnosis:
            flash('Diagnosis is required', 'error')
            return redirect(url_for('doctor.write_prescription', 
                                   patient_id=patient_id, 
                                   appointment_id=appointment_id))
        
        # Convert medicines to JSON (empty array if no medicines)
        medicines_json = json.dumps(medicines)
        
        # Create prescription
        prescription_id = create_prescription(
            doctor_id=doctor_id,
            patient_id=patient_id,
            appointment_id=appointment_id,
            diagnosis=diagnosis,
            medicines_json=medicines_json,
            notes=notes if notes else None
        )
        
        if prescription_id:
            # Create notification for patient
            doctor_name = session.get('full_name', 'Doctor')
            message = f"Dr. {doctor_name} has written a prescription for you"
            create_notification(
                user_id=patient_id,
                notification_type='PRESCRIPTION_WRITTEN',
                message=message,
                link='/patient/prescriptions',
                prescription_id=prescription_id
            )
            
            flash('Prescription created successfully', 'success')
            return redirect(url_for('doctor.appointments'))
        else:
            flash('Failed to create prescription', 'error')
            return redirect(url_for('doctor.write_prescription', 
                                   patient_id=patient_id, 
                                   appointment_id=appointment_id))
    
    # GET request - show form
    patient = get_patient_details(patient_id)
    if not patient:
        flash('Patient not found', 'error')
        return redirect(url_for('doctor.appointments'))
    
    return render_template('write_prescription.html', 
                          patient=patient, 
                          appointment_id=appointment_id)


# --------------------------------------------------
# 📬 Notification API Routes
# --------------------------------------------------

@doctor_bp.route('/api/notifications', methods=['GET'])
@role_required('DOCTOR')
def get_notifications():
    """
    Get all unread notifications for the current doctor
    """
    user_id = session.get('user_id')
    notifications = get_user_notifications(user_id, unread_only=True)
    return jsonify({'success': True, 'notifications': notifications})


@doctor_bp.route('/api/notifications/count', methods=['GET'])
@role_required('DOCTOR')
def get_notification_count():
    """
    Get count of unread notifications
    """
    user_id = session.get('user_id')
    count = get_unread_notification_count(user_id)
    return jsonify({'success': True, 'count': count})


@doctor_bp.route('/api/notifications/mark-read', methods=['POST'])
@role_required('DOCTOR')
def mark_notifications_read():
    """
    Mark all notifications as read and delete them
    """
    user_id = session.get('user_id')
    mark_notifications_as_read(user_id)
    delete_read_notifications(user_id)
    return jsonify({'success': True})


@doctor_bp.route('/api/search-patients', methods=['GET'])
@role_required('DOCTOR')
def api_search_patients():
    """
    AJAX endpoint for searching patients
    Returns JSON results for live search
    """
    query = request.args.get('q', '').strip()
    doctor_id = session.get('user_id')
    
    if not query or len(query) < 2:
        return jsonify({'success': False, 'message': 'Query too short', 'patients': []})
    
    try:
        # Search only this doctor's patients
        patients = search_patients(query, doctor_id)
        
        # Format results for frontend
        results = [{
            'id': patient['id'],
            'name': patient['full_name'],
            'email': patient['email'],
            'phone': patient['phone'] or 'N/A',
            'gender': patient['gender'] or 'N/A',
            'blood_group': patient['blood_group'] or 'N/A'
        } for patient in patients]
        
        return jsonify({
            'success': True,
            'count': len(results),
            'patients': results
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e), 'patients': []})

@doctor_bp.route('/schedule-follow-up', methods=['POST'])
@role_required('DOCTOR')
def schedule_follow_up():
    """
    Mark appointment as requiring follow-up and schedule suggested date
    """
    try:
        appointment_id = request.form.get('appointment_id')
        follow_up_date = request.form.get('follow_up_date')
        follow_up_notes = request.form.get('follow_up_notes', '').strip()
        
        if not appointment_id or not follow_up_date:
            flash('Missing required information', 'error')
            return redirect(url_for('doctor.appointments'))
        
        doctor_id = session.get('user_id')
        
        # Get patient_id from appointment
        query = "SELECT patient_id FROM appointments WHERE id = ?"
        result = execute_query(query, (appointment_id,), fetchone=True)
        
        if not result:
            flash('Appointment not found', 'error')
            return redirect(url_for('doctor.appointments'))
        
        patient_id = result['patient_id']
        
        # Mark follow-up required and create notification
        mark_follow_up_required(appointment_id, follow_up_date, doctor_id, patient_id)
        
        # Update appointment with follow-up notes if provided
        if follow_up_notes:
            update_query = "UPDATE appointments SET notes = ? WHERE id = ?"
            execute_query(update_query, (follow_up_notes, appointment_id))
        
        flash(f'Follow-up scheduled successfully for {follow_up_date}', 'success')
        return redirect(url_for('doctor.appointments'))
        
    except Exception as e:
        flash(f'Error scheduling follow-up: {str(e)}', 'error')
        return redirect(url_for('doctor.appointments'))

@doctor_bp.route('/mark-follow-up-complete/<int:appointment_id>')
@role_required('DOCTOR')
def complete_follow_up(appointment_id):
    """
    Mark a follow-up as complete
    """
    try:
        mark_follow_up_complete(appointment_id)
        flash('Follow-up marked as complete', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('doctor.appointments'))


@doctor_bp.route('/download-calendar/<int:appointment_id>')
@role_required('DOCTOR')
def download_calendar(appointment_id):
    """Download .ics calendar file for appointment"""
    doctor_id = session.get('user_id')
    
    # Get appointment details
    query = """
        SELECT a.*, 
               u.full_name as patient_name,
               dd.clinic_address
        FROM appointments a
        JOIN users u ON a.patient_id = u.id
        LEFT JOIN doctor_details dd ON a.doctor_id = dd.user_id
        WHERE a.id = ? AND a.doctor_id = ?
    """
    appointment = execute_query(query, (appointment_id, doctor_id), fetchone=True)
    
    if not appointment:
        flash('Appointment not found.', 'danger')
        return redirect(url_for('doctor.appointments'))
    
    # Generate .ics content
    ics_content = generate_ics_calendar({
        'patient_name': appointment['patient_name'],
        'doctor_name': session.get('full_name'),
        'date': appointment['date'],
        'time': appointment['time'],
        'consultation_mode': appointment['consultation_mode'],
        'meet_link': appointment.get('meet_link'),
        'clinic_address': appointment.get('clinic_address'),
        'symptoms': appointment.get('symptoms')
    })
    
    # Create response with .ics file
    response = make_response(ics_content)
    response.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename=appointment_{appointment_id}.ics'
    
    return response
