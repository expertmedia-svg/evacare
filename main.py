from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv

from app.core.database import engine, Base
from app.routers import auth, products, categories, stock, sales, customers, orders, cash, expenses, reports, dashboard, ai_assistant, users, payments

load_dotenv()

Base.metadata.create_all(bind=engine)


def get_cors_origins() -> list[str]:
    raw_origins = os.getenv("CORS_ORIGINS", "*")
    if raw_origins.strip() == "*":
        return ["*"]
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


cors_origins = get_cors_origins()

app = FastAPI(
    title="EVACARE",
    description="Plateforme africaine de bien-être et médecine traditionnelle",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(categories.router, prefix="/categories", tags=["Catégories"])
app.include_router(products.router, prefix="/products", tags=["Produits"])
app.include_router(stock.router, prefix="/stock", tags=["Stock"])
app.include_router(customers.router, prefix="/customers", tags=["Clients"])
app.include_router(sales.router, prefix="/sales", tags=["Ventes"])
app.include_router(payments.router, prefix="/payments", tags=["Paiements"])
app.include_router(orders.router, prefix="/orders", tags=["Commandes"])
app.include_router(cash.router, prefix="/cash", tags=["Caisse"])
app.include_router(expenses.router, prefix="/expenses", tags=["Dépenses"])
app.include_router(reports.router, prefix="/reports", tags=["Rapports"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(ai_assistant.router, prefix="/ai", tags=["Assistant IA"])

@app.get("/")
def root():
    return {"message": "EVACARE API", "docs": "/docs", "version": "1.0.0"}
