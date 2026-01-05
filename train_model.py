"""
Phase 2: ML Model Training for Query Complexity Classification
Trains a Random Forest classifier on the labeled training data
"""

import json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import StandardScaler
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

class ComplexityClassifier:
    """Train and evaluate query complexity classifier"""
    
    def __init__(self, training_data_path='training_data.json'):
        """Initialize and load training data"""
        print("\n" + "="*80)
        print("FitFact ML Complexity Classifier")
        print("="*80)
        
        # Load training data
        print(f"\n Loading training data from: {training_data_path}")
        with open(training_data_path, 'r') as f:
            self.data = json.load(f)
        
        print(f" Loaded {len(self.data)} labeled examples")
        
        # Convert to DataFrame
        self.df = pd.DataFrame(self.data)
        
        # Feature columns
        self.feature_columns = [
            'word_count',
            'char_count',
            'sentence_count',
            'question_mark_count',
            'has_comparison',
            'has_specificity',
            'has_mechanism',
            'has_multiple_questions',
            'technical_term_count'
        ]
        
        # Convert boolean to int
        for col in ['has_comparison', 'has_specificity', 'has_mechanism', 'has_multiple_questions']:
            self.df[col] = self.df[col].astype(int)
        
        self.models = {}
        self.scalers = {}
        self.results = {}
        
    def show_data_summary(self):
        """Display summary statistics"""
        print("\n" + "="*80)
        print(" TRAINING DATA SUMMARY")
        print("="*80)
        
        print(f"\nTotal examples: {len(self.df)}")
        print("\nComplexity distribution:")
        dist = self.df['complexity'].value_counts()
        for label, count in dist.items():
            pct = (count / len(self.df)) * 100
            print(f"  {label.capitalize()}: {count} ({pct:.1f}%)")
        
        print("\nFeature statistics by complexity:")
        for complexity in ['simple', 'medium', 'complex']:
            subset = self.df[self.df['complexity'] == complexity]
            if len(subset) > 0:
                print(f"\n  {complexity.capitalize()} ({len(subset)} examples):")
                print(f"    Avg word count: {subset['word_count'].mean():.1f}")
                print(f"    Avg technical terms: {subset['technical_term_count'].mean():.1f}")
                print(f"    Has comparison: {subset['has_comparison'].sum()} ({subset['has_comparison'].sum()/len(subset)*100:.1f}%)")
                print(f"    Has mechanism: {subset['has_mechanism'].sum()} ({subset['has_mechanism'].sum()/len(subset)*100:.1f}%)")
    
    def prepare_data(self, test_size=0.2, random_state=42):
        """Split data into train and test sets"""
        print("\n" + "="*80)
        print(" SPLITTING DATA")
        print("="*80)
        
        X = self.df[self.feature_columns].values
        y = self.df['complexity'].values
        
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        print(f"\n Data split complete:")
        print(f"  Training set: {len(self.X_train)} examples ({(1-test_size)*100:.0f}%)")
        print(f"  Test set: {len(self.X_test)} examples ({test_size*100:.0f}%)")
        
        # Show distribution in both sets
        train_dist = pd.Series(self.y_train).value_counts()
        test_dist = pd.Series(self.y_test).value_counts()
        
        print("\n  Training set distribution:")
        for label in ['simple', 'medium', 'complex']:
            if label in train_dist.index:
                print(f"    {label}: {train_dist[label]}")
        
        print("\n  Test set distribution:")
        for label in ['simple', 'medium', 'complex']:
            if label in test_dist.index:
                print(f"    {label}: {test_dist[label]}")
    
    def train_random_forest(self, n_estimators=100, max_depth=10, random_state=42):
        """Train Random Forest classifier"""
        print("\n" + "="*80)
        print(" TRAINING RANDOM FOREST")
        print("="*80)
        
        print(f"\nHyperparameters:")
        print(f"  n_estimators: {n_estimators} (number of trees)")
        print(f"  max_depth: {max_depth} (max tree depth)")
        print(f"  random_state: {random_state}")
        
        # Train model
        rf_model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            class_weight='balanced'  # Handle imbalanced classes
        )
        
        print("\n Training...")
        rf_model.fit(self.X_train, self.y_train)
        
        self.models['random_forest'] = rf_model
        print(" Random Forest training complete!")
        
        # Feature importance
        self.show_feature_importance(rf_model, 'Random Forest')
        
        return rf_model
    
    def train_logistic_regression(self, random_state=42):
        """Train Logistic Regression as baseline"""
        print("\n" + "="*80)
        print(" TRAINING LOGISTIC REGRESSION (Baseline)")
        print("="*80)
        
        # Scale features for Logistic Regression
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(self.X_train)
        
        self.scalers['logistic_regression'] = scaler
        
        # Train model
        lr_model = LogisticRegression(
            max_iter=1000,
            random_state=random_state,
            class_weight='balanced'
        )
        
        print("\n Training...")
        lr_model.fit(X_train_scaled, self.y_train)
        
        self.models['logistic_regression'] = lr_model
        print(" Logistic Regression training complete!")
        
        return lr_model
    
    def show_feature_importance(self, model, model_name):
        """Display feature importance from Random Forest"""
        if not hasattr(model, 'feature_importances_'):
            return
        
        importances = model.feature_importances_
        indices = np.argsort(importances)[::-1]
        
        print(f"\n {model_name} Feature Importance:")
        print("-" * 60)
        for i in range(len(self.feature_columns)):
            idx = indices[i]
            print(f"  {i+1}. {self.feature_columns[idx]:30s} {importances[idx]:.4f} ({importances[idx]*100:.1f}%)")
    
    def evaluate_model(self, model_name):
        """Evaluate model performance"""
        print("\n" + "="*80)
        print(f" EVALUATING {model_name.upper()}")
        print("="*80)
        
        model = self.models[model_name]
        
        # Prepare test data
        if model_name == 'logistic_regression':
            X_test_eval = self.scalers['logistic_regression'].transform(self.X_test)
        else:
            X_test_eval = self.X_test
        
        # Predictions
        y_pred = model.predict(X_test_eval)
        
        # Accuracy
        accuracy = accuracy_score(self.y_test, y_pred)
        print(f"\n Overall Accuracy: {accuracy:.2%}")
        
        # Classification report
        print("\n Detailed Classification Report:")
        print("-" * 60)
        print(classification_report(self.y_test, y_pred, 
                                   target_names=['complex', 'medium', 'simple'],
                                   zero_division=0))
        
        # Confusion matrix
        cm = confusion_matrix(self.y_test, y_pred, 
                            labels=['simple', 'medium', 'complex'])
        
        print("\n Confusion Matrix:")
        print("-" * 60)
        print("             Predicted")
        print("              Simple  Medium  Complex")
        print(f"Actual Simple   {cm[0][0]:3d}     {cm[0][1]:3d}     {cm[0][2]:3d}")
        print(f"       Medium   {cm[1][0]:3d}     {cm[1][1]:3d}     {cm[1][2]:3d}")
        print(f"       Complex  {cm[2][0]:3d}     {cm[2][1]:3d}     {cm[2][2]:3d}")
        
        # Store results
        self.results[model_name] = {
            'accuracy': accuracy,
            'y_pred': y_pred,
            'confusion_matrix': cm
        }
        
        return accuracy, y_pred
    
    def compare_models(self):
        """Compare all trained models"""
        print("\n" + "="*80)
        print(" MODEL COMPARISON")
        print("="*80)
        
        print("\n Accuracy Comparison:")
        print("-" * 60)
        for model_name, results in self.results.items():
            acc = results['accuracy']
            print(f"  {model_name.replace('_', ' ').title():25s} {acc:.2%}")
        
        # Determine best model
        best_model = max(self.results.items(), key=lambda x: x[1]['accuracy'])
        print(f"\n Best Model: {best_model[0].replace('_', ' ').title()} ({best_model[1]['accuracy']:.2%})")
        
        return best_model[0]
    
    def save_model(self, model_name, output_path='ml_optimizer/complexity_classifier.pkl'):
        """Save the trained model"""
        print("\n" + "="*80)
        print(" SAVING MODEL")
        print("="*80)
        
        model = self.models[model_name]
        scaler = self.scalers.get(model_name, None)
        
        # Package model with metadata
        model_package = {
            'model': model,
            'scaler': scaler,
            'feature_columns': self.feature_columns,
            'model_type': model_name,
            'accuracy': self.results[model_name]['accuracy'],
            'trained_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'training_samples': len(self.X_train),
            'test_samples': len(self.X_test)
        }
        
        joblib.dump(model_package, output_path)
        print(f" Model saved to: {output_path}")
        print(f"   Model type: {model_name}")
        print(f"   Accuracy: {self.results[model_name]['accuracy']:.2%}")
        print(f"   Training samples: {len(self.X_train)}")
        
        return output_path
    
    def generate_report(self, output_file='model_training_report.txt'):
        """Generate a comprehensive training report"""
        print("\n" + "="*80)
        print(" GENERATING REPORT")
        print("="*80)
        
        with open(output_file, 'w') as f:
            f.write("="*80 + "\n")
            f.write("FitFact ML Complexity Classifier - Training Report\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            
            f.write("DATASET SUMMARY\n")
            f.write("-"*80 + "\n")
            f.write(f"Total examples: {len(self.df)}\n")
            f.write(f"Training examples: {len(self.X_train)}\n")
            f.write(f"Test examples: {len(self.X_test)}\n\n")
            
            f.write("Complexity Distribution:\n")
            dist = self.df['complexity'].value_counts()
            for label, count in dist.items():
                pct = (count / len(self.df)) * 100
                f.write(f"  {label.capitalize()}: {count} ({pct:.1f}%)\n")
            
            f.write("\n" + "="*80 + "\n")
            f.write("MODEL RESULTS\n")
            f.write("-"*80 + "\n\n")
            
            for model_name, results in self.results.items():
                f.write(f"{model_name.upper()}\n")
                f.write(f"Accuracy: {results['accuracy']:.2%}\n\n")
            
            best_model = max(self.results.items(), key=lambda x: x[1]['accuracy'])
            f.write(f"Best Model: {best_model[0]} ({best_model[1]['accuracy']:.2%})\n")
        
        print(f" Report saved to: {output_file}")
        return output_file


def main():
    """Main training pipeline"""
    
    # Initialize
    classifier = ComplexityClassifier('training_data.json')
    
    # Show data summary
    classifier.show_data_summary()
    
    # Prepare data
    classifier.prepare_data(test_size=0.2)
    
    # Train models
    classifier.train_random_forest(n_estimators=100, max_depth=10)
    classifier.train_logistic_regression()
    
    # Evaluate models
    classifier.evaluate_model('random_forest')
    classifier.evaluate_model('logistic_regression')
    
    # Compare models
    best_model = classifier.compare_models()
    
    # Save best model
    classifier.save_model(best_model)
    
    # Generate report
    classifier.generate_report()
    
    print("\n" + "="*80)
    print("PHASE 2 COMPLETE!")
    print("="*80)
    print("\n Next steps:")
    print("  1. Review model_training_report.txt")
    print("  2. Check complexity_classifier.pkl (your trained model)")
    print("  3. Ready for Phase 3: Integration into FitFact!")
    print("\n")


if __name__ == "__main__":
    main()
