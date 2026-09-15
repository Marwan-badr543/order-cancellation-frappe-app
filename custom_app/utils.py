import frappe
from frappe import _


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


def on_return_invoice_before_submit(doc, method=None):
	"""
	Doc event triggered before submitting a return invoice.
	Cancels all submitted Payment Entries linked to the original invoice.
	"""
	if getattr(doc, "is_return", 0) and getattr(doc, "return_against", None):
		cancel_linked_payment_entries(doc.doctype, doc.return_against)
