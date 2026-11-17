from typing import Any, Dict
from pydantic import BaseModel, Field
from app.services.tools.base import BaseTool, ToolResult


class FetchOrderParams(BaseModel):
    order_id: str = Field(..., examples=["ORD-1042"], description="The alphanumeric order tracking identifier.")


class FetchOrderTool(BaseTool):
    name = "fetch_order_status"
    description = "Retrieves live shipping, delivery, and item details for a customer order."
    parameters_schema = FetchOrderParams
    is_sensitive = False  # Safe read-only lookup

    async def execute(self, params: FetchOrderParams, context: Dict[str, Any]) -> ToolResult:
        order_num = params.order_id.upper()

        # Simulated order database / external ERP integration
        mock_orders_db = {
            "ORD-1042": {
                "order_id": "ORD-1042",
                "status": "in_transit",
                "carrier": "FedEx",
                "tracking_number": "FX-88992211",
                "estimated_delivery": "Tomorrow by 5:00 PM",
                "items": ["Ergonomic Wireless Keyboard", "USB-C Hub"],
            },
            "ORD-9921": {
                "order_id": "ORD-9921",
                "status": "out_for_delivery",
                "carrier": "UPS",
                "tracking_number": "1Z9999999999999999",
                "estimated_delivery": "Today by 2:00 PM",
                "items": ["Noise Cancelling Headphones"],
            },
        }

        order_data = mock_orders_db.get(
            order_num,
            {
                "order_id": order_num,
                "status": "shipped",
                "carrier": "USPS",
                "tracking_number": f"94001118992231{order_num[-4:] if len(order_num)>=4 else '0000'}",
                "estimated_delivery": "In 2 business days",
                "items": ["General Merchandise"],
            },
        )

        return ToolResult(
            success=True,
            tool_name=self.name,
            data=order_data,
        )
