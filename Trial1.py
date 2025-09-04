import customtkinter as ctk
import mysql.connector
from mysql.connector import Error
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
from datetime import datetime, timedelta
import openpyxl
from tkinter import filedialog
import os

# Set appearance mode and theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect_database()
        self.create_tables()

    def connect_database(self):
        """Connect to MySQL database"""
        try:
            self.connection = mysql.connector.connect(
                host='localhost',
                database='recipe_planner',
                user='root',
                password='root'  # Change this to your MySQL password
            )
            print("Successfully connected to MySQL database")
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            messagebox.showerror("Database Error", "Failed to connect to MySQL database. Please check your connection settings.")

    def create_tables(self):
        """Create necessary tables if they don't exist"""
        if not self.connection:
            return

        cursor = self.connection.cursor()

        # Create Recipes table
        create_recipes_table = """
        CREATE TABLE IF NOT EXISTS recipes (
            recipe_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            ingredients TEXT NOT NULL,
            instructions TEXT NOT NULL,
            category VARCHAR(100) NOT NULL,
            cuisine VARCHAR(100),
            cook_time INT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        # Create MealPlan table
        create_mealplan_table = """
        CREATE TABLE IF NOT EXISTS mealplan (
            plan_id INT AUTO_INCREMENT PRIMARY KEY,
            day VARCHAR(20) NOT NULL,
            meal_type VARCHAR(20) NOT NULL,
            recipe_id INT,
            FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id) ON DELETE CASCADE
        )
        """

        try:
            cursor.execute(create_recipes_table)
            cursor.execute(create_mealplan_table)
            self.connection.commit()
            print("Tables created successfully")
        except Error as e:
            print(f"Error creating tables: {e}")
        finally:
            cursor.close()

    def insert_recipe(self, name, ingredients, instructions, category, cuisine="", cook_time=0):
        """Insert a new recipe"""
        if not self.connection:
            return False

        cursor = self.connection.cursor()
        query = """INSERT INTO recipes (name, ingredients, instructions, category, cuisine, cook_time)
                   VALUES (%s, %s, %s, %s, %s, %s)"""

        try:
            cursor.execute(query, (name, ingredients, instructions, category, cuisine, cook_time))
            self.connection.commit()
            return True
        except Error as e:
            print(f"Error inserting recipe: {e}")
            return False
        finally:
            cursor.close()

    def get_all_recipes(self):
        """Get all recipes from database"""
        if not self.connection:
            return []

        cursor = self.connection.cursor()
        query = "SELECT * FROM recipes ORDER BY created_date DESC"

        try:
            cursor.execute(query)
            return cursor.fetchall()
        except Error as e:
            print(f"Error fetching recipes: {e}")
            return []
        finally:
            cursor.close()

    def search_recipes(self, search_term, search_type="name"):
        """Search recipes by name, category, or ingredient"""
        if not self.connection:
            return []

        cursor = self.connection.cursor()

        if search_type == "name":
            query = "SELECT * FROM recipes WHERE name LIKE %s"
        elif search_type == "category":
            query = "SELECT * FROM recipes WHERE category LIKE %s"
        elif search_type == "ingredient":
            query = "SELECT * FROM recipes WHERE ingredients LIKE %s"

        try:
            cursor.execute(query, (f"%{search_term}%",))
            return cursor.fetchall()
        except Error as e:
            print(f"Error searching recipes: {e}")
            return []
        finally:
            cursor.close()

    def update_recipe(self, recipe_id, name, ingredients, instructions, category, cuisine="", cook_time=0):
        """Update an existing recipe"""
        if not self.connection:
            return False

        cursor = self.connection.cursor()
        query = """UPDATE recipes SET name=%s, ingredients=%s, instructions=%s, 
                   category=%s, cuisine=%s, cook_time=%s WHERE recipe_id=%s"""

        try:
            cursor.execute(query, (name, ingredients, instructions, category, cuisine, cook_time, recipe_id))
            self.connection.commit()
            return True
        except Error as e:
            print(f"Error updating recipe: {e}")
            return False
        finally:
            cursor.close()

    def delete_recipe(self, recipe_id):
        """Delete a recipe"""
        if not self.connection:
            return False

        cursor = self.connection.cursor()
        query = "DELETE FROM recipes WHERE recipe_id = %s"

        try:
            cursor.execute(query, (recipe_id,))
            self.connection.commit()
            return True
        except Error as e:
            print(f"Error deleting recipe: {e}")
            return False
        finally:
            cursor.close()

    def add_meal_plan(self, day, meal_type, recipe_id):
        """Add a meal plan entry"""
        if not self.connection:
            return False

        # First, remove existing plan for the same day and meal type
        self.remove_meal_plan(day, meal_type)

        cursor = self.connection.cursor()
        query = "INSERT INTO mealplan (day, meal_type, recipe_id) VALUES (%s, %s, %s)"

        try:
            cursor.execute(query, (day, meal_type, recipe_id))
            self.connection.commit()
            return True
        except Error as e:
            print(f"Error adding meal plan: {e}")
            return False
        finally:
            cursor.close()

    def get_meal_plan(self):
        """Get complete meal plan"""
        if not self.connection:
            return []

        cursor = self.connection.cursor()
        query = """SELECT mp.day, mp.meal_type, r.name, r.recipe_id
                   FROM mealplan mp
                   JOIN recipes r ON mp.recipe_id = r.recipe_id
                   ORDER BY FIELD(mp.day, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'), 
                            FIELD(mp.meal_type, 'Breakfast', 'Lunch', 'Dinner')"""

        try:
            cursor.execute(query)
            return cursor.fetchall()
        except Error as e:
            print(f"Error fetching meal plan: {e}")
            return []
        finally:
            cursor.close()

    def remove_meal_plan(self, day, meal_type):
        """Remove meal plan for specific day and meal type"""
        if not self.connection:
            return False

        cursor = self.connection.cursor()
        query = "DELETE FROM mealplan WHERE day = %s AND meal_type = %s"

        try:
            cursor.execute(query, (day, meal_type))
            self.connection.commit()
            return True
        except Error as e:
            print(f"Error removing meal plan: {e}")
            return False
        finally:
            cursor.close()

    def get_shopping_list(self):
        """Generate shopping list based on meal plan"""
        if not self.connection:
            return []

        cursor = self.connection.cursor()
        query = """SELECT DISTINCT r.ingredients
                   FROM mealplan mp
                   JOIN recipes r ON mp.recipe_id = r.recipe_id"""

        try:
            cursor.execute(query)
            results = cursor.fetchall()

            # Combine all ingredients
            all_ingredients = []
            for result in results:
                ingredients = result[0].split(',')
                for ingredient in ingredients:
                    ingredient = ingredient.strip()
                    if ingredient and ingredient not in all_ingredients:
                        all_ingredients.append(ingredient)

            return sorted(all_ingredients)
        except Error as e:
            print(f"Error generating shopping list: {e}")
            return []
        finally:
            cursor.close()


class RecipePlannerApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Recipe Organizer & Meal Planner")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)

        # Initialize database
        self.db = DatabaseManager()

        # Current recipe for editing
        self.current_recipe = None

        self.setup_ui()

    def setup_ui(self):
        """Setup the main user interface"""
        # Main container
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Sidebar for navigation
        self.sidebar = ctk.CTkFrame(self.main_frame, width=200)
        self.sidebar.pack(side="left", fill="y", padx=(0, 10))
        self.sidebar.pack_propagate(False)

        # Main content area
        self.content_frame = ctk.CTkFrame(self.main_frame)
        self.content_frame.pack(side="right", fill="both", expand=True)

        self.setup_sidebar()
        self.show_recipes_page()

    def setup_sidebar(self):
        """Setup navigation sidebar"""
        # Title
        title_label = ctk.CTkLabel(self.sidebar, text="Recipe Planner",
                                   font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(pady=20)

        # Navigation buttons
        self.nav_buttons = []

        recipes_btn = ctk.CTkButton(self.sidebar, text="📝 Recipes",
                                    command=self.show_recipes_page, height=40)
        recipes_btn.pack(pady=5, padx=20, fill="x")
        self.nav_buttons.append(recipes_btn)

        meal_plan_btn = ctk.CTkButton(self.sidebar, text="📅 Meal Planner",
                                      command=self.show_meal_planner_page, height=40)
        meal_plan_btn.pack(pady=5, padx=20, fill="x")
        self.nav_buttons.append(meal_plan_btn)

        shopping_btn = ctk.CTkButton(self.sidebar, text="🛒 Shopping List",
                                     command=self.show_shopping_list_page, height=40)
        shopping_btn.pack(pady=5, padx=20, fill="x")
        self.nav_buttons.append(shopping_btn)

        analytics_btn = ctk.CTkButton(self.sidebar, text="📊 Analytics",
                                      command=self.show_analytics_page, height=40)
        analytics_btn.pack(pady=5, padx=20, fill="x")
        self.nav_buttons.append(analytics_btn)

    def clear_content_frame(self):
        """Clear the content frame"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def show_recipes_page(self):
        """Show recipes management page"""
        self.clear_content_frame()

        # Title
        title = ctk.CTkLabel(self.content_frame, text="Recipe Manager",
                             font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(pady=20)

        # Create notebook for tabs
        notebook = ctk.CTkTabview(self.content_frame)
        notebook.pack(fill="both", expand=True, padx=20, pady=10)

        # Add Recipe Tab
        notebook.add("Add Recipe")
        self.setup_add_recipe_tab(notebook.tab("Add Recipe"))

        # View Recipes Tab
        notebook.add("View Recipes")
        self.setup_view_recipes_tab(notebook.tab("View Recipes"))

        # Set default tab
        notebook.set("View Recipes")

    def setup_add_recipe_tab(self, parent):
        """Setup add recipe tab"""
        # Scrollable frame
        scroll_frame = ctk.CTkScrollableFrame(parent)
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Recipe form
        self.recipe_name_var = tk.StringVar()
        self.recipe_ingredients_var = tk.StringVar()
        self.recipe_instructions_var = tk.StringVar()
        self.recipe_category_var = tk.StringVar(value="Breakfast")
        self.recipe_cuisine_var = tk.StringVar()
        self.recipe_cook_time_var = tk.StringVar()

        # Name
        ctk.CTkLabel(scroll_frame, text="Recipe Name:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, 5))
        self.name_entry = ctk.CTkEntry(scroll_frame, textvariable=self.recipe_name_var, height=40)
        self.name_entry.pack(fill="x", pady=(0, 15))

        # Ingredients
        ctk.CTkLabel(scroll_frame, text="Ingredients (comma separated):", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", pady=(0, 5))
        self.ingredients_textbox = ctk.CTkTextbox(scroll_frame, height=100)
        self.ingredients_textbox.pack(fill="x", pady=(0, 15))

        # Instructions
        ctk.CTkLabel(scroll_frame, text="Instructions:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, 5))
        self.instructions_textbox = ctk.CTkTextbox(scroll_frame, height=150)
        self.instructions_textbox.pack(fill="x", pady=(0, 15))

        # Category and other details in a frame
        details_frame = ctk.CTkFrame(scroll_frame)
        details_frame.pack(fill="x", pady=(0, 15))

        # Category
        ctk.CTkLabel(details_frame, text="Category:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10, 5))
        category_combo = ctk.CTkComboBox(details_frame, values=["Breakfast", "Lunch", "Dinner", "Dessert", "Snack"],
                                         variable=self.recipe_category_var)
        category_combo.pack(fill="x", padx=10, pady=(0, 10))

        # Cuisine
        ctk.CTkLabel(details_frame, text="Cuisine:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10,
                                                                                           pady=(0, 5))
        cuisine_combo = ctk.CTkComboBox(details_frame,
                                        values=["Indian", "Italian", "Chinese", "Mexican", "American", "Thai", "French",
                                                "Other"],
                                        variable=self.recipe_cuisine_var)
        cuisine_combo.pack(fill="x", padx=10, pady=(0, 10))

        # Cook Time
        ctk.CTkLabel(details_frame, text="Cook Time (minutes):", font=ctk.CTkFont(weight="bold")).pack(anchor="w",
                                                                                                       padx=10,
                                                                                                       pady=(0, 5))
        cook_time_entry = ctk.CTkEntry(details_frame, textvariable=self.recipe_cook_time_var)
        cook_time_entry.pack(fill="x", padx=10, pady=(0, 15))

        # Buttons
        button_frame = ctk.CTkFrame(scroll_frame)
        button_frame.pack(fill="x", pady=20)

        save_btn = ctk.CTkButton(button_frame, text="Save Recipe", command=self.save_recipe, height=40)
        save_btn.pack(side="left", padx=10, pady=10)

        clear_btn = ctk.CTkButton(button_frame, text="Clear Form", command=self.clear_recipe_form, height=40)
        clear_btn.pack(side="right", padx=10, pady=10)

    def setup_view_recipes_tab(self, parent):
        """Setup view recipes tab"""
        # Search frame
        search_frame = ctk.CTkFrame(parent)
        search_frame.pack(fill="x", padx=20, pady=20)

        self.search_var = tk.StringVar()
        self.search_type_var = tk.StringVar(value="name")

        ctk.CTkLabel(search_frame, text="Search:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10)
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var, width=200)
        search_entry.pack(side="left", padx=5)

        search_type_combo = ctk.CTkComboBox(search_frame, values=["name", "category", "ingredient"],
                                            variable=self.search_type_var, width=100)
        search_type_combo.pack(side="left", padx=5)

        search_btn = ctk.CTkButton(search_frame, text="Search", command=self.search_recipes)
        search_btn.pack(side="left", padx=5)

        refresh_btn = ctk.CTkButton(search_frame, text="Refresh", command=self.refresh_recipes)
        refresh_btn.pack(side="left", padx=5)

        # Recipes list frame
        self.recipes_list_frame = ctk.CTkScrollableFrame(parent)
        self.recipes_list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.refresh_recipes()

    def save_recipe(self):
        """Save recipe to database"""
        name = self.recipe_name_var.get().strip()
        ingredients = self.ingredients_textbox.get("1.0", "end-1c").strip()
        instructions = self.instructions_textbox.get("1.0", "end-1c").strip()
        category = self.recipe_category_var.get()
        cuisine = self.recipe_cuisine_var.get()

        try:
            cook_time = int(self.recipe_cook_time_var.get()) if self.recipe_cook_time_var.get() else 0
        except ValueError:
            cook_time = 0

        if not all([name, ingredients, instructions]):
            messagebox.showerror("Error", "Please fill in all required fields!")
            return

        if self.current_recipe:
            # Update existing recipe
            success = self.db.update_recipe(self.current_recipe[0], name, ingredients, instructions, category, cuisine,
                                            cook_time)
            if success:
                messagebox.showinfo("Success", "Recipe updated successfully!")
                self.current_recipe = None
                self.clear_recipe_form()
                self.refresh_recipes()
            else:
                messagebox.showerror("Error", "Failed to update recipe!")
        else:
            # Add new recipe
            success = self.db.insert_recipe(name, ingredients, instructions, category, cuisine, cook_time)
            if success:
                messagebox.showinfo("Success", "Recipe saved successfully!")
                self.clear_recipe_form()
                self.refresh_recipes()
            else:
                messagebox.showerror("Error", "Failed to save recipe!")

    def clear_recipe_form(self):
        """Clear the recipe form"""
        self.recipe_name_var.set("")
        self.ingredients_textbox.delete("1.0", "end")
        self.instructions_textbox.delete("1.0", "end")
        self.recipe_category_var.set("Breakfast")
        self.recipe_cuisine_var.set("")
        self.recipe_cook_time_var.set("")
        self.current_recipe = None

    def search_recipes(self):
        """Search recipes based on criteria"""
        search_term = self.search_var.get().strip()
        search_type = self.search_type_var.get()

        if search_term:
            recipes = self.db.search_recipes(search_term, search_type)
        else:
            recipes = self.db.get_all_recipes()

        self.display_recipes(recipes)

    def refresh_recipes(self):
        """Refresh the recipes list"""
        recipes = self.db.get_all_recipes()
        self.display_recipes(recipes)

    def display_recipes(self, recipes):
        """Display recipes in the list"""
        # Clear existing widgets
        for widget in self.recipes_list_frame.winfo_children():
            widget.destroy()

        if not recipes:
            no_recipes_label = ctk.CTkLabel(self.recipes_list_frame, text="No recipes found!",
                                            font=ctk.CTkFont(size=16))
            no_recipes_label.pack(pady=50)
            return

        for recipe in recipes:
            recipe_frame = ctk.CTkFrame(self.recipes_list_frame)
            recipe_frame.pack(fill="x", pady=10, padx=10)

            # Recipe info frame
            info_frame = ctk.CTkFrame(recipe_frame)
            info_frame.pack(fill="x", padx=10, pady=10)

            # Title
            title_label = ctk.CTkLabel(info_frame, text=recipe[1], font=ctk.CTkFont(size=18, weight="bold"))
            title_label.pack(anchor="w", padx=10, pady=(10, 5))

            # Details
            details_text = f"Category: {recipe[4]} | Cuisine: {recipe[5] or 'Not specified'} | Cook Time: {recipe[6] or 'Not specified'} min"
            details_label = ctk.CTkLabel(info_frame, text=details_text, font=ctk.CTkFont(size=12))
            details_label.pack(anchor="w", padx=10, pady=(0, 5))

            # Ingredients preview
            ingredients_preview = recipe[2][:100] + "..." if len(recipe[2]) > 100 else recipe[2]
            ingredients_label = ctk.CTkLabel(info_frame, text=f"Ingredients: {ingredients_preview}",
                                             font=ctk.CTkFont(size=12), wraplength=600)
            ingredients_label.pack(anchor="w", padx=10, pady=(0, 10))

            # Buttons
            button_frame = ctk.CTkFrame(recipe_frame)
            button_frame.pack(fill="x", padx=10, pady=(0, 10))

            view_btn = ctk.CTkButton(button_frame, text="View", command=lambda r=recipe: self.view_recipe(r))
            view_btn.pack(side="left", padx=5)

            edit_btn = ctk.CTkButton(button_frame, text="Edit", command=lambda r=recipe: self.edit_recipe(r))
            edit_btn.pack(side="left", padx=5)

            delete_btn = ctk.CTkButton(button_frame, text="Delete", fg_color="red", hover_color="darkred",
                                       command=lambda r=recipe: self.delete_recipe(r))
            delete_btn.pack(side="right", padx=5)

    def view_recipe(self, recipe):
        """View full recipe details"""
        recipe_window = ctk.CTkToplevel(self.root)
        recipe_window.title(f"Recipe: {recipe[1]}")
        recipe_window.geometry("600x700")

        # Scrollable frame
        scroll_frame = ctk.CTkScrollableFrame(recipe_window)
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        title_label = ctk.CTkLabel(scroll_frame, text=recipe[1], font=ctk.CTkFont(size=24, weight="bold"))
        title_label.pack(pady=(0, 20))

        # Details
        details_frame = ctk.CTkFrame(scroll_frame)
        details_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(details_frame, text=f"Category: {recipe[4]}", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=10,
                                                                                                   pady=5)
        ctk.CTkLabel(details_frame, text=f"Cuisine: {recipe[5] or 'Not specified'}", font=ctk.CTkFont(size=14)).pack(
            anchor="w", padx=10, pady=5)
        ctk.CTkLabel(details_frame, text=f"Cook Time: {recipe[6] or 'Not specified'} minutes",
                     font=ctk.CTkFont(size=14)).pack(anchor="w", padx=10, pady=5)

        # Ingredients
        ctk.CTkLabel(scroll_frame, text="Ingredients:", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w",
                                                                                                       pady=(0, 5))
        ingredients_textbox = ctk.CTkTextbox(scroll_frame, height=150)
        ingredients_textbox.pack(fill="x", pady=(0, 20))
        ingredients_textbox.insert("1.0", recipe[2])
        ingredients_textbox.configure(state="disabled")

        # Instructions
        ctk.CTkLabel(scroll_frame, text="Instructions:", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w",
                                                                                                        pady=(0, 5))
        instructions_textbox = ctk.CTkTextbox(scroll_frame, height=200)
        instructions_textbox.pack(fill="x", pady=(0, 20))
        instructions_textbox.insert("1.0", recipe[3])
        instructions_textbox.configure(state="disabled")

    def edit_recipe(self, recipe):
        """Edit recipe - populate form with existing data"""
        self.current_recipe = recipe

        # Populate form fields
        self.recipe_name_var.set(recipe[1])
        self.ingredients_textbox.delete("1.0", "end")
        self.ingredients_textbox.insert("1.0", recipe[2])
        self.instructions_textbox.delete("1.0", "end")
        self.instructions_textbox.insert("1.0", recipe[3])
        self.recipe_category_var.set(recipe[4])
        self.recipe_cuisine_var.set(recipe[5] or "")
        self.recipe_cook_time_var.set(str(recipe[6]) if recipe[6] else "")

        # Switch to add recipe tab
        messagebox.showinfo("Edit Mode", f"Editing recipe: {recipe[1]}\nGo to 'Add Recipe' tab to make changes.")

    def delete_recipe(self, recipe):
        """Delete recipe with confirmation"""
        result = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the recipe '{recipe[1]}'?")

        if result:
            success = self.db.delete_recipe(recipe[0])
            if success:
                messagebox.showinfo("Success", "Recipe deleted successfully!")
                self.refresh_recipes()
            else:
                messagebox.showerror("Error", "Failed to delete recipe!")

    def show_meal_planner_page(self):
        """Show meal planner page"""
        self.clear_content_frame()

        # Title
        title = ctk.CTkLabel(self.content_frame, text="Meal Planner",
                             font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(pady=20)

        # Planning form
        form_frame = ctk.CTkFrame(self.content_frame)
        form_frame.pack(fill="x", padx=20, pady=10)

        # Form elements
        form_inner = ctk.CTkFrame(form_frame)
        form_inner.pack(padx=20, pady=20)

        # Day selection
        ctk.CTkLabel(form_inner, text="Day:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=10,
                                                                                    sticky="w")
        self.day_var = tk.StringVar(value="Monday")
        day_combo = ctk.CTkComboBox(form_inner,
                                    values=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
                                            "Sunday"],
                                    variable=self.day_var, width=150)
        day_combo.grid(row=0, column=1, padx=10, pady=10)

        # Meal type
        ctk.CTkLabel(form_inner, text="Meal Type:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=10,
                                                                                          pady=10, sticky="w")
        self.meal_type_var = tk.StringVar(value="Breakfast")
        meal_combo = ctk.CTkComboBox(form_inner, values=["Breakfast", "Lunch", "Dinner"],
                                     variable=self.meal_type_var, width=150)
        meal_combo.grid(row=0, column=3, padx=10, pady=10)

        # Recipe selection
        ctk.CTkLabel(form_inner, text="Recipe:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=10,
                                                                                       pady=10, sticky="w")
        self.recipe_var = tk.StringVar()
        self.recipe_combo = ctk.CTkComboBox(form_inner, variable=self.recipe_var, width=300)
        self.recipe_combo.grid(row=1, column=1, columnspan=2, padx=10, pady=10)

        # Add to plan button
        add_meal_btn = ctk.CTkButton(form_inner, text="Add to Plan", command=self.add_to_meal_plan, height=40)
        add_meal_btn.grid(row=1, column=3, padx=10, pady=10)

        # Refresh button
        refresh_combo_btn = ctk.CTkButton(form_inner, text="Refresh Recipes", command=self.refresh_recipe_combo,
                                          height=40)
        refresh_combo_btn.grid(row=2, column=1, padx=10, pady=10)

        # Weekly plan display
        plan_frame = ctk.CTkFrame(self.content_frame)
        plan_frame.pack(fill="both", expand=True, padx=20, pady=10)

        plan_title = ctk.CTkLabel(plan_frame, text="Weekly Meal Plan", font=ctk.CTkFont(size=18, weight="bold"))
        plan_title.pack(pady=10)

        # Scrollable frame for meal plan
        self.meal_plan_frame = ctk.CTkScrollableFrame(plan_frame)
        self.meal_plan_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Initialize and load data
        self.refresh_recipe_combo()
        self.refresh_meal_plan()

    def refresh_recipe_combo(self):
        """Refresh recipe dropdown"""
        recipes = self.db.get_all_recipes()
        recipe_names = [f"{recipe[1]} (ID: {recipe[0]})" for recipe in recipes]

        if recipe_names:
            self.recipe_combo.configure(values=recipe_names)
            if not self.recipe_var.get() or self.recipe_var.get() not in recipe_names:
                self.recipe_var.set(recipe_names[0])
        else:
            self.recipe_combo.configure(values=["No recipes available"])
            self.recipe_var.set("No recipes available")

    def add_to_meal_plan(self):
        """Add recipe to meal plan"""
        day = self.day_var.get()
        meal_type = self.meal_type_var.get()
        recipe_selection = self.recipe_var.get()

        if "No recipes available" in recipe_selection:
            messagebox.showerror("Error", "Please add some recipes first!")
            return

        # Extract recipe ID from selection
        try:
            recipe_id = int(recipe_selection.split("ID: ")[1].split(")")[0])
        except (IndexError, ValueError):
            messagebox.showerror("Error", "Invalid recipe selection!")
            return

        success = self.db.add_meal_plan(day, meal_type, recipe_id)
        if success:
            messagebox.showinfo("Success", f"Added to {day} {meal_type}!")
            self.refresh_meal_plan()
        else:
            messagebox.showerror("Error", "Failed to add to meal plan!")

    def refresh_meal_plan(self):
        """Refresh meal plan display"""
        # Clear existing widgets
        for widget in self.meal_plan_frame.winfo_children():
            widget.destroy()

        meal_plan = self.db.get_meal_plan()

        if not meal_plan:
            no_plan_label = ctk.CTkLabel(self.meal_plan_frame, text="No meal plan found! Start planning your meals.",
                                         font=ctk.CTkFont(size=16))
            no_plan_label.pack(pady=50)
            return

        # Group by day
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        meals_by_day = {}

        for meal in meal_plan:
            day = meal[0]
            if day not in meals_by_day:
                meals_by_day[day] = {}
            meals_by_day[day][meal[1]] = {"name": meal[2], "id": meal[3]}

        # Display meal plan
        for day in days_order:
            if day in meals_by_day:
                day_frame = ctk.CTkFrame(self.meal_plan_frame)
                day_frame.pack(fill="x", pady=10, padx=10)

                # Day header
                day_header = ctk.CTkLabel(day_frame, text=day, font=ctk.CTkFont(size=18, weight="bold"))
                day_header.pack(pady=10)

                # Meals for the day
                meals_frame = ctk.CTkFrame(day_frame)
                meals_frame.pack(fill="x", padx=10, pady=(0, 10))

                meal_types = ['Breakfast', 'Lunch', 'Dinner']
                for i, meal_type in enumerate(meal_types):
                    meal_frame = ctk.CTkFrame(meals_frame)
                    meal_frame.pack(side="left", fill="both", expand=True, padx=5, pady=10)

                    # Meal type header
                    meal_header = ctk.CTkLabel(meal_frame, text=meal_type, font=ctk.CTkFont(size=14, weight="bold"))
                    meal_header.pack(pady=(10, 5))

                    if meal_type in meals_by_day[day]:
                        # Recipe name
                        recipe_name = meals_by_day[day][meal_type]["name"]
                        recipe_label = ctk.CTkLabel(meal_frame, text=recipe_name, wraplength=150)
                        recipe_label.pack(pady=5)

                        # Remove button
                        remove_btn = ctk.CTkButton(meal_frame, text="Remove",
                                                   command=lambda d=day, m=meal_type: self.remove_from_meal_plan(d, m),
                                                   height=25, width=80, fg_color="red", hover_color="darkred")
                        remove_btn.pack(pady=(5, 10))
                    else:
                        # Empty slot
                        empty_label = ctk.CTkLabel(meal_frame, text="No meal planned", text_color="gray")
                        empty_label.pack(pady=20)

    def remove_from_meal_plan(self, day, meal_type):
        """Remove meal from plan"""
        result = messagebox.askyesno("Confirm Remove", f"Remove meal from {day} {meal_type}?")

        if result:
            success = self.db.remove_meal_plan(day, meal_type)
            if success:
                messagebox.showinfo("Success", "Meal removed from plan!")
                self.refresh_meal_plan()
            else:
                messagebox.showerror("Error", "Failed to remove meal!")

    def show_shopping_list_page(self):
        """Show shopping list page"""
        self.clear_content_frame()

        # Title
        title = ctk.CTkLabel(self.content_frame, text="Shopping List",
                             font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(pady=20)

        # Buttons frame
        buttons_frame = ctk.CTkFrame(self.content_frame)
        buttons_frame.pack(fill="x", padx=20, pady=10)

        refresh_btn = ctk.CTkButton(buttons_frame, text="Refresh List", command=self.refresh_shopping_list)
        refresh_btn.pack(side="left", padx=10, pady=10)

        export_btn = ctk.CTkButton(buttons_frame, text="Export to Excel", command=self.export_shopping_list)
        export_btn.pack(side="right", padx=10, pady=10)

        # Shopping list display
        self.shopping_list_frame = ctk.CTkScrollableFrame(self.content_frame)
        self.shopping_list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.refresh_shopping_list()

    def refresh_shopping_list(self):
        """Refresh shopping list display"""
        # Clear existing widgets
        for widget in self.shopping_list_frame.winfo_children():
            widget.destroy()

        ingredients = self.db.get_shopping_list()

        if not ingredients:
            no_list_label = ctk.CTkLabel(self.shopping_list_frame, text="No ingredients found! Plan some meals first.",
                                         font=ctk.CTkFont(size=16))
            no_list_label.pack(pady=50)
            return

        # Display ingredients
        list_frame = ctk.CTkFrame(self.shopping_list_frame)
        list_frame.pack(fill="x", padx=20, pady=20)

        title_label = ctk.CTkLabel(list_frame, text=f"Shopping List ({len(ingredients)} items)",
                                   font=ctk.CTkFont(size=18, weight="bold"))
        title_label.pack(pady=15)

        for i, ingredient in enumerate(ingredients, 1):
            ingredient_frame = ctk.CTkFrame(list_frame)
            ingredient_frame.pack(fill="x", padx=10, pady=2)

            ingredient_label = ctk.CTkLabel(ingredient_frame, text=f"{i}. {ingredient}",
                                            font=ctk.CTkFont(size=14))
            ingredient_label.pack(side="left", padx=15, pady=8)

    def export_shopping_list(self):
        """Export shopping list to Excel"""
        ingredients = self.db.get_shopping_list()

        if not ingredients:
            messagebox.showerror("Error", "No ingredients to export!")
            return

        # Ask for save location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            title="Save Shopping List"
        )

        if not file_path:
            return

        try:
            # Create DataFrame and save to Excel
            df = pd.DataFrame(ingredients, columns=['Ingredients'])
            df.index += 1  # Start index from 1
            df.to_excel(file_path, sheet_name='Shopping List')

            messagebox.showinfo("Success", f"Shopping list exported to {file_path}!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {str(e)}")

    def show_analytics_page(self):
        """Show analytics page"""
        self.clear_content_frame()

        # Title
        title = ctk.CTkLabel(self.content_frame, text="Recipe Analytics",
                             font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(pady=20)

        # Create notebook for different charts
        notebook = ctk.CTkTabview(self.content_frame)
        notebook.pack(fill="both", expand=True, padx=20, pady=10)

        # Recipe Categories Chart
        notebook.add("Recipe Categories")
        self.create_recipe_categories_chart(notebook.tab("Recipe Categories"))

        # Meal Plan Distribution
        notebook.add("Meal Distribution")
        self.create_meal_distribution_chart(notebook.tab("Meal Distribution"))

        # Cuisine Distribution
        notebook.add("Cuisine Types")
        self.create_cuisine_chart(notebook.tab("Cuisine Types"))

    def create_recipe_categories_chart(self, parent):
        """Create pie chart for recipe categories"""
        recipes = self.db.get_all_recipes()

        if not recipes:
            no_data_label = ctk.CTkLabel(parent, text="No recipe data available!", font=ctk.CTkFont(size=16))
            no_data_label.pack(pady=50)
            return

        # Count categories
        categories = {}
        for recipe in recipes:
            category = recipe[4]
            categories[category] = categories.get(category, 0) + 1

        # Create pie chart
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.pie(categories.values(), labels=categories.keys(), autopct='%1.1f%%', startangle=90)
        ax.set_title('Recipe Distribution by Category', fontsize=16, fontweight='bold')

        # Embed chart in tkinter
        canvas = FigureCanvasTkAgg(fig, parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=20)

    def create_meal_distribution_chart(self, parent):
        """Create bar chart for meal plan distribution"""
        meal_plan = self.db.get_meal_plan()

        if not meal_plan:
            no_data_label = ctk.CTkLabel(parent, text="No meal plan data available!", font=ctk.CTkFont(size=16))
            no_data_label.pack(pady=50)
            return

        # Count meal types
        meal_types = {}
        for meal in meal_plan:
            meal_type = meal[1]
            meal_types[meal_type] = meal_types.get(meal_type, 0) + 1

        # Create bar chart
        fig, ax = plt.subplots(figsize=(8, 6))
        bars = ax.bar(meal_types.keys(), meal_types.values(), color=['#ff9999', '#66b3ff', '#99ff99'])
        ax.set_title('Meal Plan Distribution', fontsize=16, fontweight='bold')
        ax.set_ylabel('Number of Meals')
        ax.set_xlabel('Meal Type')

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., height + 0.1,
                    f'{int(height)}', ha='center', va='bottom')

        # Embed chart in tkinter
        canvas = FigureCanvasTkAgg(fig, parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=20)

    def create_cuisine_chart(self, parent):
        """Create pie chart for cuisine types"""
        recipes = self.db.get_all_recipes()

        if not recipes:
            no_data_label = ctk.CTkLabel(parent, text="No recipe data available!", font=ctk.CTkFont(size=16))
            no_data_label.pack(pady=50)
            return

        # Count cuisines
        cuisines = {}
        for recipe in recipes:
            cuisine = recipe[5] if recipe[5] else "Not Specified"
            cuisines[cuisine] = cuisines.get(cuisine, 0) + 1

        # Create pie chart
        fig, ax = plt.subplots(figsize=(8, 6))
        colors = plt.cm.Set3(range(len(cuisines)))
        wedges, texts, autotexts = ax.pie(cuisines.values(), labels=cuisines.keys(),
                                          autopct='%1.1f%%', startangle=90, colors=colors)
        ax.set_title('Recipe Distribution by Cuisine Type', fontsize=16, fontweight='bold')

        # Embed chart in tkinter
        canvas = FigureCanvasTkAgg(fig, parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=20)

    def run(self):
        """Run the application"""
        self.root.mainloop()


# Database setup instructions
def show_setup_instructions():
    """Show database setup instructions"""
    setup_window = ctk.CTk()
    setup_window.title("Database Setup Instructions")
    setup_window.geometry("600x400")

    text_frame = ctk.CTkScrollableFrame(setup_window)
    text_frame.pack(fill="both", expand=True, padx=20, pady=20)

    instructions = """
    📋 DATABASE SETUP INSTRUCTIONS

    Before running this application, please ensure MySQL is installed and configured:

    1. Install MySQL Server on your system
    2. Create a database named 'recipe_planner':
       - Open MySQL Command Line or MySQL Workbench
       - Execute: CREATE DATABASE recipe_planner;

    3. Update the database connection settings in the code:
       - Open the DatabaseManager class
       - Update host, user, and password in connect_database() method
       - Default settings:
         * Host: localhost
         * Database: recipe_planner
         * User: root
         * Password: password (change this to your MySQL password)

    4. Required Python packages (install via pip):
       - pip install customtkinter
       - pip install mysql-connector-python
       - pip install matplotlib
       - pip install pandas
       - pip install openpyxl

    5. Run the application:
       - python recipe_planner.py

    The application will automatically create the required tables on first run.

    🚀 FEATURES INCLUDED:
    ✅ Add, edit, delete, and search recipes
    ✅ Plan meals for the week
    ✅ Generate shopping lists automatically
    ✅ Visual analytics with charts
    ✅ Export shopping lists to Excel
    ✅ Modern CustomTkinter UI
    ✅ Full CRUD functionality with MySQL

    📊 BONUS FEATURES:
    ✅ Recipe categorization and cuisine types
    ✅ Cook time tracking
    ✅ Advanced search functionality
    ✅ Weekly meal plan overview
    ✅ Data visualization with matplotlib
    ✅ Export capabilities
    """

    instructions_label = ctk.CTkLabel(text_frame, text=instructions,
                                      font=ctk.CTkFont(size=12),
                                      justify="left")
    instructions_label.pack(padx=20, pady=20)

    close_btn = ctk.CTkButton(setup_window, text="Close", command=setup_window.destroy)
    close_btn.pack(pady=20)

    setup_window.mainloop()


# Main execution
if __name__ == "__main__":
    try:
        # Try to run the main application
        app = RecipePlannerApp()
        app.run()
    except Exception as e:
        if "mysql" in str(e).lower() or "database" in str(e).lower():
            # Show setup instructions if database connection fails
            print("Database connection failed. Showing setup instructions...")
            show_setup_instructions()
        else:
            print(f"Error: {e}")
            # Show setup instructions for any other errors too
            show_setup_instructions()