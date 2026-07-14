# Credit Card Approval Prediction System

## 🌐 Live Application

**Application Link:** https://credit-card-approval-prediction-1-n63c.onrender.com/

**Demo Link:**https://youtu.be/99rVdEhsewQ

---

# Credit Card Approval Prediction Using Machine Learning

## 📌 Overview

The Credit Card Approval Prediction System is a Machine Learning-based web application that predicts whether a credit card application is likely to be **Approved** or **Rejected** based on applicant details. The project aims to automate the credit approval process, reduce manual effort, and support faster decision-making.

The application is built using **Python, Flask, Scikit-learn, HTML, CSS, and Bootstrap**, with a trained Logistic Regression model deployed on Render.

---

## 🎯 Objectives

* Predict credit card approval status using Machine Learning.
* Automate the applicant evaluation process.
* Improve decision-making speed and consistency.
* Provide prediction confidence along with the result.
* Offer a simple and user-friendly web interface.

---

## ✨ Features

* User-friendly web interface
* Applicant data input form
* Real-time prediction
* Approval/Rejected result
* Prediction confidence score
* Responsive design
* Flask web deployment

---

## 🛠 Technologies Used

### Frontend

* HTML5
* CSS3
* Bootstrap

### Backend

* Python
* Flask

### Machine Learning

* Scikit-learn
* Logistic Regression
* Pandas
* NumPy
* Joblib

### Deployment

* Render

---

## 📂 Project Structure

```
Credit-Card-Approval-Prediction/
│
├── app.py
├── model.pkl
├── encoders.pkl
├── requirements.txt
├── clean_dataset.csv
├── crx.csv
│
├── templates/
│   ├── home.html
│   ├── index.html
│   ├── result.html
│   └── about.html
│
├── static/
│   ├── css/
│   ├── images/
│   └── js/
│
└── README.md
```

---

## ⚙️ How It Works

1. User enters applicant details.
2. The Flask application validates the input.
3. Categorical values are encoded using saved encoders.
4. The trained Logistic Regression model processes the data.
5. The model predicts whether the application is Approved or Rejected.
6. The prediction confidence score is displayed.

---

## 📊 Input Features

* Gender
* Age
* Debt
* Married
* Bank Customer
* Industry
* Ethnicity
* Years Employed
* Prior Default
* Employed
* Credit Score
* Driver's License
* Citizen
* Zip Code
* Income

---

## 📤 Output

* Credit Card Approval Status

  * Approved
  * Rejected
* Prediction Confidence Score

---

## 🤖 Machine Learning Model

**Algorithm Used:** Logistic Regression

The model was trained using historical credit card application data after preprocessing, categorical encoding, and feature engineering. The trained model is stored as **model.pkl**, while the label encoders are stored in **encoders.pkl**.

---

## 🚀 Installation

Clone the repository:

```bash
git clone https://github.com/your-username/credit-card-approval-prediction.git
```

Move into the project folder:

```bash
cd credit-card-approval-prediction
```

Install the required packages:

```bash
pip install -r requirements.txt
```

Run the Flask application:

```bash
python app.py
```

Open your browser and visit:

```
http://127.0.0.1:5000/
```

---

## 📈 Future Enhancements

* User Authentication
* Database Integration
* Multiple Machine Learning Models
* Explainable AI (XAI)
* API Support
* Cloud Database
* Model Retraining Pipeline

---

## 📸 Screens

* Home Page
* Prediction Form
* Prediction Result
* About Page

---

## 👨‍💻 Authors

This project was developed by:

* **Archana**
* **Kulsum**
* **Meghana**

**B.Tech – Artificial Intelligence & Machine Learning**

**SV College of Engineering**


---

## 📄 License

This project is developed for educational and academic purposes.
