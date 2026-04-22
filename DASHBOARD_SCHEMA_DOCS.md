# Smart Traffic Violation Detection - Dashboard & Schema Documentation

## Overview

This document outlines the enhanced schemas and dashboard implementations for the Smart Traffic Violation Detection system. All changes incorporate comprehensive validation, detailed evidence tracking, and officer workflow management.

## Backend Schema Enhancements

### 1. Challan Schema (`backend/schemas/challan.py`)

#### New Models Added:

**ChallanCreate** - Enhanced with validation
- Plate validation (Indian vehicle format: `XX##XX####`)
- Violation type enum validation
- Officer ID tracking
- Location information

**ChallanStatusUpdate** - Status management with approval workflow
- Status: `pending`, `approved`, `paid`, `dismissed`, `appealed`
- Dismissal reason validation (required when status="dismissed")
- Appeal notes support

**OfficerAction** - Officer workflow tracking
- Officer badge ID
- Action types: `REVIEWED`, `APPROVED`, `REJECTED`, `DISMISSED`
- Timestamp tracking

**EvidenceMetadata** - Rich evidence tracking
- Confidence scores (0.0 - 1.0)
- Frame indexing for video evidence
- Bounding box coordinates
- Timestamp of detection

**ChallanOut** - Complete response object
- All challan fields
- Evidence metadata
- Officer action history
- Dismissal/appeal information

**ChallanListResponse** - Paginated list response
- Total count
- Current page data
- Pagination metadata

#### Validation Rules:
```python
# Plate Format Validation
regex: ^[A-Z]{2}\d{2}[A-Z]{2}\d{4}$
# Examples: DL01AB1234, KA99ZZ9999

# Allowed Violation Types
{
  "OVER_SPEED", "NO_HELMET", "TRIPPLING", 
  "TRAFFIC_LIGHT_JUMP", "NO_PARKING", 
  "NO_NUMBER_PLATE", "RASH_DRIVING", "WRONG_WAY"
}

# Allowed Status Values
{"pending", "approved", "paid", "dismissed", "appealed"}

# Allowed Officer Actions
{"REVIEWED", "APPROVED", "REJECTED", "DISMISSED"}
```

---

### 2. Detection Schema (`backend/schemas/detection.py`)

#### New Models Added:

**BoundingBox** - Annotated detection boundaries
- x1, y1 (top-left coordinates)
- x2, y2 (bottom-right coordinates)
- Validation ensures x2 > x1 and y2 > y1

**FrameMetadata** - Video frame information
- Frame index (sequence number)
- Timestamp in milliseconds
- Associated bounding box

**ViolationOut** - Enhanced violation response
- Violation type with validation
- Confidence score (0.0 - 1.0)
- Detected plate number
- Base64 encoded annotated frame
- Frame metadata
- Evidence quality rating: `excellent`, `good`, `fair`, `poor`

**DetectionResult** - Complete detection response
- List of violations
- Total frames processed
- Video duration
- Processing time metrics
- Model version tracking

**BatchDetectionResult** - Batch processing results
- Batch ID
- Processing timestamps
- List of detection results

---

### 3. Payment Schema (`backend/schemas/payment.py`)

#### New Models Added:

**PaymentCreate** - Payment order creation
- Challan ID
- Amount (in paise)
- Currency validation: `INR`, `USD`, `EUR`
- Payment method tracking

**PaymentVerifyRequest** - Gateway verification
- Razorpay order ID
- Razorpay payment ID
- Razorpay signature for HMAC verification

**PaymentReceipt** - Digital receipt
- Receipt ID
- Payment timestamp
- Receipt download URL
- Complete payment details

**WebhookPayload** - Payment gateway events
- Event types: `payment.authorized`, `payment.failed`, `payment.captured`, `payment.refunded`
- Status tracking
- Error code and description
- Unix timestamp

**PaymentOut** - Complete payment response
- Payment ID
- Order ID
- Status tracking
- Receipt information
- Payment method details

**PaymentListResponse** - Paginated payment history
- Pagination metadata
- List of payments

**RefundRequest** - Refund processing
- Payment ID to refund
- Minimum 10-character reason
- Associated challan ID

---

## Frontend Dashboard Implementations

### 1. Enhanced User Dashboard (`UserDashboardEnhanced.jsx`)

**Features:**
- Vehicle number login system
- Real-time challan fetching
- Advanced filtering (status-based)
- Sorting options (date, amount)
- Statistics panel:
  - Total pending challans
  - Total pending amount
  - Payment status breakdown
- Razorpay payment integration
- Individual challan payment processing

**UI Components:**
- Vehicle login form
- Statistics cards
- Filterable challan list
- Payment processing indicator

---

### 2. Enhanced Police Dashboard (`PoliceDashboardEnhanced.jsx`)

**Features:**
- **Live Detection Tab**
  - Real-time webcam feed
  - Violation detection
  - Quick action to issue challan

- **Plate Lookup Tab**
  - Vehicle registration search
  - Owner information
  - Complete challan history

- **Issue Challan Tab**
  - Violation type selection
  - Officer ID tracking
  - Location information
  - Fine reference guide

- **Stats Tab**
  - Real-time analytics
  - Total detections and violations
  - Potential revenue calculation
  - Average confidence score
  - Violation breakdown by type

- **Officer Actions Tab**
  - Pending review queue
  - Approval workflow
  - Dismissal management

**Violation Fines:**
```javascript
{
  "NO_HELMET": 500,
  "TRIPPLING": 1000,
  "OVER_SPEED": 2000,
  "TRAFFIC_LIGHT_JUMP": 1000,
  "NO_PARKING": 500,
  "NO_NUMBER_PLATE": 5000,
  "RASH_DRIVING": 2500,
  "WRONG_WAY": 1500
}
```

---

### 3. Enhanced Aware User Dashboard (`AwareUserDashboardEnhanced.jsx`)

**Features:**
- Image/video upload for self-checking
- Violation detection with confidence scores
- Prevention tip library:
  - NO_HELMET: Helmet safety information
  - TRIPPLING: Passenger rules
  - OVER_SPEED: Speed limit compliance
  - TRAFFIC_LIGHT_JUMP: Signal compliance
  - RASH_DRIVING: Safe driving practices

- Expandable violation analysis
- Vehicle lookup with pending challan summary
- Educational resource cards
- Compliance tracking

**Prevention Tips Per Violation:**
Each violation type includes 4 personalized prevention tips that users can review and implement.

---

## Enhanced Reusable Components

### 1. ChallanCardEnhanced.jsx

**Properties Displayed:**
- Challan ID
- Violation type with label
- Vehicle plate
- Amount and status
- Timestamp
- Officer badge
- Location
- Evidence metadata
- Dismissal reasons
- Appeal notes

**Features:**
- Expandable/collapsible details
- Status badge with color coding
- Quick pay button for pending challans
- Evidence quality display

**Status Colors:**
```javascript
{
  "pending": "amber",
  "approved": "blue",
  "paid": "emerald",
  "dismissed": "slate",
  "appealed": "purple"
}
```

---

### 2. ViolationCardEnhanced.jsx

**Properties Displayed:**
- Violation type
- Confidence score with visual progress bar
- Detected plate number
- Frame metadata
- Evidence quality
- Potential fine amount
- Bounding box coordinates

**Features:**
- Confidence level color coding (red/amber/slate)
- Annotated frame preview (base64 image)
- Visual confidence indicator
- Frame index tracking
- Click-to-action pattern

---

## API Integration Points

### Challan Endpoints
```
GET  /challan/{plate}              # Fetch challans for vehicle
POST /challan                       # Create new challan
GET  /challan/{id}                 # Get challan details
PUT  /challan/{id}/status          # Update challan status
GET  /challan/{id}/actions         # Get officer actions
```

### Payment Endpoints
```
POST /payment/create-order         # Create payment order
POST /payment/verify               # Verify payment signature
GET  /payment/{challan_id}         # Get payment details
POST /payment/{id}/refund          # Request refund
```

### Vehicle Endpoints
```
GET  /vehicle/{plate}              # Get vehicle and challan info
```

### Detection Endpoints
```
POST /detect                       # Submit detection request
GET  /detect/{batch_id}           # Get batch results
```

---

## Validation & Error Handling

### Plate Validation
- Format: Indian vehicle registration number
- Pattern: `^[A-Z]{2}\d{2}[A-Z]{2}\d{4}$`
- Examples: `DL01AB1234`, `KA99ZZ9999`

### Confidence Score Validation
- Range: 0.0 to 1.0
- Levels: Low (<0.6), Medium (0.6-0.8), High (>0.8)

### Amount Validation
- Must be positive integer (in paise)
- Currency validation for supported types

### Status Transitions
```
pending → approved → paid
pending → dismissed (with reason)
pending/approved → appealed (with notes)
```

---

## Future Enhancements

1. **Real-time Notifications**
   - Payment confirmation alerts
   - Challan updates
   - Appeal status updates

2. **Advanced Analytics**
   - Violation trends by location
   - Peak violation times
   - Repeat offender tracking

3. **Mobile App**
   - Native iOS/Android implementation
   - Offline challan viewing
   - Push notifications

4. **Integration Improvements**
   - Multi-gateway payment support
   - SMS/Email notifications
   - Document uploads for appeals

5. **Officer Portal Enhancements**
   - Real-time live tracking
   - Mobile app for field officers
   - Offline challan issuance

---

## Technical Stack

### Backend
- FastAPI with Pydantic validators
- PostgreSQL with Alembic migrations
- Razorpay payment gateway
- Better Auth integration

### Frontend
- React with Vite
- TailwindCSS for styling
- Axios for API communication
- React Context for state management

---

## Security Considerations

1. **Payment Security**
   - HMAC signature verification for Razorpay webhooks
   - PCI DSS compliance
   - Secure credential storage

2. **Data Validation**
   - Input sanitization
   - Type checking with Pydantic
   - Business logic validation

3. **Access Control**
   - Role-based authentication (Citizen/Police/Admin)
   - Officer badge tracking
   - Audit logs for actions

---

## File Structure

```
backend/schemas/
├── challan.py          # Challan models with validation
├── detection.py        # Detection and violation models
├── payment.py          # Payment and refund models
└── __init__.py

frontend/src/
├── pages/
│   ├── UserDashboardEnhanced.jsx
│   ├── PoliceDashboardEnhanced.jsx
│   └── AwareUserDashboardEnhanced.jsx
├── components/
│   ├── ChallanCardEnhanced.jsx
│   ├── ViolationCardEnhanced.jsx
│   └── (other existing components)
└── api/
    └── axios.js        # API client configuration
```

---

## Getting Started

1. **Update Backend**
   - Replace schema files with enhanced versions
   - Run migrations: `alembic upgrade head`

2. **Update Frontend**
   - Replace dashboard pages
   - Update components
   - Run `npm install` if new dependencies added

3. **Test Integration**
   - Verify API responses match schema
   - Test payment flow
   - Validate all error cases

---

For questions or issues, refer to the main README.md or contact the development team.
