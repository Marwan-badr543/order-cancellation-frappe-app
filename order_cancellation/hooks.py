app_name = "order_cancellation"
app_title = "Order Cancellation"
app_publisher = "Marwan Badr"
app_description = "Frappe App to cancel linked Payment Entries, Sales Orders, Delivery Notes and activate Serial Numbers on return invoice submission"
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
		"validate": "order_cancellation.utils.on_return_invoice_validate",
		"before_submit": "order_cancellation.utils.on_return_invoice_before_submit",
		"on_submit": "order_cancellation.utils.on_return_invoice_on_submit",
	},
	"Purchase Invoice": {
		"before_submit": "order_cancellation.utils.on_return_invoice_before_submit",
	},
	"POS Invoice": {
		"before_submit": "order_cancellation.utils.on_return_invoice_before_submit",
	},
}
