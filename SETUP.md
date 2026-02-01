# Setup Guide

## Quick Start

### Prerequisites

- Python 3.8+ installed
- Node.js 16+ and npm installed
- Yandex Market Partner account with API access

### Step 1: Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```bash
# Copy the example file
copy .env.example .env  # Windows
cp .env.example .env    # Linux/Mac
```

5. Edit `.env` and add your Yandex Market API credentials:
```env
YANDEX_MARKET_API_TOKEN=your_api_token
YANDEX_MARKET_CAMPAIGN_ID=your_actual_campaign_id
```

6. Start backend server:
```bash
# Windows
python -m uvicorn app.main:app --reload --port 8000

# Linux/Mac
uvicorn app.main:app --reload --port 8000
```

Or use the startup script:
```bash
# Windows
..\start_backend.bat

# Linux/Mac
bash ../start_backend.sh
```

Backend will be available at `http://localhost:8000`

### Step 2: Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm run dev
```

Or use the startup script:
```bash
# Windows
..\start_frontend.bat

# Linux/Mac
bash ../start_frontend.sh
```

Frontend will be available at `http://localhost:3000`

## Configuration

### Yandex Market API Setup

1. Log in to your Yandex Market Partner account: https://partner.market.yandex.ru/
2. Navigate to **API and modules** → **Authorization tokens**
3. Click **"Create a new token"**
4. Give it a name and set appropriate permissions
5. Copy the token (it's only shown once!)
6. Get your Campaign ID from the dashboard (it's in the URL: `/campaigns/XXXXX`)
7. Add these to your `.env` file

### Email Configuration (Optional)

To send activation emails, configure SMTP in `.env`:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=noreply@market.yandex.ru
```

For Gmail, you'll need to:
1. Enable 2-factor authentication
2. Generate an App Password
3. Use the App Password in `SMTP_PASSWORD`

## Usage Workflow

### 1. Add Products

1. Go to Products page
2. Click "Add Product"
3. Fill in:
   - Product name and description
   - Type (Digital/Physical)
   - Cost price (what you pay supplier)
   - Selling price (Yandex Market price)
   - Supplier URL and name
4. Save

### 2. Upload to Yandex Market

1. In Products page, click upload icon (📤) next to product
2. Product will be uploaded via API
3. Product will show "Synced" status

### 3. Generate Activation Keys (Digital Products)

1. Click key icon (🔑) next to digital product
2. System generates 10 activation keys
3. Keys are automatically assigned to orders

### 4. Process Orders

**Option A: Manual Sync**
1. Go to Settings
2. Click "Sync Orders"
3. Orders appear in Orders page

**Option B: Webhook (Recommended)**
1. Configure webhook URL in Yandex Market: `http://your-domain.com/api/webhooks/yandex-market/orders`
2. Orders are automatically created when received

**Fulfill Order:**
1. Go to Orders page
2. Click refresh icon (🔄) to fulfill (assigns activation key)
3. Click mail icon (✉️) to send activation email
4. Click checkmark (✓) to mark as completed

### 5. Email Templates

1. Go to Email Templates page
2. Create/edit templates with placeholders:
   - `{order_number}` - Order ID
   - `{product_name}` - Product name
   - `{activation_code}` - Activation code
   - `{expiry_date}` - Expiry date
   - `{customer_name}` - Customer name
   - `{instructions}` - Custom instructions

## Database

The system uses **PostgreSQL** as the database.

**With Docker:**
PostgreSQL is automatically configured. The database credentials can be set in `.env`:
```env
POSTGRES_USER=yandex_user
POSTGRES_PASSWORD=yandex_password
POSTGRES_DB=yandex_market
```

**Local Development:**
1. Install PostgreSQL
2. Create database:
```bash
createdb yandex_market
```
3. Update `backend/.env`:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/yandex_market
```

## Troubleshooting

### Backend won't start
- Check Python version: `python --version` (needs 3.8+)
- Check virtual environment is activated
- Check all dependencies installed: `pip install -r requirements.txt`

### Frontend won't start
- Check Node.js version: `node --version` (needs 16+)
- Delete `node_modules` and reinstall: `rm -rf node_modules && npm install`

### API errors
- Check `.env` file has correct Yandex Market credentials
- Verify Yandex Market API is accessible
- Check backend logs for detailed error messages

### Email not sending
- Verify SMTP credentials in `.env`
- For Gmail, ensure App Password is used (not regular password)
- Check firewall allows SMTP connections

## Production Deployment

### Backend
1. Set `DATABASE_URL` to PostgreSQL
2. Set proper `SECRET_KEY` in `.env`
3. Use production WSGI server (gunicorn, uvicorn workers)
4. Set up reverse proxy (nginx)
5. Configure SSL certificates

### Frontend
1. Build production bundle: `npm run build`
2. Serve static files with nginx or similar
3. Configure API proxy

### Webhooks
1. Use HTTPS for webhook endpoint
2. Implement webhook signature verification
3. Set up proper error handling and logging

## Support

For issues or questions:
1. Check the README.md
2. Review Yandex Market API documentation
3. Check application logs
