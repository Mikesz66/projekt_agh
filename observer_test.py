import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from paths import RECIPES_FOUND

# Assume RECIPES_FOUND is correctly imported from paths
# Example: If RECIPES_FOUND is '/home/user/myproject/recipes.txt'
# from paths import RECIPES_FOUND
# For testing without your 'paths' module, let's use a dummy path:
# IMPORTANT: Replace this with your actual RECIPES_FOUND
TARGET_FILE = RECIPES_FOUND

# --- Create the file initially for testing ---
if not os.path.exists(TARGET_FILE):
    # Ensure the directory exists
    os.makedirs(os.path.dirname(TARGET_FILE), exist_ok=True)
    with open(TARGET_FILE, "w") as f:
        f.write("Initial content.\n")
    print(f"Created initial file: {TARGET_FILE}")
else:
    print(f"Using existing file: {TARGET_FILE}")

# --- Your custom function to be triggered ---
def my_trigger_function(filepath):
    """
    This function will be called once after TARGET_FILE is modified,
    thanks to debouncing.
    Place your actual logic here.
    """
    print(f"*** TRIGGERED: The file {filepath} has been modified! ***")
    # Example: Re-read the file
    try:
        with open(filepath, 'r') as f:
            content = f.read().strip()
            print(f"New file content snippet: '{content[:50]}...'")
    except FileNotFoundError:
        print(f"File {filepath} was modified but now not found (might have been moved/deleted).")
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
    print("-----------------------------------------------------")


# --- Custom Event Handler Class with Debouncing ---
class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, file_to_watch, debounce_interval=0.5):
        super().__init__()
        self.file_to_watch = os.path.abspath(file_to_watch)
        self.last_triggered_time = 0
        self.debounce_interval = debounce_interval # Time in seconds to wait before re-triggering
        print(f"Handler initialized to watch for changes to: {self.file_to_watch}")
        print(f"Debounce interval set to: {self.debounce_interval} seconds.")

    def _handle_event_debounced(self, event_path):
        """
        Internal method to apply debouncing logic.
        """
        current_time = time.time()
        # Only trigger if enough time has passed since the last trigger for this file
        if (current_time - self.last_triggered_time) > self.debounce_interval:
            print(f"Detected event for: {event_path} (debounced).")
            my_trigger_function(event_path)
            self.last_triggered_time = current_time
        # else:
        #     print(f"Event for {event_path} debounced.") # Optional: uncomment to see debounced events

    def on_modified(self, event):
        if not event.is_directory and os.path.abspath(event.src_path) == self.file_to_watch:
            self._handle_event_debounced(event.src_path)

    def on_created(self, event):
        # Neovim's safe save can look like a new file being created at the target path
        if not event.is_directory and os.path.abspath(event.src_path) == self.file_to_watch:
            self._handle_event_debounced(event.src_path)

    def on_moved(self, event):
        # This is very common for safe saves: a temp file is moved/renamed over the target
        if not event.is_directory and os.path.abspath(event.dest_path) == self.file_to_watch:
            self._handle_event_debounced(event.dest_path)
        # Handle if the watched file itself was moved away (e.g., renamed)
        elif not event.is_directory and os.path.abspath(event.src_path) == self.file_to_watch:
            print(f"Watched file '{self.file_to_watch}' was moved away to '{event.dest_path}'.")
            # You might want to re-establish the watch or take other action here.


# --- Main execution setup ---
if __name__ == "__main__":
    # The directory to watch is the parent directory of your target file
    path_to_watch_directory = os.path.dirname(TARGET_FILE)
    if not path_to_watch_directory:
        path_to_watch_directory = "." # If TARGET_FILE is in current directory

    # Adjust the debounce_interval here if 0.5 seconds is too long/short
    event_handler = FileChangeHandler(TARGET_FILE, debounce_interval=0.5)
    observer = Observer()
    # Watch the directory, not the file itself, and not recursively
    observer.schedule(event_handler, path_to_watch_directory, recursive=False)

    print(f"Starting file monitor on directory: {path_to_watch_directory}")
    print(f"Monitoring for changes to: {TARGET_FILE}")
    print("Press Ctrl+C to stop.")

    observer.start()
    try:
        while True:
            time.sleep(1) # Keep the main thread alive
    except KeyboardInterrupt:
        observer.stop()
        print("\nMonitor stopped.")
    observer.join() # Wait until the observer thread terminates
    print("Exiting.")
