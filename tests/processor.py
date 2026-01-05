# processor.py
import pandas as pd
from tqdm import tqdm
import config

# Register tqdm with pandas to enable the progress_apply function
tqdm.pandas()

def calculate_row_score(row, likes, dislikes):
    """
    Calculates score and accuracy for a single row.
    Returns: (final_score, accuracy_percentage)
    """
    # 1. Validation
    ing_str = row[config.COL_INGREDIENTS]
    if not isinstance(ing_str, str):
        return -1, 0.0

    # Parse ingredients
    ingredients = [i.strip().lower() for i in ing_str.split(config.SEPARATOR)]
    
    # 2. Check Dislikes (Killer criteria)
    # If a dislike is found, return -1 immediately
    for dislike in dislikes:
        if any(dislike in ing for ing in ingredients):
            return -1, 0.0

    # 3. Calculate Score based on Likes
    matches = 0
    for like in likes:
        if any(like in ing for ing in ingredients):
            matches += 1
            
    # Apply Weight from config
    final_score = matches * config.WEIGHT_INGREDIENT_MATCH
    
    # 4. Calculate Accuracy
    # Max possible score = If all 'likes' were found in the recipe
    max_possible_score = len(likes) * config.WEIGHT_INGREDIENT_MATCH
    
    if max_possible_score > 0:
        accuracy = (final_score / max_possible_score) * 100
    else:
        accuracy = 0.0
        
    return final_score, accuracy

def find_best_recipes(file_path, user_likes, user_dislikes):
    """
    Loads CSV, calculates scores with a progress bar, and returns top results.
    """
    try:
        print(f"Loading database from {file_path}...")
        df = pd.read_csv(file_path)
        
        print("Processing recipes...")
        # progress_apply creates the progress bar in the terminal
        results = df.progress_apply(
            lambda row: calculate_row_score(row, user_likes, user_dislikes), 
            axis=1
        )
        
        # Unpack results into new columns
        df['final_score'] = [x[0] for x in results]
        df['accuracy'] = [x[1] for x in results]
        
        # Filter: Remove recipes with -1 score (disqualified)
        valid_df = df[df['final_score'] >= 0].copy()
        
        # Sort: Primary by Score, Secondary by Review Count
        sorted_df = valid_df.sort_values(
            by=['final_score', config.COL_REVIEWS], 
            ascending=[False, False]
        )
        
        # Return the top 5 relevant columns
        return sorted_df[[config.COL_ID, config.COL_NAME, 'final_score', 'accuracy']].head(5)

    except FileNotFoundError:
        print("Error: File not found.")
        return pd.DataFrame()
