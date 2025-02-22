# -*- coding: utf-8 -*-
"""DS_Model_Final.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1o3ECCNvlJ3WeGRcdtKGzLUHRsfit4gcF

Final model code for DS evaluation

Objective: Identify the individuals who will likely have an income >60K

Approach : XGB Model - trained with selected features,crossvalidated and hyperparam tuned with focus on recall score

Detailed analysis, EDA are in DS_Analysis.py

Amudha Giridharan
"""

#import the necessary libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import KNNImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.model_selection import train_test_split, GridSearchCV
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, confusion_matrix , precision_recall_curve
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score

# Load the data treating ? as NaN and removing init space as per earlier analysis
data = pd.read_csv('/content/data science exercise - sample data.csv', na_values=' ?', skipinitialspace=True)

# Load X and y, drop the columns based on feature importance findings and code the response variable to 0/1
X = data.drop(columns=['IncomeLabel','Country','LotSize','Suburban','OwnHouse','WorkClass'], axis=1)
y = data['IncomeLabel'].apply(lambda x: 1 if x == '>60K' else 0)

# Function to evaluate the model for train/test data with a threshold of 0.5 (default)
# Threshold can be reduced to have better recall at the expense of precision, accuracy and F1
# As focus is on Recall, precision-recall curve is plotted to observe the trade off with threshold tuning
def model_evaluation(model, X_test, y_test, threshold = 0.5):
    y_test_pred_proba = model.predict_proba(X_test)
    y_test_pred = (y_test_pred_proba[:, 1] >= threshold).astype(int)
    print(classification_report(y_test, y_test_pred))
    cm = confusion_matrix(y_test, y_test_pred)
    # Extract TN, FP, FN, TP
    TN, FP, FN, TP = cm.ravel()
    # Calculate specificity
    specificity = TN / (TN + FP)
    print(f'Specificity: {specificity:.4f}')
    roc_auc = roc_auc_score(y_test, y_test_pred)
    print(f'ROC AUC Score: {roc_auc:.4f}')
    print(f'precision : {precision_score(y_test, y_test_pred):.4f}')
    print(f'recall = {recall_score(y_test, y_test_pred):.4f}')

    # Plot confusion matrix and precision-recall curve side by side
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Confusion matrix
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=['<=60K', '>60K'], yticklabels=['<=60K', '>60K'], ax=ax1)
    ax1.set_xlabel('Predicted')
    ax1.set_ylabel('Actual')
    ax1.set_title('Confusion Matrix')

    # Precision-Recall curve
    precision, recall, thresholds = precision_recall_curve(y_test, y_test_pred)
    ax2.fill_between(recall, precision, alpha=0.2, color='b')
    ax2.plot(recall, precision, color='b')
    ax2.set_xlabel("Recall")
    ax2.set_ylabel("Precision")
    ax2.set_title("Precision-Recall Curve")

    plt.tight_layout()
    plt.show()

# Define feature types
numerical_features = X.select_dtypes(include=['float64', 'int64']).columns
categorical_features = X.select_dtypes(include=['object']).columns

# Define seperate transformers for numerical data types and categorical datatypes
# KNN is used for both based on data analysis

#Scaling is added as cap gains variance is wider compared to others
numerical_transformer = Pipeline(steps=[
    ('imputer', KNNImputer(n_neighbors=5)),
    ('scaler', StandardScaler())
])

categorical_transformer = Pipeline(steps=[
    ('onehot', OneHotEncoder(sparse_output = False,handle_unknown='ignore')),
    ('imputer', KNNImputer(n_neighbors=5))

])

# Combine transformers using ColumnTransformer
preprocessor = ColumnTransformer(
    transformers=[
        ('num', numerical_transformer, numerical_features),
        ('cat', categorical_transformer, categorical_features)
    ]
)

# Define the XGBoost classifier
xgb = XGBClassifier(eval_metric='logloss', use_label_encoder=False)

# Create a full pipeline with preprocessing and classifier
pipeline = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('classifier', xgb)
])

# Define parameter grid for GridSearchCV
# scale_pos_weight is on the higher end as there is significant data imbalance
# param grid values are based on previous experiments with given data set
# param values are chosen in such a way to avoid long running time in colab - these can be adjusted to wider and higher range in high performing environment
# Scope of additional param evaluation exists
param_grid = {
    'classifier__n_estimators': [500,1000],
    'classifier__max_depth': [3,5],
    'classifier__learning_rate': [0.005,0.2],
    'classifier__scale_pos_weight': [10,12],
    'verbose' : [1]
}

# Split the data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Using Grid search CV for hyper param tuning
# cv used is minimum for local performance - this can be increased in a high performing environment
# scoring is based on recall rather than accuracy/F1 as the goal assumption is to correctly predict the postive cases >60K
#.   while trying to maintain precision recall balance
grid_search = GridSearchCV(estimator=pipeline, param_grid=param_grid, scoring='recall', cv=3, n_jobs=-1, verbose=2)
grid_search.fit(X_train, y_train)

#Store the best model for further predictions and view the params and best recall score
best_model = grid_search.best_estimator_
best_params = grid_search.best_params_
best_score = grid_search.best_score_
print("Best Parameters:", best_params)
print("Best Score:", best_score)

#check the model performance using the custom function for train data
#using default threshold of 0.5
model_evaluation(best_model, X_train, y_train)

# Save the pipeline
import joblib
joblib.dump(best_model, '/content/xgb_pipeline.pkl')

# Load the pipeline
loaded_pipeline = joblib.load('/content/xgb_pipeline.pkl')

# predict outcome with the test set if the test set doesn't have a target value already to evaluate metrics
# test set needs to have the same columns as that of train set (columns 'Country','LotSize','Suburban','OwnHouse','WorkClass' should be dropped if exists)
y_pred = loaded_pipeline.predict(X_test)

#check the model performance using the custom function for test data if target value is available
#using default threshold of 0.5
model_evaluation(loaded_pipeline, X_test, y_test)

#verifying for a different threshold
model_evaluation(loaded_pipeline, X_test, y_test,threshold = 0.4)