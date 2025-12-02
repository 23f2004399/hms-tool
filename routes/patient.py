"""
Patient Routes for MediFriend
"""
from flask import Blueprint, render_template, session, redirect, url_for, flash
from routes.auth import role_required

patient_bp = Blueprint('patient', __name__, url_prefix='/patient')


@patient_bp.route('/dashboard')
@role_required('PATIENT')
def dashboard():
    """
    Patient dashboard - main hub
    """
    user_id = session.get('user_id')
    full_name = session.get('full_name')
    
    return render_template('patient_dashboard.html', 
                         user_name=full_name,
                         user_id=user_id)


@patient_bp.route('/appointments')
@role_required('PATIENT')
def appointments():
    """
    View patient's appointments
    """
    # TODO: Implement appointment listing
    return render_template('patient_appointments.html')


@patient_bp.route('/book-appointment')
@role_required('PATIENT')
def book_appointment():
    """
    Book new appointment
    """
    # TODO: Implement appointment booking
    return render_template('book_appointment.html')


@patient_bp.route('/prescriptions')
@role_required('PATIENT')
def prescriptions():
    """
    View patient's prescriptions
    """
    # TODO: Implement prescription listing
    return render_template('patient_prescriptions.html')


@patient_bp.route('/upload-prescription')
@role_required('PATIENT')
def upload_prescription():
    """
    Upload handwritten prescription for AI reading
    """
    # TODO: Link to existing prescription reader
    return render_template('prescription_reader.html')
