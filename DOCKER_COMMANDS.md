# Docker Commands

Start containers:

docker compose up -d

Start with rebuild:

docker compose up --build

Stop containers:

docker compose down

Check running containers:

docker compose ps

Logs:

docker compose logs -f web
docker compose logs -f nginx
docker compose logs -f db

Run migrations:

docker compose exec web python manage.py migrate

Create/reset admin user:

docker compose exec web python manage.py shell -c "from django.contrib.auth import get_user_model; User=get_user_model(); u, _ = User.objects.get_or_create(username='admin', defaults={'email':'admin@classifieds.local'}); u.email='admin@classifieds.local'; u.is_staff=True; u.is_superuser=True; u.set_password('Testpass12345'); u.save(); print('admin ready')"

Admin login:

Username: admin
Password: Testpass12345

Seed demo data:

docker compose exec web python manage.py seed_demo_data

Open app:

http://localhost/
http://localhost/admin/
