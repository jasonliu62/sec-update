import re
import os

def update_12b_section(msft_path, aapl_path, output_path=None):
    with open(msft_path, 'r', encoding='utf-8') as f:
        msft_html = f.read()
    with open(aapl_path, 'r', encoding='utf-8') as f:
        aapl_html = f.read()

    fields = ["Security12bTitle", "TradingSymbol", "SecurityExchangeName"]
    msft_blocks = {}
    aapl_values = {}

    for field in fields:
        pattern = fr'(<ix:nonNumeric[^>]+name="dei:{field}"[^>]*>)(.*?)(</ix:nonNumeric>)'
        msft_blocks[field] = list(re.finditer(pattern, msft_html, re.DOTALL))
        aapl_values[field] = [m.group(2) for m in re.finditer(pattern, aapl_html, re.DOTALL)]

    fallback_symbol = aapl_values["TradingSymbol"][0] if aapl_values["TradingSymbol"] else "AAPL"
    max_rows = max(
        len(aapl_values["Security12bTitle"]),
        len(aapl_values["TradingSymbol"]),
        len(aapl_values["SecurityExchangeName"])
    )

    for field in fields:
        matches = msft_blocks[field]
        aapl_list = aapl_values[field]

        for i in range(max_rows):
            tag_start = matches[i].group(1) if i < len(matches) else matches[-1].group(1)
            tag_end = matches[i].group(3) if i < len(matches) else matches[-1].group(3)

            if field == "TradingSymbol":
                new_val = fallback_symbol
            elif field == "SecurityExchangeName":
                new_val = "Nasdaq"
            else:
                new_val = aapl_list[i] if i < len(aapl_list) else ""

            new_tag = f"{tag_start}{new_val}{tag_end}"

            if i < len(matches):
                msft_html = msft_html.replace(matches[i].group(0), new_tag, 1)
            elif new_val.strip():
                last_tag = matches[-1].group(0)
                msft_html = msft_html.replace(last_tag, last_tag + "\n" + new_tag)

        # Remove extra MSFT rows if AAPL has fewer
        for i in range(max_rows, len(matches)):
            msft_html = msft_html.replace(matches[i].group(0), '')

    if not output_path:
        output_path = os.path.join(os.path.dirname(msft_path), "msft_updated_12b.htm")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(msft_html)

    return f"✅ Updated file saved to: {output_path}"
