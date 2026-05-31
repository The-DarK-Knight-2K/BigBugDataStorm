import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def main():
    print("Starting Budget Optimization Phase...")
    
    # Setup paths
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    master_features_path = os.path.join(base_dir, 'Data', 'Gold', 'master_features.parquet')
    predictions_path = os.path.join(base_dir, 'outputs', 'round2', 'bigbug_predictions.csv')
    output_dir = os.path.join(base_dir, 'data', 'optimizations')
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
    
    # Define Tiers based on percentiles
    total_w = len(df_w)
    tier1_cutoff = int(total_w * 0.15)
    tier2_cutoff = int(total_w * 0.40)
    tier3_cutoff = int(total_w * 0.65)
    
    # Assign Base Tiers and Base Allocations
    df_w['allocation_tier'] = 'None'
    df_w['Trade_Spend_Allocation_LKR'] = 0.0
    
    df_w.loc[:tier1_cutoff-1, 'allocation_tier'] = 'High'
    df_w.loc[:tier1_cutoff-1, 'Trade_Spend_Allocation_LKR'] = 2500.0
    
    df_w.loc[tier1_cutoff:tier2_cutoff-1, 'allocation_tier'] = 'Medium'
    df_w.loc[tier1_cutoff:tier2_cutoff-1, 'Trade_Spend_Allocation_LKR'] = 1167.0
    
    df_w.loc[tier2_cutoff:tier3_cutoff-1, 'allocation_tier'] = 'Low'
    df_w.loc[tier2_cutoff:tier3_cutoff-1, 'Trade_Spend_Allocation_LKR'] = 500.0
    
    # Greedy balancing to exactly 5,000,000
    target_budget = 5000000.0
    current_budget = df_w['Trade_Spend_Allocation_LKR'].sum()
    print(f"Base allocation sum: {current_budget:,.2f} LKR. Balancing to {target_budget:,.2f} LKR...")
    
    max_cap = 15000.0
    min_cap = 500.0
    
    if current_budget < target_budget:
        diff = target_budget - current_budget
        while diff > 0.01:
            for idx in range(tier1_cutoff):
                if diff <= 0.01:
                    break
                add_amt = min(100.0, diff)
                if df_w.at[idx, 'Trade_Spend_Allocation_LKR'] + add_amt <= max_cap:
                    df_w.at[idx, 'Trade_Spend_Allocation_LKR'] += add_amt
                    diff -= add_amt
            if diff > 0.01 and all(df_w.loc[:tier1_cutoff-1, 'Trade_Spend_Allocation_LKR'] >= max_cap - 0.01):
                # Spill over to Tier 2 if Tier 1 maxes out
                for idx in range(tier1_cutoff, tier2_cutoff):
                    if diff <= 0.01:
                        break
                    add_amt = min(100.0, diff)
                    if df_w.at[idx, 'Trade_Spend_Allocation_LKR'] + add_amt <= max_cap:
                        df_w.at[idx, 'Trade_Spend_Allocation_LKR'] += add_amt
                        diff -= add_amt
                        
    elif current_budget > target_budget:
        diff = current_budget - target_budget
        while diff > 0.01:
            for idx in range(tier3_cutoff-1, tier2_cutoff-1, -1):
                if diff <= 0.01:
                    break
                current_alloc = df_w.at[idx, 'Trade_Spend_Allocation_LKR']
                if current_alloc > 0:
                    reduce_amt = min(100.0, diff)
                    if current_alloc - reduce_amt < min_cap:
                        reduce_amt = current_alloc # Drop to 0 if below min actionable
                        df_w.at[idx, 'allocation_tier'] = 'None'
                        
                    df_w.at[idx, 'Trade_Spend_Allocation_LKR'] -= reduce_amt
                    diff -= reduce_amt
                    
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
    
    # Process other provinces
    df_other['roi_rank'] = np.nan
    df_other['allocation_tier'] = 'None'
    df_other['Trade_Spend_Allocation_LKR'] = 0.0
    df_other['recommended_spend_type'] = 'None'
    
    # Combine back
    df_final = pd.concat([df_w, df_other], ignore_index=True)
    
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
    diag_df.to_parquet(os.path.join(output_dir, 'budget_features.parquet'), index=False)
    
    final_budget = df_final['Trade_Spend_Allocation_LKR'].sum()
    print(f"Budget Optimization Complete!")
    print(f"Total Budget Allocated: {final_budget:,.2f} LKR")
    print(f"Total Outlets Processed: {len(df_final)}")
    assert abs(final_budget - 5000000.0) < 1.0, f"Budget mismatch: {final_budget}"

if __name__ == '__main__':
    main()
