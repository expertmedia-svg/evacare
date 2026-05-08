import json
import os
from urllib import error, request

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.core.security import oauth2_scheme
from app.models.models import Product, RecommendationRule, Conversation, Category

router = APIRouter()
HEALTH_WARNING = "Cette recommandation ne remplace pas l'avis d'un professionnel de santé."
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_TIMEOUT_SECONDS = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "20"))

BUILTIN_RULES = [
    {"keywords": ["fatigue", "faiblesse", "énergie", "energie", "épuisement", "epuisement", "fatigué"], "category": "Bien-être homme", "advice": "Reposez-vous suffisamment et prenez ces compléments naturels le matin avec un grand verre d'eau."},
    {"keywords": ["ulcère", "ulcere", "ventre", "brûlure", "brulure", "estomac", "gastrite", "acidité"], "category": "Ulcère", "advice": "Évitez les aliments épicés, prenez les produits 30 minutes avant les repas."},
    {"keywords": ["prostate", "urine", "pipi", "uriner", "miction", "douleur urinaire"], "category": "Prostate", "advice": "Buvez beaucoup d'eau, évitez la caféine et l'alcool."},
    {"keywords": ["diabète", "diabete", "sucre", "glycémie", "glycemie", "insuline"], "category": "Diabète", "advice": "Maintenez une alimentation équilibrée, réduisez les sucres raffinés."},
    {"keywords": ["hémorroïdes", "hemorroïdes", "hemorroide", "saignement anal", "douleur anale"], "category": "Hémorroïdes", "advice": "Mangez des fibres, buvez de l'eau et évitez la constipation."},
    {"keywords": ["fertilité", "fertilite", "grossesse", "conception", "ovulation", "cycle"], "category": "Fertilité", "advice": "Maintenez un mode de vie sain, évitez le stress."},
    {"keywords": ["sexuel", "libido", "érection", "erection", "puissance", "virilité", "virilite"], "category": "Faiblesse sexuelle", "advice": "Adoptez une alimentation riche en zinc et magnésium."},
    {"keywords": ["minceur", "poids", "grossir", "obésité", "obesite", "ventre plat", "maigrir"], "category": "Minceur", "advice": "Associez ces produits à une activité physique régulière et une alimentation équilibrée."},
    {"keywords": ["beauté", "beaute", "peau", "teint", "acné", "acne", "cheveux", "ongles"], "category": "Beauté", "advice": "Appliquez les produits cutanés sur peau propre et sèche."},
    {"keywords": ["infection urinaire", "cystite", "brûlure urinaire", "urine trouble"], "category": "Infection urinaire", "advice": "Buvez beaucoup d'eau et d'infusions de persil."},
    {"keywords": ["typhoïde", "typhoide", "fièvre typhoïde", "salmonelle"], "category": "Typhoïde", "advice": "Consultez immédiatement un professionnel de santé en parallèle."},
    {"keywords": ["femme", "règles", "regles", "menstruation", "ménopause", "menopause"], "category": "Bien-être femme", "advice": "Prenez les produits régulièrement selon le cycle menstruel."},
]

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None
    customer_id: Optional[int] = None
    language: str = "fr"


def _build_rule_based_response(recommended_products, matched_advice):
    if recommended_products:
        advice_text = " ".join(list(set(matched_advice))) if matched_advice else "Prenez les produits selon les instructions."
        response = "Bonjour ! En tant qu'assistant bien-être, voici mes recommandations naturelles basées sur vos symptômes :\n\n"
        for product in recommended_products[:5]:
            response += f"• {product['name']} ({product['category']}) — {product['price']:,.0f} FCFA\n"
        response += f"\n💡 Conseil : {advice_text}"
        response += f"\n\n⚠️ {HEALTH_WARNING}"
        return response

    return (
        "Bonjour ! Je suis votre assistant bien-être HerbaIA. Décrivez-moi vos symptômes ou besoins pour que je vous propose des "
        "solutions naturelles adaptées.\n\nExemples : fatigue, ulcère, prostate, diabète, beauté, minceur...\n\n"
        f"⚠️ {HEALTH_WARNING}"
    )


def _generate_gemini_response(message, language, recommended_products, matched_advice):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    product_lines = []
    for product in recommended_products[:5]:
        usage = product.get("usage") or "Suivre les instructions du vendeur."
        product_lines.append(
            f"- {product['name']} | catégorie: {product['category']} | prix: {product['price']:,.0f} FCFA | usage: {usage}"
        )

    advice_text = " ".join(list(set(matched_advice))) if matched_advice else "Aucun conseil local spécifique."
    response_language = "français" if language.lower().startswith("fr") else language
    prompt = (
        "Tu es HerbaIA, un assistant bien-être pour une boutique de médecine traditionnelle. "
        f"Réponds uniquement en {response_language}. "
        "Tu dois rester prudent: pas de diagnostic médical, pas de promesse de guérison, et rappeler que cela ne remplace pas un professionnel de santé. "
        "Rédige une réponse courte, claire et utile. Si des produits locaux sont fournis, appuie-toi dessus sans inventer d'autres produits. "
        "Si aucun produit n'est fourni, donne une orientation générale et invite l'utilisateur à préciser ses symptômes.\n\n"
        f"Message client: {message}\n"
        f"Conseils locaux: {advice_text}\n"
        "Produits locaux:\n"
        f"{chr(10).join(product_lines) if product_lines else '- Aucun produit local correspondant.'}\n\n"
        f"Termine impérativement par: ⚠️ {HEALTH_WARNING}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 500,
        },
    }
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={api_key}"
    req = request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=GEMINI_TIMEOUT_SECONDS) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except (error.HTTPError, error.URLError, TimeoutError, ValueError):
        return None

    candidates = raw.get("candidates") or []
    if not candidates:
        return None

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "\n".join(part.get("text", "").strip() for part in parts if part.get("text", "")).strip()
    return text or None

@router.post("/chat")
def chat(data: ChatMessage, db: Session = Depends(get_db)):
    msg_lower = data.message.lower()
    matched_categories = []
    matched_advice = []
    for rule in BUILTIN_RULES:
        for kw in rule["keywords"]:
            if kw in msg_lower:
                matched_categories.append(rule["category"])
                matched_advice.append(rule["advice"])
                break
    db_rules = db.query(RecommendationRule).filter(RecommendationRule.is_active == True).all()
    for rule in db_rules:
        keywords = [k.strip().lower() for k in rule.keywords.split(",")]
        for kw in keywords:
            if kw in msg_lower:
                if rule.category_id:
                    cat = db.query(Category).filter(Category.id == rule.category_id).first()
                    if cat:
                        matched_categories.append(cat.name)
                if rule.advice:
                    matched_advice.append(rule.advice)
                break
    recommended_products = []
    if matched_categories:
        for cat_name in list(set(matched_categories)):
            cat = db.query(Category).filter(Category.name == cat_name).first()
            if cat:
                prods = db.query(Product).filter(Product.category_id == cat.id, Product.is_active == True, Product.stock_quantity > 0).limit(3).all()
                for p in prods:
                    recommended_products.append({
                        "id": p.id, "name": p.name, "category": cat_name,
                        "price": p.selling_price, "usage": p.usage_instructions,
                        "in_stock": p.stock_quantity > 0
                    })
    fallback_response = _build_rule_based_response(recommended_products, matched_advice)
    response = _generate_gemini_response(data.message, data.language, recommended_products, matched_advice) or fallback_response
    conv = Conversation(
        customer_id=data.customer_id, session_id=data.session_id,
        message=data.message, response=response, language=data.language
    )
    db.add(conv)
    db.commit()
    return {
        "response": response,
        "recommended_products": recommended_products,
        "health_warning": HEALTH_WARNING,
        "assistant_provider": "gemini" if response != fallback_response else "rules",
    }

@router.get("/rules")
def list_rules(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    rules = db.query(RecommendationRule).all()
    return rules

@router.post("/rules")
def create_rule(rule: dict, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    r = RecommendationRule(**rule)
    db.add(r)
    db.commit()
    return {"message": "Règle créée"}

@router.get("/builtin-rules")
def get_builtin_rules():
    return BUILTIN_RULES
