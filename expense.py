import datetime
import csv
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
import matplotlib.pyplot as plt
from enum import Enum
import requests
import json
import os
from dataclasses import dataclass, field
import locale


locale.setlocale(locale.LC_ALL, 'en_IN.UTF-8')


class ExpenseCategory(Enum):
    FOOD = "Food"
    TRANSPORTATION = "Transportation"
    HOUSING = "Housing"
    ENTERTAINMENT = "Entertainment"
    UTILITIES = "Utilities"
    HEALTH = "Health"
    EDUCATION = "Education"
    SHOPPING = "Shopping"
7    INVESTMENT = "Investment"
    TRAVEL = "Travel"
    OTHER = "Other"

class Currency(Enum):
    INR = "₹"
    USD = "$"
    EUR = "€"
    GBP = "£"
    JPY = "¥"
    CAD = "C$"
    AUD = "A$"
    SGD = "S$"

@dataclass
class ExpenseTag:
    name: str
    category: ExpenseCategory


class CurrencyConverter:
    _instance = None
    _rates = {
        'INR': 1.0,  
        'USD': 0.012,
        'EUR': 0.011,
        'GBP': 0.0095,
        'JPY': 1.78,
        'CAD': 0.016,
        'AUD': 0.018,
        'SGD': 0.016
    }
    _last_update = None
    CACHE_FILE = "exchange_rates.json"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.load_rates()
        return cls._instance
    
    def load_rates(self):
        if os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, 'r') as f:
                    data = json.load(f)
                    self._rates = data.get('rates', self._rates)
                    self._last_update = datetime.datetime.fromisoformat(data['last_update'])
                    if (datetime.datetime.now() - self._last_update) > datetime.timedelta(hours=12):
                        self.update_rates()
            except:
                self.update_rates()
        else:
            self.update_rates()
    
    def save_rates(self):
        data = {
            'rates': self._rates,
            'last_update': datetime.datetime.now().isoformat()
        }
        with open(self.CACHE_FILE, 'w') as f:
            json.dump(data, f)
    
    def update_rates(self):
        try:
            response = requests.get("https://api.exchangerate-api.com/v4/latest/INR", timeout=5)
            data = response.json()
            self._rates = data['rates']
            self._last_update = datetime.datetime.now()
            self.save_rates()
            print("Exchange rates updated successfully")
        except Exception as e:
            print(f"Failed to update exchange rates, using cached rates: {e}")
    
    def convert(self, amount: float, from_currency: Currency, to_currency: Currency) -> float:
        if from_currency == to_currency:
            return amount
            
        from_code = from_currency.name
        to_code = to_currency.name
        
        if from_code not in self._rates or to_code not in self._rates:
            raise ValueError(f"Unsupported currency conversion: {from_code} to {to_code}")

        inr_amount = amount / self._rates[from_code]
        return inr_amount * self._rates[to_code]
    
    def format_currency(self, amount: float, currency: Currency) -> str:
        symbol = currency.value
        if currency == Currency.INR:
            return locale.currency(amount, grouping=True, symbol=True)
        return f"{symbol}{amount:,.2f}"

@dataclass
class Expense:
    amount: float
    category: ExpenseCategory
    description: str
    date: datetime.date
    currency: Currency = Currency.INR
    is_recurring: bool = False
    recurring_period_days: int = 0
    tags: List[str] = field(default_factory=list)
    payment_method: str = "Cash"
    
    def convert_to(self, target_currency: Currency) -> float:
        converter = CurrencyConverter()
        return converter.convert(self.amount, self.currency, target_currency)
        
    def __str__(self):
        converter = CurrencyConverter()
        formatted_amount = converter.format_currency(self.amount, self.currency)
        tags = ", ".join(self.tags) if self.tags else "No tags"
        return (f"{self.date}: {formatted_amount} - {self.description} ({self.category.value}) "
                f"[Payment: {self.payment_method}, Tags: {tags}]")


class Budget:
    def __init__(self, category: ExpenseCategory, monthly_limit: float, 
                 currency: Currency = Currency.INR, alert_threshold: float = 80.0):
        self.category = category
        self.monthly_limit = monthly_limit
        self.currency = currency
        self.current_spending = 0.0
        self.alert_threshold = alert_threshold
        self.alerts_triggered = False
        
    def add_spending(self, amount: float, expense_currency: Currency):
        converter = CurrencyConverter()
        converted_amount = converter.convert(amount, expense_currency, self.currency)
        self.current_spending += converted_amount
        
        
        if not self.alerts_triggered and self.percentage_used() >= self.alert_threshold:
            self.alerts_triggered = True
            remaining = self.remaining_budget()
            print(f"\n⚠️ BUDGET ALERT: {self.category.value} budget is {self.percentage_used():.1f}% used!")
            print(f"Remaining budget: {converter.format_currency(remaining, self.currency)}")
    
    def remaining_budget(self) -> float:
        return max(0.0, self.monthly_limit - self.current_spending)
    
    def percentage_used(self) -> float:
        return (self.current_spending / self.monthly_limit) * 100 if self.monthly_limit != 0 else 0
    
    def __str__(self):
        converter = CurrencyConverter()
        remaining = self.remaining_budget()
        return (f"{self.category.value} Budget: {converter.format_currency(self.current_spending, self.currency)}/"
                f"{converter.format_currency(self.monthly_limit, self.currency)} "
                f"({self.percentage_used():.1f}% used, Remaining: {converter.format_currency(remaining, self.currency)})")


class User:
    def __init__(self, name: str, default_currency: Currency = Currency.INR):
        self.name = name
        self.default_currency = default_currency
        self.expenses: List[Expense] = []
        self.budgets: Dict[ExpenseCategory, Budget] = {}
        self.tags: Dict[str, ExpenseTag] = {}
        self.payment_methods = ["Cash", "Credit Card", "Debit Card", "UPI", "Bank Transfer", "Wallet"]
        self._initialize_default_tags()
        
    def _initialize_default_tags(self):
        default_tags = [
            ExpenseTag("groceries", ExpenseCategory.FOOD),
            ExpenseTag("dining", ExpenseCategory.FOOD),
            ExpenseTag("fuel", ExpenseCategory.TRANSPORTATION),
            ExpenseTag("rent", ExpenseCategory.HOUSING),
            ExpenseTag("movie", ExpenseCategory.ENTERTAINMENT),
            ExpenseTag("electricity", ExpenseCategory.UTILITIES),
            ExpenseTag("doctor", ExpenseCategory.HEALTH),
            ExpenseTag("books", ExpenseCategory.EDUCATION),
            ExpenseTag("shopping", ExpenseCategory.SHOPPING),
            ExpenseTag("mutual fund", ExpenseCategory.INVESTMENT),
            ExpenseTag("flight", ExpenseCategory.TRAVEL)
        ]
        for tag in default_tags:
            self.tags[tag.name] = tag
    
    def add_expense(self, amount: float, description: str, date: datetime.date = None, 
                   category: ExpenseCategory = None, currency: Currency = None,
                   is_recurring: bool = False, recurring_period_days: int = 0,
                   tags: List[str] = None, payment_method: str = None):
        if date is None:
            date = datetime.date.today()
        if currency is None:
            currency = self.default_currency
        if payment_method is None:
            payment_method = "Cash"
        if tags is None:
            tags = []
            
       
        if category is None:
            category = self._categorize_from_tags(tags) or self._categorize_from_description(description)
            
        expense = Expense(
            amount=amount,
            category=category,
            description=description,
            date=date,
            currency=currency,
            is_recurring=is_recurring,
            recurring_period_days=recurring_period_days,
            tags=tags,
            payment_method=payment_method
        )
        self.expenses.append(expense)
        
       
        if category in self.budgets:
            self.budgets[category].add_spending(amount, currency)
            
        return expense
    
    def _categorize_from_tags(self, tags: List[str]) -> Optional[ExpenseCategory]:
        for tag in tags:
            if tag in self.tags:
                return self.tags[tag].category
        return None
    
    def _categorize_from_description(self, description: str) -> ExpenseCategory:
        description_lower = description.lower()
        for tag_name, tag in self.tags.items():
            if tag_name in description_lower:
                return tag.category
        return ExpenseCategory.OTHER
    
    def set_budget(self, category: ExpenseCategory, monthly_limit: float, 
                  currency: Currency = None, alert_threshold: float = 80.0):
        if currency is None:
            currency = self.default_currency
        self.budgets[category] = Budget(category, monthly_limit, currency, alert_threshold)
        
    def add_tag(self, name: str, category: ExpenseCategory):
        self.tags[name] = ExpenseTag(name, category)
        
    def get_spending_breakdown(self, target_currency: Currency = None,
                             start_date: datetime.date = None, 
                             end_date: datetime.date = None) -> Dict[ExpenseCategory, float]:
        if target_currency is None:
            target_currency = self.default_currency
            
        breakdown = {category: 0.0 for category in ExpenseCategory}
        converter = CurrencyConverter()
        
        for expense in self.expenses:
            if start_date and expense.date < start_date:
                continue
            if end_date and expense.date > end_date:
                continue
                
            amount = expense.amount if expense.currency == target_currency else \
                   converter.convert(expense.amount, expense.currency, target_currency)
            breakdown[expense.category] += amount
                
        return {k: v for k, v in breakdown.items() if v > 0}
    
    def get_recurring_expenses(self) -> List[Expense]:
        return [expense for expense in self.expenses if expense.is_recurring]
    
    def get_expenses_by_tag(self, tag: str) -> List[Expense]:
        return [expense for expense in self.expenses if tag in expense.tags]


class ReportGenerator:
    @staticmethod
    def generate_text_report(user: User, target_currency: Currency = None,
                           start_date: datetime.date = None, end_date: datetime.date = None) -> str:
        if target_currency is None:
            target_currency = user.default_currency
            
        converter = CurrencyConverter()
        breakdown = user.get_spending_breakdown(target_currency, start_date, end_date)
        total = sum(breakdown.values())
        
        report = []
        report.append(f"📊 Expense Report for {user.name}")
        report.append(f"💵 Currency: {target_currency.value}")
        
        if start_date and end_date:
            report.append(f"📅 Period: {start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}")
        elif start_date:
            report.append(f"📅 Since: {start_date.strftime('%d %b %Y')}")
        elif end_date:
            report.append(f"📅 Until: {end_date.strftime('%d %b %Y')}")
        else:
            report.append("📅 All expenses")
            
        report.append("\n📋 Category Breakdown:")
        for category, amount in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
            percentage = (amount / total) * 100 if total > 0 else 0
            report.append(f"  - {category.value}: {converter.format_currency(amount, target_currency)} "
                        f"({percentage:.1f}%)")
                
        report.append(f"\n💰 Total Spending: {converter.format_currency(total, target_currency)}")
        

        if user.budgets:
            report.append("\n💳 Budget Status:")
            for budget in user.budgets.values():
                if budget.currency != target_currency:
                    limit = converter.convert(budget.monthly_limit, budget.currency, target_currency)
                    spending = converter.convert(budget.current_spending, budget.currency, target_currency)
                    remaining = limit - spending
                    percentage = (spending / limit) * 100 if limit != 0 else 0
                    report.append(
                        f"  - {budget.category.value}: {converter.format_currency(spending, target_currency)}/"
                        f"{converter.format_currency(limit, target_currency)} "
                        f"({percentage:.1f}% used, Remaining: {converter.format_currency(remaining, target_currency)})"
                    )
                else:
                    report.append(f"  - {str(budget)}")
        
    
        recurring = user.get_recurring_expenses()
        if recurring:
            report.append("\n🔄 Recurring Expenses:")
            for expense in recurring:
                amount = expense.amount if expense.currency == target_currency else \
                       converter.convert(expense.amount, expense.currency, target_currency)
                report.append(f"  - {expense.description}: {converter.format_currency(amount, target_currency)} "
                            f"every {expense.recurring_period_days} days")
        
        return "\n".join(report)

    @staticmethod
    def generate_pie_chart(user: User, target_currency: Currency = None,
                         start_date: datetime.date = None, end_date: datetime.date = None):
        if target_currency is None:
            target_currency = user.default_currency
            
        breakdown = user.get_spending_breakdown(target_currency, start_date, end_date)
        
        if not breakdown:
            print("No expenses to display")
            return
            
        categories = [cat.value for cat in breakdown.keys()]
        amounts = list(breakdown.values())
        
        plt.figure(figsize=(10, 8))
        plt.pie(amounts, labels=categories, autopct='%1.1f%%', startangle=140,
               textprops={'fontsize': 12})
        plt.title(f"Expense Distribution ({target_currency.value})", fontsize=16)
        plt.tight_layout()
        plt.show()
    
    @staticmethod
    def generate_spending_trend(user: User, target_currency: Currency = None,
                              start_date: datetime.date = None, end_date: datetime.date = None):
        if target_currency is None:
            target_currency = user.default_currency
            
        if start_date is None:
            start_date = min(expense.date for expense in user.expenses)
        if end_date is None:
            end_date = max(expense.date for expense in user.expenses)
            
        # Group by month
        monthly_data: Dict[Tuple[int, int], Dict[ExpenseCategory, float]] = {}
        converter = CurrencyConverter()
        
        current_date = start_date
        while current_date <= end_date:
            monthly_data[(current_date.year, current_date.month)] = {
                category: 0.0 for category in ExpenseCategory
            }
            # Move to next month
            if current_date.month == 12:
                current_date = datetime.date(current_date.year + 1, 1, 1)
            else:
                current_date = datetime.date(current_date.year, current_date.month + 1, 1)
        
        for expense in user.expenses:
            if expense.date < start_date or expense.date > end_date:
                continue
                
            year_month = (expense.date.year, expense.date.month)
            amount = expense.amount if expense.currency == target_currency else \
                   converter.convert(expense.amount, expense.currency, target_currency)
            monthly_data[year_month][expense.category] += amount
        
 
        months = [datetime.date(year, month, 1).strftime('%b %Y') for year, month in sorted(monthly_data.keys())]
        categories = ExpenseCategory
        category_totals = {category: [] for category in categories}
        
        for year_month in sorted(monthly_data.keys()):
            for category in categories:
                category_totals[category].append(monthly_data[year_month][category])
        
       
        plt.figure(figsize=(12, 8))
        bottom = [0] * len(months)
        
        for category in categories:
            amounts = category_totals[category]
            if sum(amounts) > 0:  
                plt.bar(months, amounts, label=category.value, bottom=bottom)
                bottom = [bottom[i] + amounts[i] for i in range(len(months))]
        
        plt.xlabel('Month', fontsize=12)
        plt.ylabel(f'Amount ({target_currency.value})', fontsize=12)
        plt.title('Monthly Spending Trends', fontsize=16)
        plt.xticks(rotation=45)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.show()

    @staticmethod
    def generate_csv_report(user: User, filename: str = "expense_report.csv", 
                          target_currency: Currency = None,
                          start_date: datetime.date = None, end_date: datetime.date = None):
        """
        Generates a CSV report of expenses with the given parameters
        """
        if target_currency is None:
            target_currency = user.default_currency
            
        converter = CurrencyConverter()
        expenses_to_export = []
        
       
        for expense in user.expenses:
            if start_date and expense.date < start_date:
                continue
            if end_date and expense.date > end_date:
                continue
                
            
            amount = expense.amount if expense.currency == target_currency else \
                   converter.convert(expense.amount, expense.currency, target_currency)
                   
            expenses_to_export.append({
                'Date': expense.date.isoformat(),
                'Amount': amount,
                'Currency': target_currency.name,
                'Category': expense.category.value,
                'Description': expense.description,
                'Payment Method': expense.payment_method,
                'Is Recurring': expense.is_recurring,
                'Recurring Period (days)': expense.recurring_period_days,
                'Tags': ", ".join(expense.tags) if expense.tags else ""
            })
        
        if not expenses_to_export:
            print("No expenses to export")
            return
        
        
        try:
            with open(filename, 'w', newline='') as csvfile:
                fieldnames = expenses_to_export[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for expense in expenses_to_export:
                    writer.writerow(expense)
                    
            print(f"✅ Report successfully exported to {filename}")
        except Exception as e:
            print(f"❌ Error exporting to CSV: {e}")


class ExpenseTrackerApp:
    def __init__(self):
        self.current_user: Optional[User] = None
        self.currency_converter = CurrencyConverter()
        self.data_file = "expense_tracker_data.json"
        
    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.current_user = User(data['name'], Currency[data['default_currency']])
                    
                    
                    for exp_data in data.get('expenses', []):
                        self.current_user.add_expense(
                            amount=exp_data['amount'],
                            description=exp_data['description'],
                            date=datetime.date.fromisoformat(exp_data['date']),
                            category=ExpenseCategory[exp_data['category']],
                            currency=Currency[exp_data['currency']],
                            is_recurring=exp_data['is_recurring'],
                            recurring_period_days=exp_data['recurring_period_days'],
                            tags=exp_data.get('tags', []),
                            payment_method=exp_data.get('payment_method', 'Cash')
                        )
                    
                   
                    for budget_data in data.get('budgets', []):
                        self.current_user.set_budget(
                            category=ExpenseCategory[budget_data['category']],
                            monthly_limit=budget_data['monthly_limit'],
                            currency=Currency[budget_data['currency']],
                            alert_threshold=budget_data.get('alert_threshold', 80.0)
                        )
                    
                    
                    for tag_name, tag_data in data.get('tags', {}).items():
                        self.current_user.tags[tag_name] = ExpenseTag(
                            name=tag_name,
                            category=ExpenseCategory[tag_data['category']]
                        )
                    
                    print(f"Data loaded for user {self.current_user.name}")
            except Exception as e:
                print(f"Error loading data: {e}")

    def save_data(self):
        if not self.current_user:
            return
            
        data = {
            'name': self.current_user.name,
            'default_currency': self.current_user.default_currency.name,
            'expenses': [],
            'budgets': [],
            'tags': {}
        }
        
        for expense in self.current_user.expenses:
            data['expenses'].append({
                'amount': expense.amount,
                'description': expense.description,
                'date': expense.date.isoformat(),
                'category': expense.category.name,
                'currency': expense.currency.name,
                'is_recurring': expense.is_recurring,
                'recurring_period_days': expense.recurring_period_days,
                'tags': expense.tags,
                'payment_method': expense.payment_method
            })
        
        for category, budget in self.current_user.budgets.items():
            data['budgets'].append({
                'category': category.name,
                'monthly_limit': budget.monthly_limit,
                'currency': budget.currency.name,
                'alert_threshold': budget.alert_threshold
            })
        
        for tag_name, tag in self.current_user.tags.items():
            data['tags'][tag_name] = {
                'category': tag.category.name
            }
        
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def create_user(self):
        name = input("Enter your name: ")
        print("\nAvailable currencies:")
        for currency in Currency:
            print(f"- {currency.name} ({currency.value})")
        
        currency_str = input("Enter default currency (INR recommended): ").upper()
        try:
            currency = Currency[currency_str]
            self.current_user = User(name, currency)
            print(f"\n✅ User {name} created with default currency {currency.value}")
            self.save_data()
        except KeyError:
            print("Invalid currency. Using INR as default.")
            self.current_user = User(name)
            self.save_data()
    
    def add_expense(self):
        if not self.current_user:
            print("Please create a user first")
            return
            
        try:
            print("\n➕ Add New Expense")
            amount = float(input("Amount: "))
            description = input("Description: ")
            
            print("\n💳 Payment Methods:")
            for i, method in enumerate(self.current_user.payment_methods, 1):
                print(f"{i}. {method}")
            pm_choice = input(f"Select payment method (1-{len(self.current_user.payment_methods)}): ")
            payment_method = self.current_user.payment_methods[int(pm_choice)-1]
            
            date_str = input("Date (YYYY-MM-DD, leave blank for today): ")
            date = datetime.date.today() if not date_str else datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            
            print("\n🏷️ Available Tags:")
            for tag in self.current_user.tags.values():
                print(f"- {tag.name} ({tag.category.value})")
            tags_input = input("Enter tags (comma separated, leave blank if none): ")
            tags = [tag.strip() for tag in tags_input.split(",")] if tags_input else []
            
            is_recurring = input("Is this a recurring expense? (y/n): ").lower() == 'y'
            recurring_period = 0
            if is_recurring:
                recurring_period = int(input("Recurring period in days (e.g., 30 for monthly): "))
            
            
            currency = self.current_user.default_currency
            for tag in tags:
                if tag in ['travel', 'flight', 'hotel']:
                    currency = Currency.USD  
                    break
            
            expense = self.current_user.add_expense(
                amount=amount,
                description=description,
                date=date,
                currency=currency,
                is_recurring=is_recurring,
                recurring_period_days=recurring_period,
                tags=tags,
                payment_method=payment_method
            )
            
            print(f"\n✅ Expense added successfully:")
            print(expense)
            self.save_data()
        except Exception as e:
            print(f"❌ Error adding expense: {e}")
    
    def set_budget(self):
        if not self.current_user:
            print("Please create a user first")
            return
            
        try:
            print("\n💰 Set Budget")
            print("Categories:")
            for i, category in enumerate(ExpenseCategory, 1):
                print(f"{i}. {category.value}")
            
            cat_choice = int(input(f"Select category (1-{len(ExpenseCategory)}): ")) - 1
            category = list(ExpenseCategory)[cat_choice]
            
            amount = float(input("Monthly budget amount: "))
            threshold = float(input("Alert threshold percentage (e.g., 80): "))
            
            print("\n💱 Currency Options:")
            for i, currency in enumerate(Currency, 1):
                print(f"{i}. {currency.name} ({currency.value})")
            curr_choice = int(input(f"Select currency (1-{len(Currency)}): ")) - 1
            currency = list(Currency)[curr_choice]
            
            self.current_user.set_budget(category, amount, currency, threshold)
            print(f"\n✅ Budget set for {category.value}: {self.currency_converter.format_currency(amount, currency)} per month")
            self.save_data()
        except Exception as e:
            print(f"❌ Error setting budget: {e}")
    
    def generate_reports(self):
        if not self.current_user:
            print("Please create a user first")
            return
            
        try:
            while True:
                print("\n📊 Report Options:")
                print("1. Text Summary Report")
                print("2. Pie Chart (Category Distribution)")
                print("3. Spending Trends (Monthly)")
                print("4. Export to CSV")
                print("5. Back to Main Menu")
                
                choice = input("Enter your choice (1-5): ")
                
                if choice == "5":
                    break
                
                print("\n📅 Date Range Options:")
                print("1. Current Month")
                print("2. Last 3 Months")
                print("3. Custom Range")
                print("4. All Time")
                
                range_choice = input("Select date range (1-4): ")
                
                today = datetime.date.today()
                start_date, end_date = None, None
                
                if range_choice == "1":
                    start_date = datetime.date(today.year, today.month, 1)
                    end_date = today
                elif range_choice == "2":
                    end_date = today
                    start_date = end_date - datetime.timedelta(days=90)
                elif range_choice == "3":
                    start_str = input("Start date (YYYY-MM-DD): ")
                    end_str = input("End date (YYYY-MM-DD): ")
                    start_date = datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
                    end_date = datetime.datetime.strptime(end_str, "%Y-%m-%d").date()
                elif range_choice == "4":
                    pass
                else:
                    print("Invalid choice")
                    continue
                
                print("\n💱 Currency Options:")
                for i, currency in enumerate(Currency, 1):
                    print(f"{i}. {currency.name} ({currency.value})")
                curr_choice = int(input(f"Select currency (1-{len(Currency)}): ")) - 1
                target_currency = list(Currency)[curr_choice]
                
                if choice == "1":
                    print("\n" + ReportGenerator.generate_text_report(
                        self.current_user, target_currency, start_date, end_date
                    ))
                    input("\nPress Enter to continue...")
                elif choice == "2":
                    ReportGenerator.generate_pie_chart(
                        self.current_user, target_currency, start_date, end_date
                    )
                elif choice == "3":
                    ReportGenerator.generate_spending_trend(
                        self.current_user, target_currency, start_date, end_date
                    )
                elif choice == "4":
                    filename = input("Enter filename for CSV report (default: expense_report.csv): ") or "expense_report.csv"
                    ReportGenerator.generate_csv_report(
                        self.current_user, filename, target_currency, start_date, end_date
                    )
                else:
                    print("Invalid choice")
        except Exception as e:
            print(f"❌ Error generating report: {e}")
    
    def manage_tags(self):
        if not self.current_user:
            print("Please create a user first")
            return
            
        try:
            while True:
                print("\n🏷️ Tag Management")
                print("1. View All Tags")
                print("2. Add New Tag")
                print("3. Delete Tag")
                print("4. Back to Main Menu")
                
                choice = input("Enter your choice (1-4): ")
                
                if choice == "4":
                    break
                
                if choice == "1":
                    print("\nCurrent Tags:")
                    for tag_name, tag in self.current_user.tags.items():
                        print(f"- {tag_name} → {tag.category.value}")
                elif choice == "2":
                    name = input("Tag name: ")
                    print("Categories:")
                    for i, category in enumerate(ExpenseCategory, 1):
                        print(f"{i}. {category.value}")
                    cat_choice = int(input(f"Select category (1-{len(ExpenseCategory)}): ")) - 1
                    category = list(ExpenseCategory)[cat_choice]
                    self.current_user.add_tag(name, category)
                    print(f"✅ Tag '{name}' added for category {category.value}")
                    self.save_data()
                elif choice == "3":
                    tag_name = input("Tag name to delete: ")
                    if tag_name in self.current_user.tags:
                        del self.current_user.tags[tag_name]
                        print(f"✅ Tag '{tag_name}' deleted")
                        self.save_data()
                    else:
                        print("❌ Tag not found")
                else:
                    print("Invalid choice")
        except Exception as e:
            print(f"❌ Error managing tags: {e}")
    
    def run(self):
        print("💰 Welcome to Indian Expense Tracker")
        print("Loading data...")
        self.load_data()
        
        while True:
            print("\n🏠 Main Menu:")
            print("1. Create/Change User")
            print("2. Add Expense")
            print("3. Set Budget")
            print("4. Generate Reports")
            print("5. Manage Tags")
            print("6. Update Exchange Rates")
            print("7. Exit")
            
            choice = input("Enter your choice (1-7): ")
            
            if choice == "1":
                self.create_user()
            elif choice == "2":
                self.add_expense()
            elif choice == "3":
                self.set_budget()
            elif choice == "4":
                self.generate_reports()
            elif choice == "5":
                self.manage_tags()
            elif choice == "6":
                self.currency_converter.update_rates()
                print("Exchange rates updated")
            elif choice == "7":
                self.save_data()
                print("Thank you for using Indian Expense Tracker!")
                break
            else:
                print("Invalid choice. Please try again.")

# Run the application
if __name__ == "__main__":
    app = ExpenseTrackerApp()
    app.run()
