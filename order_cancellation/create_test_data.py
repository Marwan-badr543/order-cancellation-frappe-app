import frappe
from frappe.utils import nowdate
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.selling.doctype.sales_order.sales_order import (
	make_delivery_note,
	make_sales_invoice as make_sales_invoice_from_so,
)
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry


def create_demo_data_for_user(submit_dn=False):
	company = frappe.db.get_value("Company", {}, "name") or "marwan"
	customer = frappe.db.get_value("Customer", {}, "name") or "marwan"
	item = frappe.db.get_value("Item", {"is_sales_item": 1, "has_serial_no": 1}, "name") or "marwan code"
	warehouse = frappe.db.get_value("Warehouse", {"company": company, "is_group": 0}, "name") or "Stores - M"

	# 1. Generate unique Serial Number and receive into warehouse
	serial_no_id = f"SN-TEST-{frappe.generate_hash(length=6).upper()}"

	print(f"1. Creating stock receipt for Serial No: {serial_no_id}...")
	make_stock_entry(
		item_code=item,
		target=warehouse,
		qty=1,
		basic_rate=200,
		serial_no=serial_no_id,
	)

	# 2. Create Sales Order (SO)
	print("2. Creating Sales Order...")
	so = frappe.get_doc({
		"doctype": "Sales Order",
		"company": company,
		"customer": customer,
		"delivery_date": nowdate(),
		"items": [
			{
				"item_code": item,
				"qty": 1,
				"rate": 200,
				"warehouse": warehouse,
			}
		],
	})
	so.set_missing_values()
	so.insert(ignore_permissions=True)
	so.submit()
	print(f"-> Sales Order created and submitted: {so.name}")

	# 3. Create Sales Invoice (SI) from Sales Order (NOT from Delivery Note)
	print("3. Creating Sales Invoice from Sales Order...")
	si = make_sales_invoice_from_so(so.name)
	si.items[0].serial_no = serial_no_id
	si.insert(ignore_permissions=True)
	si.submit()
	print(f"-> Sales Invoice created and submitted: {si.name} (Linked to SO: {so.name}, Delivery Note: None)")

	# 4. Create Delivery Note (DN) from Sales Order (NOT connected to Sales Invoice)
	print("4. Creating Delivery Note from Sales Order...")
	dn = make_delivery_note(so.name)
	dn.items[0].serial_no = serial_no_id
	dn.insert(ignore_permissions=True)
	if submit_dn:
		dn.submit()
		dn_status_label = "Submitted"
	else:
		dn_status_label = "Draft"
		# Set serial number status to Inactive to test that it gets re-activated
		frappe.db.set_value("Serial No", serial_no_id, "status", "Inactive")
	print(f"-> Delivery Note created ({dn_status_label}): {dn.name} (Linked to SO: {so.name})")

	# 5. Create Payment Entry against Sales Invoice
	print("5. Creating Payment Entry for Sales Invoice...")
	pe = get_payment_entry(si.doctype, si.name)
	pe.reference_no = f"PAY-{frappe.generate_hash(length=4).upper()}"
	pe.reference_date = nowdate()
	pe.insert(ignore_permissions=True)
	pe.submit()
	print(f"-> Payment Entry created and submitted: {pe.name}")

	# Check current Serial No status
	sn_status = frappe.db.get_value("Serial No", serial_no_id, "status")

	frappe.db.commit()

	print("\n" + "=" * 60)
	print("NEW TEST DATA CREATED SUCCESSFULLY:")
	print(f"Sales Invoice : {si.name} (Status: Paid, Linked to SO: {so.name})")
	print(f"Sales Order   : {so.name} (Status: Submitted)")
	print(f"Delivery Note : {dn.name} (Status: {dn_status_label}, Linked to SO: {so.name})")
	print(f"Payment Entry : {pe.name} (Status: Submitted)")
	print(f"Serial Number : {serial_no_id} (Status: {sn_status})")
	print("=" * 60)

	return {
		"sales_invoice": si.name,
		"sales_order": so.name,
		"delivery_note": dn.name,
		"payment_entry": pe.name,
		"serial_no": serial_no_id,
		"dn_status": dn_status_label,
	}


if __name__ == "__main__":
	create_demo_data_for_user(submit_dn=False)
