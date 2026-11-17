# ConnectFlow REST API Reference

All protected endpoints require an `X-API-Key` header issued to an active business account.

---

## 1. Authentication Header

```http
X-API-Key: cf_live_demo_key_12345
```

---

## 2. Customer Management Endpoints

### Register Customer
- **Endpoint**: `POST /api/v1/customers`
- **Status Code**: `201 Created`
- **Request Body**:
```json
{
  "phone_number": "+14155552671",
  "name": "Sarah Connor",
  "email": "sarah@example.com",
  "custom_metadata": { "vip": true, "loyalty_tier": "gold" }
}
```

### List Customers (Paginated & Search)
- **Endpoint**: `GET /api/v1/customers?limit=20&offset=0&search=Sarah`
- **Status Code**: `200 OK`

### Update Customer Profile
- **Endpoint**: `PATCH /api/v1/customers/{customer_id}`
- **Status Code**: `200 OK`
- **Request Body**:
```json
{
  "name": "Sarah J. Connor",
  "custom_metadata": { "loyalty_tier": "platinum" }
}
```

---

## 3. Messaging & Conversations

### Send Outbound Message
- **Endpoint**: `POST /api/v1/messages`
- **Status Code**: `201 Created`
- **Request Body**:
```json
{
  "recipient": "+14155552671",
  "content": "Your package has departed the fulfillment center.",
  "channel": "sms"
}
```

### Get Conversation Transcript
- **Endpoint**: `GET /api/v1/conversations/{conversation_id}/messages`
- **Status Code**: `200 OK`
- **Response**:
```json
{
  "id": "5a57ea98-c57a-47c0-ae79-5ddf615d779e",
  "customer_id": "271807c4-2160-4bbb-8c30-a460829ef29d",
  "channel": "sms",
  "status": "active",
  "created_at": "2026-11-17T15:20:00Z",
  "updated_at": "2026-11-17T15:21:00Z",
  "messages": [
    {
      "id": "c255e9a6-cfcf-4af6-8643-a833dc58146d",
      "direction": "inbound",
      "sender": "+14155552671",
      "recipient": "+18005550199",
      "content": "Where is my order ORD-1042?",
      "status": "received",
      "provider_message_id": "msg_001",
      "created_at": "2026-11-17T15:20:00Z"
    }
  ]
}
```

---

## 4. Webhooks Ingress

### Receive Inbound SMS / WhatsApp
- **Endpoint**: `POST /api/v1/webhooks/inbound`
- **Security**: Validated via `X-Plivo-Signature-V2` (or `X-Bypass-Signature: true` in development)
- **Status Code**: `200 OK`
- **Request Body**:
```json
{
  "From": "+14155552671",
  "To": "+18005550199",
  "Text": "Can you check the delivery status for ORD-1042?",
  "MessageUUID": "plivo_msg_uuid_992211",
  "Type": "sms"
}
```

---

## 5. Workflow & Human-in-the-Loop (HITL)

### List Pending Approvals
- **Endpoint**: `GET /api/v1/workflow/actions/pending`
- **Status Code**: `200 OK`

### Approve Sensitive Action
- **Endpoint**: `POST /api/v1/workflow/actions/{action_id}/approve`
- **Status Code**: `200 OK`
- **Request Body**:
```json
{
  "approved_by": "supervisor@acmeretail.com"
}
```

### Reject Sensitive Action
- **Endpoint**: `POST /api/v1/workflow/actions/{action_id}/reject`
- **Status Code**: `200 OK`
- **Request Body**:
```json
{
  "reason": "Exceeded 30-day return window",
  "rejected_by": "supervisor@acmeretail.com"
}
```

---

## 6. Observability & System Diagnostics

### System Health & Metrics
- **Endpoint**: `GET /api/v1/metrics/system`
- **Status Code**: `200 OK`

### Failed Requests Log
- **Endpoint**: `GET /api/v1/metrics/failed-requests?limit=20`
- **Status Code**: `200 OK`
