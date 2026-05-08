"""
Seed script: python seed.py
"""
import sys
sys.path.append(".")

from app.core.database import SessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.models import *
from datetime import date, timedelta
import random

Base.metadata.create_all(bind=engine)
db = SessionLocal()

print("🌱 Seeding HERBACARE AI database...")

# Clear existing
for model in [Conversation, Reminder, Prescription, RecommendationRule, Delivery, OrderItem, Order, Payment, SaleItem, Sale, StockMovement, Expense, CashJournal, Customer, Product, Category, User]:
    db.query(model).delete()
db.commit()

# USERS
owner = User(full_name="Abdoulaye Diallo", email="owner@herbacare.ai", phone="+22670000001", hashed_password=get_password_hash("password123"), role=UserRole.owner)
seller = User(full_name="Mariama Traoré", email="seller@herbacare.ai", phone="+22670000002", hashed_password=get_password_hash("password123"), role=UserRole.seller)
manager = User(full_name="Ibrahim Sawadogo", email="manager@herbacare.ai", phone="+22670000003", hashed_password=get_password_hash("password123"), role=UserRole.manager)
db.add_all([owner, seller, manager])
db.commit()
print("✅ Users créés")

# CATEGORIES
categories_data = [
    ("Diabète", "Produits naturels pour la gestion du diabète", "🩺"),
    ("Ulcère", "Soins naturels pour l'ulcère gastrique", "🌿"),
    ("Fertilité", "Accompagnement naturel de la fertilité", "🌺"),
    ("Faiblesse sexuelle", "Tonifiants naturels pour la vitalité", "💪"),
    ("Hémorroïdes", "Soins naturels des hémorroïdes", "🍃"),
    ("Prostate", "Bien-être de la prostate", "🫀"),
    ("Minceur", "Accompagnement minceur naturel", "⚖️"),
    ("Beauté", "Cosmétiques naturels africains", "✨"),
    ("Infection urinaire", "Soins naturels des voies urinaires", "💧"),
    ("Typhoïde", "Compléments naturels fortifiants", "🌡️"),
    ("Bien-être femme", "Santé naturelle de la femme", "🌸"),
    ("Bien-être homme", "Vitalité naturelle de l'homme", "🧘"),
]
cats = {}
for name, desc, icon in categories_data:
    c = Category(name=name, description=desc, icon=icon)
    db.add(c)
    db.flush()
    cats[name] = c.id
db.commit()
print("✅ Catégories créées")

# PRODUCTS
products_data = [
    ("Sirop Diabète Pro", "Diabète", 2200, 4500, 25, "Phyto Burkina", "Prendre 2 cuillères à soupe matin et soir avant les repas."),
    ("Gélules Moringa Diabète", "Diabète", 1800, 3800, 30, "NaturAfrica", "2 gélules matin et soir avec de l'eau."),
    ("Tisane Ulcère Guérison", "Ulcère", 1500, 3200, 20, "Phyto Burkina", "Infuser 2 sachets dans 500ml d'eau chaude, 2 fois par jour."),
    ("Sirop Gastrite Relief", "Ulcère", 2000, 4200, 15, "HerboMali", "1 cuillère à soupe avant chaque repas."),
    ("Pack Fertilité Femme+", "Fertilité", 4500, 9800, 18, "NaturAfrica", "1 comprimé matin et soir avec un grand verre d'eau."),
    ("Tisane Prostate+", "Prostate", 3000, 7200, 8, "Phyto Burkina", "1 sachet dans 250ml d'eau chaude, 2 fois par jour."),
    ("Gélules Prostate Max", "Prostate", 3500, 8500, 6, "HerboMali", "2 gélules matin et soir."),
    ("Gélules Vitalité Homme", "Faiblesse sexuelle", 3200, 7500, 22, "NaturAfrica", "2 gélules le soir avec un verre d'eau tiède."),
    ("Sirop Énergie+", "Bien-être homme", 2500, 5500, 35, "Phyto Burkina", "2 cuillères le matin à jeun."),
    ("Huile Hémorroïdes Apais", "Hémorroïdes", 2800, 6000, 12, "HerboMali", "Appliquer localement 2 fois par jour."),
    ("Capsules Minceur Rapide", "Minceur", 2000, 4800, 28, "NaturAfrica", "2 capsules 30 min avant les repas principaux."),
    ("Thé Minceur Africain", "Minceur", 1200, 2800, 40, "Phyto Burkina", "1 sachet dans 250ml d'eau chaude après chaque repas."),
    ("Sérum Éclat Karité", "Beauté", 1800, 3500, 30, "BeautyNat", "Appliquer le soir sur peau propre et sèche."),
    ("Savon Teint Naturel", "Beauté", 800, 1800, 50, "BeautyNat", "Utiliser matin et soir pour laver le visage."),
    ("Tisane Infection Urinaire", "Infection urinaire", 1400, 3000, 18, "Phyto Burkina", "2 sachets par jour dans 500ml d'eau chaude."),
    ("Pack Tonique Typhoïde", "Typhoïde", 3500, 8000, 10, "HerboMali", "Selon prescription du vendeur."),
    ("Tisane Bien-être Femme", "Bien-être femme", 1600, 3500, 25, "NaturAfrica", "1 sachet le matin à jeun."),
    ("Gélules Ménopause Douce", "Bien-être femme", 3000, 6500, 15, "HerboMali", "2 gélules matin et soir."),
    ("Moringa Pur 500g", "Bien-être homme", 1200, 2800, 4, "Phyto Burkina", "1 cuillère à café dans un verre d'eau ou de jus matin et soir."),
    ("Ginseng Local Énergie", "Bien-être homme", 2800, 6000, 20, "NaturAfrica", "2 gélules le matin avec de l'eau."),
]

prods = {}
for name, cat_name, purchase, selling, stock, supplier, usage in products_data:
    expiry = date.today() + timedelta(days=random.randint(60, 730))
    p = Product(
        name=name, category_id=cats[cat_name],
        purchase_price=purchase, selling_price=selling,
        stock_quantity=stock, supplier=supplier,
        entry_date=date.today(), expiry_date=expiry,
        usage_instructions=usage, low_stock_threshold=5,
        status=ProductStatus.available if stock > 0 else ProductStatus.rupture
    )
    db.add(p)
    db.flush()
    prods[name] = p
    if stock > 0:
        mov = StockMovement(product_id=p.id, movement_type=StockMovementType.entry, quantity=stock, reason="Stock initial")
        db.add(mov)
db.commit()
print("✅ Produits créés")

# CUSTOMERS
customers_data = [
    ("Aminata Koné", "+22676111001", "Ouagadougou"),
    ("Ibrahim Sawadogo", "+22670222002", "Bobo-Dioulasso"),
    ("Fatou Diallo", "+22665333003", "Ouagadougou"),
    ("Mamadou Traoré", "+22671444004", "Koudougou"),
    ("Mariam Compaoré", "+22672555005", "Ouagadougou"),
    ("Seydou Ouédraogo", "+22673666006", "Banfora"),
    ("Awa Sankara", "+22674777007", "Ouagadougou"),
    ("Boubacar Barry", "+22675888008", "Fada N'Gourma"),
    ("Kadiatou Bah", "+22676999009", "Ouagadougou"),
    ("Moussa Coulibaly", "+22677000010", "Dédougou"),
]
cust_list = []
for name, phone, city in customers_data:
    c = Customer(full_name=name, phone=phone, city=city)
    db.add(c)
    db.flush()
    cust_list.append(c)
db.commit()
print("✅ Clients créés")

# SALES with items
sale_scenarios = [
    (cust_list[0], [("Sirop Diabète Pro", 2), ("Moringa Pur 500g", 1)], "cash"),
    (cust_list[1], [("Tisane Prostate+", 1), ("Gélules Prostate Max", 1)], "orange_money"),
    (cust_list[2], [("Pack Fertilité Femme+", 1), ("Tisane Bien-être Femme", 2)], "wave"),
    (cust_list[3], [("Gélules Vitalité Homme", 2)], "cash"),
    (cust_list[4], [("Sérum Éclat Karité", 1), ("Savon Teint Naturel", 2)], "moov_money"),
    (cust_list[5], [("Capsules Minceur Rapide", 1), ("Thé Minceur Africain", 2)], "cash"),
    (cust_list[6], [("Tisane Ulcère Guérison", 2), ("Sirop Gastrite Relief", 1)], "orange_money"),
    (cust_list[7], [("Sirop Énergie+", 1), ("Ginseng Local Énergie", 1)], "wave"),
]

import random, string
from datetime import datetime

for customer, items_data, payment in sale_scenarios:
    total = 0
    total_cost = 0
    sale_items_to_add = []
    for pname, qty in items_data:
        p = prods.get(pname)
        if p and p.stock_quantity >= qty:
            sub = p.selling_price * qty
            total += sub
            total_cost += p.purchase_price * qty
            sale_items_to_add.append((p, qty, p.selling_price, sub, p.purchase_price))
    if not sale_items_to_add:
        continue
    receipt = "RC" + datetime.now().strftime("%Y%m%d") + "".join(random.choices(string.digits, k=4))
    sale = Sale(
        customer_id=customer.id, seller_id=seller.id,
        total_amount=total, total_cost=total_cost,
        payment_method=payment, amount_paid=total,
        receipt_number=receipt
    )
    db.add(sale)
    db.flush()
    for p, qty, price, sub, cost in sale_items_to_add:
        si = SaleItem(sale_id=sale.id, product_id=p.id, quantity=qty, unit_price=price, unit_cost=cost, subtotal=sub)
        db.add(si)
        p.stock_quantity -= qty
        mov = StockMovement(product_id=p.id, movement_type=StockMovementType.exit, quantity=qty, reason=f"Vente {receipt}")
        db.add(mov)
    pmt = Payment(sale_id=sale.id, method=payment, amount=total)
    db.add(pmt)
    cash_e = CashJournal(entry_type=CashType.entry, amount=total, description=f"Vente {receipt}", user_id=seller.id)
    db.add(cash_e)

db.commit()
print("✅ Ventes créées")

# EXPENSES
expenses_data = [
    (ExpenseCategory.rent, 50000, "Loyer boutique janvier"),
    (ExpenseCategory.transport, 15000, "Transport livraisons semaine"),
    (ExpenseCategory.communication, 5000, "Crédit téléphone"),
    (ExpenseCategory.packaging, 8000, "Sacs et emballages"),
    (ExpenseCategory.advertising, 20000, "Publicité Facebook"),
    (ExpenseCategory.salary, 75000, "Salaire vendeur"),
    (ExpenseCategory.mobile_money_fees, 3500, "Frais Mobile Money du mois"),
]
for cat, amount, desc in expenses_data:
    e = Expense(category=cat, amount=amount, description=desc, expense_date=date.today(), user_id=owner.id)
    db.add(e)
db.commit()
print("✅ Dépenses créées")

# RECOMMENDATION RULES
rules = [
    RecommendationRule(name="Fatigue générale", keywords="fatigue,faiblesse,épuisement,manque énergie", category_id=cats["Bien-être homme"], advice="Prenez les tonifiants naturels le matin à jeun."),
    RecommendationRule(name="Problèmes digestifs", keywords="ulcère,brûlure estomac,gastrite,ventre", category_id=cats["Ulcère"], advice="Évitez les épices et prenez avant les repas."),
    RecommendationRule(name="Santé prostate", keywords="prostate,urine,miction difficile", category_id=cats["Prostate"], advice="Buvez 2L d'eau par jour."),
]
for r in rules:
    db.add(r)
db.commit()
print("✅ Règles IA créées")

# Commit final
db.close()
print("\n🎉 Base de données initialisée avec succès !")
print("\n📋 COMPTES DE TEST:")
print("  owner@herbacare.ai  / password123  (Propriétaire)")
print("  seller@herbacare.ai / password123  (Vendeur)")
print("  manager@herbacare.ai / password123 (Gestionnaire)")
print("\n🚀 Backend: http://localhost:8000")
print("📚 Docs API: http://localhost:8000/docs")
