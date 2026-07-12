import os
from flask import Flask, render_template, request
import joblib

app = Flask(__name__)

# Load model and encoders from the application directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'model.pkl')
ENCODER_PATH = os.path.join(BASE_DIR, 'encoders.pkl')
model = joblib.load(MODEL_PATH)
encoders = joblib.load(ENCODER_PATH)
feature_order = list(getattr(model, 'feature_names_in_', [
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
    'Income'
]))
print('DEBUG loaded model from', MODEL_PATH)
print('DEBUG feature_order:', feature_order)
print('DEBUG model classes:', list(model.classes_))


@app.route('/')
def home():
    return render_template("home.html")
@app.route('/about')
def about():
    return render_template('about.html')
@app.route('/predict')
def predict_page():
    return render_template("index.html")


def _parse_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _parse_int(value, default=0):
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def _validate_inputs(raw_inputs):
    errors = []

    age = _parse_float(raw_inputs.get('Age', ''))
    if age < 18 or age > 100:
        errors.append('Age must be between 18 and 100.')

    income = _parse_float(raw_inputs.get('Income', ''))
    if income <= 0:
        errors.append('Annual income must be greater than zero.')

    debt = _parse_float(raw_inputs.get('Debt', ''))
    if debt < 0:
        errors.append('Debt cannot be negative.')

    years_employed = _parse_float(raw_inputs.get('YearsEmployed', ''))
    if years_employed < 0:
        errors.append('Years employed cannot be negative.')

    credit_score = _parse_int(raw_inputs.get('CreditScore', ''))
    if credit_score <= 0:
        errors.append('Credit score must be a positive number.')

    zip_code = raw_inputs.get('ZipCode', '').strip()
    if zip_code == '':
        errors.append('ZIP code is required.')
    else:
        zip_code_val = _parse_float(zip_code)
        if zip_code_val < 0:
            errors.append('ZIP code cannot be negative.')

    for col, encoder in encoders.items():
        raw_value = raw_inputs.get(col, '')
        if raw_value == '':
            errors.append(f'{col} is required.')
        elif raw_value not in list(encoder.classes_):
            errors.append(f'Invalid value for {col}: {raw_value}.')

    return errors

def _build_explanation(raw_inputs, status):
    age = _parse_float(raw_inputs.get('Age'))
    income = _parse_float(raw_inputs.get('Income'))
    credit_score = _parse_int(raw_inputs.get('CreditScore'))
    debt = _parse_float(raw_inputs.get('Debt'))
    years_employed = _parse_float(raw_inputs.get('YearsEmployed'))
    employed = raw_inputs.get('Employed', '').lower() == 't'
    prior_default = raw_inputs.get('PriorDefault', '').lower() == 't'
    married = raw_inputs.get('Married', '')
    bank_customer = raw_inputs.get('BankCustomer', '')
    citizen = raw_inputs.get('Citizen', '')
    drivers_license = raw_inputs.get('DriversLicense', '').lower() == 't'

    reasons = []

    if status == 'approved':
        if employed and income >= 30000:
            reasons.append(
                f'At age {int(age)}, your current employment and income of {int(income)} make it easier to handle a new credit card responsibly.'
            )
        elif employed:
            reasons.append(
                f'You are currently employed, and your income of {int(income)} helps support the application.'
            )
        else:
            reasons.append(
                f'You have some positive elements in your profile even though you are not employed right now.'
            )

        if credit_score >= 650:
            reasons.append(f'Your credit score of {credit_score} is one of the positive factors in this application.')
        elif credit_score >= 550:
            reasons.append(f'Your credit score of {credit_score} is reasonable and helps support the approval.')
        else:
            reasons.append(
                f'Your credit score of {credit_score} is lower, but other parts of your profile were strong enough to support approval.'
            )

        if debt <= 3:
            reasons.append(f'Your current debt level of {debt} is modest, which makes a new card easier to manage.')
        elif debt <= 7:
            reasons.append(
                f'Your existing debt of {debt} is moderate and still manageable given your other strengths.'
            )
        else:
            reasons.append(
                f'Although you have some existing loan obligations totaling {debt}, the application still shows enough strengths.'
            )

        if prior_default:
            reasons.append('A past loan issue was present, but the rest of your financial profile appears solid.')
        else:
            reasons.append('No prior default on record is a positive sign for this application.')

        if married == 'u':
            reasons.append('Being married can add stability to your overall financial picture.')
        elif married == 'y':
            reasons.append('As a single applicant, the strength of your income and credit score becomes especially important.')
        elif married == 'l':
            reasons.append('Your current marital status is part of the application, and other strong factors helped your case.')

        if citizen in ('g', 'p'):
            reasons.append('Your residency status is stable, which supports the decision.')
        elif citizen == 's':
            reasons.append('Your residency status is noted, and the rest of your profile helped the application.')

    else:
        reasons.append('Your application may not meet the approval requirements at the moment.')

        concerns = []
        if credit_score < 600:
            concerns.append('a lower credit score')
        if income < 30000:
            concerns.append('limited income')
        if debt > 7:
            concerns.append('a relatively high level of existing debt')
        if not employed:
            concerns.append('not being currently employed')
        if prior_default:
            concerns.append('a past repayment issue')
        if citizen == 's':
            concerns.append('a foreign residency status')

        if concerns:
            if len(concerns) == 1:
                reasons.append(f'Factors such as {concerns[0]} could have affected the outcome.')
            else:
                reason_text = ', '.join(concerns[:-1]) + ' and ' + concerns[-1]
                reasons.append(f'Factors such as {reason_text} could have affected the outcome.')
        else:
            reasons.append(
                'Some combination of the details you provided may not match the issuer’s current requirements.'
            )

        improvements = []
        if credit_score < 700:
            improvements.append('strengthening your credit history')
        if debt > 0:
            improvements.append('reducing outstanding debt')
        if income < 40000:
            improvements.append('increasing your income')
        if not employed:
            improvements.append('securing steady employment')
        if prior_default:
            improvements.append('keeping accounts current and avoiding missed payments')

        if improvements:
            if len(improvements) == 1:
                improvement_text = improvements[0]
            else:
                improvement_text = ', '.join(improvements[:-1]) + ' and ' + improvements[-1]
            reasons.append(f'Focusing on {improvement_text} may improve your chances in the future.')
        else:
            reasons.append('Reviewing your overall finances and applying again later may improve your chances.')

        if not employed or years_employed < 2:
            reasons.append(
                'Building a longer employment history and stable banking activity tends to make future applications stronger.'
            )

    return reasons[:5]


@app.route('/predict', methods=['POST'])
def predict():
    raw_inputs = {col: request.form.get(col, '') for col in feature_order}
    validation_errors = _validate_inputs(raw_inputs)
    print('DEBUG raw_inputs:', raw_inputs)
    if validation_errors:
        print('DEBUG validation_errors:', validation_errors)
        return render_template(
            'result.html',
            prediction_text='Invalid input',
            status='invalid',
            confidence=None,
            explanations=[],
            confidence_message='',
            validation_errors=validation_errors
        )

    processed_data = []
    encoded_inputs = {}
    for col in feature_order:
        value = raw_inputs[col]

        if col in encoders:
            encoded_value = encoders[col].transform([value])[0]
        else:
            encoded_value = _parse_float(value)

        encoded_inputs[col] = encoded_value
        processed_data.append(encoded_value)

    print('DEBUG encoded_inputs:', encoded_inputs)
    print('DEBUG feature_vector:', processed_data)

    import pandas as pd
    input_data = pd.DataFrame([processed_data], columns=feature_order)
    prediction = model.predict(input_data)[0]
    probabilities = model.predict_proba(input_data)[0]
    predicted_index = list(model.classes_).index(prediction)
    confidence = float(probabilities[predicted_index]) * 100
    confidence = max(0.0, min(confidence, 100.0))

    print('DEBUG prediction:', prediction)
    print('DEBUG probabilities:', probabilities.tolist())

    if prediction == '+':
        status = 'approved'
        result = 'Approved'
    else:
        status = 'rejected'
        result = 'Rejected'

    if confidence >= 90:
        confidence_message = 'High confidence prediction'
    elif confidence >= 70:
        confidence_message = 'Moderate confidence prediction'
    else:
        confidence_message = 'Low confidence prediction - applicant is close to the decision boundary'

    explanations = _build_explanation(raw_inputs, status)

    return render_template(
        'result.html',
        prediction_text=result,
        status=status,
        confidence=confidence,
        explanations=explanations,
        confidence_message=confidence_message,
        validation_errors=[]
    )


if __name__ == "__main__":
    app.run(debug=True)