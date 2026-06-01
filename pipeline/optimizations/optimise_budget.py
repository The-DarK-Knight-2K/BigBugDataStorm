import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def main():
    print("Starting Advanced Tier-Budget Capped Greedy Knapsack Optimization...")
    
    # Setup paths
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    master_features_path = os.path.join(base_dir, 'Data', 'Gold', 'master_features.parquet')
    predictions_path = os.path.join(base_dir, 'outputs', 'round2_final', 'bigbug_predictions.csv')
    
    # Fallback paths if round2_final doesn't exist
    if not os.path.exists(predictions_path):
        predictions_path = os.path.join(base_dir, 'outputs', 'round2', 'bigbug_predictions.csv')
    if not os.path.exists(predictions_path):
        predictions_path = os.path.join(base_dir, 'outputs', 'bigbug_predictions.csv')
        
    output_dir = os.path.join(base_dir, 'outputs')
    os.makedirs(output_dir, exist_ok=True)
    
    # Check dataset existence
    if not os.path.exists(master_features_path):
        raise FileNotFoundError(f"Master features not found at: {master_features_path}")
    if not os.path.exists(predictions_path):
        raise FileNotFoundError(f"Model predictions not found at: {predictions_path}")
        
    # Load data
    print(f"Loading master features from {master_features_path}...")
    df_features = pd.read_parquet(master_features_path)
    print(f"Loading predictions from {predictions_path}...")
    df_preds = pd.read_csv(predictions_path)
    
    # Merge datasets
    df = pd.merge(df_features, df_preds, on='Outlet_ID', how='inner')
    print(f"Merged dataset shape: {df.shape}")
    
    # Check and fallback column names robustly
    recent_sales_col = 'recent_3m_avg' if 'recent_3m_avg' in df.columns else 'hist_mean_monthly'
    gravity_col = 'composite_gravity_score' if 'composite_gravity_score' in df.columns else 'gravity_score'
    
    if gravity_col not in df.columns:
        # If no gravity column, check for POI proxy or default to 50
        if 'poi_total_1km' in df.columns:
            df['composite_gravity_score'] = df['poi_total_1km']
        else:
            df['composite_gravity_score'] = 50.0
        gravity_col = 'composite_gravity_score'
        
    if 'cooler_count' not in df.columns:
        df['cooler_count'] = 0.0
        
    if 'Outlet_Size' not in df.columns:
        df['Outlet_Size'] = 'Medium'
        
    if 'Outlet_Type' not in df.columns:
        df['Outlet_Type'] = 'Grocery'
        
    # Isolate Western Province
    is_western = df['distributor_id'].isin(['DIST_W_01', 'DIST_W_02', 'DIST_W_03'])
    df_w = df[is_western].copy()
    print(f"Isolated {len(df_w)} Western Province outlets eligible for allocation.")
    
    # Step 1: Calculate robust ROI scores
    print("Calculating ROI scores...")
    df_w['uplift_gap_litres'] = (df_w['Maximum_Monthly_Liters'] - df_w[recent_sales_col]).clip(lower=0)
    
    def minmax(series):
        s_min = series.min()
        s_max = series.max()
        if s_max - s_min == 0:
            return series * 0.0
        return (series - s_min) / (s_max - s_min + 1e-9)
        
    df_w['norm_uplift'] = minmax(df_w['uplift_gap_litres'])
    df_w['norm_gravity'] = minmax(df_w[gravity_col])
    df_w['norm_sales'] = minmax(df_w[recent_sales_col])
    df_w['norm_coolers'] = minmax(df_w['cooler_count'])
    
    # Composite ROI score formula
    df_w['roi_score'] = (
        0.40 * df_w['norm_uplift'] +
        0.30 * df_w['norm_gravity'] +
        0.20 * df_w['norm_sales'] +
        0.10 * df_w['norm_coolers']
    )
    
    # Step 2: Sort and assign base percentiles / Tiers
    df_w = df_w.sort_values(by='roi_score', ascending=False).reset_index(drop=True)
    df_w['roi_rank'] = df_w.index + 1
    
    total_w = len(df_w)
    high_cutoff = int(total_w * 0.15)      # Top 15%
    med_cutoff = high_cutoff + int(total_w * 0.35) # Next 35%
    low_cutoff = med_cutoff + int(total_w * 0.15)  # Next 15%
    
    df_w['allocation_tier'] = 'None'
    df_w.loc[:high_cutoff-1, 'allocation_tier'] = 'High'
    df_w.loc[high_cutoff:med_cutoff-1, 'allocation_tier'] = 'Medium'
    df_w.loc[med_cutoff:low_cutoff-1, 'allocation_tier'] = 'Low'
    
    # Step 3: Apply Operational Capacity & Activity Guardrails
    print("Applying operational capacity & activity guardrails...")
    # Activity: Outlets must have history and positive headroom
    no_activity = (df_w[recent_sales_col] == 0) | (df_w['uplift_gap_litres'] == 0)
    df_w.loc[no_activity, 'allocation_tier'] = 'None'
    
    # Cold-start cap (no transaction history) capped at Medium
    if 'has_transaction_history' in df_w.columns:
        cold_start = df_w['has_transaction_history'] == False
        df_w.loc[cold_start & (df_w['allocation_tier'] == 'High'), 'allocation_tier'] = 'Medium'
        
    # Size & Type Cap: Small shops, Kiosks, and Pharmacies cannot absorb High tier cooler grants
    is_small_layout = df_w['Outlet_Size'].isin(['Small']) | df_w['Outlet_Type'].isin(['Kiosk', 'Pharmacy'])
    df_w.loc[is_small_layout & (df_w['allocation_tier'] == 'High'), 'allocation_tier'] = 'Medium'
    
    # Step 4: Map Tiers to Parameters
    # As approved, the Low tier floor is set to 500 LKR to prevent any allocations in the [1, 499] range
    tier_params = {
        'High': {'cap': 12000.0, 'floor': 2000.0, 'efficiency': 0.028, 'spend_type': 'Cooler Subsidy / Display Rack'},
        'Medium': {'cap': 3000.0, 'floor': 500.0, 'efficiency': 0.012, 'spend_type': 'Promotional Discount'},
        'Low': {'cap': 800.0, 'floor': 500.0, 'efficiency': 0.004, 'spend_type': 'Light Merchandising'},
        'None': {'cap': 0.0, 'floor': 0.0, 'efficiency': 0.0, 'spend_type': 'None'}
    }
    
    df_w['tier_cap'] = df_w['allocation_tier'].map(lambda t: tier_params[t]['cap'])
    df_w['tier_floor'] = df_w['allocation_tier'].map(lambda t: tier_params[t]['floor'])
    df_w['volume_per_lkr'] = df_w['allocation_tier'].map(lambda t: tier_params[t]['efficiency'])
    df_w['recommended_spend_type'] = df_w['allocation_tier'].map(lambda t: tier_params[t]['spend_type'])
    
    # Step 5: Compute Headroom-Scaled, Rounded Spending Limits
    print("Computing headroom-scaled and rounded limits...")
    df_w['max_headroom_allocation'] = 0.0
    
    has_eff = df_w['volume_per_lkr'] > 0
    df_w.loc[has_eff, 'max_headroom_allocation'] = np.minimum(
        df_w.loc[has_eff, 'tier_cap'],
        df_w.loc[has_eff, 'uplift_gap_litres'] / df_w.loc[has_eff, 'volume_per_lkr']
    )
    
    # Round to nearest 50 LKR
    df_w['max_headroom_allocation'] = (df_w['max_headroom_allocation'] / 50.0).round() * 50.0
    
    # Enforce Floor limits
    below_floor = df_w['max_headroom_allocation'] < df_w['tier_floor']
    df_w.loc[below_floor, 'max_headroom_allocation'] = 0.0
    df_w.loc[below_floor, 'allocation_tier'] = 'None'
    df_w.loc[below_floor, 'recommended_spend_type'] = 'None'
    
    # Step 6: Greedy Knapsack Allocation Pass with Option A Tier-Budget Buckets
    print("Running Tier-Budget Capped Greedy Knapsack Allocation loop...")
    df_w = df_w.sort_values(by='roi_score', ascending=False).reset_index(drop=True)
    
    # Partitioned budget buckets
    high_budget = 2500000.0
    med_budget = 1750000.0
    low_budget = 750000.0
    
    allocations = np.zeros(len(df_w))
    
    for i, row in df_w.iterrows():
        tier = row['allocation_tier']
        max_alloc = row['max_headroom_allocation']
        floor = row['tier_floor']
        
        if max_alloc <= 0 or tier == 'None':
            continue
            
        # Allocate based on matching tier budget bucket
        if tier == 'High':
            spend = min(max_alloc, high_budget)
            spend = round(spend / 50.0) * 50.0
            if spend < floor:
                spend = 0.0
            else:
                high_budget -= spend
                allocations[i] = spend
        elif tier == 'Medium':
            spend = min(max_alloc, med_budget)
            spend = round(spend / 50.0) * 50.0
            if spend < floor:
                spend = 0.0
            else:
                med_budget -= spend
                allocations[i] = spend
        elif tier == 'Low':
            spend = min(max_alloc, low_budget)
            spend = round(spend / 50.0) * 50.0
            if spend < floor:
                spend = 0.0
            else:
                low_budget -= spend
                allocations[i] = spend
                
    df_w['Trade_Spend_Allocation_LKR'] = allocations
    
    leftover_high = high_budget
    leftover_med = med_budget
    leftover_low = low_budget
    total_leftover = leftover_high + leftover_med + leftover_low
    print(f"Knapsack pass budget leftovers: High={leftover_high:,.2f}, Med={leftover_med:,.2f}, Low={leftover_low:,.2f} LKR")
    print(f"Total budget remaining to redistribute: {total_leftover:,.2f} LKR")
    
    # Redistribute leftovers to funded outlets to exhaust the total 5M budget exactly
    diff = total_leftover
    if diff > 0:
        print(f"Greedy redistributing leftovers: {diff:,.2f} LKR to top High-tier active outlets...")
        # First pass: try adding to active High-tier outlets up to their cap
        for idx in range(len(df_w)):
            if diff == 0:
                break
            tier = df_w.at[idx, 'allocation_tier']
            current_alloc = df_w.at[idx, 'Trade_Spend_Allocation_LKR']
            tier_cap = df_w.at[idx, 'tier_cap']
            
            if diff >= 50.0 and current_alloc > 0 and tier == 'High' and current_alloc + 50.0 <= tier_cap:
                df_w.at[idx, 'Trade_Spend_Allocation_LKR'] += 50.0
                diff -= 50.0
                
        # Second pass: if any remains, add to any active funded outlet up to their cap
        for idx in range(len(df_w)):
            if diff == 0:
                break
            current_alloc = df_w.at[idx, 'Trade_Spend_Allocation_LKR']
            tier_cap = df_w.at[idx, 'tier_cap']
            if diff >= 50.0 and current_alloc > 0 and current_alloc + 50.0 <= tier_cap:
                df_w.at[idx, 'Trade_Spend_Allocation_LKR'] += 50.0
                diff -= 50.0
                
    print(f"Budget allocated after redistribution: {df_w['Trade_Spend_Allocation_LKR'].sum():,.2f} LKR")
    
    # Step 7: Distributor Rebalancing Pass (>= 25% budget share, i.e., 1.25M LKR each)
    distributors = ['DIST_W_01', 'DIST_W_02', 'DIST_W_03']
    min_dist_budget = 1250000.0
    
    print("Evaluating distributor share guardrails...")
    for pass_num in range(10): # Guard against infinite loop
        dist_totals = df_w.groupby('distributor_id')['Trade_Spend_Allocation_LKR'].sum()
        for d in distributors:
            if d not in dist_totals:
                dist_totals[d] = 0.0
        print(f"Distributor Shares: {dict(dist_totals)}")
        
        under_funded = [d for d in distributors if dist_totals[d] < min_dist_budget]
        over_funded = [d for d in distributors if dist_totals[d] > min_dist_budget]
        
        if not under_funded:
            print("All distributor guardrails satisfied!")
            break
            
        print(f"Rebalancing distributor share (Pass {pass_num+1})...")
        # Shift spend from lowest-ROI funded outlet of over-funded distributor
        # to the highest-ROI unallocated/under-allocated outlet of under-funded distributor
        for uf_dist in under_funded:
            deficit = min_dist_budget - dist_totals[uf_dist]
            while deficit > 0:
                # Find over-allocated source
                of_dist = max(over_funded, key=lambda d: dist_totals[d])
                
                # Get eligible source outlet (lowest ROI, has spend > floor)
                source_idx = df_w[
                    (df_w['distributor_id'] == of_dist) & 
                    (df_w['Trade_Spend_Allocation_LKR'] > df_w['tier_floor'])
                ]['roi_score'].idxmin() if not df_w[
                    (df_w['distributor_id'] == of_dist) & 
                    (df_w['Trade_Spend_Allocation_LKR'] > df_w['tier_floor'])
                ].empty else None
                
                # Get eligible target outlet (highest ROI, unallocated or has room below cap)
                target_idx = df_w[
                    (df_w['distributor_id'] == uf_dist) & 
                    (df_w['Trade_Spend_Allocation_LKR'] < df_w['max_headroom_allocation']) &
                    (df_w['max_headroom_allocation'] > 0)
                ]['roi_score'].idxmax() if not df_w[
                    (df_w['distributor_id'] == uf_dist) & 
                    (df_w['Trade_Spend_Allocation_LKR'] < df_w['max_headroom_allocation']) &
                    (df_w['max_headroom_allocation'] > 0)
                ].empty else None
                
                if source_idx is None or target_idx is None:
                    print("Warning: Could not perform further distributor rebalancing due to lack of eligible outlets.")
                    break
                    
                # Reallocate 50 LKR
                df_w.at[source_idx, 'Trade_Spend_Allocation_LKR'] -= 50.0
                if df_w.at[target_idx, 'Trade_Spend_Allocation_LKR'] == 0:
                    # If target is getting funded for the first time, give it the floor
                    add_amt = df_w.at[target_idx, 'tier_floor']
                else:
                    add_amt = 50.0
                    
                df_w.at[target_idx, 'Trade_Spend_Allocation_LKR'] += add_amt
                
                # Deduct extra added amount from source to keep budget net neutral
                if add_amt > 50.0:
                    df_w.at[source_idx, 'Trade_Spend_Allocation_LKR'] -= (add_amt - 50.0)
                    
                # Clean up if source dropped below floor
                if df_w.at[source_idx, 'Trade_Spend_Allocation_LKR'] < df_w.at[source_idx, 'tier_floor']:
                    # Revert and drop to 0
                    refund = df_w.at[source_idx, 'Trade_Spend_Allocation_LKR']
                    df_w.at[source_idx, 'Trade_Spend_Allocation_LKR'] = 0.0
                    # Redeposit to target or handle deficit
                    df_w.at[target_idx, 'Trade_Spend_Allocation_LKR'] += refund
                    
                # Recalculate deficit
                dist_totals = df_w.groupby('distributor_id')['Trade_Spend_Allocation_LKR'].sum()
                deficit = min_dist_budget - dist_totals[uf_dist]
                
    # Final check and force exact 5M sum budget if any small discrepancy exists
    final_allocated = df_w['Trade_Spend_Allocation_LKR'].sum()
    diff = 5000000.0 - final_allocated
    
    if diff != 0:
        print(f"Applying final micro-adjustments for budget deficit/surplus: {diff:,.2f} LKR...")
        # Greedy adjust top performing active outlets up to their tier cap
        for idx in range(len(df_w)):
            if diff == 0:
                break
            current_alloc = df_w.at[idx, 'Trade_Spend_Allocation_LKR']
            headroom_cap = df_w.at[idx, 'max_headroom_allocation']
            tier_cap = df_w.at[idx, 'tier_cap']
            floor = df_w.at[idx, 'tier_floor']
            
            if diff > 0 and current_alloc > 0 and current_alloc + 50.0 <= min(tier_cap, headroom_cap + 100.0):
                df_w.at[idx, 'Trade_Spend_Allocation_LKR'] += 50.0
                diff -= 50.0
            elif diff < 0 and current_alloc > floor and current_alloc >= 50.0:
                df_w.at[idx, 'Trade_Spend_Allocation_LKR'] -= 50.0
                diff += 50.0
                
    # Step 8: Calculate expected lift and project volume uplift
    df_w['projected_volume_uplift_litres'] = df_w['Trade_Spend_Allocation_LKR'] * df_w['volume_per_lkr']
    
    # Recalculate tier mappings if allocation got dropped to zero
    zero_alloc = df_w['Trade_Spend_Allocation_LKR'] == 0.0
    df_w.loc[zero_alloc, 'allocation_tier'] = 'None'
    df_w.loc[zero_alloc, 'recommended_spend_type'] = 'None'
    
    # Step 9: Export Artifacts
    print("Exporting diagnostics and outputs...")
    
    # 1. Submission File (strictly two columns: Outlet_ID, Trade_Spend_Allocation_LKR)
    submit_df = df_w[['Outlet_ID', 'Trade_Spend_Allocation_LKR']].copy()
    submit_df['Trade_Spend_Allocation_LKR'] = submit_df['Trade_Spend_Allocation_LKR'].round(2)
    submit_df.to_csv(os.path.join(output_dir, 'bigbug_budget_allocations.csv'), index=False)
    print(f"Saved submission output to: {os.path.join(output_dir, 'bigbug_budget_allocations.csv')}")
    
    # 2. Detailed diagnostics csv
    cols = [
        'Outlet_ID', 'province', 'distributor_id', 'Outlet_Size', 'Outlet_Type', 
        'uplift_gap_litres', 'composite_gravity_score', 'competition_density_score', 
        'roi_score', 'roi_rank', 'allocation_tier', 'recommended_spend_type', 
        'Trade_Spend_Allocation_LKR', 'projected_volume_uplift_litres'
    ]
    # Ensure missing columns don't fail diagnostic export
    export_cols = [c for c in cols if c in df_w.columns]
    diag_df = df_w[export_cols].copy()
    diag_df['Trade_Spend_Allocation_LKR'] = diag_df['Trade_Spend_Allocation_LKR'].round(2)
    diag_df.to_csv(os.path.join(output_dir, 'budget_diagnostics.csv'), index=False)
    print(f"Saved diagnostics to: {os.path.join(output_dir, 'budget_diagnostics.csv')}")
    
    # 3. Save as parquet in data/Optimizations/
    opt_dir = os.path.join(base_dir, 'data', 'Optimizations')
    os.makedirs(opt_dir, exist_ok=True)
    diag_df.to_parquet(os.path.join(opt_dir, 'budget_features.parquet'), index=False)
    print(f"Saved parquet features to: {os.path.join(opt_dir, 'budget_features.parquet')}")
    
    # Step 10: Generate Right-Skewed ROI Plot
    print("Generating ROI score distribution plot...")
    plt.figure(figsize=(12, 6))
    
    tier_high = df_w[df_w['allocation_tier'] == 'High']['roi_score']
    tier_med = df_w[df_w['allocation_tier'] == 'Medium']['roi_score']
    tier_low = df_w[df_w['allocation_tier'] == 'Low']['roi_score']
    
    # Filter 0s for visual clarity
    plot_data = df_w[df_w['roi_score'] > 0]
    sns.histplot(data=plot_data, x='roi_score', bins=60, color='gray', alpha=0.5)
    
    # Colored bands
    high_min = tier_high.min() if not tier_high.empty else plot_data['roi_score'].max()
    med_min = tier_med.min() if not tier_med.empty else high_min
    low_min = tier_low.min() if not tier_low.empty else med_min
    
    plt.axvspan(high_min, plot_data['roi_score'].max(), color='green', alpha=0.2, label='High (Growth Accelerator)')
    plt.axvspan(med_min, high_min, color='blue', alpha=0.2, label='Medium (Visibility Boost)')
    plt.axvspan(low_min, med_min, color='orange', alpha=0.2, label='Low (Brand Presence)')
    plt.axvspan(0, low_min, color='red', alpha=0.2, label='None (No Allocation)')
    
    plt.title('ROI Score Distribution & Optimised Budget Allocation Tiers (Western Province)')
    plt.xlabel('ROI Score')
    plt.ylabel('Frequency (Outlets)')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'roi_distribution.png'))
    plt.close()
    print(f"Saved ROI distribution plot to: {os.path.join(output_dir, 'roi_distribution.png')}")
    
    # Assertions and validations
    print("\n--- Running Automated Assertions & Validation ---")
    final_budget = df_w['Trade_Spend_Allocation_LKR'].sum()
    print(f"Total Budget Allocated: {final_budget:,.2f} LKR")
    assert np.isclose(final_budget, 5000000.0), f"Assertion Failed: Budget is {final_budget}, must be exactly 5,000,000.00 LKR"
    print("[PASS] Assertion Passed: Budget allocated is exactly 5,000,000.00 LKR.")
    
    # Floor / boundary check (no allocations between 1 and 499 LKR)
    invalids = df_w[
        (df_w['Trade_Spend_Allocation_LKR'] > 0) & 
        (df_w['Trade_Spend_Allocation_LKR'] < 500.0)
    ]
    assert invalids.empty, f"Assertion Failed: Outlets found below Rs 500 minimum actionable limit: {invalids[['Outlet_ID', 'Trade_Spend_Allocation_LKR']]}"
    print("[PASS] Assertion Passed: No allocations fall below the Rs 500 minimum actionable limit.")
    
    # Cap check
    excessive = df_w[df_w['Trade_Spend_Allocation_LKR'] > df_w['max_headroom_allocation'] + 100.0]
    assert excessive.empty, f"Assertion Failed: Outlets found exceeding dynamic caps: {excessive[['Outlet_ID', 'Trade_Spend_Allocation_LKR', 'max_headroom_allocation']]}"
    print("[PASS] Assertion Passed: No allocations exceed the dynamic headroom-scaled caps (with +100 LKR tolerance).")
    
    # Distributor guardrail check
    dist_budgets = df_w.groupby('distributor_id')['Trade_Spend_Allocation_LKR'].sum()
    for d in distributors:
        amt = dist_budgets.get(d, 0.0)
        assert amt >= min_dist_budget - 1.0, f"Assertion Failed: Distributor {d} got {amt:,.2f} LKR, under the 1.25M LKR minimum"
    print("[PASS] Assertion Passed: All 3 distributors received >= 25% of the total budget.")
    
    # Tier share check
    high_med_sum = df_w[df_w['allocation_tier'].isin(['High', 'Medium'])]['Trade_Spend_Allocation_LKR'].sum()
    print(f"High + Medium Tiers Spend: {high_med_sum:,.2f} LKR ({high_med_sum/5000000.0*100:.1f}%)")
    assert high_med_sum >= 3000000.0, f"Assertion Failed: High+Med got {high_med_sum:,.2f} LKR, under the 60% minimum (3.0M LKR)"
    print("[PASS] Assertion Passed: High and Medium tiers combined received >= 60% of the total budget.")
    
    # Operational layout check
    improper = df_w[
        (df_w['Outlet_Size'] == 'Small') | 
        (df_w['Outlet_Type'].isin(['Kiosk', 'Pharmacy']))
    ]
    improper_high = improper[improper['Trade_Spend_Allocation_LKR'] > 3000.0]
    assert improper_high.empty, f"Assertion Failed: Small/Kiosk/Pharmacy outlets found with allocations > 3,000 LKR: {improper_high[['Outlet_ID', 'Trade_Spend_Allocation_LKR']]}"
    print("[PASS] Assertion Passed: Small outlets, Pharmacies, and Kiosks are strictly capped at <= 3,000 LKR.")
    
    # 50 LKR rounding check
    fractional = df_w[df_w['Trade_Spend_Allocation_LKR'] % 50.0 != 0.0]
    assert fractional.empty, f"Assertion Failed: Fractional allocations found: {fractional[['Outlet_ID', 'Trade_Spend_Allocation_LKR']]}"
    print("[PASS] Assertion Passed: All non-zero allocations are clean multiples of 50 LKR.")
    
    # Coverage Check (Option A should fund >= 1,000 outlets)
    funded_count = (df_w['Trade_Spend_Allocation_LKR'] > 0.0).sum()
    print(f"Total Outlets Funded: {funded_count} ({funded_count/len(df_w)*100:.1f}% market coverage)")
    assert funded_count >= 1000, f"Assertion Failed: Option A failed to achieve high coverage, funded count is {funded_count}"
    print("[PASS] Assertion Passed: Option A achieved high market footprint (> 1,000 stores).")
    
    print("\nAll systems normal. Overhaul execution successful! [PASS]")

if __name__ == '__main__':
    main()
