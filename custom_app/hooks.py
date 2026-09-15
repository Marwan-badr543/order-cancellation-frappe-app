app_name = "custom_app"
app_title = "Custom App"
app_publisher = "Marwan Badr"
app_description = "Custom App to cancel payment entry, sales order, delivery note and activate serial numbers on return invoice submission"
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
		"on_submit": "custom_app.utils.on_return_invoice_on_submit",
	},
	"Purchase Invoice": {
		"before_submit": "custom_app.utils.on_return_invoice_before_submit",
	},
	"POS Invoice": {
		"before_submit": "custom_app.utils.on_return_invoice_before_submit",
	},
}
