# -*- coding: utf-8 -*-
"""DS_Analysis.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/11iOZTc027umxve0KMZBvHdgFmcoB4DSL

******
**Modeling Exercise for Data Science Candidates**

Analytics Center of Excellence (ACOE)
******
Amudha Giridharan

****
This notebook contains the analysis done on data, visualizations, imputation validations, class imbalance checks and model selection
Final model code is in DS_Model_Final.py
****

#Objective

Objective : To build a binary classification model to identify the individuals who are likely to earn more than $60K

#Python Lib import and Data load
"""

#import the necessary libraries
!pip install catboost
!pip install scikit-optimize
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import imblearn
from sklearn.feature_selection import SelectKBest, chi2
from sklearn.preprocessing import LabelEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import KNNImputer
from sklearn.model_selection import train_test_split
from matplotlib.colors import LinearSegmentedColormap
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score, confusion_matrix

#Read the input csv file provided
#This file is placed in collab files and the path needs to be tweaked as needed

#Define the file path
file_path = '/content/data science exercise - sample data.csv'
df = pd.read_csv(file_path)

#View few records from the file
df.head()

"""# Initial Data Analysis"""

#Let's analyze the data quality

#First look of data shows individual's details which are both categorical and continous. Incomelabel is the dependent variable.

#Let us first check the volume of data
df.shape

df.info()

df.describe()

df.describe(include=['object'])

"""**Initial observations**
1. Based on un uniform count values across the fields, we can interpret that the data is not complete for all individuals and we could expect Nulls (for ex Education shows count as 27207 implying that 260 records are NaN)
2. The response variable has a very high count for <=60K (24720 out of 27467 records have <=60k) indicating a highly imbalanced train data set and the need to address this
3. Based on this data, a baseline prediction of <=60K for all cases in general would provide 0.8999% accuracy. However we want to make sure TPR/sensitivity is as high as possible based on the goal.

#Data Pre-Processing

###Duplicate data analysis
"""

#Check for duplicates
df.duplicated().sum()
#No duplicates found

"""### Missing data analysis"""

#Let us quickly check the unique values in each categorical column to make sure of data quality

for column in df.select_dtypes(include=['object', 'category']).columns:
    unique_values = df[column].unique()
    print(f"Unique values in '{column}': \n {unique_values} \n")

#Observing NaN, '?' in columns and also observing a single space in all strings. Will fix these in subsequent steps

#Check for volume of missing/Null values
df[df.isnull().any(axis=1)]

#Observing few '?' Let us Convert '?' to Null as well - this would be taken care while loading the data for the final model
# Also let us make sure there is no leading/trailing spaces in all string fields - this should also be addressed in the final code
df = df.applymap(lambda x: str(x).strip() if isinstance(x, str) else x)
df.replace('?', np.nan, inplace=True)

#Let us check the total null count again
df[df.isnull().any(axis=1)]

#The total incomplete records are ~4589, which is approx 17% of the data provided
#As it is not advisable to ignore this volume, we will work on imputation for select fields based on feature importance

#Finally let us update response variable to binary value for ease of handling and factorize it
df['IncomeLabel'] = df['IncomeLabel'].apply(lambda x: 1 if x == '>60K' else 0).astype('category')

"""##Data Imputation"""

'''Based on data, it might not be right to impute the mean of values for numerical and most frequent for categorical
For example, we observe a person in  Prof-specialty work with 15 years of education. If most frequent is chosen then his education would be
defaulted to Hs-grad, which is not right'''

knn_imputer = KNNImputer(n_neighbors=5)
# Apply KNN imputer to numerical data
numerical_data = df.select_dtypes(include=['float64', 'int64'])
data_imputed = knn_imputer.fit_transform(numerical_data)

# Convert the imputed data back to a DataFrame
data_imputed_df = pd.DataFrame(data_imputed, columns=numerical_data.columns)

# Encode categorical columns
#Initally used label encoding, but during model performance it looked like one hot encoding
df_cat = df.select_dtypes(include=['object'])
label_encoders = {}
for column in df_cat.columns:
    le = LabelEncoder()
    non_null_indices = df_cat[column].notna()
    df_cat.loc[non_null_indices, column] = le.fit_transform(df_cat.loc[non_null_indices, column].astype(str))
    label_encoders[column] = le

label_encoders

# Apply KNN Imputer
knn_imputer = KNNImputer(n_neighbors=5)
data_cat_imputed = knn_imputer.fit_transform(df_cat)

# Decode back to categorical
data_cat_imputed_df = pd.DataFrame(data_cat_imputed, columns=df_cat.columns)
for column in df_cat.columns:
    data_cat_imputed_df[column] = label_encoders[column].inverse_transform(data_cat_imputed_df[column].round().astype(int))

data_cat_imputed_df.head(20)

df_imputed_final = pd.concat([data_imputed_df, data_cat_imputed_df,df.IncomeLabel], axis=1)

print("Imputed Data:")
print(df_imputed_final.head())

df_imputed_final = df_imputed_final[df.columns]

df_imputed_final.head(20)

df_imputed_final.describe()
df_imputed_final[df_imputed_final.select_dtypes(include=['float64', 'int64']).columns].isna().sum()

#verify if all the NaN values are imputed
#we see that the imputed data frame doesnt have any NaN values now
df_imputed_final[df_imputed_final.isnull().any(axis=1)]

# Identify rows with missing values in the original DataFrame
missing_indices = df[df.isna().any(axis=1)].index

# View these rows in the imputed DataFrame
df_imputed_final.loc[missing_indices]

"""# Data Exploration

## Visualization and Inferences
"""

df_imputed_final.info()

# Let us see the class distribution acoss Gender, Education, workclass and

def annotate_countplot(ax, data, column, hue):
    total = len(data)
    for p in ax.patches:
        height = p.get_height()
        ax.annotate(f'{100 * height / total:.2f}%',
                    (p.get_x() + p.get_width() / 2., height),
                    ha = 'center', va = 'center',
                    fontsize = 10, color = 'black',
                    xytext = (0, 10),
                    textcoords = 'offset points')

fig, axes = plt.subplots(2, 2, figsize=(20, 20))
data = df_imputed_final
# Visualization 1: Income vs. Gender
ax1 = sns.countplot(data=data, x='Gender', hue='IncomeLabel', ax=axes[0, 0])
axes[0, 0].set_title('Income vs. Gender')
axes[0, 0].set_xlabel('Gender')
axes[0, 0].set_ylabel('Count')
annotate_countplot(ax1, data, 'Gender', 'IncomeLabel')

# Visualization 2: Income vs. Education Level
ax2 = sns.countplot(data=data, x='Education', hue='IncomeLabel', order=data['Education'].value_counts().index, ax=axes[0, 1])
axes[0, 1].set_title('Income vs. Education Level')
axes[0, 1].set_xlabel('Education Level')
axes[0, 1].set_ylabel('Count')
axes[0, 1].tick_params(axis='x', rotation=90)
annotate_countplot(ax2, data, 'Education', 'IncomeLabel')

# Visualization 3: Income vs. Hours per Week (boxplot does not directly show percentages, but we can add some context)
sns.boxplot(data=data, x='IncomeLabel', y='HoursWorkWeekly', ax=axes[1, 0])
axes[1, 0].set_title('Income vs. Hours per Week')
axes[1, 0].set_xlabel('Income Label')
axes[1, 0].set_ylabel('Hours per Week')

# Visualization 4: Income vs. Workclass
ax4 = sns.countplot(data=data, x='WorkClass', hue='IncomeLabel', order=data['WorkClass'].value_counts().index, ax=axes[1, 1])
axes[1, 1].set_title('Income vs. Workclass')
axes[1, 1].set_xlabel('Workclass')
axes[1, 1].set_ylabel('Count')
axes[1, 1].tick_params(axis='x', rotation=45)
annotate_countplot(ax4, data, 'WorkClass', 'IncomeLabel')
plt.tight_layout()
plt.show()

"""From above plots, we can observe that

1.   Gender Vs Income plot

  *   64% of the data provided is that of Males while 36% is of Females. I believe this % represent the true population in terms of employment
  *   13% of Male population earns =>60K while only 4% of female populatio earns more than 60K. There are chances that this may be due to data imbalance

2.   Education vs Income

  *   Highest % of population is under High school grad category.
  *   If we sum up some college and bachelors then this % is also close to first category
  *   Though the population at Masters, professional school are Doctorate are very less we can observe that the % population earning >60K is almost equal to those <=60K in the same population

3. We can see that most workclass is in private sector. Interesting to see that Never worked class has income added. Further anlysis show they are teens or early 20s with an outlier of age 30.

4. Hours per week shows obvious relation with Income that people who work more hours per week tend to have more income.






"""

sns.pairplot(df_imputed_final, hue='IncomeLabel', size=2.5);

"""Below are the observations from pair plot
1. Age shows right skewed distribution. It indicates that most of the work force are in early years with start of range at 17 upto 90.
2. We can also observe that the high income age groups is close to being normally distributed (with slight right skew) with the minimum age range starting at 20 and peak at around 45
3. We observe that the individuals with high education years and average age have more % of high income, which is relatable
4. We can see a strong postive correlation between capital gain and high income and a strong postive correlation between education years and high income. These can also be observed in the heat map in next section
5. Lotsize, ownhouse and suburban doesn't seem to have any correlation with income as the distributions seems identical across.
6. Caploss doesnt seem to have correlatin with Income
"""

plt.figure(figsize=(16, 12))

# Plot income distribution by marital status
plt.subplot(2,2,1)
sns.countplot(y='MaritalStatus', hue='IncomeLabel', data=data, order=data['MaritalStatus'].value_counts().index)
plt.title('Income Distribution by Marital Status')
plt.xlabel('Count')
plt.ylabel('Marital Status')
plt.legend(title='Income Label', loc='upper right')


# Plot income distribution by occupation
plt.subplot(2,2,2)
sns.countplot(y='Occupation', hue='IncomeLabel', data=data, order=data['Occupation'].value_counts().index)
plt.title('Income Distribution by Occupation')
plt.xlabel('Count')
plt.ylabel('Occupation')
plt.legend(title='Income Label', loc='upper right')


# Plot income distribution by hours worked per week
plt.subplot(2,2,3)
sns.histplot(data=data, x='HoursWorkWeekly', hue='IncomeLabel', multiple='stack', kde=True)
plt.title('Income Distribution by Hours Per Week')
plt.xlabel('Hours Per Week')
plt.ylabel('Count')
plt.legend(title='Income Label', loc='upper right')

# Plot income distribution by race
plt.subplot(2,2,4)
sns.countplot(y='Race', hue='IncomeLabel', data=data, order=data['Race'].value_counts().index)
plt.title('Income Distribution by Race')
plt.xlabel('Count')
plt.ylabel('Race')
plt.legend(title='Income Label', loc='upper right')

plt.tight_layout()
plt.show()

"""# Feature Importance"""

# Let us check on feature importance with reference to response variable
# we can observe that lotsize, ownhouse and suburban have very less correlation with response var

# Simple heatmap
df_cont = df
df_cont.IncomeLabel = df_cont.IncomeLabel.astype('int')
df_cont = df_cont.select_dtypes(include=[np.number])
correlation_matrix = df_cont.corr()
plt.figure(figsize=(10, 6))
heatmap = sns.heatmap(correlation_matrix, annot=True,  fmt='.3f',linewidths=0.5, vmin=-1, vmax=1)
plt.title('Correlation Heatmap with continous variables and unimputed data ')
plt.show()

# Let us check on feature importance with reference to response variable with imputed data
# we dont observe much change due to imputation

# Simple heatmap
df_cont = df_imputed_final
df_cont.IncomeLabel = df_cont.IncomeLabel.astype('int')
df_cont = df_cont.select_dtypes(include=[np.number])
correlation_matrix = df_cont.corr()
plt.figure(figsize=(10, 6))
heatmap = sns.heatmap(correlation_matrix, annot=True,  fmt='.3f',linewidths=0.5, vmin=-1, vmax=1)
plt.title('Correlation Heatmap continous & imputed data ')
plt.show()

# sorted_index = sorted_features.index
# sorted_correlation_matrix = correlation_matrix.loc[sorted_index, sorted_index]

# # Plot the heatmap
# plt.figure(figsize=(10, 8))
# heatmap = sns.heatmap(sorted_correlation_matrix, annot=True, cmap='coolwarm', fmt='.2f', linewidths=0.5)
# plt.title('Correlation Heatmap Ordered by Feature Importance')
# plt.show()

#Feature importace check for categorical variables
df['IncomeLabel'] = df['IncomeLabel'].astype('category')
X = df[df.select_dtypes(include=['object']).columns]
y = df[df.select_dtypes(include=['category']).columns]

# use label encoder for feature importance check
df_chi = df_imputed_final
label_encoder = LabelEncoder()
for column in df_chi.select_dtypes(include=['object']).columns:
    df_chi[column] = label_encoder.fit_transform(df_chi[column])

df_chi.info()

X = df_chi.drop(df_chi.select_dtypes(include=['float64','category']),axis=1)
y = df_chi['IncomeLabel']

#final chi scores of features
chi_scores = chi2(X,y)
chi_scores

#plot for feature importance
p_values = pd.Series(chi_scores[1],index = X.columns)
p_values.sort_values(ascending = False , inplace = True)
pd.options.display.float_format = '{:.4f}'.format
p_values.plot.bar()

# Let us check on all feature importance across the df with encoded df

# Simple heatmap
df_cont = df_chi
df_cont.IncomeLabel = df_cont.IncomeLabel.astype('int')
df_cont = df_cont.select_dtypes(include=[np.number])
correlation_matrix = df_cont.corr()

# Select the correlations with the target variable
target_correlations = correlation_matrix['IncomeLabel'].drop('IncomeLabel')

# Sort the features by absolute correlation with the target variable
#again we observe that ownhouse, suburban, lotsize and occupation are <0.015 and we can choose to ignore these
#Based on model experiments with differnt sets of features, we confirmed that there is no performance depreciation if these features are removed
#In XGB experiment country was included but showed no improvement in test/train metrics
sorted_features = target_correlations.abs().sort_values(ascending=False)

print("Features ordered by importance based on correlation with target variable:")
print(sorted_features)

"""# Model Building

##Train-Test Split

Reserving 20% of provided data set as test dataset as there is no seperate test dataset provided.
"""

# Let us use the label encoded data for model selection
# Assign all columns except the target variable to X
X = df_chi.drop(columns=['IncomeLabel'])

# Assign the target variable to y
y = df['IncomeLabel']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

"""## Data Class Imbalance"""

#As the data provided is highly imbalanced, oversampling could help when non-decision tree samples are used

from imblearn.over_sampling import SMOTE
smote = SMOTE(random_state=42)
X_resampled, y_resampled = smote.fit_resample(X_train, y_train)

#Based on the experiments with XGB, CatBoost and LGBM classifiers we found that oversampling didn't add value
#hence was dropped in final modeling approach

"""##Model evaluation"""

import matplotlib.pyplot as plt
import seaborn as sns

#Let us use a common function to predict and analyze the metrics of various models
def model_prediction(model, x_train, y_train, x_test, y_test):
    # Fit the model on training data
    model.fit(x_train, y_train)
    # Predictions on training and testing data
    x_train_pred = model.predict(x_train)
    x_test_pred = model.predict(x_test)

    # Probability predictions for ROC AUC score
    y_test_prob = model.predict_proba(x_test)[:, 1]

    # Calculating various metrics
    train_accuracy = accuracy_score(y_train, x_train_pred) * 100
    test_accuracy = accuracy_score(y_test, x_test_pred) * 100
    precision = precision_score(y_test, x_test_pred)
    recall = recall_score(y_test, x_test_pred)
    auc_score = roc_auc_score(y_test, y_test_prob)

    # Printing metrics
    print(f"Accuracy Score of {model.__class__.__name__} model on Training Data is: {train_accuracy:.2f}%")
    print(f"Accuracy Score of {model.__class__.__name__} model on Testing Data is: {test_accuracy:.2f}%")
    print(f"Precision Score of {model.__class__.__name__} model is: {precision:.2f}")
    print(f"Recall Score of {model.__class__.__name__} model is: {recall:.2f}")
    print(f"AUC Score of {model.__class__.__name__} model is: {auc_score:.2f}")
    print("\n------------------------------------------------------------------------")
    print(f"Confusion Matrix of {model.__class__.__name__} model is:")

    # Confusion Matrix
    cm = confusion_matrix(y_test, x_test_pred)
    plt.figure(figsize=(8, 4))
    sns.heatmap(cm, annot=True, fmt="g", cmap="Greens")
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.title(f'Confusion Matrix of {model.__class__.__name__}')
    plt.show()

#Let us use default parameters and choose the ones which perform comparitively good for further experiments
#As mentioned earlier, the focus was on recall
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.neural_network import MLPClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier
from sklearn.linear_model import LogisticRegression

# Define models to evaluate
models = {
    'logisticregression': LogisticRegression(),
    'RandomForest': RandomForestClassifier(),
    'GradientBoosting': GradientBoostingClassifier(),
    'SVC': SVC(probability=True),
    'KNN': KNeighborsClassifier(),
    'NaiveBayes': GaussianNB(),
    'MLP': MLPClassifier(),
    'XGBoost': XGBClassifier(),
    'LightGBM': LGBMClassifier(),
    'CatBoost': CatBoostClassifier(verbose=False)
}



# Evaluate each model
for name, model in models.items():
    print(f"Evaluating {name}...")
    model_prediction(model, X_train, y_train, X_test, y_test)

# Based on above XGBclassifier, LightGBM classifier and CatBoostClassifiers were chosen for further experiment
# Hyper param tuning was done for these using gridsearchcv and finally XGB classifier was chosen for final model
