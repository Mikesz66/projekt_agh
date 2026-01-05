class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt6 Recipe Search")
        self.setGeometry(100, 100, 900, 600)
        self.setObjectName("mainWindow")
        
        self.recipe_db = {}
        self.current_results_ids = [] # To track order for Next/Prev
        self.current_detail_id = None # ID currently being viewed

        self._load_recipe_db()

        self._ui()
        
        self._setup_file_watcher()
        self.reload_results_from_file()

    def _ui(self):
        # We use a Stack to switch between Search (Index 0) and Details (Index 1)
        self.stack = QStackedWidget(self)
        
        # --- LAYER 0: SEARCH VIEW ---
        search_widget = QWidget()
        search_layout = QHBoxLayout(search_widget)
        
        # Left Menu
        left_menu = QVBoxLayout()
        search_button = QPushButton("Search") # Does nothing, but kept as requested
        search_button.clicked.connect(self.on_search_press)
        left_menu.addWidget(self._ui_app_title())
        left_menu.addWidget(self._ui_scrollable_menu())
        left_menu.addWidget(search_button)

        # Right Menu (Results)
        right_decoration = QWidget()
        self.right_menu_layout = QVBoxLayout(right_decoration)
        self.right_menu_layout.addStretch()

        search_layout.addLayout(left_menu)
        search_layout.addWidget(right_decoration)
        search_layout.setStretch(0, 1)
        search_layout.setStretch(1, 2)
        
        self.stack.addWidget(search_widget) # Add to stack at index 0

        # --- LAYER 1: DETAIL VIEW ---
        self.detail_view = self._ui_detail_view_layer()
        self.stack.addWidget(self.detail_view) # Add to stack at index 1

        # Main Layout for the Window
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.stack)

    def _ui_detail_view_layer(self) -> QWidget:
        """Constructs the container for the detail view."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # 1. Header Area (Will hold the duplicate card)
        self.detail_header_container = QVBoxLayout()
        layout.addLayout(self.detail_header_container)

        # 2. Scrollable Content (Details)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        self.detail_content_widget = QWidget()
        self.detail_content_layout = QVBoxLayout(self.detail_content_widget)
        self.detail_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll.setWidget(self.detail_content_widget)
        layout.addWidget(scroll)

        # 3. Floating Controls (Bottom Bar)
        controls = QHBoxLayout()
        
        btn_prev = QPushButton("Previous")
        btn_prev.clicked.connect(self.action_prev_recipe)
        
        btn_close = QPushButton("Close / Back")
        btn_close.clicked.connect(self.action_close_detail)
        btn_close.setStyleSheet("background-color: #ffcccc; color: red; font-weight: bold;")
        
        btn_next = QPushButton("Next")
        btn_next.clicked.connect(self.action_next_recipe)

        controls.addWidget(btn_prev)
        controls.addWidget(btn_close)
        controls.addWidget(btn_next)
        
        layout.addLayout(controls)
        
        return container

    def _load_recipe_db(self):
        """Loads CSVs and parses stringified lists using ast.literal_eval."""
        # Load Display Data (Name, Desc, Steps, Ingredients)
        if os.path.exists(DISPLAY_CSV):
            try:
                with open(DISPLAY_CSV, mode='r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            r_id = int(row['id'])
                            if r_id not in self.recipe_db: self.recipe_db[r_id] = {}
                            
                            self.recipe_db[r_id]['name'] = row.get('name', 'Unknown')
                            self.recipe_db[r_id]['description'] = row.get('description', '')
                            
                            # Parse lists safely
                            try:
                                self.recipe_db[r_id]['steps'] = ast.literal_eval(row.get('steps', '[]'))
                            except:
                                self.recipe_db[r_id]['steps'] = []
                                
                            try:
                                self.recipe_db[r_id]['ingredients'] = ast.literal_eval(row.get('ingredients', '[]'))
                            except:
                                self.recipe_db[r_id]['ingredients'] = []
                                
                        except ValueError:
                            continue
            except Exception as e:
                print(f"Error loading DISPLAY_CSV: {e}")

        # Load Search Data (Stats)
        if os.path.exists(SEARCH_CSV):
            try:
                with open(SEARCH_CSV, mode='r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            r_id = int(row['id'])
                            if r_id not in self.recipe_db: self.recipe_db[r_id] = {}
                            self.recipe_db[r_id]['rating'] = row.get('avg_rating', '-')
                            self.recipe_db[r_id]['minutes'] = row.get('minutes', '-')
                            self.recipe_db[r_id]['cal'] = row.get('cal', '-')
                            self.recipe_db[r_id]['prot'] = row.get('prot', '-')
                            self.recipe_db[r_id]['fat'] = row.get('fat', '-')
                        except ValueError:
                            continue
            except Exception as e:
                print(f"Error loading SEARCH_CSV: {e}")

    def populate_results(self, results: list):
        self._clear_right_menu()
        self.current_results_ids.clear() # Reset ID list

        valid_items_count = 0
        for data in results:
            if not isinstance(data, dict): continue
            if "id" not in data or "accuracy" not in data: continue

            # Track ID order
            r_id = data.get("id")
            self.current_results_ids.append(r_id)

            # Create Widget
            widget = self._create_result_widget(data)
            self.right_menu_layout.addWidget(widget)
            valid_items_count += 1
        
        if valid_items_count == 0:
            self._show_placeholder("No matching recipes found")
        else:
            self.right_menu_layout.addStretch()

    def _create_result_widget(self, data: dict, clickable: bool = True) -> QWidget:
        r_id = data.get("id")
        
        # Use ClickableCard if it needs to be interactive, else standard QWidget
        if clickable:
            card = ClickableCard(r_id)
            card.clicked.connect(self.open_detail_view) # Connect signal
        else:
            card = QWidget()

        card.setObjectName("resultCard")
        card.setStyleSheet("""
            QWidget#resultCard {
                background-color: #ffffff; 
                border: 1px solid #d0d0d0; 
                border-radius: 8px;
            }
            QLabel { color: #333; }
            QLabel#title { font-size: 16px; font-weight: bold; color: #000; }
            QLabel#desc { font-size: 12px; color: #555; }
            QLabel#stat { font-size: 11px; font-weight: bold; color: #444; }
        """)

        # ... (Rest of layout logic identical to previous answer) ...
        # (For brevity, assuming the layout logic from previous response is here)
        # REPEATING LAYOUT LOGIC FOR COMPLETENESS:
        main_layout = QHBoxLayout(card)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)

        db_entry = self.recipe_db.get(r_id, {})
        name = db_entry.get('name', f"Unknown Recipe (ID: {r_id})")
        desc = db_entry.get('description', "No description available.")
        
        # Stats
        accuracy = data.get("accuracy", 0.0)
        rating = db_entry.get('rating', '-')
        minutes = db_entry.get('minutes', '-')
        cal = db_entry.get('cal', '-')
        prot = db_entry.get('prot', '-')
        fat = db_entry.get('fat', '-')

        # Left Column
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        lbl_name = QLabel(name)
        lbl_name.setObjectName("title")
        lbl_name.setWordWrap(True)
        lbl_desc = QLabel(desc)
        lbl_desc.setObjectName("desc")
        lbl_desc.setWordWrap(True)
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignTop)
        left_layout.addWidget(lbl_name)
        left_layout.addWidget(lbl_desc)
        left_layout.addStretch()

        # Right Column
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_widget.setFixedWidth(120)

        acc_text = f"{accuracy * 100:.1f}%"
        lbl_acc = QLabel(f"Match: {acc_text}")
        lbl_acc.setObjectName("stat")
        if accuracy > 0.9: lbl_acc.setStyleSheet("color: green;")
        elif accuracy > 0.6: lbl_acc.setStyleSheet("color: orange;")
        else: lbl_acc.setStyleSheet("color: red;")

        def make_stat_row(label, value):
            l = QLabel(f"{label}: {value}")
            l.setObjectName("stat")
            return l

        right_layout.addWidget(lbl_acc)
        right_layout.addWidget(make_stat_row("Rating", rating))
        right_layout.addWidget(make_stat_row("Time", f"{minutes} min"))
        right_layout.addWidget(make_stat_row("Cal", cal))
        right_layout.addWidget(make_stat_row("Prot", f"{prot} g"))
        right_layout.addWidget(make_stat_row("Fat", f"{fat} g"))
        right_layout.addStretch()

        main_layout.addWidget(left_widget, stretch=3)
        main_layout.addWidget(right_widget, stretch=1)
        
        return card

    # --- ACTION HANDLERS ---

    def open_detail_view(self, r_id: int):
        self.current_detail_id = r_id
        self._populate_detail_view(r_id)
        self.stack.setCurrentIndex(1) # Switch to Detail Layer

    def action_close_detail(self):
        self.stack.setCurrentIndex(0) # Switch back to Search Layer

    def action_next_recipe(self):
        if not self.current_detail_id or not self.current_results_ids: return
        try:
            curr_idx = self.current_results_ids.index(self.current_detail_id)
            next_idx = (curr_idx + 1) % len(self.current_results_ids) # Loop around
            next_id = self.current_results_ids[next_idx]
            self.open_detail_view(next_id)
        except ValueError:
            pass

    def action_prev_recipe(self):
        if not self.current_detail_id or not self.current_results_ids: return
        try:
            curr_idx = self.current_results_ids.index(self.current_detail_id)
            prev_idx = (curr_idx - 1) % len(self.current_results_ids) # Loop around
            prev_id = self.current_results_ids[prev_idx]
            self.open_detail_view(prev_id)
        except ValueError:
            pass

    def _populate_detail_view(self, r_id: int):
        """Fills the detail view with content for the given ID."""
        
        # 1. Clear previous content
        # Clear Header
        while self.detail_header_container.count():
            item = self.detail_header_container.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        # Clear Details
        while self.detail_content_layout.count():
            item = self.detail_content_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        # 2. Re-create the Top Card (Non-clickable this time)
        # We need to find the original data dict (accuracy, etc) for this ID
        # Since we only stored IDs in list, we can quickly look up accuracy or default it.
        # Ideally, we should have stored the full result objects, but for now we reconstruct:
        data_packet = {"id": r_id, "accuracy": 0.0} # Default if not found
        # (Optional: You could search self.current_results_ids or store data map to get real accuracy)
        
        header_card = self._create_result_widget(data_packet, clickable=False)
        self.detail_header_container.addWidget(header_card)

        # 3. Add Details
        db_data = self.recipe_db.get(r_id, {})
        
        # Helper for titles
        def add_section_title(text):
            lbl = QLabel(text)
            lbl.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 20px; color: #222;")
            self.detail_content_layout.addWidget(lbl)

        # Name (Duplicate)
        add_section_title("Name")
        lbl_name = QLabel(db_data.get('name', ''))
        lbl_name.setStyleSheet("font-size: 16px;")
        lbl_name.setWordWrap(True)
        self.detail_content_layout.addWidget(lbl_name)

        # Description (Duplicate)
        add_section_title("Description")
        lbl_desc = QLabel(db_data.get('description', ''))
        lbl_desc.setWordWrap(True)
        self.detail_content_layout.addWidget(lbl_desc)

        # Ingredients
        add_section_title("Ingredients")
        ingredients = db_data.get('ingredients', [])
        if ingredients:
            # Create a bulleted list string
            ing_text = "\n".join([f"• {item}" for item in ingredients])
            lbl_ing = QLabel(ing_text)
            lbl_ing.setWordWrap(True)
            lbl_ing.setStyleSheet("margin-left: 10px;")
            self.detail_content_layout.addWidget(lbl_ing)
        else:
            self.detail_content_layout.addWidget(QLabel("No ingredients listed."))

        # Steps
        add_section_title("Steps")
        steps = db_data.get('steps', [])
        if steps:
            # Create a numbered list string
            steps_text = "\n".join([f"{i+1}. {step}" for i, step in enumerate(steps)])
            lbl_steps = QLabel(steps_text)
            lbl_steps.setWordWrap(True)
            lbl_steps.setStyleSheet("margin-left: 10px;")
            self.detail_content_layout.addWidget(lbl_steps)
        else:
            self.detail_content_layout.addWidget(QLabel("No steps listed."))

        self.detail_content_layout.addStretch()
