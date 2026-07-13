import logging
import os

import joblib
import pandas as pd
from flask import Flask, render_template, request

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'model.pkl')
ENCODER_PATH = os.path.join(BASE_DIR, 'encoders.pkl')


def load_artifacts():
    """Load the serialized model and encoders from local assets."""
    try:
        model = joblib.load(MODEL_PATH)
        encoders = joblib.load(ENCODER_PATH)
        logger.info('Loaded model from %s', MODEL_PATH)
        logger.info('Loaded encoders from %s', ENCODER_PATH)
        logger.info('Model classes: %s', list(getattr(model, 'classes_', [])))
        return model, encoders
    except Exception:
        logger.exception('Failed to load model or encoders')
        raise


model, encoders = load_artifacts()
feature_order = list(
    getattr(
        model,
        'feature_names_in_',
        [
            'Gender',
            'Age',
            'Debt',
            'Married',
            'BankCustomer',
            'Industry',
            'Ethnicity',
            'YearsEmployed',
            'PriorDefault',
            'Employed',
            'CreditScore',
            'DriversLicense',
            'Citizen',
            'ZipCode',
            'Income',
        ],
    )
)

categorical_fields = [field for field in feature_order if field in encoders]
category_values = {field: set(encoders[field].classes_) for field in categorical_fields}

APPROVAL_CLASS = '+' if '+' in getattr(model, 'classes_', []) else None
if APPROVAL_CLASS is None:
    class_list = list(getattr(model, 'classes_', []))
    if class_list:
        APPROVAL_CLASS = class_list[0]


def parse_float(value):
    """Parse a numeric value to float, returning None for invalid input."""
    if value is None:
        return None
    try:
        parsed = float(str(value).strip())
    except (ValueError, TypeError):
        return None
    return parsed


def parse_int(value):
    """Parse a numeric value to int, returning None for invalid input."""
    if value is None:
        return None
    try:
        parsed = int(float(str(value).strip()))
    except (ValueError, TypeError):
        return None
    return parsed


def validate_inputs(raw_inputs):
    """Validate raw form values and return a list of user-facing errors."""
    errors = []

    for field in categorical_fields:
        value = raw_inputs.get(field, '').strip()
        if not value:
            errors.append(f'{field} is required.')
            continue
        if value not in category_values[field]:
            errors.append(f'Invalid value for {field}: {value}.')

    age = parse_float(raw_inputs.get('Age', '').strip())
    if age is None:
        errors.append('Age must be a valid number.')
    elif age < 18 or age > 100:
        errors.append('Age must be between 18 and 100.')

    income = parse_float(raw_inputs.get('Income', '').strip())
    if income is None:
        errors.append('Annual income must be a valid number.')
    elif income <= 0:
        errors.append('Annual income must be greater than zero.')

    debt = parse_float(raw_inputs.get('Debt', '').strip())
    if debt is None:
        errors.append('Debt must be a valid number.')
    elif debt < 0:
        errors.append('Debt cannot be negative.')

    years_employed = parse_float(raw_inputs.get('YearsEmployed', '').strip())
    if years_employed is None:
        errors.append('Years employed must be a valid number.')
    elif years_employed < 0:
        errors.append('Years employed cannot be negative.')

    credit_score = parse_int(raw_inputs.get('CreditScore', '').strip())
    if credit_score is None:
        errors.append('Credit score must be a valid whole number.')
    elif credit_score < 0 or credit_score > 1000:
        errors.append('Credit score must be a realistic value.')

    zip_code_raw = raw_inputs.get('ZipCode', '').strip()
    if not zip_code_raw:
        errors.append('ZIP code is required.')
    else:
        zip_code = parse_int(zip_code_raw)
        if zip_code is None:
            errors.append('ZIP code must be a valid number.')
        elif zip_code < 0:
            errors.append('ZIP code cannot be negative.')

    return errors


def calculate_financial_metrics(income, debt):
    """Calculate debt-to-income ratio and other financial metrics."""
    debt_to_income = (debt / income * 100) if income > 0 else 0
    manageable_threshold = 30  # Standard debt-to-income threshold
    return {
        'debt_to_income': debt_to_income,
        'is_manageable': debt_to_income <= manageable_threshold,
        'debt_concern': 'high' if debt_to_income > 50 else 'moderate' if debt_to_income > 30 else 'low'
    }


def assess_credit_profile(credit_score):
    """Assess credit score against standard ranges."""
    if credit_score >= 750:
        return 'excellent', 'Your excellent credit score demonstrates a strong history of responsible borrowing.'
    elif credit_score >= 700:
        return 'very_good', 'Your very good credit score shows solid creditworthiness.'
    elif credit_score >= 650:
        return 'good', 'Your credit score is in a good range.'
    elif credit_score >= 580:
        return 'fair', 'Your credit score is in the fair range.'
    else:
        return 'poor', 'Your credit score is below desired levels.'


def assess_employment_stability(employed, years_employed):
    """Assess employment status and tenure."""
    if not employed:
        return 'unemployed', 'not currently employed'
    elif years_employed >= 5:
        return 'stable', f'{years_employed:.1f} years of stable employment'
    elif years_employed >= 2:
        return 'moderate', f'{years_employed:.1f} years of employment experience'
    else:
        return 'recent', f'{years_employed:.1f} years of employment'


def build_strengths_section(raw_inputs):
    """Generate personalized strengths from the applicant's profile."""
    age = parse_float(raw_inputs.get('Age')) or 0
    income = parse_float(raw_inputs.get('Income')) or 0
    credit_score = parse_int(raw_inputs.get('CreditScore')) or 0
    debt = parse_float(raw_inputs.get('Debt')) or 0
    years_employed = parse_float(raw_inputs.get('YearsEmployed')) or 0
    employed = raw_inputs.get('Employed', '').lower() == 't'
    prior_default = raw_inputs.get('PriorDefault', '').lower() == 't'
    drivers_license = raw_inputs.get('DriversLicense', '').lower() == 't'

    strengths = []
    
    # Employment strength
    employment_status, employment_desc = assess_employment_stability(employed, years_employed)
    if employment_status != 'unemployed':
        strengths.append(f'Strong employment profile: You have {employment_desc}.')
    
    # Credit strength
    credit_level, credit_desc = assess_credit_profile(credit_score)
    if credit_level in ('excellent', 'very_good', 'good'):
        strengths.append(credit_desc)
    
    # Income strength
    if income >= 60000:
        strengths.append(f'Solid income foundation: Your annual income of ${int(income):,} supports your debt obligations.')
    elif income >= 40000:
        strengths.append(f'Adequate income level: Your annual income of ${int(income):,} is sufficient for credit management.')
    
    # Debt management
    metrics = calculate_financial_metrics(income, debt)
    if metrics['is_manageable']:
        dti = metrics['debt_to_income']
        strengths.append(f'Healthy debt management: Your debt-to-income ratio of {dti:.1f}% is well-managed.')
    
    # Payment history
    if not prior_default:
        strengths.append('Clean payment history: No prior defaults on record.')
    
    # Identity verification
    if drivers_license:
        strengths.append('Verified identity: Valid driver\'s license on file.')
    
    return strengths


def build_weaknesses_section(raw_inputs):
    """Generate personalized weaknesses from the applicant's profile."""
    income = parse_float(raw_inputs.get('Income')) or 0
    credit_score = parse_int(raw_inputs.get('CreditScore')) or 0
    debt = parse_float(raw_inputs.get('Debt')) or 0
    years_employed = parse_float(raw_inputs.get('YearsEmployed')) or 0
    employed = raw_inputs.get('Employed', '').lower() == 't'
    prior_default = raw_inputs.get('PriorDefault', '').lower() == 't'

    weaknesses = []
    
    # Employment weakness
    if not employed:
        weaknesses.append('Employment gap: You are not currently employed.')
    elif years_employed < 2:
        weaknesses.append(f'Limited employment history: Only {years_employed:.1f} years at current position.')
    
    # Credit weakness
    if credit_score < 600:
        weaknesses.append(f'Lower credit score: Your score of {credit_score} is below preferred standards.')
    elif credit_score < 650:
        weaknesses.append(f'Fair credit score: Your score of {credit_score} requires improvement.')
    
    # Income weakness
    if income < 30000:
        weaknesses.append(f'Limited income: Your annual income of ${int(income):,} is below average.')
    
    # Debt weakness
    metrics = calculate_financial_metrics(income, debt)
    if not metrics['is_manageable']:
        dti = metrics['debt_to_income']
        weaknesses.append(f'High debt load: Your debt-to-income ratio of {dti:.1f}% exceeds preferred levels.')
    
    # Payment history weakness
    if prior_default:
        weaknesses.append('Previous default: A prior loan default is on record.')
    
    return weaknesses


def build_recommendations(raw_inputs, status):
    """Generate targeted recommendations based on applicant profile and decision."""
    credit_score = parse_int(raw_inputs.get('CreditScore')) or 0
    income = parse_float(raw_inputs.get('Income')) or 0
    debt = parse_float(raw_inputs.get('Debt')) or 0
    employed = raw_inputs.get('Employed', '').lower() == 't'
    prior_default = raw_inputs.get('PriorDefault', '').lower() == 't'

    recommendations = []
    
    if status == 'rejected':
        if credit_score < 700:
            recommendations.append('Build your credit score to 700+ by maintaining on-time payments for the next 6-12 months.')
        
        if debt > income * 0.3:
            recommendations.append('Work on reducing your debt-to-income ratio below 30% through debt repayment.')
        
        if not employed:
            recommendations.append('Secure stable employment, which is crucial for credit approval.')
        
        if prior_default:
            recommendations.append('Maintain a clean payment record for at least 2 years before reapplying.')
        
        if not recommendations:
            recommendations.append('Consider reapplying after 6 months with improved financial metrics.')
    
    else:  # approved
        recommendations.append('Congratulations! Maintain your current payment habits to keep your credit in good standing.')
        if credit_score < 750:
            recommendations.append('Continue building your credit score above 750 for better future financial opportunities.')
        if debt > income * 0.2:
            recommendations.append('Consider paying down debt to improve your financial flexibility.')
    
    return recommendations


def build_explanation(raw_inputs, status):
    """Create comprehensive, personalized explanation for the decision."""
    age = parse_float(raw_inputs.get('Age')) or 0.0
    income = parse_float(raw_inputs.get('Income')) or 0.0
    credit_score = parse_int(raw_inputs.get('CreditScore')) or 0
    debt = parse_float(raw_inputs.get('Debt')) or 0.0
    employed = raw_inputs.get('Employed', '').lower() == 't'
    
    # Generate components
    strengths = build_strengths_section(raw_inputs)
    weaknesses = build_weaknesses_section(raw_inputs)
    recommendations = build_recommendations(raw_inputs, status)
    
    return {
        'strengths': strengths[:3],  # Top 3 strengths
        'weaknesses': weaknesses[:3],  # Top 3 weaknesses
        'recommendations': recommendations[:3],  # Top 3 recommendations
        'summary': build_summary_statement(income, debt, credit_score, employed, status)
    }


def build_summary_statement(income, debt, credit_score, employed, status):
    """Build the main decision summary statement."""
    metrics = calculate_financial_metrics(income, debt)
    
    if status == 'approved':
        if metrics['is_manageable'] and credit_score >= 700 and employed:
            return 'Your application demonstrates solid financial responsibility and creditworthiness.'
        elif credit_score >= 700:
            return 'Your strong credit history supports a positive approval decision.'
        else:
            return 'Your overall profile shows sufficient financial stability for this credit product.'
    else:
        if metrics['debt_concern'] == 'high':
            return 'Your debt level requires attention before credit approval.'
        elif credit_score < 650:
            return 'Your credit profile needs improvement before reapplication.'
        elif not employed:
            return 'Stable employment is essential for credit approval.'
        else:
            return 'Your financial profile does not currently meet approval criteria.'


def prepare_input_data(raw_inputs):
    """Convert validated raw inputs into the feature vector expected by the model."""
    row = []
    for field in feature_order:
        value = str(raw_inputs.get(field, '')).strip()
        if field in categorical_fields:
            if value not in category_values[field]:
                raise ValueError(f'Invalid category for {field}: {value}')
            row.append(encoders[field].transform([value])[0])
        else:
            if field in ('CreditScore', 'ZipCode'):
                transformed = parse_int(value)
            else:
                transformed = parse_float(value)
            if transformed is None:
                raise ValueError(f'Invalid numeric value for {field}: {value}')
            row.append(transformed)
    return pd.DataFrame([row], columns=feature_order)


def format_confidence(confidence):
    if confidence >= 85:
        return 'High confidence prediction.'
    if confidence >= 60:
        return 'Moderate confidence prediction.'
    return 'Low confidence prediction. The applicant is close to the decision boundary.'


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/predict', methods=['GET'])
def predict_page():
    return render_template('index.html')


@app.route('/predict', methods=['POST'])
def predict():
    """Process credit card application prediction."""
    raw_inputs = {field: request.form.get(field, '').strip() for field in feature_order}
    validation_errors = validate_inputs(raw_inputs)
    
    if validation_errors:
        logger.info('Validation failed: %s', validation_errors)
        return render_template(
            'result.html',
            prediction_text='Invalid Input',
            status='invalid',
            confidence=None,
            explanation_data={},
            confidence_message='Please correct the highlighted issues and try again.',
            validation_errors=validation_errors,
            applicant_data={}
        )

    try:
        input_data = prepare_input_data(raw_inputs)
        prediction = model.predict(input_data)[0]
        probabilities = model.predict_proba(input_data)[0]
        predicted_index = list(model.classes_).index(prediction)
        confidence = float(probabilities[predicted_index]) * 100.0
        confidence = max(0.0, min(confidence, 100.0))

        if prediction == APPROVAL_CLASS:
            status = 'approved'
            result_text = 'Approved'
        else:
            status = 'rejected'
            result_text = 'Rejected'

        confidence_message = format_confidence(confidence)
        explanation_data = build_explanation(raw_inputs, status)
        
        # Prepare applicant summary data
        applicant_data = {
            'age': parse_float(raw_inputs.get('Age')),
            'income': int(parse_float(raw_inputs.get('Income')) or 0),
            'debt': int(parse_float(raw_inputs.get('Debt')) or 0),
            'credit_score': parse_int(raw_inputs.get('CreditScore')),
            'years_employed': parse_float(raw_inputs.get('YearsEmployed')),
            'employed': raw_inputs.get('Employed', '').lower() == 't',
        }

        logger.info(
            'Prediction success: status=%s confidence=%.2f',
            status,
            confidence,
        )

        return render_template(
            'result.html',
            prediction_text=result_text,
            status=status,
            confidence=confidence,
            explanation_data=explanation_data,
            confidence_message=confidence_message,
            validation_errors=[],
            applicant_data=applicant_data
        )
    except Exception:
        logger.exception('Prediction failed for input')
        return render_template(
            'result.html',
            prediction_text='Prediction Failed',
            status='error',
            confidence=None,
            explanation_data={},
            confidence_message='We could not process your request at this time.',
            validation_errors=['There was an unexpected issue. Please try again later.'],
            applicant_data={}
        )


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    logger.warning('404 error: %s', error)
    return render_template(
        'result.html',
        prediction_text='Page Not Found',
        status='error',
        confidence=None,
        explanation_data={},
        confidence_message='The requested page does not exist.',
        validation_errors=['Please use the navigation links to continue.'],
        applicant_data={}
    ), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 internal server errors."""
    logger.exception('500 error: %s', error)
    return render_template(
        'result.html',
        prediction_text='Server Error',
        status='error',
        confidence=None,
        explanation_data={},
        confidence_message='An internal error occurred. Please try again later.',
        validation_errors=['Our application encountered an issue.'],
        applicant_data={}
    ), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
