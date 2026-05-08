# Deploiement EVACARE sur VM avec PM2 et Nginx

Ce guide suppose une VM Linux avec `pm2`, `nginx`, `python3`, `python3-venv`, `node`, `npm` deja installes.

## 1. Arborescence conseillee

```bash
/var/www/evacare/
  backend/
  admin-web/
```

## 2. Backend FastAPI

```bash
cd /var/www/evacare/backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
nano .env
python seed.py
pm2 start ecosystem.config.cjs
pm2 save
pm2 startup
```

Variables minimales dans `.env`:

```env
DATABASE_URL=sqlite:///./herbacare.db
SECRET_KEY=mettre-une-cle-longue-et-secrete
ACCESS_TOKEN_EXPIRE_MINUTES=1440
ENVIRONMENT=production
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TIMEOUT_SECONDS=20
CORS_ORIGINS=https://admin.example.com
```

Test local backend sur la VM:

```bash
curl http://127.0.0.1:8623/
```

## 3. Admin React

Par defaut, l'admin peut etre construit a la racine `/` ou sous un sous-chemin comme `/evacare/`.
Dans ton cas, pour `comtratmedia.com/evacare`, construis-le avec `VITE_APP_BASE_PATH=/evacare/`.

```bash
cd /var/www/evacare/admin-web
npm ci
VITE_APP_BASE_PATH=/evacare/ npm run build
```

Les fichiers statiques seront dans `dist/`.

## 4. Nginx

Copier la config fournie:

```bash
sudo cp /var/www/evacare/backend/deploy/nginx/evacare.conf /etc/nginx/sites-available/evacare.conf
sudo ln -s /etc/nginx/sites-available/evacare.conf /etc/nginx/sites-enabled/evacare.conf
sudo nginx -t
sudo systemctl reload nginx
```

Pense a remplacer `admin.example.com` par ton vrai domaine.
Si tu sers l'app sous `comtratmedia.com/evacare`, garde bien le bloc `location /evacare/` de la config fournie.

## 5. SSL

Quand le domaine pointe sur la VM:

```bash
sudo certbot --nginx -d admin.example.com
```

## 6. Mise a jour applicative

```bash
cd /var/www/evacare/backend
git pull
source .venv/bin/activate
pip install -r requirements.txt
pm2 restart evacare-api

cd /var/www/evacare/admin-web
git pull
npm ci
npm run build
```

## 7. Commandes utiles

```bash
pm2 logs evacare-api
pm2 status
pm2 restart evacare-api
sudo nginx -t
sudo systemctl reload nginx
```