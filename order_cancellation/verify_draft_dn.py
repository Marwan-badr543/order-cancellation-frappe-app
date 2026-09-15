import frappe
from order_cancellation.create_test_data import create_demo_data_for_user
from erpnext.controllers.sales_and_purchase_return import make_return_doc


def test_draft_dn_workflow():
	print("\n--- STEP 1: Creating dataset with DRAFT Delivery Note ---")
	data = create_demo_data_for_user(submit_dn=False)
	si_name = data["sales_invoice"]
	so_name = data["sales_order"]
	dn_name = data["delivery_note"]
	pe_name = data["payment_entry"]
	sn_id = data["serial_no"]

	print("\n--- STEP 2: Verifying initial statuses ---")
	print(f"Sales Invoice {si_name} docstatus: {frappe.db.get_value('Sales Invoice', si_name, 'docstatus')}")
	print(f"Sales Order   {so_name} docstatus: {frappe.db.get_value('Sales Order', so_name, 'docstatus')}")
	print(f"Delivery Note {dn_name} docstatus: {frappe.db.get_value('Delivery Note', dn_name, 'docstatus')} (Draft)")
	print(f"Payment Entry {pe_name} docstatus: {frappe.db.get_value('Payment Entry', pe_name, 'docstatus')}")
	print(f"Serial No     {sn_id} status   : {frappe.db.get_value('Serial No', sn_id, 'status')}")

	assert frappe.db.get_value("Delivery Note", dn_name, "docstatus") == 0, "Delivery Note should be draft"

	print("\n--- STEP 3: Creating and Submitting Return Sales Invoice ---")
	return_doc = make_return_doc("Sales Invoice", si_name)
	return_doc.insert(ignore_permissions=True)
	return_doc.submit()
	print(f"-> Return Invoice submitted successfully: {return_doc.name}")

	print("\n--- STEP 4: Verifying final statuses ---")
	so_status = frappe.db.get_value("Sales Order", so_name, "docstatus")
	dn_status = frappe.db.get_value("Delivery Note", dn_name, "docstatus")
	pe_status = frappe.db.get_value("Payment Entry", pe_name, "docstatus")
	sn_status = frappe.db.get_value("Serial No", sn_id, "status")

	print(f"Sales Order   {so_name} docstatus: {so_status} (Expected: 2 - Cancelled)")
	print(f"Delivery Note {dn_name} docstatus: {dn_status} (Expected: 0 - Draft / Untouched)")
	print(f"Payment Entry {pe_name} docstatus: {pe_status} (Expected: 2 - Cancelled)")
	print(f"Serial Number {sn_id} status   : {sn_status} (Expected: Active)")

	assert so_status == 2, "Sales Order was not cancelled"
	assert dn_status == 0, "Draft Delivery Note should remain draft (0)"
	assert pe_status == 2, "Payment Entry was not cancelled"
	assert sn_status == "Active", "Serial No was not set to Active"

	frappe.db.commit()

	print("\n" + "=" * 60)
	print("DRAFT DN WORKFLOW PASSED ALL VERIFICATIONS!")
	print("=" * 60)


if __name__ == "__main__":
	test_draft_dn_workflow()
