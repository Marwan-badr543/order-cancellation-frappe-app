frappe.ui.form.on("Purchase Invoice", {
	refresh: function (frm) {
		if (frm.doc.docstatus === 1 && !frm.doc.is_return) {
			if (
				frm.doc.outstanding_amount >= 0 ||
				Math.abs(flt(frm.doc.outstanding_amount)) < flt(frm.doc.grand_total)
			) {
				frm.add_custom_button(
					__("Return / Debit Note"),
					function () {
						frappe.model.open_mapped_doc({
							method: "erpnext.accounts.doctype.purchase_invoice.purchase_invoice.make_debit_note",
							frm: frm,
						});
					},
					__("Create")
				);
			}
		}
	},
});
