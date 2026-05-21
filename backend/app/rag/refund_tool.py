import logging

logger = logging.getLogger(__name__)

def process_refund(order_id: str) -> str:
    """
    Simulates a database action to process a customer refund based on Order ID.
    """
    if not order_id:
        return "Error: Missing a valid Order ID to process the refund request."
    
    logger.info(f"Processing automated refund pipeline for Order {order_id}")
    return f"Successfully processed refund for Order {order_id}. The amount will reflect in the customer bank account within 3-5 business days."