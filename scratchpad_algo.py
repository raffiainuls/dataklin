import pandas as pd
import numpy as np
from rapidfuzz import fuzz

def calculate_u_probabilities(df, rules):
    u_probs = {}
    for r in rules:
        col = r["column"]
        if col not in df.columns: continue
        # frequency of each value
        counts = df[col].value_counts(normalize=True).to_dict()
        u_probs[col] = counts
    return u_probs

def get_bayes_factor(sim_score, val_a, val_b, col, u_probs, m_prob=0.9):
    # Base u-prob if values match exactly
    freq_a = u_probs.get(col, {}).get(val_a, 0.01)
    freq_b = u_probs.get(col, {}).get(val_b, 0.01)
    
    # If they are very similar, u is related to their frequency
    # We take the average frequency or max frequency
    u_prob_match = max(freq_a, freq_b)
    
    # Floor u_prob to avoid division by zero or infinite weight
    u_prob_match = max(u_prob_match, 0.0001)
    
    # Interpolate Bayes Factor based on similarity score (0.0 to 1.0)
    # If sim_score == 1.0, BF = m / u
    # If sim_score == 0.0, BF = (1-m) / (1-u)
    
    bf_match = m_prob / u_prob_match
    bf_non_match = (1.0 - m_prob) / (1.0 - u_prob_match)
    
    # We can do a linear interpolation in log space
    import math
    log_bf_match = math.log2(bf_match)
    log_bf_non_match = math.log2(bf_non_match)
    
    # Final log BF
    log_bf = log_bf_non_match + sim_score * (log_bf_match - log_bf_non_match)
    return math.pow(2, log_bf)

