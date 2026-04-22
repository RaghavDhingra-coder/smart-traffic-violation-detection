# Migration Guide: Schema & Dashboard Upgrades

## Overview

This guide helps you migrate from the basic schema implementation to the enhanced version with validation, evidence tracking, and improved dashboards.

---

## Backend Migration Steps

### Step 1: Update Schema Files

#### Before (Basic Challan Schema)
```python
class ChallanCreate(BaseModel):
    plate: str
    violation_type: str
    image_path: str | None = None
```

#### After (Enhanced Challan Schema)
```python
class ChallanCreate(BaseModel):
    plate: str = Field(..., min_length=8, max_length=12, example="DL01AB1234")
    violation_type: str = Field(...)
    image_path: Optional[str] = Field(None)
    officer_id: Optional[str] = Field(None)
    location: Optional[str] = Field(None)
    
    @validator("plate")
    def validate_plate_format(cls, v):
        # Validation logic
        pass
```

**Files to Update:**
- `backend/schemas/challan.py` → New file with validation
- `backend/schemas/detection.py` → Enhanced detection models
- `backend/schemas/payment.py` → Added receipt and webhook support

### Step 2: Update Database Models

If your database models don't have these fields, create a migration:

```bash
# Generate migration
alembic revision --autogenerate -m "Add officer_id, location, dismissal_reason to challan"

# Apply migration
alembic upgrade head
```

**Required New Fields in `challan` Table:**
```sql
ALTER TABLE challan ADD COLUMN officer_id VARCHAR(50);
ALTER TABLE challan ADD COLUMN location VARCHAR(255);
ALTER TABLE challan ADD COLUMN dismissal_reason TEXT;
ALTER TABLE challan ADD COLUMN appeal_notes TEXT;
```

**Required New Fields in `payment` Table:**
```sql
ALTER TABLE payment ADD COLUMN payment_method VARCHAR(50);
ALTER TABLE payment ADD COLUMN receipt_url TEXT;
ALTER TABLE payment ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE payment ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
```

### Step 3: Update API Endpoints

#### Challan Endpoints

**Before:**
```python
@router.post("/challan")
def create_challan(challan: ChallanCreate):
    return db_create_challan(challan)
```

**After:**
```python
@router.post("/challan")
def create_challan(challan: ChallanCreate):
    # Validates plate format, violation type automatically
    # Tracks officer_id and location
    return db_create_challan(challan)

@router.put("/challan/{challan_id}/status")
def update_challan_status(challan_id: int, update: ChallanStatusUpdate):
    # Validates dismissal_reason when needed
    # Tracks appeal_notes
    return db_update_challan_status(challan_id, update)
```

**New Officers Actions Endpoint:**
```python
@router.post("/challan/{challan_id}/officer-action")
def record_officer_action(challan_id: int, action: OfficerAction):
    # Record what officer did
    return db_record_action(challan_id, action)

@router.get("/challan/{challan_id}/actions")
def get_challan_actions(challan_id: int):
    # Retrieve officer action history
    return db_get_actions(challan_id)
```

#### Payment Endpoints

**New Refund Endpoint:**
```python
@router.post("/payment/{payment_id}/refund")
def request_refund(payment_id: str, refund: RefundRequest):
    # Process refund with reason tracking
    return db_process_refund(payment_id, refund)

@router.post("/payment/webhook")
def handle_payment_webhook(payload: WebhookPayload):
    # Handle gateway webhook events
    return db_update_payment_status(payload)
```

### Step 4: Update Service Layer

#### challan_service.py

```python
from schemas.challan import (
    ChallanCreate, 
    ChallanStatusUpdate, 
    OfficerAction,
    EvidenceMetadata
)

class ChallanService:
    
    @staticmethod
    def create_challan(challan_data: ChallanCreate):
        """Create challan with validation & metadata"""
        # Plate format is already validated by Pydantic
        # violation_type is already validated
        
        # Add additional business logic
        challan = Challan(
            plate=challan_data.plate,
            violation_type=challan_data.violation_type,
            image_path=challan_data.image_path,
            officer_id=challan_data.officer_id,  # NEW
            location=challan_data.location,      # NEW
            amount=VIOLATION_FINES[challan_data.violation_type],
            status="pending"
        )
        db.add(challan)
        db.commit()
        return challan
    
    @staticmethod
    def update_challan_status(challan_id: int, update: ChallanStatusUpdate):
        """Update status with validation"""
        challan = db.query(Challan).get(challan_id)
        
        if update.status == "dismissed" and not update.dismissal_reason:
            raise ValueError("Dismissal reason required")
        
        challan.status = update.status
        if update.dismissal_reason:
            challan.dismissal_reason = update.dismissal_reason
        if update.appeal_notes:
            challan.appeal_notes = update.appeal_notes
        
        db.commit()
        return challan
    
    @staticmethod
    def record_officer_action(challan_id: int, action: OfficerAction):
        """Record officer's action on challan"""
        officer_record = OfficerActionLog(
            challan_id=challan_id,
            officer_id=action.officer_id,
            action=action.action,
            notes=action.notes,
            timestamp=action.timestamp
        )
        db.add(officer_record)
        db.commit()
        return officer_record
```

#### payment_service.py

```python
from schemas.payment import (
    PaymentCreate,
    PaymentVerifyRequest,
    WebhookPayload,
    RefundRequest
)

class PaymentService:
    
    @staticmethod
    def handle_webhook(payload: WebhookPayload):
        """Process payment gateway webhook"""
        payment = db.query(Payment).filter_by(
            razorpay_order_id=payload.order_id
        ).first()
        
        if payload.event == "payment.captured":
            payment.status = "paid"
            # Find and update challan
            challan = payment.challan
            challan.status = "paid"
        elif payload.event == "payment.failed":
            payment.status = "failed"
            # Store error details
            payment.error_code = payload.error_code
            payment.error_description = payload.error_description
        
        db.commit()
        return payment
    
    @staticmethod
    def request_refund(payment_id: str, refund_req: RefundRequest):
        """Process refund with audit trail"""
        payment = db.query(Payment).get(payment_id)
        
        # Create refund record
        refund = Refund(
            payment_id=payment_id,
            amount=payment.amount,
            reason=refund_req.reason,
            status="requested",
            timestamp=datetime.utcnow()
        )
        db.add(refund)
        db.commit()
        
        # Call payment gateway refund API
        # (Razorpay, etc.)
        
        return refund
```

---

## Frontend Migration Steps

### Step 1: Update Dashboard Pages

Replace old dashboard pages with enhanced versions:

```
OLD: pages/UserDashboard.jsx
NEW: pages/UserDashboardEnhanced.jsx

OLD: pages/PoliceDashboard.jsx
NEW: pages/PoliceDashboardEnhanced.jsx

OLD: pages/AwareUserDashboard.jsx
NEW: pages/AwareUserDashboardEnhanced.jsx
```

### Step 2: Update Components

```
OLD: components/ChallanCard.jsx
NEW: components/ChallanCardEnhanced.jsx

OLD: components/ViolationCard.jsx
NEW: components/ViolationCardEnhanced.jsx
```

### Step 3: Update App Routing

**Before:**
```jsx
import UserDashboard from "./pages/UserDashboard";
import PoliceDashboard from "./pages/PoliceDashboard";

<Route path="/user" element={<UserDashboard />} />
<Route path="/police" element={<PoliceDashboard />} />
```

**After:**
```jsx
import UserDashboardEnhanced from "./pages/UserDashboardEnhanced";
import PoliceDashboardEnhanced from "./pages/PoliceDashboardEnhanced";
import AwareUserDashboardEnhanced from "./pages/AwareUserDashboardEnhanced";

<Route path="/user" element={<UserDashboardEnhanced />} />
<Route path="/police" element={<PoliceDashboardEnhanced />} />
<Route path="/aware" element={<AwareUserDashboardEnhanced />} />
```

### Step 4: Test Component Integration

**Expected Response Format (After Migration):**

```json
{
  "id": 1,
  "plate": "DL01AB1234",
  "violation_type": "NO_HELMET",
  "amount": 500,
  "status": "pending",
  "timestamp": "2024-04-22T10:30:00Z",
  "officer_id": "BADGE001",
  "location": "Ring Road, Delhi",
  "evidence": {
    "image_path": "/evidence/12345.jpg",
    "confidence_score": 0.95,
    "frame_index": 120,
    "bounding_box": {
      "x1": 100,
      "y1": 50,
      "x2": 400,
      "y2": 300
    }
  },
  "officer_actions": [
    {
      "officer_id": "BADGE001",
      "action": "REVIEWED",
      "notes": "Clear violation",
      "timestamp": "2024-04-22T10:35:00Z"
    }
  ]
}
```

---

## Database Schema Changes

### Challan Table Migration

```sql
-- Add new columns
ALTER TABLE challan ADD COLUMN officer_id VARCHAR(50);
ALTER TABLE challan ADD COLUMN location VARCHAR(255);
ALTER TABLE challan ADD COLUMN dismissal_reason TEXT;
ALTER TABLE challan ADD COLUMN appeal_notes TEXT;
ALTER TABLE challan ADD COLUMN confidence_score FLOAT;
ALTER TABLE challan ADD COLUMN frame_index INTEGER;

-- Create officer_actions table
CREATE TABLE officer_actions (
    id SERIAL PRIMARY KEY,
    challan_id INTEGER NOT NULL REFERENCES challan(id),
    officer_id VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (challan_id) REFERENCES challan(id) ON DELETE CASCADE
);

-- Create indices for performance
CREATE INDEX idx_challan_officer_id ON challan(officer_id);
CREATE INDEX idx_challan_location ON challan(location);
CREATE INDEX idx_challan_status ON challan(status);
CREATE INDEX idx_officer_actions_challan ON officer_actions(challan_id);
```

### Payment Table Migration

```sql
-- Add new columns
ALTER TABLE payment ADD COLUMN payment_method VARCHAR(50);
ALTER TABLE payment ADD COLUMN receipt_url TEXT;
ALTER TABLE payment ADD COLUMN error_code VARCHAR(100);
ALTER TABLE payment ADD COLUMN error_description TEXT;
ALTER TABLE payment ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE payment ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Create refunds table
CREATE TABLE refunds (
    id SERIAL PRIMARY KEY,
    payment_id INTEGER NOT NULL REFERENCES payment(id),
    amount INTEGER NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'requested',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (payment_id) REFERENCES payment(id) ON DELETE CASCADE
);

-- Create webhook_logs table
CREATE TABLE webhook_logs (
    id SERIAL PRIMARY KEY,
    event VARCHAR(100) NOT NULL,
    payment_id VARCHAR(100),
    order_id VARCHAR(100),
    payload JSONB NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Testing Checklist

- [ ] All schemas validate input correctly
- [ ] Plate format validation works
- [ ] Violation type enum validation works
- [ ] Dismissal reason required for dismissed status
- [ ] Officer actions recorded correctly
- [ ] Evidence metadata stored and retrieved
- [ ] Payment webhook events processed
- [ ] Refund requests created
- [ ] Frontend dashboards display new data
- [ ] Filtering and sorting work correctly
- [ ] Payment flow completes end-to-end
- [ ] Error messages are user-friendly
- [ ] Database migrations applied successfully

---

## Rollback Plan

If you need to revert to the old version:

```bash
# Revert database changes
alembic downgrade -1

# Restore old schema files
git checkout backend/schemas/challan.py
git checkout backend/schemas/detection.py
git checkout backend/schemas/payment.py

# Restore old pages
git checkout frontend/src/pages/UserDashboard.jsx
git checkout frontend/src/pages/PoliceDashboard.jsx
git checkout frontend/src/pages/AwareUserDashboard.jsx

# Restore old components
git checkout frontend/src/components/ChallanCard.jsx
git checkout frontend/src/components/ViolationCard.jsx
```

---

## Common Issues & Solutions

### Issue: "Plate validation failing for valid plates"
**Solution:** Ensure plate format is exactly `XX##XX####` (2 letters, 2 digits, 2 letters, 4 digits)

### Issue: "Dismissal reason not required when status='dismissed'"
**Solution:** Check that `ChallanStatusUpdate` validator is properly checking `values.get("status")`

### Issue: "Officer actions not appearing in response"
**Solution:** Ensure API returns `officer_actions` in `ChallanOut` model with proper relationship loading

### Issue: "Payment webhook not updating challan status"
**Solution:** Verify webhook signature verification with Razorpay secret key

### Issue: "Old dashboards still loading"
**Solution:** Clear browser cache, verify App.jsx routing points to Enhanced versions

---

## Performance Considerations

1. **Add Database Indices**
   - On `challan.status` for filtering
   - On `challan.officer_id` for officer views
   - On `payment.status` for payment tracking

2. **Optimize Queries**
   - Use `joinedload()` for officer_actions
   - Implement pagination for large result sets

3. **Cache Frequently Accessed Data**
   - Violation fines mapping
   - Violation labels mapping

---

For support or questions, contact the development team or refer to DASHBOARD_SCHEMA_DOCS.md
