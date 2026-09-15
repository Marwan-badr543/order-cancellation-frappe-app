import frappe
from frappe import _
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos


def cancel_linked_payment_entries(doctype: str, docname: str):
	"""
	Finds and cancels all submitted Payment Entries linked to the specified invoice.
	"""
	if not doctype or not docname:
		return []

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


def get_linked_sales_orders(invoice_name: str):
	"""
	Retrieves all distinct Sales Order names linked to the specified Sales Invoice.
	"""
	if not invoice_name:
		return []

	so_rows = frappe.db.sql(
		"""
		SELECT DISTINCT sales_order
		FROM `tabSales Invoice Item`
		WHERE parent = %s
		  AND sales_order IS NOT NULL
		  AND sales_order != ''
		""",
		(invoice_name,),
		as_dict=True,
	)
	return [row.sales_order for row in so_rows if row.sales_order]


def get_linked_delivery_notes(invoice_name: str, sales_orders=None):
	"""
	Retrieves all distinct Delivery Note names linked directly to the Sales Invoice
	or to the linked Sales Orders.
	"""
	dn_names = set()
	if not invoice_name:
		return []

	# 1. From Sales Invoice Items (delivery_note field)
	dn_from_si = frappe.db.sql(
		"""
		SELECT DISTINCT delivery_note
		FROM `tabSales Invoice Item`
		WHERE parent = %s
		  AND delivery_note IS NOT NULL
		  AND delivery_note != ''
		""",
		(invoice_name,),
		as_dict=True,
	)
	for row in dn_from_si:
		if row.delivery_note:
			dn_names.add(row.delivery_note)

	# 2. From Delivery Note Item referencing this Sales Invoice
	dn_from_dni = frappe.db.sql(
		"""
		SELECT DISTINCT parent
		FROM `tabDelivery Note Item`
		WHERE against_sales_invoice = %s
		""",
		(invoice_name,),
		as_dict=True,
	)
	for row in dn_from_dni:
		if row.parent:
			dn_names.add(row.parent)

	# 3. From Delivery Note Item referencing the linked Sales Orders
	if sales_orders:
		so_list = [so for so in sales_orders if so]
		if so_list:
			dn_from_so = frappe.db.sql(
				"""
				SELECT DISTINCT parent
				FROM `tabDelivery Note Item`
				WHERE against_sales_order IN ({0})
				""".format(", ".join(["%s"] * len(so_list))),
				tuple(so_list),
				as_dict=True,
			)
			for row in dn_from_so:
				if row.parent:
					dn_names.add(row.parent)

	return list(dn_names)


def get_serial_numbers_from_docs(docs):
	"""
	Extracts all serial numbers from the items of given documents.
	"""
	serial_nos = set()
	for doc in docs:
		if not doc:
			continue
		items = doc.get("items") or []
		for item in items:
			if item.get("serial_no"):
				for s in get_serial_nos(item.serial_no):
					if s and s.strip():
						serial_nos.add(s.strip())
			if item.get("serial_and_batch_bundle"):
				try:
					bundle_serials = frappe.db.get_all(
						"Serial and Batch Entry",
						filters={"parent": item.serial_and_batch_bundle},
						pluck="serial_no",
					)
					for s in bundle_serials:
						if s and s.strip():
							serial_nos.add(s.strip())
				except Exception:
					pass
	return list(serial_nos)


def cancel_linked_documents_and_activate_serials(doctype: str, docname: str, return_doc=None):
	"""
	Cancels Payment Entries, Delivery Notes, Sales Orders linked to the invoice,
	and activates all associated Serial Numbers.
	"""
	if doctype != "Sales Invoice" or not docname:
		return

	orig_si = frappe.get_doc("Sales Invoice", docname)

	# 1. Cancel linked Payment Entries
	cancel_linked_payment_entries(doctype, docname)

	# 2. Find linked Sales Orders & Delivery Notes
	sales_orders = get_linked_sales_orders(docname)
	delivery_notes = get_linked_delivery_notes(docname, sales_orders)

	docs_for_serials = [orig_si, return_doc]

	# 3. Cancel linked Delivery Notes (if submitted, docstatus == 1)
	cancelled_dns = []
	for dn_name in delivery_notes:
		if frappe.db.exists("Delivery Note", dn_name):
			dn_doc = frappe.get_doc("Delivery Note", dn_name)
			docs_for_serials.append(dn_doc)
			if dn_doc.docstatus == 1:
				try:
					# Unlink delivery_note reference in Sales Invoice items to bypass check_next_docstatus validation
					frappe.db.sql(
						"""
						UPDATE `tabSales Invoice Item`
						SET delivery_note = ''
						WHERE delivery_note = %s
						""",
						(dn_name,),
					)
					frappe.db.sql(
						"""
						UPDATE `tabDelivery Note Item`
						SET against_sales_invoice = ''
						WHERE parent = %s
						""",
						(dn_name,),
					)
					dn_doc.cancel()
					cancelled_dns.append(dn_name)
				except Exception as e:
					frappe.log_error(
						title=_("Failed to cancel Delivery Note {0}").format(dn_name),
						message=frappe.get_traceback(),
					)
					frappe.throw(
						_("Failed to cancel linked Delivery Note {0}: {1}").format(
							dn_name, str(e)
						)
					)

	# 4. Cancel linked Sales Orders (if submitted, docstatus == 1)
	cancelled_sos = []
	for so_name in sales_orders:
		if frappe.db.exists("Sales Order", so_name):
			so_doc = frappe.get_doc("Sales Order", so_name)
			docs_for_serials.append(so_doc)
			if so_doc.docstatus == 1:
				try:
					# Unlink sales_order reference across all Sales Invoice items to bypass check_nextdoc_docstatus validation
					frappe.db.sql(
						"""
						UPDATE `tabSales Invoice Item`
						SET sales_order = ''
						WHERE sales_order = %s
						""",
						(so_name,),
					)
					if return_doc:
						for item in (return_doc.get("items") or []):
							if getattr(item, "sales_order", None) == so_name:
								item.sales_order = None

					so_doc.cancel()
					cancelled_sos.append(so_name)
				except Exception as e:
					frappe.log_error(
						title=_("Failed to cancel Sales Order {0}").format(so_name),
						message=frappe.get_traceback(),
					)
					frappe.throw(
						_("Failed to cancel linked Sales Order {0}: {1}").format(
							so_name, str(e)
						)
					)

	# 5. Extract all serial numbers and set their status to "Active"
	serial_nos = get_serial_numbers_from_docs(docs_for_serials)
	activated_serials = []
	for sn in serial_nos:
		if frappe.db.exists("Serial No", sn):
			frappe.db.set_value("Serial No", sn, "status", "Active")
			activated_serials.append(sn)

	messages = []
	if cancelled_dns:
		messages.append(_("Cancelled linked Delivery Note(s): {0}").format(", ".join(cancelled_dns)))
	if cancelled_sos:
		messages.append(_("Cancelled linked Sales Order(s): {0}").format(", ".join(cancelled_sos)))
	if activated_serials:
		messages.append(_("Activated Serial Number(s): {0}").format(", ".join(activated_serials)))

	if messages:
		frappe.msgprint("<br>".join(messages), alert=True)


def on_return_invoice_before_submit(doc, method=None):
	"""
	Doc event triggered before submitting a return invoice.
	Cancels all linked documents (Payment Entries, Delivery Notes, Sales Orders)
	and sets serial numbers back to Active.
	"""
	if getattr(doc, "is_return", 0) and getattr(doc, "return_against", None):
		if doc.doctype == "Sales Invoice":
			cancel_linked_documents_and_activate_serials(
				doc.doctype, doc.return_against, return_doc=doc
			)
		else:
			cancel_linked_payment_entries(doc.doctype, doc.return_against)


def on_return_invoice_on_submit(doc, method=None):
	"""
	Doc event triggered on submit to ensure serial numbers remain Active.
	"""
	if getattr(doc, "is_return", 0) and getattr(doc, "return_against", None) and doc.doctype == "Sales Invoice":
		orig_si = frappe.get_doc("Sales Invoice", doc.return_against)
		sales_orders = get_linked_sales_orders(doc.return_against)
		delivery_notes = get_linked_delivery_notes(doc.return_against, sales_orders)
		docs_for_serials = [orig_si, doc]
		for dn_name in delivery_notes:
			if frappe.db.exists("Delivery Note", dn_name):
				docs_for_serials.append(frappe.get_doc("Delivery Note", dn_name))
		for so_name in sales_orders:
			if frappe.db.exists("Sales Order", so_name):
				docs_for_serials.append(frappe.get_doc("Sales Order", so_name))

		serial_nos = get_serial_numbers_from_docs(docs_for_serials)
		for sn in serial_nos:
			if frappe.db.exists("Serial No", sn):
				frappe.db.set_value("Serial No", sn, "status", "Active")
