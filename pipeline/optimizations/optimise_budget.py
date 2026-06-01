import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from itertools import product

def main():
    print("Starting Budget Optimization Phase with Grid Search...")
    
    # Setup paths
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    master_features_path = os.path.join(base_dir, 'Data', 'Gold', 'master_features.parquet')
    predictions_path = os.path.join(base_dir, 'outputs', 'round2_final', 'bigbug_predictions.csv')
    
    # We need to gracefully fallback if round2_final doesn't exist
    if not os.path.exists(predictions_path):
        predictions_path = os.path.join(base_dir, 'outputs', 'round2', 'bigbug_predictions.csv')
        
    output_dir = os.path.join(base_dir, 'outputs')
    os.makedirs(output_dir, exist_ok=True)
    
    # Load data
    print("Loading datasets...")
    df_features = pd.read_parquet(master_features_path)
    df_preds = pd.read_csv(predictions_path)
    
    df = pd.merge(df_features, df_preds, on='Outlet_ID', how='inner')
    
    # Verify required columns exist, fallback gracefully if not
    if 'competition_density_score' not in df.columns:
        if 'poi_total_1km' in df.columns:
            df['competition_density_score'] = df['poi_total_1km'] # Proxy
        else:
            df['competition_density_score'] = 1.0 # Default fallback
            
    if 'composite_gravity_score' not in df.columns:
        df['composite_gravity_score'] = 50.0 # Default fallback

    # Calculate ROI logic
    print("Calculating ROI scores...")
    df['uplift_gap_litres'] = df['Maximum_Monthly_Liters'] - df['hist_mean_monthly']
    df['uplift_gap_litres'] = df['uplift_gap_litres'].clip(lower=0)
    
    df['gravity_multiplier'] = df['composite_gravity_score'] / 100.0
    df['competition_multiplier'] = 1.0 / (1.0 + df['competition_density_score'])
    df['roi_score'] = df['uplift_gap_litres'] * df['gravity_multiplier'] * df['competition_multiplier']
    
    # Separate Western Province for allocation
    is_western = df['province'] == 'Western'
    df_w = df[is_western].copy()
    df_other = df[~is_western].copy()
    
    print(f"Found {len(df_w)} Western Province outlets.")
    
    # Sort and rank Western
    df_w = df_w.sort_values(by='roi_score', ascending=False).reset_index(drop=True)
    df_w['roi_rank'] = df_w.index + 1
    
    print("Running Grid Search Optimization for Tier Percentiles...")
    
    # Percentages to test for Tier 1, Tier 2, Tier 3
    # They must sum to <= 1.0
    t1_pcts = np.arange(0.05, 0.25, 0.05)
    t2_pcts = np.arange(0.10, 0.45, 0.05)
    t3_pcts = np.arange(0.10, 0.45, 0.05)
    
    best_profit = -np.inf
    best_config = None
    best_df = None
    
    target_budget = 5000000.0
    
    for t1, t2, t3 in product(t1_pcts, t2_pcts, t3_pcts):
        if t1 + t2 + t3 > 1.0:
            continue
            
        temp_df = df_w.copy()
        total_w = len(temp_df)
        
        c1 = int(total_w * t1)
        c2 = c1 + int(total_w * t2)
        c3 = c2 + int(total_w * t3)
        
        temp_df['allocation_tier'] = 'None'
        temp_df['Trade_Spend_Allocation_LKR'] = 0.0
        
        temp_df.loc[:c1-1, 'allocation_tier'] = 'High'
        temp_df.loc[:c1-1, 'Trade_Spend_Allocation_LKR'] = 2500.0
        
        temp_df.loc[c1:c2-1, 'allocation_tier'] = 'Medium'
        temp_df.loc[c1:c2-1, 'Trade_Spend_Allocation_LKR'] = 1200.0
        
        temp_df.loc[c2:c3-1, 'allocation_tier'] = 'Low'
        temp_df.loc[c2:c3-1, 'Trade_Spend_Allocation_LKR'] = 500.0
        
        current_budget = temp_df['Trade_Spend_Allocation_LKR'].sum()
        
        # Penalize severely if budget is grossly over
        if current_budget > target_budget * 1.1:
            continue
            
        # If under budget, we pretend we can balance it to 5M by adding to High tier
        # (which gives 20% conversion)
        diff = target_budget - current_budget
        
        # Expected lift calculation
        temp_df['expected_lift'] = 0.0
        temp_df.loc[temp_df['allocation_tier'] == 'High', 'expected_lift'] = temp_df['uplift_gap_litres'] * 0.20
        temp_df.loc[temp_df['allocation_tier'] == 'Medium', 'expected_lift'] = temp_df['uplift_gap_litres'] * 0.10
        temp_df.loc[temp_df['allocation_tier'] == 'Low', 'expected_lift'] = temp_df['uplift_gap_litres'] * 0.03
        
        total_lift = temp_df['expected_lift'].sum()
        
        # If we have leftover budget, we'll assign it to High tier outlets, giving extra lift.
        # But for grid search ranking, we just want to find a good baseline.
        # Let's approximate the final profit
        profit_margin = 50.0
        projected_profit = (total_lift * profit_margin) - current_budget
        
        if current_budget <= target_budget and projected_profit > best_profit:
            best_profit = projected_profit
            best_config = (t1, t2, t3)
            best_df = temp_df
            
    if best_config is None:
        print("Grid search failed to find a valid configuration under budget. Reverting to safe defaults.")
        # Safe defaults
        best_config = (0.10, 0.20, 0.20)
        t1, t2, t3 = best_config
        temp_df = df_w.copy()
        total_w = len(temp_df)
        c1 = int(total_w * t1)
        c2 = c1 + int(total_w * t2)
        c3 = c2 + int(total_w * t3)
        temp_df['allocation_tier'] = 'None'
        temp_df['Trade_Spend_Allocation_LKR'] = 0.0
        temp_df.loc[:c1-1, 'allocation_tier'] = 'High'
        temp_df.loc[:c1-1, 'Trade_Spend_Allocation_LKR'] = 2500.0
        temp_df.loc[c1:c2-1, 'allocation_tier'] = 'Medium'
        temp_df.loc[c1:c2-1, 'Trade_Spend_Allocation_LKR'] = 1200.0
        temp_df.loc[c2:c3-1, 'allocation_tier'] = 'Low'
        temp_df.loc[c2:c3-1, 'Trade_Spend_Allocation_LKR'] = 500.0
        best_df = temp_df
        
    print(f"Optimal Configuration Found: Top {best_config[0]*100}% Tier 1, Next {best_config[1]*100}% Tier 2, Next {best_config[2]*100}% Tier 3")
    df_w = best_df.copy()
    
    # Identify cutoffs for balancing logic
    total_w = len(df_w)
    tier1_cutoff = int(total_w * best_config[0])
    tier2_cutoff = tier1_cutoff + int(total_w * best_config[1])
    tier3_cutoff = tier2_cutoff + int(total_w * best_config[2])

    # Greedy balancing using multiples of 50
    current_budget = df_w['Trade_Spend_Allocation_LKR'].sum()
    print(f"Base allocation sum: {current_budget:,.2f} LKR. Balancing towards {target_budget:,.2f} LKR...")
    
    max_cap = 15000.0
    min_cap = 500.0
    
    if current_budget < target_budget:
        diff = target_budget - current_budget
        for _ in range(5000):
            if diff < 50.0:
                break
            
            made_change = False
            for idx in range(tier2_cutoff): # Add to Tier 1 and Tier 2
                if diff < 50.0:
                    break
                current_val = df_w.at[idx, 'Trade_Spend_Allocation_LKR']
                if max_cap - current_val >= 50.0:
                    df_w.at[idx, 'Trade_Spend_Allocation_LKR'] += 50.0
                    diff -= 50.0
                    made_change = True
            
            if not made_change:
                break
                        
    elif current_budget > target_budget:
        diff = current_budget - target_budget
        for _ in range(5000):
            if diff < 50.0:
                break
                
            made_change = False
            for idx in range(tier3_cutoff-1, -1, -1): # Reduce from bottom up
                if diff < 50.0:
                    break
                current_alloc = df_w.at[idx, 'Trade_Spend_Allocation_LKR']
                if current_alloc >= 50.0:
                    reduce_amt = 50.0
                    if current_alloc - reduce_amt < min_cap and current_alloc > 0:
                        reduce_amt = current_alloc # Drop to 0
                        df_w.at[idx, 'allocation_tier'] = 'None'
                    
                    df_w.at[idx, 'Trade_Spend_Allocation_LKR'] -= reduce_amt
                    diff -= reduce_amt
                    made_change = True
            
            if not made_change:
                break
                    
    # Map Spend Types
    spend_mapping = {
        'High': 'Cooler Subsidy / Display Rack',
        'Medium': 'Promotional Discount',
        'Low': 'Light Merchandising',
        'None': 'None'
    }
    df_w['recommended_spend_type'] = df_w['allocation_tier'].map(spend_mapping)
    
    # Ensure exact precision rounding issues don't fail verification
    df_w['Trade_Spend_Allocation_LKR'] = df_w['Trade_Spend_Allocation_LKR'].round(2)
    
    # Combine back (Only Western for output, as requested)
    df_final = df_w.copy()
    
    print("Generating ROI Distribution Plot...")
    plt.figure(figsize=(12, 6))
    
    tier1_min = df_w[df_w['allocation_tier'] == 'High']['roi_score'].min() if not df_w[df_w['allocation_tier'] == 'High'].empty else df_w['roi_score'].max()
    tier2_min = df_w[df_w['allocation_tier'] == 'Medium']['roi_score'].min() if not df_w[df_w['allocation_tier'] == 'Medium'].empty else tier1_min
    tier3_min = df_w[df_w['allocation_tier'] == 'Low']['roi_score'].min() if not df_w[df_w['allocation_tier'] == 'Low'].empty else tier2_min

    plot_data = df_w[df_w['roi_score'] > 0] # Filter exactly 0s for clearer visual
    
    sns.histplot(data=plot_data, x='roi_score', bins=60, color='gray', alpha=0.6)
    
    max_roi = plot_data['roi_score'].max()
    plt.axvspan(tier1_min, max_roi, color='green', alpha=0.2, label='High (Growth Accelerator)')
    plt.axvspan(tier2_min, tier1_min, color='blue', alpha=0.2, label='Medium (Visibility Boost)')
    plt.axvspan(tier3_min, tier2_min, color='yellow', alpha=0.2, label='Low (Brand Presence)')
    plt.axvspan(0, tier3_min, color='red', alpha=0.2, label='None (No Allocation)')
    
    plt.title('ROI Score Distribution & Budget Allocation Tiers (Western Province)')
    plt.xlabel('ROI Score')
    plt.ylabel('Frequency (Outlets)')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'roi_distribution.png'))
    plt.close()

    print("Exporting Artifacts...")
    submit_df = df_final[['Outlet_ID', 'Trade_Spend_Allocation_LKR']]
    submit_df.to_csv(os.path.join(output_dir, 'bigbug_budget_allocations.csv'), index=False)
    
    cols = [
        'Outlet_ID', 'province', 'uplift_gap_litres', 'composite_gravity_score', 
        'competition_density_score', 'roi_score', 'roi_rank', 'allocation_tier', 
        'recommended_spend_type', 'Trade_Spend_Allocation_LKR'
    ]
    diag_df = df_final[cols]
    diag_df.to_csv(os.path.join(output_dir, 'budget_diagnostics.csv'), index=False)
    
    # Save the parquet file in data/Optimization as requested
    opt_dir = os.path.join(base_dir, 'data', 'Optimization')
    os.makedirs(opt_dir, exist_ok=True)
    diag_df.to_parquet(os.path.join(opt_dir, 'budget_features.parquet'), index=False)
    
    final_budget = df_final['Trade_Spend_Allocation_LKR'].sum()
    print(f"Budget Optimization Complete!")
    print(f"Total Budget Allocated: {final_budget:,.2f} LKR")
    print(f"Total Outlets Processed: {len(df_final)}")
    
    # Check budget is <= 5,000,000
    assert final_budget <= 5000000.0, f"Budget exceeded: {final_budget}"

if __name__ == '__main__':
    main()
