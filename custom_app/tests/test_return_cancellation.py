import unittest
import frappe
from frappe.utils import flt, nowdate
from erpnext.controllers.sales_and_purchase_return import make_return_doc
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from custom_app.utils import (
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

	def _create_paid_sales_invoice(self, rate=100, qty=1):
		company = frappe.db.get_value("Company", {}, "name") or "marwan"
		customer = frappe.db.get_value("Customer", {}, "name") or "marwan"
		item = frappe.db.get_value("Item", {"is_sales_item": 1}, "name") or "Office Consumables"

		si = frappe.get_doc({
			"doctype": "Sales Invoice",
			"company": company,
			"customer": customer,
			"posting_date": nowdate(),
			"due_date": nowdate(),
			"items": [
				{
					"item_code": item,
					"qty": qty,
					"rate": rate,
				}
			],
		})
		si.set_missing_values()
		si.insert(ignore_permissions=True)
		si.submit()

		# Create and submit payment entry against this sales invoice
		pe = get_payment_entry(si.doctype, si.name)
		pe.reference_no = "TEST-PAY-001"
		pe.reference_date = nowdate()
		pe.insert(ignore_permissions=True)
		pe.submit()

		si.reload()
		return si, pe

	def test_creating_draft_return_does_not_cancel_payment_entry(self):
		si, pe = self._create_paid_sales_invoice()
		self.assertEqual(pe.docstatus, 1)

		# User clicks Return / Credit note -> creates draft return document
		return_doc = make_return_doc("Sales Invoice", si.name)

		pe.reload()
		# Payment entry must STILL be submitted (not cancelled)
		self.assertEqual(pe.docstatus, 1)
		self.assertEqual(return_doc.is_return, 1)
		self.assertEqual(return_doc.return_against, si.name)

	def test_submitting_return_invoice_cancels_payment_entry(self):
		si, pe = self._create_paid_sales_invoice()
		self.assertEqual(pe.docstatus, 1)

		return_doc = make_return_doc("Sales Invoice", si.name)
		return_doc.insert(ignore_permissions=True)
		# User submits the return invoice
		return_doc.submit()

		pe.reload()
		# Payment entry must now be cancelled
		self.assertEqual(pe.docstatus, 2)
		self.assertEqual(return_doc.docstatus, 1)

	def test_cancel_linked_documents_and_activate_serials_full_flow(self):
		company = frappe.db.get_value("Company", {}, "name") or "marwan"
		customer = frappe.db.get_value("Customer", {}, "name") or "marwan"
		item = frappe.db.get_value("Item", {"is_sales_item": 1, "has_serial_no": 1}, "name") or "marwan code"
		warehouse = frappe.db.get_value("Warehouse", {"company": company, "is_group": 0}, "name") or "Stores - M"

		# 1. Receive Serial No into warehouse via Stock Entry
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

		# 3. Create Delivery Note from Sales Order
		from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
		dn = make_delivery_note(so.name)
		dn.items[0].serial_no = serial_no_id
		dn.insert(ignore_permissions=True)
		dn.submit()

		# 4. Create Sales Invoice from Delivery Note
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
		si = make_sales_invoice(dn.name)
		si.items[0].serial_no = serial_no_id
		si.insert(ignore_permissions=True)
		si.submit()

		# 5. Create and submit Payment Entry against Sales Invoice
		pe = get_payment_entry(si.doctype, si.name)
		pe.reference_no = "TEST-PAY-002"
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

		# 7. Verify everything is cancelled and serial number is Active
		pe.reload()
		dn.reload()
		so.reload()
		self.assertEqual(pe.docstatus, 2)
		self.assertEqual(dn.docstatus, 2)
		self.assertEqual(so.docstatus, 2)
		self.assertEqual(frappe.db.get_value("Serial No", serial_no_id, "status"), "Active")
		self.assertEqual(return_doc.docstatus, 1)
