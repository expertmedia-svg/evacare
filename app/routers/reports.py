from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
import csv, io
from app.core.database import get_db
from app.core.security import oauth2_scheme
from app.models.models import Sale, SaleItem, Product, Expense, Customer

router = APIRouter()

@router.get("/accounting-summary")
def accounting_summary(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    all_sales = db.query(Sale).all()
    total_revenue = sum(s.total_amount for s in all_sales)
    total_cost = sum(s.total_cost for s in all_sales)
    total_profit = sum(s.profit for s in all_sales)
    total_credit = sum(s.credit_amount for s in all_sales)
    total_expenses = db.query(func.sum(Expense.amount)).scalar() or 0

    products = db.query(Product).filter(Product.is_active == True).all()
    stock_value = sum(p.purchase_price * p.stock_quantity for p in products)
    stock_retail = sum(p.selling_price * p.stock_quantity for p in products)

    from datetime import date as d
    today = d.today()
    expired = db.query(Product).filter(Product.expiry_date != None, Product.expiry_date < today, Product.stock_quantity > 0).all()
    expired_value = sum(p.purchase_price * p.stock_quantity for p in expired)

    products_margin = []
    for p in products[:20]:
        sold_q = db.query(func.sum(SaleItem.quantity)).filter(SaleItem.product_id == p.id).scalar() or 0
        sold_rev = db.query(func.sum(SaleItem.subtotal)).filter(SaleItem.product_id == p.id).scalar() or 0
        products_margin.append({"name": p.name, "margin_percent": p.margin_percent, "quantity_sold": sold_q, "revenue": sold_rev})

    return {
        "revenue": total_revenue,
        "total_cost_of_goods": total_cost,
        "gross_profit": total_profit,
        "total_expenses": total_expenses,
        "net_profit": total_profit - total_expenses,
        "client_debt": total_credit,
        "stock_cost_value": stock_value,
        "stock_retail_value": stock_retail,
        "expired_stock_loss": expired_value,
        "global_margin_percent": round((total_profit / total_revenue * 100) if total_revenue > 0 else 0, 2),
        "products_margin": products_margin
    }

@router.get("/exports/sales.csv")
def export_sales_csv(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    sales = db.query(Sale).order_by(Sale.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Reçu", "Client", "Montant", "Bénéfice", "Paiement", "Payé", "Crédit", "Date"])
    for s in sales:
        writer.writerow([s.id, s.receipt_number, s.customer.full_name if s.customer else "Anonyme", s.total_amount, s.profit, s.payment_method, s.amount_paid, s.credit_amount, s.created_at])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=ventes.csv"})

@router.get("/exports/stock.csv")
def export_stock_csv(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    products = db.query(Product).filter(Product.is_active == True).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Nom", "Catégorie", "Prix Achat", "Prix Vente", "Marge%", "Stock", "Seuil", "Statut", "Fournisseur", "Expiration"])
    for p in products:
        writer.writerow([p.id, p.name, p.category.name if p.category else "", p.purchase_price, p.selling_price, p.margin_percent, p.stock_quantity, p.low_stock_threshold, p.status, p.supplier or "", p.expiry_date or ""])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=stock.csv"})

@router.get("/exports/accounting.csv")
def export_accounting_csv(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    summary = accounting_summary(db=db, token=token)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Indicateur", "Valeur (FCFA)"])
    for k, v in summary.items():
        if not isinstance(v, list):
            writer.writerow([k, v])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=bilan.csv"})
