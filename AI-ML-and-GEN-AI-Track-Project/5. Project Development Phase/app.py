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


def build_explanation(raw_inputs, status):
    """Create a short, realistic explanation for an approval or rejection."""
    age = parse_float(raw_inputs.get('Age')) or 0.0
    income = parse_float(raw_inputs.get('Income')) or 0.0
    credit_score = parse_int(raw_inputs.get('CreditScore')) or 0
    debt = parse_float(raw_inputs.get('Debt')) or 0.0
    years_employed = parse_float(raw_inputs.get('YearsEmployed')) or 0.0
    employed = raw_inputs.get('Employed', '').lower() == 't'
    prior_default = raw_inputs.get('PriorDefault', '').lower() == 't'
    married = raw_inputs.get('Married', '')
    citizen = raw_inputs.get('Citizen', '')
    drivers_license = raw_inputs.get('DriversLicense', '').lower() == 't'
    bank_customer = raw_inputs.get('BankCustomer', '')
    industry = raw_inputs.get('Industry', '')

    explanations = []

    if status == 'approved':
        if employed:
            explanations.append(
                f'Your current employment history of {years_employed:.1f} years gives confidence in your ability to manage payments.'
            )
        else:
            explanations.append('The model found other strengths in your profile even though you are not currently employed.')

        if credit_score >= 700:
            explanations.append(f'Your credit score of {credit_score} is generally seen as a strong factor for approval.')
        elif credit_score >= 600:
            explanations.append(f'Your credit score of {credit_score} is within a reasonable range for approval.')
        else:
            explanations.append(
                f'Your credit score of {credit_score} is lower than ideal, but the rest of your profile supported approval.'
            )

        if income >= 40000:
            explanations.append(f'An annual income of {int(income)} provides good support for repayment capacity.')
        elif income > 0:
            explanations.append(f'An annual income of {int(income)} is still a positive factor when combined with your profile.')

        if debt <= max(10000, income * 0.25):
            explanations.append('Your total debt is within a manageable range for this application.')
        else:
            explanations.append('Your debt is higher, but other profile elements helped maintain a positive decision.')

        if not prior_default:
            explanations.append('No prior default makes your application more stable.')
        else:
            explanations.append('The model notes your prior default, but current details were strong enough to support approval.')

        if married == 'u':
            explanations.append('Your marital status can contribute to financial stability in this application.')
        elif married == 'y':
            explanations.append('As a single applicant, your income and payment history helped support approval.')
        elif married == 'l':
            explanations.append('Your current marital status was considered along with your other financial strengths.')

        if citizen in ('g', 'p'):
            explanations.append('Your residency status is stable, which supports the decision.')
        elif citizen == 's':
            explanations.append('Your foreign national status was factored in, and the model still found enough supporting information.')

        if drivers_license:
            explanations.append('Having a valid driver’s license can be a positive sign of local stability and identity verification.')
        if bank_customer in ('g', 'gg', 'p'):
            explanations.append('Your bank customer relationship was part of the evaluation.')
        if industry:
            explanations.append('Your industry and employment sector helped shape the model’s decision.')

    else:
        if credit_score < 650:
            explanations.append(f'A credit score of {credit_score} may have reduced your approval chances.')
        if income < 30000:
            explanations.append(f'An annual income of {int(income)} is lower than the stronger profiles in the training data.')
        if debt > max(10000, income * 0.25):
            explanations.append('Existing debt was a significant factor in this decision.')
        if not employed:
            explanations.append('Not being currently employed is a factor in the rejection decision.')
        if prior_default:
            explanations.append('A prior default is a negative factor for credit decisions.')

        if not explanations:
            explanations.append('The application did not meet the approval pattern used by the model.')

        follow_up = []
        if credit_score < 700:
            follow_up.append('improve your credit history')
        if debt > 0:
            follow_up.append('lower your existing debt')
        if income < 40000:
            follow_up.append('increase your annual income')
        if not employed:
            follow_up.append('build stable employment')
        if prior_default:
            follow_up.append('keep payments current over time')

        if follow_up:
            improvement_text = ', '.join(follow_up[:-1]) + (' and ' + follow_up[-1] if len(follow_up) > 1 else '')
            explanations.append(f'Consider {improvement_text} before applying again.')

    return explanations[:5]


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
    raw_inputs = {field: request.form.get(field, '').strip() for field in feature_order}
    validation_errors = validate_inputs(raw_inputs)
    if validation_errors:
        logger.info('Validation failed: %s', validation_errors)
        return render_template(
            'result.html',
            prediction_text='Invalid input',
            status='invalid',
            confidence=None,
            explanations=[],
            confidence_message='Please correct the highlighted issues and try again.',
            validation_errors=validation_errors,
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
        explanations = build_explanation(raw_inputs, status)

        logger.info(
            'Prediction success: status=%s confidence=%.2f raw_inputs=%s',
            status,
            confidence,
            raw_inputs,
        )

        return render_template(
            'result.html',
            prediction_text=result_text,
            status=status,
            confidence=confidence,
            explanations=explanations,
            confidence_message=confidence_message,
            validation_errors=[],
        )
    except Exception:
        logger.exception('Prediction failed for input: %s', raw_inputs)
        return render_template(
            'result.html',
            prediction_text='Prediction failed',
            status='error',
            confidence=None,
            explanations=[],
            confidence_message='We could not process your request at this time.',
            validation_errors=['There was an unexpected issue while predicting. Please try again later.'],
        )


@app.errorhandler(404)
def not_found(error):
    logger.warning('404 error: %s', error)
    return render_template(
        'result.html',
        prediction_text='Page not found',
        status='error',
        confidence=None,
        explanations=[],
        confidence_message='The requested page does not exist.',
        validation_errors=['Please use the navigation links to continue.'],
    ), 404


@app.errorhandler(500)
def internal_error(error):
    logger.exception('500 error: %s', error)
    return render_template(
        'result.html',
        prediction_text='Server error',
        status='error',
        confidence=None,
        explanations=[],
        confidence_message='An internal error occurred. Please try again later.',
        validation_errors=['Our application encountered an issue.'],
    ), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
