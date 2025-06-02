# Pona Health Payment Backend

This is the payment processing backend for Pona Health, optimized for deployment on Railway.

## Features

- AzamPay integration for mobile money payments
- Support for multiple payment methods (Airtel Money, M-Pesa, Tigo Pesa, Halo Pesa)
- Robust amount string formatting handling
- Comprehensive payment method normalization
- Health check endpoint for monitoring

## Deployment Instructions

### Prerequisites

- A Railway account (https://railway.app/)
- GitHub account for repository hosting

### Steps to Deploy

1. Create a new repository on GitHub and push these files to it
2. Create a new project in Railway and select "Deploy from GitHub"
3. Connect your GitHub account and select the repository
4. Set up the following environment variables in Railway:
   - `AZAMPAY_CLIENT_ID`: Your AzamPay client ID
   - `AZAMPAY_SECRET_KEY`: Your AzamPay secret key
   - `AZAMPAY_BASE_URL`: AzamPay API base URL (use sandbox for testing)
   - `CALLBACK_URL`: Your callback URL (your-app-url.railway.app/api/payments/azampay/callback)
   - `PORT`: 5000 (Railway will override this)
   - `DEBUG`: False (set to True for development)
5. Deploy the application

### Testing

Once deployed, you can test the payment flow with:

```
curl -X POST \
  https://your-app-url.railway.app/api/payments/azampay/checkout \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Shaban Busega",
    "phone": "0687511886",
    "amount": "5,000",
    "payment_method": "Airtel Money"
  }'
```

## Frontend Integration

Update your frontend API configuration to point to your new backend URL:

```javascript
// api.js
const API_BASE_URL = 'https://your-app-url.railway.app/api';
```

## API Endpoints

- `GET /api/health` - Health check endpoint
- `POST /api/payments/azampay/checkout` - Process payment through AzamPay
- `POST /api/payments/azampay/callback` - Callback endpoint for AzamPay

## Environment Variables

See `.env.example` for all required environment variables.
