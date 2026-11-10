"""
SoloBiz AI - Unified Runner & Executive CLI Daemon
Supports:
  python run_system.py --eval     -> Runs Golden Benchmark (T011-T020)
  python run_system.py --cli      -> Interactive Small-Business Simulation Mode
  python run_system.py --daemon   -> Local Webhook API Server (Zero Framework Bloat)
  python run_system.py --status   -> Displays Database Health & Pending Approvals
"""
import sys
import json
import time
import argparse
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

# Ensure Windows terminal handles UTF-8 cleanly
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from core.database import init_database, get_db_connection
from core.state import (
    SoloBizInboundEvent,
    CustomerRef,
    MessagePayload,
    InboundMetadata
)
from agents.chief_agent import ChiefOfAgent
from services.finance_service import get_daily_operational_rollup
from evals.eval_runner import run_evaluations

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("solobiz.runner")


def run_interactive_cli():
    """Interactive small-business test simulation terminal."""
    init_database()
    chief = ChiefOfAgent()

    print("\n" + "=" * 75)
    print(" [*] SOLOBIZ AI -- EXECUTIVE MULTI-AGENT SYSTEM (INTERACTIVE CLI)")
    print(" Supervised by Chief of Agent | Zero 3rd-Party Frameworks | Langfuse Tracing")
    print("=" * 75)
    print("Type a simulated customer DM (e.g. 'Do you have Jasmine candles in stock?')")
    print("Type 'status' to view database & approvals | Type 'exit' to quit.\n")

    cust_counter = 100

    while True:
        try:
            user_input = input("\n👤 Customer WhatsApp DM > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit"]:
                print("Exiting SoloBiz AI.")
                break
            if user_input.lower() == "status":
                display_status()
                continue

            cust_counter += 1
            event = SoloBizInboundEvent(
                event_type="CUSTOMER_ENQUIRY",
                channel="WHATSAPP",
                customer_ref=CustomerRef(
                    customer_id=f"cust_wa_{cust_counter}",
                    channel_user_id="+919876543210",
                    name="Priya Sharma"
                ),
                message_payload=MessagePayload(
                    message_id=f"msg_wa_{cust_counter}",
                    message_text=user_input
                ),
                metadata=InboundMetadata(
                    idempotency_key=f"idemp_cli_{cust_counter}_{int(time.time()*1000)}"
                )
            )

            print("\n[*] Chief of Agent orchestrating specialists...")
            output = chief.process_event(event)

            print(f"\n[WORKFLOW OUTPUT] ID: {output.workflow_id}")
            print(f" * Intent Classified : {output.classification.intent} (Confidence: {output.classification.confidence_score:.2f})")
            print(f" * Status            : {output.status}")
            print(f" * HITL Approval Gate: {'[REQUIRED]' if output.approval_required else '[Autonomous Resolution]'}")

            if output.approval_payload:
                print(f"   |-- Trigger Type   : {output.approval_payload.trigger_type}")
                print(f"   |-- Summary        : {output.approval_payload.summary}")
                print(f"   |-- Actions Held   : {', '.join(output.approval_payload.actions_held)}")

            if output.customer_reply:
                status_str = "Dispatched" if output.customer_reply.dispatched else "Held in Draft Queue"
                print(f"\n[CUSTOMER REPLY DRAFT] ({status_str}):")
                print(f"   \"{output.customer_reply.draft_text}\"")

            if output.order_state:
                print(f"\n[ORDER QUOTE] ID: {output.order_state.provisional_order_id}")
                print(f" * Subtotal    : Rs. {output.order_state.subtotal:,.2f}")
                print(f" * Shipping Fee: Rs. {output.order_state.shipping_fee:,.2f}")
                print(f" * Total Quote : Rs. {output.order_state.total_quote:,.2f}")

            if output.inventory_state:
                print(f"\n[INVENTORY STATE] SKU: {output.inventory_state.sku}")
                print(f" * Reserved: {output.inventory_state.quantity_reserved} unit(s) | Health: {output.inventory_state.stock_health}")

            if output.procurement_request:
                print(f"\n[PROCUREMENT REQUISITION]")
                print(f" * Supplier ID   : {output.procurement_request.supplier_id}")
                print(f" * Estimated Cost: Rs. {output.procurement_request.estimated_cost:,.2f} (Status: {output.procurement_request.status})")

        except (KeyboardInterrupt, EOFError):
            print("\nExiting SoloBiz AI.")
            break


def display_status():
    """Prints current SQLite database status and metrics."""
    init_database()
    rollup = get_daily_operational_rollup("biz_artisan_candles_001")

    conn = get_db_connection()
    cursor = conn.cursor()

    print("\n" + "=" * 60)
    print(" [DASHBOARD] SOLOBIZ AI OPERATIONAL HEALTH")
    print("=" * 60)
    print(f" Today's Orders Booked  : {rollup['today_order_count']}")
    print(f" Today's Gross Sales    : Rs. {rollup['today_gross_sales']:,.2f}")
    print(f" Pending Approvals      : {rollup['pending_approvals_count']}")
    print(f" Low-Stock Alerts       : {rollup['low_stock_alerts_count']}")
    print("-" * 60)

    print("\n[ACTIVE INVENTORY STATUS]")
    cursor.execute("SELECT sku, name, available_qty, reserved_qty, unit_price FROM inventory;")
    for r in cursor.fetchall():
        print(f" * {r['sku']:<22} | Avail: {r['available_qty']:<3} | Res: {r['reserved_qty']:<2} | Price: Rs. {r['unit_price']:<6.0f} | {r['name']}")

    cursor.execute("SELECT approval_id, trigger_type, summary, status FROM approval_queue WHERE status = 'PENDING_APPROVAL';")
    approvals = cursor.fetchall()
    if approvals:
        print("\n[PENDING OWNER APPROVAL ITEMS]")
        for a in approvals:
            print(f" * [{a['approval_id']}] ({a['trigger_type']}): {a['summary']}")
    else:
        print("\n[OK] Zero pending approvals in queue.")

    print("=" * 60 + "\n")
    conn.close()


class WebhookHandler(BaseHTTPRequestHandler):
    chief = None

    def do_POST(self):
        if self.path == "/webhook":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                event = SoloBizInboundEvent(**data)
                output = self.chief.process_event(event)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(output.model_dump_json(indent=2).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy", "service": "SoloBiz AI"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def run_daemon(host: str = "127.0.0.1", port: int = 8080):
    """Runs zero-dependency local HTTP webhook server."""
    init_database()
    WebhookHandler.chief = ChiefOfAgent()
    server = HTTPServer((host, port), WebhookHandler)
    print(f"\n🚀 SoloBiz AI Webhook Server listening at http://{host}:{port}/webhook")
    print(f"Health check at http://{host}:{port}/health (Press Ctrl+C to stop)\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping SoloBiz AI daemon.")
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description="SoloBiz AI - Multi-Agent Executive System")
    parser.add_argument("--eval", action="store_true", help="Run Golden Benchmark suite (T011-T020)")
    parser.add_argument("--cli", action="store_true", help="Launch interactive small-business simulation CLI")
    parser.add_argument("--daemon", action="store_true", help="Start local webhook daemon server")
    parser.add_argument("--status", action="store_true", help="Display operational database status & approvals")

    args = parser.parse_args()

    if args.eval:
        run_evaluations()
    elif args.daemon:
        run_daemon()
    elif args.status:
        display_status()
    else:
        # Default to interactive CLI if no flag is passed
        run_interactive_cli()


if __name__ == "__main__":
    main()
