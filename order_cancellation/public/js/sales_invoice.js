frappe.provide("erpnext.accounts");

if (erpnext.accounts.SalesInvoiceController) {
	erpnext.accounts.SalesInvoiceController.prototype.make_sales_return = function () {
		frappe.model.open_mapped_doc({
			method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.make_sales_return",
			frm: cur_frm,
		});
	};
}

frappe.ui.form.on("Sales Invoice", {
	refresh: function (frm) {
		if (frm.doc.docstatus === 1 && !frm.doc.is_return) {
			if (
				frm.doc.outstanding_amount >= 0 ||
				Math.abs(flt(frm.doc.outstanding_amount)) < flt(frm.doc.grand_total)
			) {
				frm.add_custom_button(
					__("Return / Credit Note"),
					function () {
						frappe.model.open_mapped_doc({
							method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.make_sales_return",
							frm: frm,
						});
					},
					__("Create")
				);
				frm.page.set_inner_btn_group_as_primary(__("Create"));
			}
		}
	},
});
