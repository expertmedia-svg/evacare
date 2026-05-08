from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base

class UserRole(str, enum.Enum):
    owner = "owner"
    manager = "manager"
    seller = "seller"
    accountant = "accountant"
    delivery = "delivery"
    system_admin = "system_admin"

class ProductStatus(str, enum.Enum):
    available = "available"
    rupture = "rupture"
    disabled = "disabled"

class OrderStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    delivered = "delivered"
    cancelled = "cancelled"

class PaymentMethod(str, enum.Enum):
    cash = "cash"
    orange_money = "orange_money"
    moov_money = "moov_money"
    coris_money = "coris_money"
    wave = "wave"
    credit = "credit"
    partial = "partial"

class StockMovementType(str, enum.Enum):
    entry = "entry"
    exit = "exit"
    adjustment = "adjustment"
    loss = "loss"

class CashType(str, enum.Enum):
    entry = "entry"
    exit = "exit"
    withdrawal = "withdrawal"
    correction = "correction"

class ExpenseCategory(str, enum.Enum):
    rent = "rent"
    transport = "transport"
    delivery = "delivery"
    communication = "communication"
    advertising = "advertising"
    packaging = "packaging"
    mobile_money_fees = "mobile_money_fees"
    salary = "salary"
    other = "other"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone = Column(String(20))
    hashed_password = Column(String(200), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.seller)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sales = relationship("Sale", back_populates="seller")

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    icon = Column(String(50))
    cover_image = Column(String(200))
    is_active = Column(Boolean, default=True)
    products = relationship("Product", back_populates="category")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category_id = Column(Integer, ForeignKey("categories.id"))
    purchase_price = Column(Float, nullable=False, default=0)
    selling_price = Column(Float, nullable=False)
    stock_quantity = Column(Integer, default=0)
    low_stock_threshold = Column(Integer, default=5)
    supplier = Column(String(200))
    entry_date = Column(Date)
    expiry_date = Column(Date)
    image = Column(String(200))
    status = Column(Enum(ProductStatus), default=ProductStatus.available)
    usage_instructions = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    category = relationship("Category", back_populates="products")
    stock_movements = relationship("StockMovement", back_populates="product")
    sale_items = relationship("SaleItem", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")

    @property
    def margin_percent(self):
        if self.selling_price > 0:
            return round(((self.selling_price - self.purchase_price) / self.selling_price) * 100, 2)
        return 0

class StockMovement(Base):
    __tablename__ = "stock_movements"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    movement_type = Column(Enum(StockMovementType))
    quantity = Column(Integer, nullable=False)
    reason = Column(String(300))
    reference = Column(String(100))
    unit_cost = Column(Float)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    product = relationship("Product", back_populates="stock_movements")

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, index=True)
    email = Column(String(100))
    address = Column(String(300))
    city = Column(String(100))
    notes = Column(Text)
    loyalty_points = Column(Integer, default=0)
    credit_balance = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sales = relationship("Sale", back_populates="customer")
    orders = relationship("Order", back_populates="customer")
    reminders = relationship("Reminder", back_populates="customer")
    conversations = relationship("Conversation", back_populates="customer")

class Sale(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    seller_id = Column(Integer, ForeignKey("users.id"))
    total_amount = Column(Float, nullable=False)
    total_cost = Column(Float, default=0)
    discount = Column(Float, default=0)
    payment_method = Column(Enum(PaymentMethod), default=PaymentMethod.cash)
    amount_paid = Column(Float, default=0)
    credit_amount = Column(Float, default=0)
    notes = Column(Text)
    receipt_number = Column(String(50), unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    customer = relationship("Customer", back_populates="sales")
    seller = relationship("User", back_populates="sales")
    items = relationship("SaleItem", back_populates="sale")
    payments = relationship("Payment", back_populates="sale")

    @property
    def profit(self):
        return self.total_amount - self.total_cost - self.discount

class SaleItem(Base):
    __tablename__ = "sale_items"
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    unit_cost = Column(Float, default=0)
    subtotal = Column(Float, nullable=False)
    sale = relationship("Sale", back_populates="items")
    product = relationship("Product", back_populates="sale_items")

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"))
    method = Column(Enum(PaymentMethod))
    amount = Column(Float, nullable=False)
    reference = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sale = relationship("Sale", back_populates="payments")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    status = Column(Enum(OrderStatus), default=OrderStatus.pending)
    total_amount = Column(Float, default=0)
    delivery_address = Column(String(300))
    customer_phone = Column(String(20))
    notes = Column(Text)
    order_number = Column(String(50), unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

class CashJournal(Base):
    __tablename__ = "cash_journal"
    id = Column(Integer, primary_key=True, index=True)
    entry_type = Column(Enum(CashType))
    amount = Column(Float, nullable=False)
    description = Column(String(300))
    reference = Column(String(100))
    user_id = Column(Integer, ForeignKey("users.id"))
    balance_after = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(Enum(ExpenseCategory))
    amount = Column(Float, nullable=False)
    description = Column(String(300))
    supplier = Column(String(200))
    receipt_ref = Column(String(100))
    user_id = Column(Integer, ForeignKey("users.id"))
    expense_date = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class RecommendationRule(Base):
    __tablename__ = "recommendation_rules"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200))
    keywords = Column(Text)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    advice = Column(Text)
    health_warning = Column(Text, default="Cette recommandation ne remplace pas l'avis d'un professionnel de santé.")
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Prescription(Base):
    __tablename__ = "prescriptions"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    symptoms = Column(Text)
    recommendations = Column(Text)
    advice = Column(Text)
    health_warning = Column(String(300), default="Cette recommandation ne remplace pas l'avis d'un professionnel de santé.")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Reminder(Base):
    __tablename__ = "reminders"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    message = Column(Text)
    reminder_date = Column(DateTime)
    is_sent = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    customer = relationship("Customer", back_populates="reminders")

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    session_id = Column(String(100))
    message = Column(Text)
    response = Column(Text)
    language = Column(String(20), default="fr")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    customer = relationship("Customer", back_populates="conversations")

class Delivery(Base):
    __tablename__ = "deliveries"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    delivery_person = Column(String(100))
    address = Column(String(300))
    status = Column(String(50), default="pending")
    notes = Column(Text)
    delivered_at = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
