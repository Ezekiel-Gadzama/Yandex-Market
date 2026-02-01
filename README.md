# Yandex Market Digital Products Manager

A complete ecosystem for managing digital products on Yandex Market, including product management, order fulfillment, email templates, and comprehensive analytics.

## Features

- **Product Management**: Add, edit, delete, and manage digital and physical products
- **Order Processing**: Automatically fulfill digital product orders with activation codes
- **Email Templates**: Customizable email templates for activation code delivery
- **Yandex Market Integration**: Sync products and orders with Yandex Market API
- **Dashboard Analytics**: Track sales, revenue, profit, and top-selling products
- **Activation Key Management**: Generate and track activation keys for digital products
- **Profit Tracking**: Automatic calculation of profit and profit margins

## Project Structure

```
.
├── backend/          # FastAPI backend
│   ├── app/
│   │   ├── models.py          # Database models
│   │   ├── schemas.py         # Pydantic schemas
│   │   ├── routers/           # API routes
│   │   ├── services/          # Business logic
│   │   └── main.py           # FastAPI application
│   └── requirements.txt
├── frontend/        # React + TypeScript frontend
│   ├── src/
│   │   ├── pages/            # Page components
│   │   ├── components/       # Reusable components
│   │   └── api/             # API client
│   └── package.json
└── README.md
```

## Setup Instructions

### Option 1: Docker (Recommended)

**Quick Start:**
```bash
# 1. Create .env file
cp .env.example .env
# Edit .env and add your Yandex Market API credentials

# 2. Start with Docker Compose
docker-compose up -d

# 3. Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

For development with hot-reload:
```bash
docker-compose -f docker-compose.dev.yml up -d
```

See [DOCKER.md](DOCKER.md) for detailed Docker instructions.

### Option 2: Local Development

#### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the backend directory:
```bash
cp .env.example .env
```

5. Configure your `.env` file with your Yandex Market API credentials:
```env
YANDEX_MARKET_API_TOKEN=your_api_token
YANDEX_MARKET_CAMPAIGN_ID=your_campaign_id
YANDEX_MARKET_API_URL=https://api.partner.market.yandex.ru

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=noreply@market.yandex.ru
```

6. Run the backend server:
```bash
uvicorn app.main:app --reload --port 8000
```

#### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Usage

### Adding Products

1. Navigate to the Products page
2. Click "Add Product"
3. Fill in the product details:
   - Name, description, type (digital/physical)
   - Cost price (what you pay to supplier)
   - Selling price (price on Yandex Market)
   - Supplier URL and name
4. Click "Create"

### Uploading Products to Yandex Market

1. Go to Products page
2. Click the upload icon (📤) next to a product
3. The product will be uploaded to Yandex Market via API

### Generating Activation Keys

1. For digital products, click the key icon (🔑) to generate activation keys
2. Keys are automatically assigned to orders when fulfilled

### Processing Orders

1. Orders can be synced from Yandex Market in Settings
2. On the Orders page:
   - Click the refresh icon to fulfill an order (assigns activation key)
   - Click the mail icon to send activation email to customer
   - Click the checkmark to mark order as completed

### Email Templates

1. Go to Email Templates page
2. Create templates with placeholders:
   - `{order_number}` - Order ID
   - `{product_name}` - Product name
   - `{activation_code}` - Activation code
   - `{expiry_date}` - Expiry date
   - `{customer_name}` - Customer name
   - `{instructions}` - Activation instructions

### Syncing with Yandex Market

1. Go to Settings page
2. Click "Sync Products" to sync products from Yandex Market
3. Click "Sync Orders" to sync orders from Yandex Market

## Yandex Market API Integration

The system integrates with Yandex Market Partner API. You need to:

1. Register as a partner on Yandex Market
2. Get your API credentials (Client ID, Client Secret, Campaign ID)
3. Implement OAuth 2.0 flow (currently placeholder in `yandex_api.py`)
4. Configure webhooks to receive order notifications

## Database

The system uses **PostgreSQL** as the database. When running with Docker, PostgreSQL is automatically set up as a service. The database is automatically initialized on first run.

## Future Enhancements

- Physical product shipping management
- Inventory tracking
- Multi-currency support
- Advanced reporting
- Automated order processing
- Webhook integration for real-time order updates

## License

MIT
