import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

# Load dataset
df = pd.read_csv("clean_dataset.csv")

print("Dataset Loaded Successfully!")
print(df.head())

# Separate features and target
X = df.drop("Approved", axis=1)
y = df["Approved"]

# Encode categorical columns
encoders = {}

# Encode all non-numeric columns
encoders = {}

for col in X.columns:
    try:
        pd.to_numeric(X[col])
    except:
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col].astype(str))
        encoders[col] = le

# Encode target
target_encoder = LabelEncoder()
y = target_encoder.fit_transform(y)

# Save target encoder too
encoders["Approved"] = target_encoder

# Split dataset
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# Train Logistic Regression model
model = LogisticRegression(max_iter=1000)

model.fit(X_train, y_train)

# Test Accuracy
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print("\n===================================")
print("Model Trained Successfully!")
print(f"Accuracy: {accuracy * 100:.2f}%")
print("===================================")

# Save model
joblib.dump(model, "model.pkl")

# Save encoders
joblib.dump(encoders, "encoders.pkl")

print("\nmodel.pkl saved successfully.")
print("encoders.pkl saved successfully.")
print("\nTraining Completed!")