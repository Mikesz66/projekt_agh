# config.py

# --- WEIGHTS ---
# How many points is a single matched ingredient worth?
WEIGHT_INGREDIENT_MATCH = 10.0

# (Optional) You can add weights for other columns here later
# e.g., WEIGHT_REVIEW_COUNT = 0.05 

# --- CONSTANTS ---
# Column names in your CSV
COL_ID = 'id'
COL_INGREDIENTS = 'ingredients_serialized'
COL_REVIEWS = 'review_count'
COL_NAME = 'name_clean'

# Data cleaning settings
SEPARATOR = ';'
