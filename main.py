import os
import numpy as np
from mock_data_generator import SolapurWadiDataGenerator
from ai_decision_model import RailwayDecisionAI
from data_models import ScenarioType

def train_and_save_model():
    """
    Manages the AI training curriculum, feeding it a balanced set of
    difficult scenarios to ensure robust and diverse decision-making skills.
    """
    print("Initializing model training process with problem-centric curriculum...")
    
    generator = SolapurWadiDataGenerator()
    ai_model = RailwayDecisionAI(generator.section)
    
    all_X_data, all_y_data = [], []
    
    # Define the curriculum: how many scenarios of each type to generate.
    # This ensures the AI sees many examples of each problem type.
    curriculum = {
        ScenarioType.BOTTLENECK_CONFLICT: 200,
        ScenarioType.MAJOR_DISRUPTION: 150,
        ScenarioType.HIGH_DENSITY: 150,
    }
    
    total_scenarios = sum(curriculum.values())
    completed_scenarios = 0

    for scenario_type, count in curriculum.items():
        for i in range(count):
            completed_scenarios += 1
            print(f"\n--- Generating Scenario {completed_scenarios}/{total_scenarios} (Type: {scenario_type.name}) ---")
            
            # Generate a specific problematic scenario
            schedules, positions = generator.generate_scenario(scenario_type)
            # Extract features from this scenario
            features_df = ai_model.extract_features(schedules, positions)
            
            if features_df.empty:
                continue

            # For each train in the scenario, find the best decision via simulation
            for _, row in features_df.iterrows():
                all_X_data.append([row[col] for col in ai_model.feature_columns])
                decision = ai_model._generate_optimal_decision_by_simulation(row, schedules, positions)
                all_y_data.append(decision)

    print(f"\nGenerated {len(all_X_data)} total training samples from {total_scenarios} scenarios.")
    
    # Train the AI model on the curated curriculum
    ai_model.train_model(np.array(all_X_data), np.array(all_y_data))
    
    # Save the battle-hardened model
    ai_model.save_model("railway_ai_model.joblib")
    
    print("\n✅ AI Model training complete and saved successfully!")

if __name__ == "__main__":
    train_and_save_model()