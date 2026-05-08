import json
import os
from urllib import error, request

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.core.security import oauth2_scheme
from app.models.models import Product, RecommendationRule, Conversation, Category, Prescription

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

CLARIFICATION_RULES = {
    "Ulcère": [
        "Depuis quand avez-vous cette douleur ou brûlure d'estomac ?",
        "La douleur apparaît-elle avant les repas, après les repas, ou la nuit ?",
        "Avez-vous aussi des vomissements, des selles noires ou une perte d'appétit ?",
    ],
    "Prostate": [
        "Quel âge avez-vous et depuis quand avez-vous ces troubles urinaires ?",
        "Avez-vous des brûlures, un jet faible ou des réveils fréquents la nuit pour uriner ?",
        "Avez-vous de la fièvre, du sang dans les urines ou une douleur importante ?",
    ],
    "Diabète": [
        "Avez-vous déjà un diagnostic médical de diabète ou une glycémie connue ?",
        "Avez-vous une soif intense, des urines fréquentes ou une grande fatigue ?",
        "Prenez-vous déjà un traitement médical pour la glycémie ?",
    ],
    "Infection urinaire": [
        "Avez-vous des brûlures à la miction ou un besoin fréquent d'uriner ?",
        "Y a-t-il de la fièvre, une douleur lombaire ou des urines troubles ?",
        "Depuis combien de temps ces symptômes ont-ils commencé ?",
    ],
    "Typhoïde": [
        "Avez-vous une forte fièvre, des diarrhées ou des douleurs abdominales importantes ?",
        "Avez-vous déjà fait un test ou consulté un centre de santé ?",
        "Êtes-vous actuellement très faible, déshydraté ou confus ?",
    ],
    "Fertilité": [
        "Depuis combien de temps essayez-vous d'avoir une grossesse ?",
        "Le cycle est-il régulier et existe-t-il déjà un suivi médical ?",
        "Y a-t-il des douleurs pelviennes, infections répétées ou antécédents connus ?",
    ],
}

CATEGORY_KNOWLEDGE = {
    "Diabète": {
        "composition": "Association de plantes traditionnellement utilisées pour le métabolisme du sucre, souvent autour du moringa et d'extraits végétaux amers.",
        "action": "Soutient l'équilibre glycémique et accompagne l'hygiène de vie, sans remplacer un traitement médical.",
    },
    "Ulcère": {
        "composition": "Plantes adoucissantes et digestives utilisées en médecine traditionnelle pour apaiser l'estomac.",
        "action": "Apaise les brûlures digestives, protège la muqueuse gastrique et soutient le confort digestif.",
    },
    "Fertilité": {
        "composition": "Complexe de plantes et nutriments naturels traditionnellement utilisés pour la vitalité reproductive.",
        "action": "Soutient l'équilibre hormonal, la vitalité générale et la préparation de l'organisme.",
    },
    "Faiblesse sexuelle": {
        "composition": "Plantes toniques traditionnelles, souvent associées à des actifs de vitalité.",
        "action": "Soutient l'énergie, la tonicité et la performance sexuelle de façon naturelle.",
    },
    "Hémorroïdes": {
        "composition": "Extraits végétaux apaisants et circulatoires à usage local ou oral selon le produit.",
        "action": "Apaise l'inconfort local, soutient la circulation et réduit l'irritation.",
    },
    "Prostate": {
        "composition": "Plantes traditionnellement utilisées pour le confort urinaire et prostatique.",
        "action": "Aide à améliorer le confort urinaire et soutient le bien-être prostatique.",
    },
    "Minceur": {
        "composition": "Actifs végétaux drainants et digestifs associés à des plantes de soutien minceur.",
        "action": "Accompagne la gestion du poids avec alimentation équilibrée et activité physique.",
    },
    "Beauté": {
        "composition": "Actifs naturels de soin, huiles végétales et extraits de plantes ou de karité selon le produit.",
        "action": "Soutient l'éclat, la nutrition et la protection de la peau ou des cheveux.",
    },
    "Infection urinaire": {
        "composition": "Plantes traditionnellement utilisées pour les voies urinaires et le drainage.",
        "action": "Soutient le confort urinaire et l'élimination, sans remplacer une prise en charge médicale si infection avérée.",
    },
    "Typhoïde": {
        "composition": "Compléments fortifiants naturels de soutien général.",
        "action": "Soutient la récupération générale mais n'est pas un traitement de la typhoïde.",
    },
    "Bien-être femme": {
        "composition": "Plantes traditionnelles de confort féminin et de soutien hormonal naturel.",
        "action": "Accompagne le confort féminin, le cycle et la vitalité générale.",
    },
    "Bien-être homme": {
        "composition": "Plantes tonifiantes et nutritives comme le moringa ou d'autres extraits de vitalité.",
        "action": "Soutient l'énergie, la récupération et le tonus général.",
    },
}

PRODUCT_KNOWLEDGE = {
    "Sirop Diabète Pro": {
        "composition": "Sirop de plantes traditionnelles de soutien glycémique, à dominante végétale.",
        "action": "Aide à accompagner la régulation du sucre et la fatigue associée.",
    },
    "Gélules Moringa Diabète": {
        "composition": "Moringa et actifs végétaux de soutien du métabolisme du sucre.",
        "action": "Soutient l'équilibre glycémique et la vitalité générale.",
    },
    "Tisane Ulcère Guérison": {
        "composition": "Mélange de plantes digestives et apaisantes pour l'estomac.",
        "action": "Apaise les brûlures et soutient le confort gastrique.",
    },
    "Sirop Gastrite Relief": {
        "composition": "Actifs végétaux digestifs sous forme de sirop.",
        "action": "Réduit l'irritation gastrique et améliore le confort digestif.",
    },
    "Pack Fertilité Femme+": {
        "composition": "Association de plantes et nutriments de soutien de la fertilité féminine.",
        "action": "Accompagne la vitalité reproductive et l'équilibre du cycle.",
    },
    "Tisane Prostate+": {
        "composition": "Plantes traditionnellement utilisées pour la prostate et le confort urinaire.",
        "action": "Soutient un meilleur confort urinaire et réduit les gênes fonctionnelles.",
    },
    "Gélules Prostate Max": {
        "composition": "Extraits végétaux concentrés pour le soutien prostatique.",
        "action": "Aide à améliorer le confort de la prostate et la miction.",
    },
    "Gélules Vitalité Homme": {
        "composition": "Plantes toniques naturelles et actifs de vitalité masculine.",
        "action": "Soutient la libido, l'énergie et la tonicité.",
    },
    "Sirop Énergie+": {
        "composition": "Sirop fortifiant à base d'extraits végétaux énergisants.",
        "action": "Aide à réduire la fatigue et soutenir le tonus.",
    },
    "Huile Hémorroïdes Apais": {
        "composition": "Huile végétale enrichie en extraits apaisants et circulatoires.",
        "action": "Apaise localement la douleur, l'irritation et l'inconfort.",
    },
    "Capsules Minceur Rapide": {
        "composition": "Association de plantes de drainage et de soutien minceur.",
        "action": "Accompagne la gestion du poids et la sensation de lourdeur.",
    },
    "Thé Minceur Africain": {
        "composition": "Infusion de plantes digestives et drainantes.",
        "action": "Soutient la digestion et l'accompagnement minceur.",
    },
    "Sérum Éclat Karité": {
        "composition": "Karité et actifs naturels de nutrition cutanée.",
        "action": "Nourrit la peau, améliore l'éclat et aide à l'uniformité du teint.",
    },
    "Savon Teint Naturel": {
        "composition": "Base lavante naturelle avec actifs végétaux de soin cutané.",
        "action": "Nettoie la peau et soutient un teint plus net.",
    },
    "Tisane Infection Urinaire": {
        "composition": "Plantes drainantes et traditionnellement utilisées pour les voies urinaires.",
        "action": "Soutient le confort urinaire et l'élimination.",
    },
    "Pack Tonique Typhoïde": {
        "composition": "Fortifiants naturels et extraits végétaux de soutien général.",
        "action": "Soutient l'organisme en complément d'une prise en charge médicale.",
    },
    "Tisane Bien-être Femme": {
        "composition": "Plantes de confort féminin en infusion.",
        "action": "Soutient l'équilibre féminin et le bien-être général.",
    },
    "Gélules Ménopause Douce": {
        "composition": "Extraits végétaux de soutien du confort de la ménopause.",
        "action": "Aide à mieux vivre les inconforts liés à la ménopause.",
    },
    "Moringa Pur 500g": {
        "composition": "Poudre pure de moringa.",
        "action": "Soutient la vitalité, l'apport nutritionnel et la récupération.",
    },
    "Ginseng Local Énergie": {
        "composition": "Actifs énergisants naturels de type ginseng local.",
        "action": "Stimule l'énergie physique et mentale.",
    },
}

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None
    customer_id: Optional[int] = None
    language: str = "fr"


def _extract_signals(message: str) -> dict:
    msg_lower = message.lower()
    words = [word for word in msg_lower.replace(",", " ").split() if word]
    duration_markers = ["depuis", "jour", "jours", "semaine", "semaines", "mois", "hier", "ce matin"]
    intensity_markers = ["fort", "forte", "grave", "intense", "beaucoup", "très", "tres", "violent"]
    red_flag_markers = ["sang", "fièvre", "fievre", "vomissement", "perte", "malaise", "vertige", "confusion"]
    location_markers = [
        "ventre", "estomac", "bas ventre", "reins", "dos", "poitrine", "tête", "tete", "urine", "anus",
    ]
    return {
        "word_count": len(words),
        "has_duration": any(marker in msg_lower for marker in duration_markers),
        "has_intensity": any(marker in msg_lower for marker in intensity_markers),
        "has_red_flags": any(marker in msg_lower for marker in red_flag_markers),
        "has_location": any(marker in msg_lower for marker in location_markers),
    }


def _build_product_payload(product: Product, category_name: str) -> dict:
    product_knowledge = PRODUCT_KNOWLEDGE.get(product.name, {})
    category_knowledge = CATEGORY_KNOWLEDGE.get(category_name, {})
    composition = (
        product_knowledge.get("composition")
        or (product.description.strip() if product.description else None)
        or category_knowledge.get("composition")
        or "Composition non renseignée dans la fiche produit."
    )
    action = (
        product_knowledge.get("action")
        or category_knowledge.get("action")
        or "Action naturelle de soutien non précisée dans la fiche produit."
    )
    usage = product.usage_instructions or "Suivre les instructions du vendeur."
    return {
        "id": product.id,
        "name": product.name,
        "category": category_name,
        "price": product.selling_price,
        "usage": usage,
        "composition": composition,
        "action": action,
        "in_stock": product.stock_quantity > 0,
    }


def _needs_clarification(message: str, matched_categories: list[str], signals: dict) -> bool:
    if not matched_categories:
        return True
    if signals["has_red_flags"]:
        return False
    detail_score = sum(
        [signals["has_duration"], signals["has_intensity"], signals["has_location"]]
    )
    if any(category in CLARIFICATION_RULES for category in matched_categories):
        return signals["word_count"] < 6 or detail_score < 2
    return signals["word_count"] < 4 or detail_score == 0


def _build_clarification_questions(matched_categories: list[str]) -> list[str]:
    questions = []
    for category in matched_categories[:2]:
        questions.extend(CLARIFICATION_RULES.get(category, []))
    if not questions:
        questions = [
            "Depuis quand avez-vous ce problème ?",
            "Quels sont les symptômes exacts et leur intensité ?",
            "Y a-t-il d'autres signes associés comme fièvre, douleur importante ou fatigue ?",
        ]
    return questions[:3]


def _build_prescription(recommended_products: list[dict], matched_advice: list[str], matched_categories: list[str]) -> dict:
    if not recommended_products:
        return {
            "orientation": "Informations insuffisantes pour une orientation produit fiable.",
            "general_advice": "Merci de répondre aux questions de clarification avant toute recommandation détaillée.",
            "products": [],
        }

    advice_text = " ".join(dict.fromkeys(matched_advice)) if matched_advice else "Suivez le mode d'utilisation indiqué pour chaque produit."
    orientation = f"Orientation bien-être probable: {', '.join(dict.fromkeys(matched_categories))}."
    return {
        "orientation": orientation,
        "general_advice": advice_text,
        "products": [
            {
                "name": product["name"],
                "usage": product["usage"],
                "composition": product["composition"],
                "action": product["action"],
            }
            for product in recommended_products[:5]
        ],
    }


def _format_prescription_text(prescription: dict) -> str:
    if not prescription.get("products"):
        return (
            "Je n'ai pas encore assez d'éléments pour vous proposer une orientation produit fiable. "
            "Merci de répondre d'abord aux questions ci-dessous."
        )

    lines = [prescription["orientation"], "", "Prescription bien-être suggérée :"]
    for product in prescription["products"]:
        lines.extend(
            [
                f"• {product['name']}",
                f"  - Mode d'utilisation : {product['usage']}",
                f"  - Composition : {product['composition']}",
                f"  - Action sur le problème : {product['action']}",
            ]
        )
    lines.extend(["", f"💡 Conseil : {prescription['general_advice']}"])
    return "\n".join(lines)


def _build_clarification_response(questions: list[str], matched_categories: list[str]) -> str:
    orientation = ", ".join(dict.fromkeys(matched_categories)) if matched_categories else "vos symptômes"
    response = (
        f"Je peux vous orienter sur {orientation}, mais il me manque encore des éléments avant de vous faire une prescription bien-être plus précise.\n\n"
        "Merci de répondre à ces questions :\n"
    )
    for index, question in enumerate(questions, start=1):
        response += f"{index}. {question}\n"
    response += f"\n⚠️ {HEALTH_WARNING}"
    return response


def _generate_gemini_response(message, language, recommended_products, matched_advice, needs_clarification, clarifying_questions, prescription):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    product_lines = []
    for product in recommended_products[:5]:
        usage = product.get("usage") or "Suivre les instructions du vendeur."
        composition = product.get("composition") or "Composition non renseignée."
        action = product.get("action") or "Action non renseignée."
        product_lines.append(
            f"- {product['name']} | catégorie: {product['category']} | prix: {product['price']:,.0f} FCFA | usage: {usage} | composition: {composition} | action: {action}"
        )

    advice_text = " ".join(list(set(matched_advice))) if matched_advice else "Aucun conseil local spécifique."
    response_language = "français" if language.lower().startswith("fr") else language
    clarification_block = ""
    if needs_clarification:
        clarification_block = (
            "Avant de recommander précisément, pose d'abord ces questions de clarification à l'utilisateur, une seule réponse structurée suffit :\n"
            + "\n".join([f"- {question}" for question in clarifying_questions])
            + "\n"
        )

    prescription_block = ""
    if prescription.get("products"):
        prescription_block = (
            "Si tu recommandes des produits, donne pour chacun le mode d'utilisation, la composition et l'action sur le problème. "
            "Présente cela comme une prescription bien-être prudente, pas comme un acte médical.\n"
        )

    prompt = (
        "Tu es EvaIA, un assistant bien-être pour une boutique de médecine traditionnelle. "
        f"Réponds uniquement en {response_language}. "
        "Tu dois rester prudent: pas de diagnostic médical, pas de promesse de guérison, et rappeler que cela ne remplace pas un professionnel de santé. "
        "Tu peux donner une orientation bien-être probable, mais jamais un diagnostic médical certain. "
        "S'il manque des éléments, pose des questions ciblées avant de conclure. "
        "Si des produits locaux sont fournis, appuie-toi uniquement dessus sans inventer d'autres produits. "
        f"{clarification_block}"
        f"{prescription_block}"
        "Rédige une réponse claire, structurée et utile.\n\n"
        f"Message client: {message}\n"
        f"Conseils locaux: {advice_text}\n"
        f"Prescription structurée disponible: {json.dumps(prescription, ensure_ascii=False)}\n"
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
    signals = _extract_signals(data.message)
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
                    recommended_products.append(_build_product_payload(p, cat_name))

    needs_clarification = _needs_clarification(data.message, matched_categories, signals)
    clarifying_questions = _build_clarification_questions(matched_categories)
    prescription = _build_prescription(recommended_products, matched_advice, matched_categories)

    if needs_clarification:
        fallback_response = _build_clarification_response(clarifying_questions, matched_categories)
    else:
        fallback_response = _format_prescription_text(prescription) + f"\n\n⚠️ {HEALTH_WARNING}"

    response = (
        _generate_gemini_response(
            data.message,
            data.language,
            recommended_products,
            matched_advice,
            needs_clarification,
            clarifying_questions,
            prescription,
        )
        or fallback_response
    )

    conv = Conversation(
        customer_id=data.customer_id, session_id=data.session_id,
        message=data.message, response=response, language=data.language
    )
    db.add(conv)

    if prescription.get("products"):
        db.add(
            Prescription(
                customer_id=data.customer_id,
                symptoms=data.message,
                recommendations=_format_prescription_text(prescription),
                advice=prescription.get("general_advice"),
                health_warning=HEALTH_WARNING,
            )
        )

    db.commit()
    return {
        "response": response,
        "recommended_products": recommended_products,
        "health_warning": HEALTH_WARNING,
        "needs_clarification": needs_clarification,
        "clarifying_questions": clarifying_questions if needs_clarification else [],
        "assessment": prescription.get("orientation"),
        "prescription": prescription,
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
