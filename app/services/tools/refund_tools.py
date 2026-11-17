from typing import Any, Dict
from pydantic import BaseModel, Field
from app.services.tools.base import BaseTool, ToolResult


class IssueRefundParams(BaseModel):
    order_id: str = Field(..., examples=["ORD-1042"], description="The order identifier to refund.")
    amount: float = Field(..., gt=0.0, examples=[49.99], description="The dollar amount to be refunded.")
    reason: str = Field(..., examples=["Customer damaged goods on arrival"], description="Reason for refund.")


class IssueRefundTool(BaseTool):
    name = "issue_refund"
    description = "Issues a financial credit refund to a customer's payment method. Requires human approval."
    parameters_schema = IssueRefundParams
    is_sensitive = True  # SENSITIVE: Cannot execute without explicit human approval

    async def execute(self, params: IssueRefundParams, context: Dict[str, Any]) -> ToolResult:
        # Simulated payment processor call (e.g. Stripe refund API)
        refund_transaction_id = f"re_mock_{params.order_id.lower()}_9921"
        return ToolResult(
            success=True,
            tool_name=self.name,
            data={
                "refund_id": refund_transaction_id,
                "order_id": params.order_id,
                "amount": params.amount,
                "status": "succeeded",
                "message": f"Successfully refunded ${params.amount:.2f} for order {params.order_id}.",
            },
        )
