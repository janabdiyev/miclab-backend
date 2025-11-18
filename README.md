# MicLab Solo - Backend API

Django REST Framework backend for the MicLab Solo karaoke app.

## Quick Start

### Development Mode (Local)

```bash
# Clone and setup
cd miclab-backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

Access:
- **Admin Panel**: http://localhost:8000/admin/
- **API Root**: http://localhost:8000/api/
- **API Docs**: http://localhost:8000/api/ (DRF browsable API)

---

## Admin Login

```
Email: canabdiyev@gmail.com
Username: admin
Password: admin123
```

---

## API Endpoints

### Authentication

#### Register New User (5-day free trial)
```
POST /api/auth/register/

{
  "email": "user@example.com",
  "password": "secure_password",
  "username": "optional_username"
}

Response:
{
  "user_id": 1,
  "email": "user@example.com",
  "token": "abc123token",
  "trial_end_date": "2025-11-12T06:33:00Z",
  "subscription_type": "free"
}
```

#### Login
```
POST /api/auth/login/

{
  "email": "user@example.com",
  "password": "secure_password"
}

Response:
{
  "user_id": 1,
  "email": "user@example.com",
  "token": "abc123token",
  "subscription_type": "free",
  "trial_end_date": "2025-11-12T06:33:00Z"
}
```

#### Get Current User Profile
```
GET /api/auth/me/
Header: Authorization: Token abc123token

Response:
{
  "user_id": 1,
  "email": "user@example.com",
  "username": "username",
  "subscription_type": "free",
  "trial_start_date": "2025-11-07T06:33:00Z",
  "trial_end_date": "2025-11-12T06:33:00Z"
}
```

#### Check User Access (Free/Premium)
```
GET /api/auth/check_access/
Header: Authorization: Token abc123token

Response:
{
  "access": true,
  "reason": "Trial (5 days left)"
}
```

#### Handle IAP Purchase
```
POST /api/auth/purchase/
Header: Authorization: Token abc123token

{
  "product_id": "com.miclab.premium.monthly",
  "receipt": "receipt_data_from_apple_or_google",
  "platform": "ios"
}

Response:
{
  "subscription_type": "premium_monthly",
  "subscription_end_date": "2025-12-07T06:33:00Z"
}
```

---

### Songs

#### List All Songs
```
GET /api/songs/?page=1

Response:
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "Saba Boldy",
      "artist": "Agamyrat Kurt",
      "category": {
        "id": 1,
        "name": "Traditional",
        "slug": "traditional"
      },
      "thumbnail": null,
      "duration": 341,
      "is_favorite": false
    }
  ]
}
```

#### Get Song Details (with lyrics & audio)
```
GET /api/songs/1/
Header: Authorization: Token abc123token (optional)

Response:
{
  "id": 1,
  "title": "Saba Boldy",
  "artist": "Agamyrat Kurt",
  "category": {
    "id": 1,
    "name": "Traditional",
    "slug": "traditional"
  },
  "thumbnail": null,
  "duration": 341,
  "audio_url": "http://localhost:8000/media/songs/audio/...",
  "lyrics": "[ar:Agamyrat Kurt]\n[ti:Saba Boldy]\n[00:41.31] Senem oglan menem oglan\n...",
  "is_favorite": false,
  "created_at": "2025-11-07T06:33:00Z"
}
```

#### Search Songs
```
GET /api/songs/search/?q=kurt

Response: [array of songs matching query]
```

#### Filter by Category
```
GET /api/songs/by_category/?category=traditional

Response: [array of songs in category]
```

---

### Categories

#### List All Categories
```
GET /api/categories/

Response:
{
  "count": 1,
  "results": [
    {
      "id": 1,
      "name": "Traditional",
      "slug": "traditional"
    }
  ]
}
```

---

### Favorites

#### List User Favorites
```
GET /api/favorites/
Header: Authorization: Token abc123token

Response:
{
  "count": 1,
  "results": [
    {
      "id": 1,
      "song": { ...song object... },
      "added_at": "2025-11-07T06:33:00Z"
    }
  ]
}
```

#### Add/Remove Favorite
```
POST /api/favorites/toggle/
Header: Authorization: Token abc123token

{
  "song_id": 1
}

Response:
{
  "detail": "Added to favorites"
}
```

---

### User Profile

#### Get Profile Info
```
GET /api/profile/my_profile/
Header: Authorization: Token abc123token

Response:
{
  "subscription_type": "free",
  "trial_start_date": "2025-11-07T06:33:00Z",
  "trial_end_date": "2025-11-12T06:33:00Z",
  "subscription_status": "Free trial - 5 days left"
}
```

---

## Database Models

### Song
```
- id (PK)
- title (string)
- artist (string)
- category (FK)
- audio_file (file)
- lyrics_file (file)
- thumbnail (image, optional)
- duration (int, seconds)
- is_active (bool)
- created_at, updated_at
```

### Category
```
- id (PK)
- name (string)
- slug (string, unique)
- created_at
```

### UserProfile
```
- user (OneToOne FK)
- subscription_type (free/premium_monthly/premium_yearly)
- trial_start_date, trial_end_date
- subscription_start_date, subscription_end_date
- stripe_customer_id, stripe_subscription_id
- created_at, updated_at
```

### Favorite
```
- user (FK)
- song (FK)
- added_at
- unique_together: (user, song)
```

---

## Admin Panel Usage

1. Go to http://localhost:8000/admin/
2. Login with admin credentials
3. **Add Songs**: Songs → Add Song
   - Upload MP3 and .LRC files
   - Set duration in seconds
4. **Manage Categories**: Categories → Add Category
5. **View Users**: Users / User Profiles

---

## Pricing Configuration

Update in `auth_app/views.py` (purchase endpoint):

```python
PRICING = {
    'com.miclab.premium.monthly': {
        'type': 'premium_monthly',
        'price': '$5.99',
        'duration': 30  # days
    },
    'com.miclab.premium.yearly': {
        'type': 'premium_yearly',
        'price': '$39.99',
        'duration': 365  # days
    }
}
```

---

## Next Steps (iOS Development)

The backend is ready for iOS integration. The iOS app will:

1. **Register/Login** → `POST /api/auth/register/` or `POST /api/auth/login/`
2. **Fetch Songs** → `GET /api/songs/`
3. **Get Song Details** → `GET /api/songs/{id}/` (includes lyrics & audio URL)
4. **Handle Favorites** → `POST /api/favorites/toggle/`
5. **Process IAP** → `POST /api/auth/purchase/`
6. **Check Access** → `GET /api/auth/check_access/`

---

## Deployment

### Docker

```bash
docker-compose up
```

### Production

1. Use PostgreSQL instead of SQLite
2. Set `DEBUG = False`
3. Configure proper `ALLOWED_HOSTS`
4. Use environment variables for secrets
5. Set up Stripe webhook verification for IAP
6. Use Nginx + Gunicorn for serving

---

## Support

For issues, reach out to: canabdiyev@gmail.com
