# Telecom & AI Integration Guide

ConnectFlow supports two operating modes:
1. **Mock Simulator Mode (Default)**: Free, zero credentials required, 100% testable out-of-the-box.
2. **Live Production Mode**: Connects directly to Plivo's telecom network and Google Gemini's AI models.

---

## 1. Connecting Plivo for Live Messaging

### Step 1: Obtain Plivo Credentials
1. Sign up at [plivo.com](https://www.plivo.com).
2. Retrieve your **Auth ID** and **Auth Token** from the dashboard.
3. Purchase or rent an SMS/WhatsApp-enabled phone number (e.g. `+18005550199`).

### Step 2: Expose Your Local Server with Ngrok (for Local Webhooks)
Because telecom providers deliver webhooks over the public internet, use **Ngrok** to create a secure tunnel to your local FastAPI server:

```bash
ngrok http 8000
```
Ngrok provides a public HTTPS forwarding address:
```text
Forwarding https://a1b2-your-domain.ngrok-free.app -> http://localhost:8000
```

### Step 3: Configure Webhook URLs in Plivo Console
In your Plivo console under **Phone Numbers > Your Number**:
- **Message URL**: `https://a1b2-your-domain.ngrok-free.app/api/v1/webhooks/inbound`
- **Method**: `POST`
- **Delivery Report URL**: `https://a1b2-your-domain.ngrok-free.app/api/v1/webhooks/delivery-report`

### Step 4: Update Your `.env` File
```ini
PLIVO_AUTH_ID=MAMZLLNZM0NDU0YZHMZW
PLIVO_AUTH_TOKEN=your_real_plivo_auth_token_here
PLIVO_PHONE_NUMBER=+18005550199
```
Restart your server. ConnectFlow will automatically verify incoming cryptographic signatures and dispatch real SMS messages!

---

## 2. Connecting Google Gemini LLM

### Step 1: Obtain a Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com).
2. Generate a free API key.

### Step 2: Configure in `.env`
```ini
LLM_PROVIDER=gemini
LLM_API_KEY=AIzaSyYourGeminiApiKeyHere
LLM_MODEL=gemini-2.5-flash
```
Restart the server. ConnectFlow will now perform zero-shot intent categorization and contextual customer response drafting using Google Gemini in JSON mode!
