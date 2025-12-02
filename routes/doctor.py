"""
Doctor Routes for MediFriend
"""
from flask import Blueprint, render_template, session, redirect, url_for, flash
from routes.auth import role_required

doctor_bp = Blueprint('doctor', __name__, url_prefix='/doctor')


@doctor_bp.route('/dashboard')
@role_required('DOCTOR')
def dashboard():
    """
    Doctor dashboard - main hub
    """
    user_id = session.get('user_id')
    full_name = session.get('full_name')
    
    return render_template('doctor_dashboard.html',
                         doctor_name=full_name,
                         doctor_id=user_id)


@doctor_bp.route('/appointments')
@role_required('DOCTOR')
def appointments():
    """
    View doctor's appointments
    """
    # TODO: Implement appointment listing
    return render_template('doctor_appointments.html')


@doctor_bp.route('/patients')
@role_required('DOCTOR')
def patients():
    """
    View doctor's patients
    """
    # TODO: Implement patient listing
    return render_template('doctor_patients.html')


@doctor_bp.route('/write-prescription/<int:patient_id>')
@role_required('DOCTOR')
def write_prescription(patient_id):
    """
    Write prescription for patient
    """
    # TODO: Implement prescription writing
    return render_template('write_prescription.html', patient_id=patient_id)
