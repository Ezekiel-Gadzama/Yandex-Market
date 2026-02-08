# 🚀 Apply All Yandex Market Fixes - Quick Start

## ⚡ Quick Fix (2 Minutes)

Run these commands in order:

```bash
# 1. Run database migration
docker-compose exec -T postgres psql -U yandex_user -d yandex_market < backend/migrations/add_new_product_fields.sql

# 2. Restart backend to apply authentication fixes
docker-compose restart backend

# 3. Test authentication
docker-compose exec backend python test_yandex_auth.py

# 4. Watch logs for confirmation
docker-compose logs -f backend
```

**Expected Result:** No more 401/403 errors, API calls succeed

---

## 🔍 What Was Fixed

### Authentication Error (401)
- ✅ Fixed: Application token `ACMA:...` now uses `Bearer` header
- ✅ Fixed: All endpoints use `/v2/campaigns/...` format
- ✅ Added: Detailed error logging

### Missing Form Fields
- ✅ Added: Product Model Number (SKU) * - Required
- ✅ Added: Category * - Required
- ✅ Added: Brand or Manufacturer * - Required
- ✅ Added: Barcode field
- ✅ Added: Dimensions (width, height, length, weight)
- ✅ Added: VAT Rate dropdown
- ✅ Added: Crossed Out Price (for discounts)
- ✅ Added: Certificate fields (type, delivery, theme, design)

### Form Validation
- ✅ Name field: 60+ characters recommended
- ✅ Description: Up to 6,000 characters
- ✅ Photos: At least 1 required
- ✅ Videos: Optional

---

## 📊 Check Docker Logs for Errors

### View Backend Logs
```bash
# All logs
docker-compose logs backend

# Follow in real-time
docker-compose logs -f backend

# Only errors
docker-compose logs backend 2>&1 | Select-String -Pattern "error|401|403" -CaseSensitive:$false

# Only authentication
docker-compose logs backend 2>&1 | Select-String -Pattern "auth|unauthorized" -CaseSensitive:$false

# Last 100 lines
docker-compose logs --tail 100 backend
```

### View All Container Logs
```bash
# List containers
docker-compose ps

# View frontend logs
docker-compose logs frontend

# View database logs
docker-compose logs postgres

# All services
docker-compose logs
```

---

## ✅ Verify Everything Works

### Test 1: Authentication
```bash
docker-compose exec backend python test_yandex_auth.py
```

Should output:
```
✓ API initialized successfully
✓ Successfully fetched products
✓ Successfully fetched orders
✓ ALL TESTS PASSED!
```

### Test 2: Create Product via UI

1. Open http://localhost:3000
2. Navigate to Products
3. Click "Add Product"
4. Fill required fields:
   ```
   Name: Netflix Premium Subscription 1 Month - Full HD Streaming Access
   SKU: NETFLIX-PREMIUM-1M
   Category: All products · Leisure and entertainment · Digital and gift certificates
   Brand: Netflix
   Cost Price: 500
   Selling Price: 750
   ```
5. Upload at least 1 photo
6. Submit
7. Check product syncs to Yandex Market

### Test 3: Check Yandex Market Dashboard

1. Go to https://partner.market.yandex.ru
2. Navigate to Products
3. Verify product appears
4. Check API Logs:
   - Settings → API and Modules → Request Log
   - Should see 200/201 responses

---

## 🐛 If Issues Persist

### 401 Error Still Happening?

**Check token type in database:**
```bash
docker-compose exec postgres psql -U yandex_user -d yandex_market -c "SELECT yandex_api_token FROM app_settings LIMIT 1;"
```

**Verify token is correct:**
1. Go to Yandex Partner Dashboard
2. Settings → API and Modules → Tokens
3. Copy the **Application Token** (ACMA:...)
4. Update in your app Settings page

### Missing Fields in Form?

The form automatically includes all fields. If some are missing:
```bash
# Rebuild frontend
docker-compose up -d --build frontend
```

### Database Migration Failed?

Run SQL manually:
```bash
docker-compose exec postgres psql -U yandex_user -d yandex_market

-- Then paste SQL from backend/migrations/add_new_product_fields.sql
```

---

## 📖 Additional Resources

- **API Documentation:** https://yandex.ru/dev/market/partner-api/doc/ru/
- **API Logs:** https://yandex.ru/support/marketplace/ru/tools/api-modules/api-log
- **Complete Guide:** See `YANDEX_API_COMPLETE_GUIDE.md`

---

## 🎉 Success Indicators

After applying fixes, you should see:

✅ **In Docker Logs:**
```
[Startup] Performing initial sync from Yandex Market...
✓ Successfully synced products from Yandex Market
✓ Successfully synced orders from Yandex Market
```

✅ **In Yandex Dashboard:**
- No errors in API Request Log
- 200/201 response codes
- Products appear in catalog

✅ **In Your App:**
- Products page loads without errors
- Can create products with all fields
- Can edit products
- Can delete products
- Photos upload successfully
- Products sync to Yandex Market
