from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import date, timedelta
from app.core.database import get_db
from app.core.security import oauth2_scheme
from app.models.models import Sale, SaleItem, Product, Customer, Expense, Payment

router = APIRouter()

@router.get("/overview")
def dashboard_overview(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    today = date.today()
    month_start = today.replace(day=1)

    today_sales = db.query(Sale).filter(Sale.created_at >= today).all()
    today_revenue = sum(s.total_amount for s in today_sales)
    today_profit = sum(s.profit for s in today_sales)

    month_sales = db.query(Sale).filter(Sale.created_at >= month_start).all()
    month_revenue = sum(s.total_amount for s in month_sales)
    month_profit = sum(s.profit for s in month_sales)

    low_stock = db.query(Product).filter(Product.stock_quantity <= Product.low_stock_threshold, Product.is_active == True).count()

    popular = db.query(
        Product.name, func.sum(SaleItem.quantity).label("qty")
    ).join(SaleItem).group_by(Product.id).order_by(desc("qty")).limit(5).all()

    week_data = []
    for i in range(7):
        day = today - timedelta(days=6-i)
        day_sales = db.query(Sale).filter(Sale.created_at >= day, Sale.created_at < day + timedelta(days=1)).all()
        week_data.append({"date": str(day), "revenue": sum(s.total_amount for s in day_sales), "count": len(day_sales)})

    payment_dist = db.query(Payment.method, func.sum(Payment.amount)).group_by(Payment.method).all()

    month_expenses = db.query(func.sum(Expense.amount)).filter(Expense.created_at >= month_start).scalar() or 0

    return {
        "today": {"revenue": today_revenue, "profit": today_profit, "sales_count": len(today_sales)},
        "month": {"revenue": month_revenue, "profit": month_profit, "sales_count": len(month_sales), "expenses": month_expenses},
        "low_stock_count": low_stock,
        "popular_products": [{"name": n, "quantity_sold": q} for n, q in popular],
        "week_chart": week_data,
        "payment_distribution": [{"method": m, "total": t} for m, t in payment_dist],
        "total_customers": db.query(Customer).count(),
    }
