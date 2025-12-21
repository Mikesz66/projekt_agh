# main.py
import processor

# --- USER CONFIGURATION ---
FILE_PATH = '/home/john/Projects/School/projekt_agh/data/processed/search_db.csv'

# Define what you are looking for (lowercase)
USER_LIKES = [
    'beef', 
    'water', 
    'potato',
    'carrot'
]

# Define what you strictly want to avoid
USER_DISLIKES = [
    'onion',
    'mushroom' 
]

# --- EXECUTION ---
if __name__ == "__main__":
    
    print(f"Searching for recipes with: {USER_LIKES}")
    print(f"Avoiding: {USER_DISLIKES}")
    print("-" * 30)

    # Run the algorithm
    top_recipes = processor.find_best_recipes(FILE_PATH, USER_LIKES, USER_DISLIKES)
    
    # Output
    if not top_recipes.empty:
        print("\n--- RESULTS ---")
        # Iterating to print nicely formatted output
        for index, row in top_recipes.iterrows():
            print(f"ID: {row['id']}")
            print(f"Name: {row['name_clean']}")
            print(f"Score: {row['final_score']}")
            print(f"Accuracy: {row['accuracy']:.2f}%")
            print("-" * 20)
    else:
        print("No matching recipes found.")
