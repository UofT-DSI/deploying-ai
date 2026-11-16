EXCHANGE_RATES = {
    "CAD": {"CAD": 1.0, "USD": 0.73, "EUR": 0.67},
    "USD": {"CAD": 1.37, "USD": 1.0, "EUR": 0.92},
    "EUR": {"CAD": 1.49, "USD": 1.09, "EUR": 1.0}
}

def convert_currency(amount, from_currency, to_currency):
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency not in EXCHANGE_RATES:
        return {"error": f"Unsupported currency: {from_currency}"}

    if to_currency not in EXCHANGE_RATES[from_currency]:
        return {"error": f"Unsupported currency: {to_currency}"}

    converted_amount = amount * EXCHANGE_RATES[from_currency][to_currency]

    return {
        "amount": amount,
        "from_currency": from_currency,
        "to_currency": to_currency,
        "converted_amount": round(converted_amount, 2)
    }