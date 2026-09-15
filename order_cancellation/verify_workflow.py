import frappe
from order_cancellation.create_test_data import create_demo_data_for_user
from erpnext.controllers.sales_and_purchase_return import make_return_doc


def test_full_cancellation_workflow():
	print("\n--- STEP 1: Creating full dataset ---")
	data = create_demo_data_for_user()
	si_name = data["sales_invoice"]
	so_name = data["sales_order"]
	dn_name = data["delivery_note"]
	pe_name = data["payment_entry"]
	sn_id = data["serial_no"]

	print("\n--- STEP 2: Verifying initial statuses ---")
	print(f"Sales Invoice {si_name} docstatus: {frappe.db.get_value('Sales Invoice', si_name, 'docstatus')}")
	print(f"Sales Order   {so_name} docstatus: {frappe.db.get_value('Sales Order', so_name, 'docstatus')}")
	print(f"Delivery Note {dn_name} docstatus: {frappe.db.get_value('Delivery Note', dn_name, 'docstatus')}")
	print(f"Payment Entry {pe_name} docstatus: {frappe.db.get_value('Payment Entry', pe_name, 'docstatus')}")
	print(f"Serial No     {sn_id} status   : {frappe.db.get_value('Serial No', sn_id, 'status')}")

	print("\n--- STEP 3: Creating Return / Credit Note (Draft) ---")
	return_doc = make_return_doc("Sales Invoice", si_name)
	return_doc.insert(ignore_permissions=True)
	print(f"-> Draft Return Invoice created: {return_doc.name}")

	# Check that nothing is cancelled yet in draft
	assert frappe.db.get_value("Payment Entry", pe_name, "docstatus") == 1, "Payment Entry should still be submitted in draft return"
	assert frappe.db.get_value("Delivery Note", dn_name, "docstatus") == 1, "Delivery Note should still be submitted in draft return"
	assert frappe.db.get_value("Sales Order", so_name, "docstatus") == 1, "Sales Order should still be submitted in draft return"
	print("-> Verified: Draft return did NOT cancel any linked documents.")

	print("\n--- STEP 4: Submitting Return / Credit Note ---")
	return_doc.submit()
	print(f"-> Return Invoice submitted: {return_doc.name} (docstatus: {return_doc.docstatus})")

	print("\n--- STEP 5: Verifying all linked documents are CANCELLED and serial is ACTIVE ---")
	so_status = frappe.db.get_value("Sales Order", so_name, "docstatus")
	dn_status = frappe.db.get_value("Delivery Note", dn_name, "docstatus")
	pe_status = frappe.db.get_value("Payment Entry", pe_name, "docstatus")
	sn_status = frappe.db.get_value("Serial No", sn_id, "status")

	print(f"Sales Order   {so_name} docstatus: {so_status} (Expected: 2 - Cancelled)")
	print(f"Delivery Note {dn_name} docstatus: {dn_status} (Expected: 2 - Cancelled)")
	print(f"Payment Entry {pe_name} docstatus: {pe_status} (Expected: 2 - Cancelled)")
	print(f"Serial Number {sn_id} status   : {sn_status} (Expected: Active)")

	assert so_status == 2, "Sales Order was not cancelled"
	assert dn_status == 2, "Delivery Note was not cancelled"
	assert pe_status == 2, "Payment Entry was not cancelled"
	assert sn_status == "Active", "Serial No was not set to Active"

	frappe.db.commit()

	print("\n" + "=" * 50)
	print("ALL CHECKS PASSED SUCCESSFULLY!")
	print("=" * 50)


if __name__ == "__main__":
	test_full_cancellation_workflow()
