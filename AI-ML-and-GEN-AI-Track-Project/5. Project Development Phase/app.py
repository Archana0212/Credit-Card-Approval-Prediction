from flask import Flask, render_template, request
import joblib
import numpy as np

app = Flask(__name__)

# Load model and encoders
model = joblib.load("model.pkl")
encoders = joblib.load("encoders.pkl")
feature_order = [
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
    ]

feature_weights = dict(zip(
    feature_order,
    model.coef_[0]
))


@app.route('/')
def home():
    return render_template("home.html")
@app.route('/about')
def about():
    return render_template('about.html')
@app.route('/predict')
def predict_page():
    return render_template("index.html")


@app.route('/predict', methods=['POST'])
def predict():
    processed_data = []
    for col in feature_order:
        value = request.form[col]

        # Encode categorical columns
        if col in encoders:
            value = encoders[col].transform([value])[0]
        else:
            value = float(value)

        processed_data.append(value)

    # Convert to NumPy array
    import pandas as pd
    input_data = pd.DataFrame([processed_data], columns=feature_order)
    prediction = model.predict(input_data)[0]
    explanations = []
    for feature, value in input_data.iloc[0].items():
        print(feature, value)
        weight = feature_weights[feature]
        impact = value * weight
        if prediction == '+' and impact > 0:\
            explanations.append(
                f"{feature} helped increase approval chances"
             )
        elif prediction == '-' and impact < 0:
            explanations.append(
                f"{feature} increased rejection risk"
             )
    probabilities = model.predict_proba(input_data)[0]
    if prediction == '+':
        confidence = probabilities[list(model.classes_).index('+')] * 100
    else:
        confidence = probabilities[list(model.classes_).index('-')] * 100
    if confidence >= 90:
        confidence_message = "High confidence prediction"
    elif confidence >= 70:
        confidence_message = "Moderate confidence prediction"
    else:
        confidence_message = "Low confidence prediction - applicant is close to the decision boundary"

    # Convert prediction into readable text
    if prediction == '+':
        result = "Approved"
        status = "approved"
    else:
        result = "Rejected"
        status = "rejected"

    return render_template(
    "result.html",
    prediction_text=result,
    status=status,
    confidence=round(confidence, 2),
    explanations=explanations[:5],
    confidence_message=confidence_message
)


if __name__ == "__main__":
    app.run(debug=True)