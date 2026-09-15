app_name = "custom_app"
app_title = "Custom App"
app_publisher = "Marwan Badr"
app_description = "Custom App to cancel payment entry on return invoice"
app_email = "marwanbadr@gmail.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js in doctype views
doctype_js = {
	"Sales Invoice": "public/js/sales_invoice.js",
	"Purchase Invoice": "public/js/purchase_invoice.js",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Sales Invoice": {
		"before_submit": "custom_app.utils.on_return_invoice_before_submit",
	},
	"Purchase Invoice": {
		"before_submit": "custom_app.utils.on_return_invoice_before_submit",
	},
	"POS Invoice": {
		"before_submit": "custom_app.utils.on_return_invoice_before_submit",
	},
}

# Overriding Methods
# ------------------------------

override_whitelisted_methods = {
	"erpnext.accounts.doctype.sales_invoice.sales_invoice.make_sales_return": "custom_app.utils.make_sales_return",
	"erpnext.accounts.doctype.purchase_invoice.purchase_invoice.make_debit_note": "custom_app.utils.make_debit_note",
	"erpnext.accounts.doctype.pos_invoice.pos_invoice.make_sales_return": "custom_app.utils.make_pos_sales_return",
	"erpnext.controllers.sales_and_purchase_return.make_return_doc": "custom_app.utils.custom_make_return_doc",
}
