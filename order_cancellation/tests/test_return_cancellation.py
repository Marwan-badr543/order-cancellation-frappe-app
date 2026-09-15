import unittest
import frappe
from frappe.utils import flt, nowdate
from erpnext.controllers.sales_and_purchase_return import make_return_doc
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.selling.doctype.sales_order.sales_order import (
	make_delivery_note,
	make_sales_invoice as make_sales_invoice_from_so,
)
from order_cancellation.utils import (
	cancel_linked_payment_entries,
	get_linked_sales_orders,
	get_linked_delivery_notes,
	get_serial_numbers_from_docs,
	cancel_linked_documents_and_activate_serials,
)


class TestReturnPaymentCancellation(unittest.TestCase):
	def setUp(self):
		frappe.db.rollback()

	def tearDown(self):
		frappe.db.rollback()

	def test_so_connected_to_si_and_dn_flow(self):
		company = frappe.db.get_value("Company", {}, "name") or "marwan"
		customer = frappe.db.get_value("Customer", {}, "name") or "marwan"
		item = frappe.db.get_value("Item", {"is_sales_item": 1, "has_serial_no": 1}, "name") or "marwan code"
		warehouse = frappe.db.get_value("Warehouse", {"company": company, "is_group": 0}, "name") or "Stores - M"

		# 1. Receive Serial No
		serial_no_id = f"TEST-SN-{frappe.generate_hash(length=6)}"
		make_stock_entry(
			item_code=item,
			target=warehouse,
			qty=1,
			basic_rate=100,
			serial_no=serial_no_id,
		)

		# 2. Create Sales Order
		so = frappe.get_doc({
			"doctype": "Sales Order",
			"company": company,
			"customer": customer,
			"delivery_date": nowdate(),
			"items": [
				{
					"item_code": item,
					"qty": 1,
					"rate": 100,
					"warehouse": warehouse,
				}
			],
		})
		so.set_missing_values()
		so.insert(ignore_permissions=True)
		so.submit()

		# 3. Create Sales Invoice from Sales Order (NOT from Delivery Note)
		si = make_sales_invoice_from_so(so.name)
		si.items[0].serial_no = serial_no_id
		si.insert(ignore_permissions=True)
		si.submit()

		# 4. Create Delivery Note from Sales Order (NOT connected to Sales Invoice)
		dn = make_delivery_note(so.name)
		dn.items[0].serial_no = serial_no_id
		dn.insert(ignore_permissions=True)
		dn.submit()

		# 5. Create Payment Entry against Sales Invoice
		pe = get_payment_entry(si.doctype, si.name)
		pe.reference_no = "TEST-PAY-003"
		pe.reference_date = nowdate()
		pe.insert(ignore_permissions=True)
		pe.submit()

		# Verify all are submitted
		so.reload()
		dn.reload()
		si.reload()
		pe.reload()
		self.assertEqual(so.docstatus, 1)
		self.assertEqual(dn.docstatus, 1)
		self.assertEqual(si.docstatus, 1)
		self.assertEqual(pe.docstatus, 1)

		# 6. Create and submit Return Sales Invoice
		return_doc = make_return_doc("Sales Invoice", si.name)
		return_doc.insert(ignore_permissions=True)
		return_doc.submit()

		# 7. Verify: SO cancelled, DN cancelled, PE cancelled, Serial No active
		pe.reload()
		dn.reload()
		so.reload()
		self.assertEqual(pe.docstatus, 2)
		self.assertEqual(dn.docstatus, 2)
		self.assertEqual(so.docstatus, 2)
		self.assertEqual(frappe.db.get_value("Serial No", serial_no_id, "status"), "Active")
		self.assertEqual(return_doc.docstatus, 1)

	def test_draft_dn_is_ignored_and_serial_activated(self):
		company = frappe.db.get_value("Company", {}, "name") or "marwan"
		customer = frappe.db.get_value("Customer", {}, "name") or "marwan"
		item = frappe.db.get_value("Item", {"is_sales_item": 1, "has_serial_no": 1}, "name") or "marwan code"
		warehouse = frappe.db.get_value("Warehouse", {"company": company, "is_group": 0}, "name") or "Stores - M"

		serial_no_id = f"TEST-SN-{frappe.generate_hash(length=6)}"
		make_stock_entry(
			item_code=item,
			target=warehouse,
			qty=1,
			basic_rate=100,
			serial_no=serial_no_id,
		)

		so = frappe.get_doc({
			"doctype": "Sales Order",
			"company": company,
			"customer": customer,
			"delivery_date": nowdate(),
			"items": [
				{
					"item_code": item,
					"qty": 1,
					"rate": 100,
					"warehouse": warehouse,
				}
			],
		})
		so.set_missing_values()
		so.insert(ignore_permissions=True)
		so.submit()

		si = make_sales_invoice_from_so(so.name)
		si.items[0].serial_no = serial_no_id
		si.insert(ignore_permissions=True)
		si.submit()

		# Create Delivery Note in DRAFT state (docstatus == 0)
		dn = make_delivery_note(so.name)
		dn.items[0].serial_no = serial_no_id
		dn.insert(ignore_permissions=True)

		pe = get_payment_entry(si.doctype, si.name)
		pe.reference_no = "TEST-PAY-004"
		pe.reference_date = nowdate()
		pe.insert(ignore_permissions=True)
		pe.submit()

		# Set serial number to Inactive manually to test activation
		frappe.db.set_value("Serial No", serial_no_id, "status", "Inactive")

		# Submit return invoice
		return_doc = make_return_doc("Sales Invoice", si.name)
		return_doc.insert(ignore_permissions=True)
		return_doc.submit()

		pe.reload()
		dn.reload()
		so.reload()
		# Draft DN remains draft (0)
		self.assertEqual(dn.docstatus, 0)
		# SO and PE are cancelled (2)
		self.assertEqual(so.docstatus, 2)
		self.assertEqual(pe.docstatus, 2)
		# Serial No is Active
		self.assertEqual(frappe.db.get_value("Serial No", serial_no_id, "status"), "Active")
