import asyncio
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from app.db.init_db import init_models
from app.db.session import async_session_factory, engine
from app.models.business_account import BusinessAccount
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.message import Message
from app.models.ticket import Ticket
from app.models.workflow_action import WorkflowAction


async def seed():
    print("🌱 Initializing database schema...")
    await init_models(engine)

    async with async_session_factory() as session:
        # Check if demo business already exists
        stmt = select(BusinessAccount).where(BusinessAccount.email == "demo@acmeretail.com")
        existing_biz = (await session.execute(stmt)).scalar_one_or_none()

        if existing_biz:
            print("ℹ️  Demo business already seeded.")
            return

        print("🏢 Creating demo business account: Acme Retail Corp...")
        business = BusinessAccount(
            name="Acme Retail Corp",
            email="demo@acmeretail.com",
            hashed_password="pbkdf2:sha256:demo_password_hash",
            api_key="cf_live_demo_key_12345",
            is_active=True,
        )
        session.add(business)
        await session.flush()

        print("👤 Creating sample customers...")
        alice = Customer(
            business_id=business.id,
            phone_number="+14155552671",
            name="Alice Smith",
            email="alice@example.com",
            custom_metadata={"tier": "platinum", "city": "San Francisco"},
        )
        bob = Customer(
            business_id=business.id,
            phone_number="+12025550199",
            name="Bob Jones",
            email="bob@example.com",
            custom_metadata={"tier": "silver", "city": "Washington DC"},
        )
        session.add_all([alice, bob])
        await session.flush()

        print("💬 Creating sample conversations...")
        conv_alice = Conversation(
            customer_id=alice.id,
            channel="sms",
            status="active",
        )
        conv_bob = Conversation(
            customer_id=bob.id,
            channel="sms",
            status="pending_human",
        )
        session.add_all([conv_alice, conv_bob])
        await session.flush()

        print("📨 Creating sample messages...")
        msg1 = Message(
            conversation_id=conv_alice.id,
            direction="inbound",
            sender=alice.phone_number,
            recipient="+18005550199",
            content="Where is my package for order ORD-1042?",
            provider_message_id="msg_demo_01",
            status="received",
        )
        msg2 = Message(
            conversation_id=conv_alice.id,
            direction="outbound",
            sender="+18005550199",
            recipient=alice.phone_number,
            content="Hi Alice! Your order ORD-1042 is in_transit via FedEx (Tracking: FX-88992211). Estimated delivery: Tomorrow by 5:00 PM.",
            provider_message_id="msg_demo_02",
            status="delivered",
        )
        msg3 = Message(
            conversation_id=conv_bob.id,
            direction="inbound",
            sender=bob.phone_number,
            recipient="+18005550199",
            content="My package arrived with a cracked screen for order ORD-9900! I want a full refund.",
            provider_message_id="msg_demo_03",
            status="received",
        )
        msg4 = Message(
            conversation_id=conv_bob.id,
            direction="outbound",
            sender="+18005550199",
            recipient=bob.phone_number,
            content="Hello Bob! I have submitted your refund request for supervisor review. A support manager will confirm shortly.",
            provider_message_id="msg_demo_04",
            status="delivered",
        )
        session.add_all([msg1, msg2, msg3, msg4])

        print("🛡️  Creating sample sensitive action awaiting human approval...")
        action_refund = WorkflowAction(
            conversation_id=conv_bob.id,
            action_type="issue_refund",
            status="pending_approval",
            payload={"order_id": "ORD-9900", "amount": 75.00, "reason": "Damaged goods on delivery"},
            requires_human_approval=True,
        )
        session.add(action_refund)

        print("🎫 Creating sample support ticket...")
        ticket = Ticket(
            business_id=business.id,
            customer_id=bob.id,
            title="Cracked Screen Replacement / Refund Request",
            description="Customer received order ORD-9900 with cracked screen.",
            priority="high",
            status="open",
        )
        session.add(ticket)

        await session.commit()
        print("✅ Database seeding complete!")
        print("\n🔑 Demo Credentials:")
        print("   Business Name: Acme Retail Corp")
        print("   X-API-Key:     cf_live_demo_key_12345")
        print("   Dashboard:     http://localhost:8000/dashboard\n")


if __name__ == "__main__":
    asyncio.run(seed())
