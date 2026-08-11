PRODUCT_HTML_FIXTURE = """<!doctype html>
<html lang="en">
  <head>
    <title>Pulse Mix</title>
    <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Pulse Mix",
        "description": "Energy powder in a <strong>resealable</strong> pouch.\\u003cscript\\u003ebad()\\u003c/script\\u003e",
        "category": "Food > Drink Mix",
        "image": ["https://example.com/pulse.png"],
        "offers": {
          "@type": "Offer",
          "price": "19.90",
          "priceCurrency": "usd"
        },
        "ignoredPrivateField": "must not be retained"
      }
    </script>
  </head>
  <body>Public product page.</body>
</html>
"""
