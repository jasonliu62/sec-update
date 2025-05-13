import re
import os
from pathlib import Path

def update_12b_section(msft_path, aapl_path, output_path=None):
    with open(aapl_path, 'r', encoding='utf-8') as f:
        aapl_html = f.read()

    fields = ["Security12bTitle", "TradingSymbol", "SecurityExchangeName"]
    msft_blocks = {}
    aapl_values = {}

    for field in fields:
        pattern = fr'(<ix:nonNumeric[^>]+name="dei:{field}"[^>]*>)(.*?)(</ix:nonNumeric>)'
        aapl_values[field] = [m.group(2) for m in re.finditer(pattern, aapl_html, re.DOTALL)]

    fallback_symbol = aapl_values["TradingSymbol"][0] if aapl_values["TradingSymbol"] else "AAPL"
    max_rows = max(len(aapl_values[field]) for field in fields)

    msft_path = parse_stock_first(msft_path, max_rows)

    with open(msft_path, 'r', encoding='utf-8') as f:
        msft_html = f.read()

    updated_html = msft_html

    for field in fields:
        pattern = fr'(<ix:nonNumeric[^>]+name="dei:{field}"[^>]*>)(.*?)(</ix:nonNumeric>)'
        msft_blocks[field] = list(re.finditer(pattern, msft_html, re.DOTALL))


    # Step 2: Replace data fields inside repeated blocks
    # Get new matches from updated_html
    for field in fields:
        pattern = fr'(<ix:nonNumeric[^>]+name="dei:{field}"[^>]*>)(.*?)(</ix:nonNumeric>)'
        new_matches = list(re.finditer(pattern, updated_html, re.DOTALL))
        aapl_list = aapl_values[field]

        if len(new_matches) < max_rows:
            raise ValueError(
                f"Expected at least {max_rows} <ix:nonNumeric> tags for {field}, found {len(new_matches)}.")

        for i in range(max_rows):
            tag_start = new_matches[i].group(1)
            tag_end = new_matches[i].group(3)

            if field == "TradingSymbol":
                new_val = fallback_symbol
            elif field == "SecurityExchangeName":
                new_val = "Nasdaq"
            else:
                new_val = aapl_list[i] if i < len(aapl_list) else ""

            new_tag = f"{tag_start}{new_val}{tag_end}"
            updated_html = updated_html.replace(new_matches[i].group(0), new_tag, 1)

    if not output_path:
        output_path = os.path.join(os.path.dirname(msft_path), "msft_updated_12b.htm")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(updated_html)

    return f"✅ Updated file saved to: {output_path}"


def parse_stock_first(msft_path, max_rows):
    # Read the HTML content
    html_content = Path(msft_path).read_text()

    # The exact <tr> block to replicate — must match exactly
    target_tr = '''<tr style="height:10pt;white-space:pre-wrap;word-break:break-word;">
     <td style="padding-top:0in;padding-left:0in;vertical-align:bottom;padding-bottom:0in;padding-right:0in;"><p style="font-size:10pt;margin-top:2pt;font-family:Times New Roman;margin-bottom:0;text-align:left;"><span style="font-family:Arial;"><ix:nonNumeric id="F_90a2aa2b-069a-431b-9289-956d06186026" contextRef="C_01_002" name="dei:Security12bTitle"><span style="color:#000000;white-space:pre-wrap;font-weight:bold;font-kerning:none;min-width:fit-content;">Common stock, $0.00000625 par value per share</span></ix:nonNumeric></span></p></td>
     <td style="padding-top:0in;padding-left:0in;vertical-align:top;padding-bottom:0in;padding-right:0in;text-align:left;"><p style="font-size:10pt;margin-top:2pt;font-family:Times New Roman;margin-bottom:0;text-align:center;"><span style="white-space:pre-wrap;font-family:Arial;font-kerning:none;min-width:fit-content;">&#160;</span></p></td>
     <td style="padding-top:0in;padding-left:0in;vertical-align:bottom;padding-bottom:0in;padding-right:0in;text-align:left;"><p style="font-size:10pt;margin-top:2pt;font-family:Times New Roman;margin-bottom:0;text-align:center;"><span style="font-family:Arial;"><ix:nonNumeric id="F_ff724dc0-c97a-44b6-94e7-bc16e4a380b1" contextRef="C_01_002" name="dei:TradingSymbol"><span style="text-transform:uppercase;color:#000000;white-space:pre-wrap;font-weight:bold;font-kerning:none;min-width:fit-content;">MSFT</span></ix:nonNumeric></span></p></td>
     <td style="padding-top:0in;padding-left:0in;vertical-align:top;padding-bottom:0in;padding-right:0in;"><p style="font-size:10pt;margin-top:2pt;font-family:Times New Roman;margin-bottom:0;text-align:left;"><span style="white-space:pre-wrap;font-family:Arial;font-kerning:none;min-width:fit-content;">&#160;</span></p></td>
     <td style="padding-top:0in;padding-left:0in;vertical-align:bottom;padding-bottom:0in;padding-right:0in;text-align:left;"><p style="font-size:10pt;margin-top:2pt;font-family:Times New Roman;margin-bottom:0;text-align:center;"><span style="font-family:Arial;"><ix:nonNumeric id="F_80771a21-114f-4a5a-a942-722817fdbbda" contextRef="C_01_002" name="dei:SecurityExchangeName" format="ixt-sec:exchnameen"><span style="text-transform:uppercase;color:#000000;white-space:pre-wrap;font-weight:bold;font-kerning:none;min-width:fit-content;">Nasdaq</span></ix:nonNumeric></span></p></td>
    </tr>'''

    # Replace the original block with N copies
    expanded_blocks = []
    for i in range(max_rows):
        new_block = target_tr.replace('F_90a2aa2b-069a-431b-9289-956d06186026', f'F_title_{i}')
        new_block = new_block.replace('F_ff724dc0-c97a-44b6-94e7-bc16e4a380b1', f'F_symbol_{i}')
        new_block = new_block.replace('F_80771a21-114f-4a5a-a942-722817fdbbda', f'F_exchange_{i}')
        expanded_blocks.append(new_block)

    expanded_block = '\n'.join(expanded_blocks)
    updated_html = html_content.replace(target_tr, expanded_block)

    #also needs to update the htm file and the xsd file.
    #todo

    # Save the updated HTML
    Path(msft_path).write_text(updated_html)

    print(f"✅ Modified HTML saved to: {msft_path}")
    return msft_path