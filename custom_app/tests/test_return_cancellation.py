import unittest
import frappe
from frappe.utils import flt, nowdate
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from custom_app.utils import (
	cancel_linked_payment_entries,
	make_sales_return,
	custom_make_return_doc,
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

	def test_cancel_linked_payment_entries_function(self):
		si, pe = self._create_paid_sales_invoice()
		self.assertEqual(pe.docstatus, 1)

		cancelled = cancel_linked_payment_entries("Sales Invoice", si.name)
		self.assertIn(pe.name, cancelled)

		pe.reload()
		self.assertEqual(pe.docstatus, 2)

	def test_make_sales_return_cancels_payment_entry(self):
		si, pe = self._create_paid_sales_invoice()
		self.assertEqual(pe.docstatus, 1)

		return_doc = make_sales_return(si.name)

		pe.reload()
		self.assertEqual(pe.docstatus, 2)
		self.assertEqual(return_doc.is_return, 1)
		self.assertEqual(return_doc.return_against, si.name)
		self.assertEqual(flt(return_doc.items[0].qty), -1)

	def test_custom_make_return_doc_cancels_payment_entry(self):
		si, pe = self._create_paid_sales_invoice()
		self.assertEqual(pe.docstatus, 1)

		return_doc = custom_make_return_doc("Sales Invoice", si.name)

		pe.reload()
		self.assertEqual(pe.docstatus, 2)
		self.assertEqual(return_doc.is_return, 1)
		self.assertEqual(return_doc.return_against, si.name)

	def test_return_invoice_submission_cancels_payment_entry(self):
		si, pe = self._create_paid_sales_invoice()
		self.assertEqual(pe.docstatus, 1)

		return_doc = custom_make_return_doc("Sales Invoice", si.name)
		return_doc.insert(ignore_permissions=True)
		return_doc.submit()

		pe.reload()
		self.assertEqual(pe.docstatus, 2)
		self.assertEqual(return_doc.docstatus, 1)
