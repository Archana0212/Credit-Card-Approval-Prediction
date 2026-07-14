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

# Real-world consumer credit score range accepted from the user.
REAL_CREDIT_SCORE_MIN = 300
REAL_CREDIT_SCORE_MAX = 900

# UCI Credit Approval Dataset internal CreditScore feature range.
UCI_CREDIT_SCORE_MIN = 0
UCI_CREDIT_SCORE_MAX = 67


def load_artifacts():
    """Load the serialized model and encoders from local assets."""
    try:
        model = joblib.load(MODEL_PATH)
        encoders = joblib.load(ENCODER_PATH)
        logger.info('Loaded model from %s', MODEL_PATH)
        logger.info('Loaded encoders from %s', ENCODER_PATH)
        print("="*50)
        print("ENCODERS LOADED BY FLASK")
        for key in encoders:
            print(key, encoders[key].classes_)
        print("="*50)
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

APPROVAL_CLASS = 0


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def parse_float(value):
    """Parse a value to float, returning None for invalid or empty input."""
    if value is None:
        return None
    try:
        parsed = float(str(value).strip())
    except (ValueError, TypeError):
        return None
    return parsed


def parse_int(value):
    """Parse a value to int, returning None for invalid or empty input."""
    if value is None:
        return None
    try:
        parsed = int(float(str(value).strip()))
    except (ValueError, TypeError):
        return None
    return parsed


def convert_credit_score_to_uci_scale(real_credit_score):
    """Convert a real-world credit score (300-900) to the UCI dataset's
    internal CreditScore scale (0-67).

    This conversion is only ever used to build the feature vector that is
    fed into the model. The original, user-entered real-world score is what
    is shown throughout the rest of the application.
    """
    real_range = REAL_CREDIT_SCORE_MAX - REAL_CREDIT_SCORE_MIN
    uci_range = UCI_CREDIT_SCORE_MAX - UCI_CREDIT_SCORE_MIN

    normalized = (real_credit_score - REAL_CREDIT_SCORE_MIN) / real_range
    uci_score = round(normalized * uci_range) + UCI_CREDIT_SCORE_MIN

    return max(UCI_CREDIT_SCORE_MIN, min(uci_score, UCI_CREDIT_SCORE_MAX))


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

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

    income = parse_float(raw_inputs.get("Income"))
    if income is None or income < 10000:
        errors.append("Annual income must be at least ₹10,000.")

    debt = parse_float(raw_inputs.get('Debt', '').strip())
    if debt is None:
        errors.append('Debt must be a valid number.')
    elif debt < 0 or debt > 28:
        errors.append('Debt must be between 0 and 28.')

    years_employed = parse_float(raw_inputs.get('YearsEmployed', '').strip())
    if years_employed is None:
        errors.append('Years employed must be a valid number.')
    elif years_employed < 0:
        errors.append('Years employed cannot be negative.')

    credit_score = parse_int(raw_inputs.get('CreditScore', '').strip())
    if credit_score is None:
        errors.append('Credit score must be a valid whole number.')
    elif credit_score < REAL_CREDIT_SCORE_MIN or credit_score > REAL_CREDIT_SCORE_MAX:
        errors.append(
            f'Credit score must be between {REAL_CREDIT_SCORE_MIN} and '
            f'{REAL_CREDIT_SCORE_MAX}.'
        )

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


# ---------------------------------------------------------------------------
# Financial / profile analysis helpers (all operate on the ORIGINAL,
# real-world values entered by the user)
# ---------------------------------------------------------------------------

def calculate_financial_metrics(income, debt):
    """Compute debt level based on UCI dataset debt scale."""

    if debt <= 5:
        debt_level = 'Low'
    elif debt <= 15:
        debt_level = 'Moderate'
    else:
        debt_level = 'High'

    return {
        'debt_level': debt_level,
        'income': income,
        'debt_value': debt,
        'is_manageable': debt <= 10,
        'debt_concern': 'high' if debt > 10 else 'low',
    }


def assess_credit_profile(credit_score):
    """Assess a real-world credit score (300-900) into a qualitative tier."""
    if credit_score >= 750:
        return 'excellent', 'Your excellent credit score shows strong creditworthiness.'
    elif credit_score >= 650:
        return 'good', 'Your credit score is satisfactory.'
    else:
        return 'low', 'Your credit score needs improvement.'


def assess_employment_stability(employed, years_employed):
    """Assess employment status and tenure."""
    if not employed:
        return 'unemployed', 'not currently employed'
    elif years_employed <= 0:
        return 'unknown', 'employment duration not provided'
    elif years_employed >= 5:
        return 'stable', f'{years_employed:.1f} years of stable employment'
    elif years_employed >= 2:
        return 'moderate', f'{years_employed:.1f} years of employment experience'
    else:
        return 'recent', f'{years_employed:.1f} years of employment'


def _extract_profile_values(raw_inputs):
    """Extract and coerce the commonly-used applicant fields once, so the
    explanation builders below don't each repeat the same parsing logic."""
    return {
        'age': parse_float(raw_inputs.get('Age')) or 0.0,
        'income': parse_float(raw_inputs.get('Income')) or 0.0,
        'credit_score': parse_int(raw_inputs.get('CreditScore')) or 0,
        'debt': parse_float(raw_inputs.get('Debt')) or 0.0,
        'years_employed': parse_float(raw_inputs.get('YearsEmployed')) or 0.0,
        'employed': raw_inputs.get('Employed', '').lower() == 't',
        'prior_default': raw_inputs.get('PriorDefault', '').lower() == 't',
        'drivers_license': raw_inputs.get('DriversLicense', '').lower() == 't',
    }


def build_strengths_section(raw_inputs):
    """Generate personalized strengths from the applicant's profile."""
    profile = _extract_profile_values(raw_inputs)
    strengths = []

    employment_status, employment_desc = assess_employment_stability(
        profile['employed'], profile['years_employed']
    )
    if employment_status != 'unemployed':
        strengths.append(f'Strong employment profile: You have {employment_desc}.')

    credit_level, credit_desc = assess_credit_profile(profile['credit_score'])
    if credit_level in ('excellent', 'good'):
        strengths.append(credit_desc)

    if profile['income'] >= 60000:
        strengths.append(
            f"Solid income foundation: Your annual income of "
            f"\u20b9{int(profile['income']):,} supports your debt obligations."
        )
    elif profile['income'] >= 40000:
        strengths.append(
            f"Adequate income level: Your annual income of "
            f"\u20b9{int(profile['income']):,} is sufficient for credit management."
        )

    metrics = calculate_financial_metrics(profile['income'], profile['debt'])
    if metrics['is_manageable']:
        strengths.append(
            f"Healthy debt profile: Your debt level ({metrics['debt_value']}) is manageable."
        )

    if not profile['prior_default']:
        strengths.append('Clean payment history: No prior defaults on record.')

    if profile['drivers_license']:
        strengths.append("Verified identity: Valid driver's license on file.")

    return strengths


def build_weaknesses_section(raw_inputs):
    """Generate personalized weaknesses from the applicant's profile."""
    profile = _extract_profile_values(raw_inputs)
    weaknesses = []

    if not profile['employed']:
        weaknesses.append('Employment gap: You are not currently employed.')
    elif profile['years_employed'] < 2:
        weaknesses.append(
            f"Limited employment history: Only {profile['years_employed']:.1f} "
            f"years at current position."
        )

    if profile['credit_score'] < 600:
        weaknesses.append(
            f"Lower credit score: Your score of {profile['credit_score']} is "
            f"below preferred standards."
        )
    elif profile['credit_score'] < 650:
        weaknesses.append(
            f"Fair credit score: Your score of {profile['credit_score']} "
            f"requires improvement."
        )

    if profile['income'] < 30000:
        weaknesses.append(
            f"Limited income: Your annual income of "
            f"\u20b9{int(profile['income']):,} is below average."
        )

    metrics = calculate_financial_metrics(profile['income'], profile['debt'])
    if not metrics['is_manageable']:
        weaknesses.append(
            f"High debt level: Your debt score ({metrics['debt_value']}) requires improvement."
        )

    if profile['prior_default']:
        weaknesses.append('Previous default: A prior loan default is on record.')

    return weaknesses


def build_recommendations(raw_inputs, status):
    """Generate targeted recommendations based on applicant profile and decision."""
    profile = _extract_profile_values(raw_inputs)
    recommendations = []

    if status == 'rejected':
        if profile['credit_score'] < 700:
            recommendations.append(
                'Build your credit score to 700+ by maintaining on-time payments for the next 6-12 months.'
            )

        if profile['debt'] > 10:
            recommendations.append(
                'Reduce your debt level before applying again.'
            )

        if not profile['employed']:
            recommendations.append(
                'Secure stable employment before reapplying.'
            )

        if profile['prior_default']:
            recommendations.append(
                'Maintain a clean repayment history for at least 2 years.'
            )

        if not recommendations:
            recommendations.append(
                'Consider reapplying after improving your financial profile.'
            )

    else:
        recommendations.append(
            'Maintain timely payments and responsible credit usage.'
        )

        if profile['credit_score'] < 750:
            recommendations.append(
                'Continue improving your credit score.'
            )

        if profile['debt'] > 10:
            recommendations.append(
                'Consider reducing your debt level.'
            )

    return recommendations


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


def build_explanation(raw_inputs, status):
    """Create a comprehensive, personalized explanation for the decision.

    All figures used here, including CreditScore, are the ORIGINAL
    real-world values entered by the user -- never the UCI-scaled value
    used internally for prediction.
    """
    profile = _extract_profile_values(raw_inputs)

    strengths = build_strengths_section(raw_inputs)
    weaknesses = build_weaknesses_section(raw_inputs)
    recommendations = build_recommendations(raw_inputs, status)
    summary = build_summary_statement(
        profile['income'],
        profile['debt'],
        profile['credit_score'],
        profile['employed'],
        status,
    )

    return {
        'strengths': strengths[:3],
        'weaknesses': weaknesses[:3],
        'recommendations': recommendations[:3],
        'summary': summary,
    }


# ---------------------------------------------------------------------------
# Model input preparation
# ---------------------------------------------------------------------------

def prepare_input_data(raw_inputs):
    """Convert validated raw inputs into the feature vector expected by the
    model.

    The user-entered CreditScore (300-900) is converted to the UCI dataset's
    internal 0-67 scale here, and only here. The raw_inputs dict itself is
    left untouched so that every other part of the application continues to
    see and display the original real-world score.
    """
    row = []
    for field in feature_order:
        value = str(raw_inputs.get(field, '')).strip()

        if field in categorical_fields:
            if value not in category_values[field]:
                raise ValueError(f'Invalid category for {field}: {value}')
            row.append(encoders[field].transform([value])[0])
        elif field == 'CreditScore':
            real_credit_score = parse_int(value)
            if real_credit_score is None:
                raise ValueError(f'Invalid numeric value for {field}: {value}')
            row.append(convert_credit_score_to_uci_scale(real_credit_score))
        else:
            transformed = parse_int(value) if field == 'ZipCode' else parse_float(value)
            if transformed is None:
                raise ValueError(f'Invalid numeric value for {field}: {value}')
            row.append(transformed)

    return pd.DataFrame([row], columns=feature_order)


def format_confidence(confidence):
    """Translate a numeric confidence percentage into a human-readable message."""
    if confidence >= 85:
        return 'High confidence prediction.'
    if confidence >= 60:
        return 'Moderate confidence prediction.'
    return 'Low confidence prediction. The applicant is close to the decision boundary.'


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def home():
    """Render the landing page."""
    return render_template('home.html')


@app.route('/about')
def about():
    """Render the about page."""
    return render_template('about.html')


@app.route('/predict', methods=['GET'])
def predict_page():
    """Render the prediction input form."""
    return render_template('index.html')


@app.route('/predict', methods=['POST'])
def predict():
    """Process a credit card application prediction request."""
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
            applicant_data={},
        )

    try:
        input_data = prepare_input_data(raw_inputs)
        prediction = model.predict(input_data)[0]
        probabilities = model.predict_proba(input_data)[0]
        print("===== PREDICT ROUTE CALLED =====")
        print("\n========== MODEL OUTPUT ==========")
        print("Prediction:", prediction)
        print("Classes:", model.classes_)
        print("Probabilities:", probabilities)
        print("==================================\n")
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

        # Applicant summary always reflects the original real-world values.
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
            applicant_data=applicant_data,
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
            applicant_data={},
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
        applicant_data={},
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
        applicant_data={},
    ), 500


if __name__ == '__main__':
    app.run(debug=True)