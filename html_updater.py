import re
import os
from pathlib import Path

def update_12b_section(msft_path, aapl_path, xsd_path, output_path=None):
    with open(aapl_path, 'r', encoding='utf-8') as f:
        aapl_html = f.read()

    fields = ["Security12bTitle", "TradingSymbol", "SecurityExchangeName"]
    aapl_values = {}

    for field in fields:
        pattern = fr'(<ix:nonNumeric[^>]+name="dei:{field}"[^>]*>)(.*?)(</ix:nonNumeric>)'
        aapl_values[field] = [m.group(2) for m in re.finditer(pattern, aapl_html, re.DOTALL)]

    fallback_symbol = aapl_values["TradingSymbol"][0] if aapl_values["TradingSymbol"] else "AAPL"
    max_rows = max(len(aapl_values[field]) for field in fields)

    msft_path = parse_stock_first(msft_path, max_rows)

    with open(msft_path, 'r', encoding='utf-8') as f:
        msft_html = f.read()

    updated_html = update_msft_namespace_and_refs(msft_html, aapl_html)

    fields_to_replace = [
        "EntityRegistrantName",  # Apple Inc.
        "EntityFileNumber",  # 001-36743
        "EntityAddressAddressLine1",  # One Apple Park Way
        "EntityAddressCityOrTown",  # Cupertino
        "EntityAddressStateOrProvince",  # California
        "EntityAddressPostalZipCode",  # 95014
        "CityAreaCode",  # 408
        "LocalPhoneNumber",  # 996-1010
        "EntityIncorporationStateCountryCode",  # California
        "EntityTaxIdentificationNumber",  # 94-2404110
    ]

    updated_html = replace_dei_fields(updated_html, aapl_html, fields_to_replace)

    labels = aapl_values["Security12bTitle"][:max_rows]
    prefix_match = re.search(r'xmlns:([a-z0-9]+)="http://www\.[a-z0-9.-]+/(\d{8})"', aapl_html)
    prefix = prefix_match.group(1)

    cik_match = re.search(r'<xbrli:identifier scheme="http://www.sec.gov/CIK">(\d+)</xbrli:identifier>', aapl_html)
    new_cik = cik_match.group(1)
    # Step 2: Replace data fields inside repeated blocks
    # Get new matches from updated_html
    context_start_index = 3
    context_blocks = []

    # Extract start/end date once
    start_date_match = re.search(r"<xbrli:startDate>(.*?)</xbrli:startDate>", aapl_html)
    end_date_match = re.search(r"<xbrli:endDate>(.*?)</xbrli:endDate>", aapl_html)
    new_start_date = start_date_match.group(1)
    new_end_date = end_date_match.group(1)

    for i in range(max_rows):
        sec_title = aapl_values["Security12bTitle"][i] if i < len(aapl_values["Security12bTitle"]) else ""
        trading_symbol = fallback_symbol
        exchange_name = "Nasdaq"

        # default to no change
        context_id = None

        if "common stock" not in sec_title.lower():
            context_id = f"C_01_00{context_start_index + len(context_blocks)}"
            member_name = normalize_label_to_member(prefix, sec_title)
            context_block = f"""
            <xbrli:context id="{context_id}">
              <xbrli:entity>
                <xbrli:identifier scheme="http://www.sec.gov/CIK">{new_cik}</xbrli:identifier>
                <xbrli:segment>
                  <xbrldi:explicitMember dimension="us-gaap:StatementClassOfStockAxis">{member_name}</xbrldi:explicitMember>
                </xbrli:segment>
              </xbrli:entity>
              <xbrli:period>
                <xbrli:startDate>{new_start_date}</xbrli:startDate>
                <xbrli:endDate>{new_end_date}</xbrli:endDate>
              </xbrli:period>
            </xbrli:context>
            """
            context_blocks.append(context_block)

        # Replace 12bTitle, TradingSymbol, ExchangeName
        for field, value in zip(
                ["Security12bTitle", "TradingSymbol", "SecurityExchangeName"],
                [sec_title, trading_symbol, exchange_name]
        ):
            pattern = fr'(<ix:nonNumeric[^>]+name="dei:{field}"[^>]*>)(.*?)(</ix:nonNumeric>)'
            matches = list(re.finditer(pattern, updated_html, re.DOTALL))
            if i >= len(matches):
                raise ValueError(f"Not enough <ix:nonNumeric> matches for {field} at row {i}")

            full_tag = matches[i].group(0)

            # Only replace contextRef if we made a new one
            if context_id:
                new_tag = re.sub(r'contextRef="[^"]+"', f'contextRef="{context_id}"', matches[i].group(1))
                new_tag = f"{new_tag}{value}{matches[i].group(3)}"
                updated_html = updated_html.replace(full_tag, new_tag, 1)
            else:
                # Replace value but leave contextRef untouched
                new_tag = f"{matches[i].group(1)}{value}{matches[i].group(3)}"
                updated_html = updated_html.replace(full_tag, new_tag, 1)

    # Inject all contexts before </ix:resources>
    updated_html = re.sub(r"(</ix:resources>)", '\n'.join(context_blocks) + r"\1", updated_html, count=1)


    if not output_path:
        output_path = os.path.join(os.path.dirname(msft_path), "msft_updated_12b.htm")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(updated_html)

    return f"✅ Updated file saved to: {output_path}"

def normalize_label_to_member(prefix: str, label: str) -> str:
    # Match the pattern like "0.000% Notes due 2025"
    # Goal: Extract the part after "Notes" and before "due", and the year after "due"
    match = re.search(r'Notes\s*(.*?)\s*due\s*(\d+)', label, re.IGNORECASE)
    if match:
        amount = re.sub(r'\D', '', match.group(1)) or "0000"
        year = match.group(2)
        return f"{prefix}:Notes{amount}due{year}Member"
    else:
        # fallback, just remove bad chars
        clean = re.sub(r'[^A-Za-z0-9]', '', label)
        return f"{prefix}:{clean}Member"


def parse_stock_first(msft_path, max_rows):
    # Read the HTML content
    html_content = Path(msft_path).read_text()

    # The exact <tr> block to replicate — must match exactly
    target_tr = '''<tr style="height:10pt;white-space:pre-wrap;word-break:break-word;">
     <td style="padding-top:0in;padding-left:0in;vertical-align:bottom;padding-bottom:0in;padding-right:0in;"><p style="font-size:10pt;margin-top:2pt;font-family:Times New Roman;margin-bottom:0;text-align:left;"><span style="font-family:Arial;"><ix:nonNumeric id="F_90a2aa2b-069a-431b-9289-956d06186026" contextRef="C_01_002" name="dei:Security12bTitle"><span style="color:#000000;white-space:pre-wrap;font-weight:bold;font-kerning:none;min-width:fit-content;">Common stock, $0.00000625 par value per share</span></ix:nonNumeric></span></p></td>
     <td style="padding-top:0in;padding-left:0in;vertical-align:top;padding-bottom:0in;padding-right:0in;text-align:left;"><p style="font-size:10pt;margin-top:2pt;font-family:Times New Roman;margin-bottom:0;text-align:center;"><span style="white-space:pre-wrap;font-family:Arial;font-kerning:none;min-width:fit-content;">&#160;</span></p></td>
     <td style="padding-top:0in;padding-left:0in;vertical-align:bottom;padding-bottom:0in;padding-right:0in;text-align:left;"><p style="font-size:10pt;margin-top:2pt;font-family:Times New Roman;margin-bottom:0;text-align:center;"><span style="font-family:Arial;"><ix:nonNumeric id="F_ff724dc0-c97a-44b6-94e7-bc16e4a380b1" contextRef="C_01_002" name="dei:TradingSymbol"><span style="text-transform:uppercase;color:#000000;white-space:pre-wrap;font-weight:bold;font-kerning:none;min-width:fit-content;">EXAP</span></ix:nonNumeric></span></p></td>
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

    # Save the updated HTML
    Path(msft_path).write_text(updated_html)

    print(f"✅ Modified HTML saved to: {msft_path}")
    return msft_path

def update_msft_namespace_and_refs(msft_html: str, aapl_html: str) -> str:
    # Replace <html> tag
    old_html_tag = re.search(r"<html[^>]*>", msft_html)
    new_html_tag = re.search(r"<html[^>]*>", aapl_html)
    if old_html_tag and new_html_tag:
        msft_html = msft_html.replace(old_html_tag.group(0), new_html_tag.group(0))

    # Replace xlink:href
    aapl_xsd_match = re.search(r'xlink:href="([^"]+\.xsd)"', aapl_html)
    if aapl_xsd_match:
        aapl_xsd_href = aapl_xsd_match.group(1)
        msft_html = re.sub(r'xlink:href="[^"]+\.xsd"', f'xlink:href="{aapl_xsd_href}"', msft_html)

    # Replace CIK
    cik_match = re.search(r'<xbrli:identifier scheme="http://www.sec.gov/CIK">(\d+)</xbrli:identifier>', aapl_html)

    if cik_match:
        new_cik = cik_match.group(1)
        msft_html = re.sub(
            r'(<xbrli:identifier scheme="http://www.sec.gov/CIK">)(\d+)(</xbrli:identifier>)',
            lambda m: f"{m.group(1)}{new_cik}{m.group(3)}",
            msft_html
        )

    update_dates_from_reference(msft_html, aapl_html)
    return msft_html


def update_dates_from_reference(msft_html: str, aapl_html: str) -> str:
    # Extract first startDate and endDate from AAPL file
    start_date_match = re.search(r"<xbrli:startDate>(.*?)</xbrli:startDate>", aapl_html)
    end_date_match = re.search(r"<xbrli:endDate>(.*?)</xbrli:endDate>", aapl_html)

    if not (start_date_match and end_date_match):
        raise ValueError("StartDate or EndDate not found in replacement file.")

    new_start_date = start_date_match.group(1)
    new_end_date = end_date_match.group(1)

    # Replace all startDate and endDate in MSFT file
    msft_html = re.sub(r"<xbrli:startDate>.*?</xbrli:startDate>", f"<xbrli:startDate>{new_start_date}</xbrli:startDate>", msft_html)
    msft_html = re.sub(r"<xbrli:endDate>.*?</xbrli:endDate>", f"<xbrli:endDate>{new_end_date}</xbrli:endDate>", msft_html)

    return msft_html


def replace_dei_fields(msft_html: str, aapl_html: str, fields: list) -> str:
    """
    Replace specific <ix:nonNumeric> dei fields from AAPL into MSFT HTML content.
    """
    for field in fields:
        pattern = fr'(<ix:nonNumeric[^>]+name="dei:{field}"[^>]*>)(.*?)(</ix:nonNumeric>)'

        # Extract from AAPL
        aapl_match = re.search(pattern, aapl_html, re.DOTALL)
        if not aapl_match:
            continue  # Skip if field not found

        new_val = aapl_match.group(2)

        # Replace in MSFT — all occurrences
        def replace_one(match):
            return f"{match.group(1)}{new_val}{match.group(3)}"

        msft_html = re.sub(pattern, replace_one, msft_html, flags=re.DOTALL)

    return msft_html


#also needs to update the htm file and the xsd file.
#todo

def insert_to_xsd():
    return