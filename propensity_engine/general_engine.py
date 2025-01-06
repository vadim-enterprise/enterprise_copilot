from typing import List, Dict, Tuple
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report, brier_score_loss
from churn_model.model.reporting import decile_bin_all_propensities, count_churn_rate_within_bin
from sklearn.utils.class_weight import compute_class_weight

# Hyperparameters
_HIDDEN_LAYERS = [64, 32, 16]
_LEARNING_RATE = 0.001
_BATCH_SIZE = 32
_EPOCHS = 100
# _DROP_OUT_RATE = 0.3
# _MODEL_PATH = "nn_churn_model.pth"

class NeuralNetworkModel(nn.Module):
    def __init__(self,input_dim: int, 
                 hidden_layers: List[int] = None,
                 class_weights=None): # dropout_rate: float = _DROP_OUT_RATE,
        super(NeuralNetworkModel, self).__init__()

        # Default hidden layer configuration
        if hidden_layers is None:
            hidden_layers = _HIDDEN_LAYERS

        layers = []

        # Input layer
        layers.append(nn.Linear(input_dim, hidden_layers[0]))
        layers.append(nn.ReLU())
        # layers.append(nn.Dropout(dropout_rate))

        # Hidden layers
        for i in range(len(hidden_layers) - 1):
            layers.append(nn.Linear(hidden_layers[i], hidden_layers[i + 1]))
            layers.append(nn.ReLU())
            # layers.append(nn.Dropout(dropout_rate))

        # Output layer
        layers.append(nn.Linear(hidden_layers[-1], 2))  # 2 output units for binary classification with CrossEntropyLoss
        # layers.append(nn.Sigmoid())

        # Define the model as a sequential block of layers
        self.model = nn.Sequential(*layers)
        self.learning_rate = _LEARNING_RATE

        # Use CrossEntropyLoss with class weights if provided
        if class_weights is not None:
            self.criterion = nn.CrossEntropyLoss(weight=class_weights)
        else:
            self.criterion = nn.CrossEntropyLoss()

        # self.criterion = nn.BCEWithLogitsLoss()
        self.optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate)

    def forward(self, x):
        return self.model(x)
    
    def fit(self, X_train, y_train):
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.to(device)

        X_train_tensor = torch.tensor(X_train.values, dtype=torch.float32).to(device)
        y_train_tensor = torch.tensor(y_train.values, dtype=torch.long).to(device)

        for epoch in range(_EPOCHS):
            self.train()
            self.optimizer.zero_grad()
            outputs = self(X_train_tensor)
            loss = self.criterion(outputs, y_train_tensor)
            loss.backward()
            self.optimizer.step()

            # Print loss periodically
            if (epoch + 1) % 10 == 0:
                print(f"Epoch [{epoch+1}/{_EPOCHS}], Loss: {loss.item():.4f}")
    
    def predict(self, X):
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.to(device)
        
        X_tensor = torch.tensor(X.values, dtype=torch.float32).to(device)
        self.eval()
        with torch.no_grad():
            logits = self(X_tensor).cpu()
            probabilities = torch.softmax(logits, dim=1).numpy()[:, 1] # Probability of positive class
            predictions = logits.argmax(dim=1).numpy() # Class preciction

        return predictions, probabilities
    
    def evaluate(self, X_train, y_train, X_test, y_test) -> Dict:
        eval_results = {}

        # Training set evaluation
        y_train_pred, y_train_pred_prob = self.predict(X_train)
        train_accuracy = accuracy_score(y_train, y_train_pred)
        train_conf_matrix = confusion_matrix(y_train, y_train_pred)
        train_report = classification_report(y_train, y_train_pred)
        train_brier_score = brier_score_loss(y_train, y_train_pred_prob)
        
        eval_results["train_accuracy"] = train_accuracy
        eval_results["train_conf_matrix"] = train_conf_matrix
        eval_results["train_classification_report"] = train_report
        eval_results["train_brier_score"] = train_brier_score

        print("\nTraining Set Evaluation:")
        print(f"Accuracy: {train_accuracy}")
        print(f"Brier Score: {train_brier_score}")
        print(f"Confusion Matrix:\n{train_conf_matrix}")
        print(f"Classification Report:\n{train_report}")

        # Testing set evaluation
        y_test_pred, y_test_pred_prob = self.predict(X_test)
        test_accuracy = accuracy_score(y_test, y_test_pred)
        test_conf_matrix = confusion_matrix(y_test, y_test_pred)
        test_report = classification_report(y_test, y_test_pred)
        test_brier_score = brier_score_loss(y_test, y_test_pred_prob)
        
        eval_results["test_accuracy"] = test_accuracy
        eval_results["test_conf_matrix"] = test_conf_matrix
        eval_results["test_classification_report"] = test_report
        eval_results["test_brier_score"] = test_brier_score

        print("\nTesting Set Evaluation:")
        print(f"Accuracy: {test_accuracy}")
        print(f"Brier Score: {test_brier_score}")
        print(f"Confusion Matrix:\n{test_conf_matrix}")
        print(f"Classification Report:\n{test_report}")

        # Prepare output DataFrame for test predictions
        output_df = X_test.copy()
        output_df['churn'] = y_test
        output_df['churn_probability'] = y_test_pred_prob
        output_df = decile_bin_all_propensities(output_df)
        output_df_group = count_churn_rate_within_bin(output_df)

        return eval_results, output_df, output_df_group



def train_nn_model(train_df, test_df, target='churn') -> Tuple[nn.Module, Dict, pd.DataFrame, pd.DataFrame]:
    """
    Train and evaluate a PyTorch neural network model on the train and test sets.
    
    Parameters:
    - train_df (pd.DataFrame): Training data with features and target.
    - test_df (pd.DataFrame): Testing data with features and target.
    - target (str): Target column name.
    
    Returns:
    - model (nn.Module): Trained PyTorch model.
    - eval_results (dict): Dictionary of evaluation metrics.
    - output_df (pd.DataFrame): DataFrame with actual churn, churn probabilities, and decile bins.
    - output_df_group (pd.DataFrame): DataFrame with churn rate by decile bin.
    """
    removed_columns = ['CUSTOMER_KEY', 'window_start', 'window_end', 'churn_date', 'FIRST_CONTRACT_DATE', 'INDUSTRY', target]

    X_train = train_df.drop(columns=[col for col in removed_columns if col in train_df.columns], errors='ignore')
    y_train = train_df[target]
    X_test = test_df.drop(columns=[col for col in removed_columns if col in test_df.columns], errors='ignore')
    y_test = test_df[target]

    # Calculate class weights based on the imbalance in y_train
    class_weights_np = compute_class_weight('balanced', classes=[0, 1], y=y_train)
    class_weights = torch.tensor(class_weights_np, dtype=torch.float32)

    model = NeuralNetworkModel(input_dim=X_train.shape[1], class_weights = class_weights)
    model.fit(X_train, y_train)
    eval_results, output_df, output_df_group = model.evaluate(X_train, y_train, X_test, y_test)
    
    return model, eval_results, output_df, output_df_group