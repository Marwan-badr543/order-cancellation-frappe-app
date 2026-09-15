import frappe
from frappe import _
import erpnext.controllers.sales_and_purchase_return


def cancel_linked_payment_entries(doctype: str, docname: str):
	"""
	Finds and cancels all submitted Payment Entries linked to the specified invoice.
	"""
	if not doctype or not docname:
		return []

	# Get all submitted Payment Entries referencing this invoice in tabPayment Entry Reference
	payment_entries = frappe.db.sql(
		"""
		SELECT DISTINCT per.parent
		FROM `tabPayment Entry Reference` per
		INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent
		WHERE per.reference_doctype = %s
		  AND per.reference_name = %s
		  AND pe.docstatus = 1
		""",
		(doctype, docname),
		as_dict=True,
	)

	cancelled = []
	for row in payment_entries:
		pe_name = row.parent
		try:
			pe_doc = frappe.get_doc("Payment Entry", pe_name)
			if pe_doc.docstatus == 1:
				pe_doc.cancel()
				cancelled.append(pe_name)
		except Exception as e:
			frappe.log_error(
				title=_("Failed to cancel Payment Entry {0} on return of {1} {2}").format(
					pe_name, doctype, docname
				),
				message=frappe.get_traceback(),
			)
			frappe.throw(
				_("Failed to cancel linked Payment Entry {0}: {1}").format(
					pe_name, str(e)
				)
			)

	if cancelled:
		msg = _("Cancelled linked Payment Entry: {0}").format(", ".join(cancelled))
		frappe.msgprint(msg, alert=True)

	return cancelled


@frappe.whitelist()
def make_sales_return(source_name, target_doc=None):
	"""
	Overridden handler for Sales Invoice return / credit note.
	Cancels any linked Payment Entry for the original invoice before creating the return document.
	"""
	cancel_linked_payment_entries("Sales Invoice", source_name)
	return erpnext.controllers.sales_and_purchase_return.make_return_doc(
		"Sales Invoice", source_name, target_doc
	)


@frappe.whitelist()
def make_debit_note(source_name, target_doc=None):
	"""
	Overridden handler for Purchase Invoice return / debit note.
	Cancels any linked Payment Entry for the original invoice before creating the return document.
	"""
	cancel_linked_payment_entries("Purchase Invoice", source_name)
	return erpnext.controllers.sales_and_purchase_return.make_return_doc(
		"Purchase Invoice", source_name, target_doc
	)


@frappe.whitelist()
def make_pos_sales_return(source_name, target_doc=None):
	"""
	Overridden handler for POS Invoice return.
	Cancels any linked Payment Entry for the original invoice before creating the return document.
	"""
	cancel_linked_payment_entries("POS Invoice", source_name)
	return erpnext.controllers.sales_and_purchase_return.make_return_doc(
		"POS Invoice", source_name, target_doc
	)


@frappe.whitelist()
def custom_make_return_doc(doctype: str, source_name: str, target_doc=None):
	"""
	Overridden handler for general make_return_doc.
	Cancels linked payment entries if doctype is Sales Invoice, Purchase Invoice, or POS Invoice.
	"""
	if doctype in ("Sales Invoice", "Purchase Invoice", "POS Invoice"):
		cancel_linked_payment_entries(doctype, source_name)
	return erpnext.controllers.sales_and_purchase_return.make_return_doc(
		doctype, source_name, target_doc
	)


def on_return_invoice_before_submit(doc, method=None):
	"""
	Doc event triggered before submitting a return invoice.
	Ensures that any remaining submitted Payment Entries linked to the original invoice are cancelled.
	"""
	if getattr(doc, "is_return", 0) and getattr(doc, "return_against", None):
		cancel_linked_payment_entries(doc.doctype, doc.return_against)
