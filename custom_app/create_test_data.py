import frappe
from frappe.utils import nowdate
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry


def create_demo_data_for_user():
	company = frappe.db.get_value("Company", {}, "name") or "marwan"
	customer = frappe.db.get_value("Customer", {}, "name") or "marwan"
	item = frappe.db.get_value("Item", {"is_sales_item": 1, "has_serial_no": 1}, "name") or "marwan code"
	warehouse = frappe.db.get_value("Warehouse", {"company": company, "is_group": 0}, "name") or "Stores - M"

	# Generate a unique serial number
	serial_no_id = f"SN-TEST-{frappe.generate_hash(length=6).upper()}"

	print(f"Creating stock receipt for Serial No: {serial_no_id}...")
	make_stock_entry(
		item_code=item,
		target=warehouse,
		qty=1,
		basic_rate=150,
		serial_no=serial_no_id,
	)

	print("Creating Sales Order...")
	so = frappe.get_doc({
		"doctype": "Sales Order",
		"company": company,
		"customer": customer,
		"delivery_date": nowdate(),
		"items": [
			{
				"item_code": item,
				"qty": 1,
				"rate": 150,
				"warehouse": warehouse,
			}
		],
	})
	so.set_missing_values()
	so.insert(ignore_permissions=True)
	so.submit()
	print(f"-> Sales Order created and submitted: {so.name}")

	print("Creating Delivery Note...")
	dn = make_delivery_note(so.name)
	dn.items[0].serial_no = serial_no_id
	dn.insert(ignore_permissions=True)
	dn.submit()
	print(f"-> Delivery Note created and submitted: {dn.name}")

	print("Creating Sales Invoice...")
	si = make_sales_invoice(dn.name)
	si.items[0].serial_no = serial_no_id
	si.insert(ignore_permissions=True)
	si.submit()
	print(f"-> Sales Invoice created and submitted: {si.name}")

	print("Creating Payment Entry...")
	pe = get_payment_entry(si.doctype, si.name)
	pe.reference_no = f"PAY-{frappe.generate_hash(length=4).upper()}"
	pe.reference_date = nowdate()
	pe.insert(ignore_permissions=True)
	pe.submit()
	print(f"-> Payment Entry created and submitted: {pe.name}")

	# Check current Serial No status
	sn_status = frappe.db.get_value("Serial No", serial_no_id, "status")
	print(f"-> Serial Number status is currently: {sn_status}")

	frappe.db.commit()

	print("\n" + "=" * 50)
	print("TEST DATA CREATED SUCCESSFULLY:")
	print(f"Sales Invoice : {si.name} (Status: Paid)")
	print(f"Sales Order   : {so.name}")
	print(f"Delivery Note : {dn.name}")
	print(f"Payment Entry : {pe.name}")
	print(f"Serial Number : {serial_no_id} (Status: {sn_status})")
	print("=" * 50)

	return {
		"sales_invoice": si.name,
		"sales_order": so.name,
		"delivery_note": dn.name,
		"payment_entry": pe.name,
		"serial_no": serial_no_id,
	}


if __name__ == "__main__":
	create_demo_data_for_user()
