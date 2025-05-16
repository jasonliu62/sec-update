import re
import os
from datetime import datetime
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
        "DocumentPeriodEndDate",
    ]

    updated_html = replace_dei_fields(updated_html, aapl_html, fields_to_replace)

    labels = aapl_values["Security12bTitle"][:max_rows]
    prefix_match = re.search(r'xmlns:([a-z0-9]+)="http://www\.[a-z0-9.-]+/(\d{8})"', aapl_html)
    if prefix_match:
        prefix = prefix_match.group(1)
    else:
        prefix = fallback_symbol.lower()

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

    labels_to_insert = []

    for i in range(max_rows):
        sec_title = aapl_values["Security12bTitle"][i] if i < len(aapl_values["Security12bTitle"]) else ""
        trading_symbol = fallback_symbol
        exchange_name = "Nasdaq"

        # default to no change
        context_id = None

        if "common stock" not in sec_title.lower():
            labels_to_insert.append(sec_title)
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

    if labels_to_insert:
        insert_to_xsd(xsd_path, aapl_html, labels_to_insert, prefix)
    # Inject all contexts before </ix:resources>
    updated_html = re.sub(r"(</ix:resources>)", '\n'.join(context_blocks) + r"\1", updated_html, count=1)


    if not output_path:
        output_path = os.path.join(os.path.dirname(msft_path), "msft_updated_12b.htm")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(updated_html)

    return f"✅ Updated file saved to: {output_path}"

def normalize_label_to_member(prefix: str, label: str) -> str:
    # Try full date pattern first: e.g., "6.500% Notes due August 15, 2062"
    match_full_date = re.search(r'([0-9.]+)%\s+(.+?)\s+due\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})', label, re.IGNORECASE)

    if match_full_date:
        rate = match_full_date.group(1)      # e.g., "6.500"
        descriptor = match_full_date.group(2)  # e.g., "Senior Notes"
        date_str = match_full_date.group(3)  # e.g., "August 15, 2062"

        try:
            dt = datetime.strptime(date_str, "%B %d, %Y")
            month = dt.strftime("%b")  # "Aug"
            day = ordinal(dt.day)     # "Fifteenth"
            year = dt.year
            full_date = f"{month}{day}{year}"
            #full_date = f"{year}"
        except ValueError:
            full_date = "0000-00-00"

        words_clean = re.sub(r'\W+', '', descriptor)
        return f"{prefix}:{words_clean}{rate}Due{full_date}Member"

    # Try year-only pattern: e.g., "6.200% Notes due 2059"
    match_year_only = re.search(r'([0-9.]+)%\s+(.+?)\s+due\s+(\d{4})', label, re.IGNORECASE)

    if match_year_only:
        rate = match_year_only.group(1)
        descriptor = match_year_only.group(2)
        year = match_year_only.group(3)

        words_clean = re.sub(r'\W+', '', descriptor)
        return f"{prefix}:{words_clean}{rate}Due{year}Member"

    # fallback
    clean = re.sub(r'\W+', '', label)
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
    match = re.search(r'(xmlns:([a-z0-9]+)="http://www\.[^"]+/(\d{8})")', aapl_html)
    if match:
        new_xmlns_attr = match.group(1)  # full xmlns string, e.g., xmlns:f="http://www.ford.com/20250507"
        prefix = match.group(2)

        # Only add if not already present
        if f'xmlns:{prefix}=' not in msft_html:
            msft_html = re.sub(r'(<html\b[^>]*?)>', fr'\1 {new_xmlns_attr}>', msft_html, count=1)

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

    msft_html = update_dates_from_reference(msft_html, aapl_html)
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

def insert_to_xsd(xsd_path: str, aapl_html: str, labels: list[str], prefix: str):
    xsd_text = Path(xsd_path).read_text(encoding='utf-8')
    xsd_name = get_new_xsd_name(aapl_html)

    label_links = []
    presentation_links = []
    definition_links = []
    element_declarations = []

    for label in labels:
        if "common stock" in label.lower():
            continue  # skip common stock

        # Try full date pattern: e.g., "6.500% Senior Notes due August 15, 2062"
        match_full = re.search(r'([0-9.]+)%\s+(.+?)\s+due\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})', label, re.IGNORECASE)
        if match_full:
            rate = match_full.group(1)  # "6.500"
            descriptor = match_full.group(2)  # "Senior Notes"
            date_str = match_full.group(3)  # "August 15, 2062"

            # Convert to YYYY-MM-DD
            try:
                dt = datetime.strptime(date_str, "%B %d, %Y")
                month = dt.strftime("%b")  # "Aug"
                day = ordinal(dt.day)  # "Fifteenth"
                year = dt.year
                full_date = f"{month}{day}{year}"
                # full_date = f"{year}"
            except ValueError:
                full_date = "0000-00-00"

            descriptor_clean = re.sub(r'\W+', '', descriptor)  # "SeniorNotes"
            member_base = f"{prefix}:{descriptor_clean}{rate}Due{full_date}Member"
            href = f"{xsd_name}#{member_base}"
            clean_name = f"{descriptor_clean}{rate}Due{full_date}Member"

        else:
            # Try year-only pattern
            match_year = re.search(r'([0-9.]+)%\s+(.+?)\s+due\s+(\d{4})', label, re.IGNORECASE)
            if not match_year:
                continue  # skip malformed

            rate = match_year.group(1)  # "6.000"
            descriptor = match_year.group(2)  # "Notes"
            year = match_year.group(3)

            descriptor_clean = re.sub(r'\W+', '', descriptor)
            member_base = f"{prefix}:{descriptor_clean}{rate}Due{year}Member"
            href = f"{xsd_name}#{member_base}"
            clean_name = f"{descriptor_clean}{rate}Due{year}Member"

        # labelLink
        label_links.append(f"""
    <link:loc xlink:type="locator" xlink:href="{href}" xlink:label="{member_base}"/>
    <link:labelArc xlink:type="arc"
        xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-label"
        xlink:from="{member_base}"
        xlink:to="{member_base}_lbl"/>""")

        # presentationLink
        presentation_links.append(f"""
    <link:loc xlink:type="locator" xlink:href="{href}" xlink:label="{member_base}"/>
    <link:presentationArc xlink:type="arc"
        xlink:arcrole="http://www.xbrl.org/2003/arcrole/parent-child"
        xlink:from="us-gaap_ClassOfStockDomain"
        xlink:to="{member_base}" order="1" priority="2" use="optional"
        preferredLabel="http://www.xbrl.org/2003/role/terseLabel"/>""")

        # definitionLink
        definition_links.append(f"""
    <link:loc xlink:type="locator" xlink:href="{href}" xlink:label="{member_base}"/>
    <link:definitionArc xlink:type="arc"
        xlink:arcrole="http://xbrl.org/int/dim/arcrole/domain-member"
        xlink:from="us-gaap_ClassOfStockDomain"
        xlink:to="{member_base}" priority="2" use="optional"/>""")

        # xsd:element
        element_declarations.append(f"""
    <xsd:element
        id="{member_base}"
        name="{clean_name}"
        type="dtr-types:domainItemType"
        substitutionGroup="xbrli:item"
        xbrli:periodType="duration"
        nillable="true"
        abstract="true"/>""")

    # Insert everything once
    xsd_text = re.sub(r"(</link:labelLink>)", "\n".join(label_links) + r"\n\1", xsd_text, count=1)
    xsd_text = re.sub(r"(</link:presentationLink>)", "\n".join(presentation_links) + r"\n\1", xsd_text, count=1)
    xsd_text = re.sub(r"(</link:definitionLink>)", "\n".join(definition_links) + r"\n\1", xsd_text, count=1)
    xsd_text = re.sub(r"(</xsd:schema>)", "\n".join(element_declarations) + r"\n\1", xsd_text, count=1)

    # Save once
    new_xsd_path = os.path.join(os.path.dirname(xsd_path), xsd_name)
    Path(new_xsd_path).write_text(xsd_text, encoding='utf-8')
    print(f"✅ XSD updated and saved as {new_xsd_path} with {len(labels)} members.")


def get_new_xsd_name(aapl_html: str) -> str:
    aapl_xsd_match = re.search(r'xlink:href="([^"]+\.xsd)"', aapl_html)
    if aapl_xsd_match:
        return  aapl_xsd_match.group(1)
    else:
        return ""


def ordinal(n: int) -> str:
    """Convert an integer to an ordinal string (e.g., 1 → First, 2 → Second)."""
    ORDINAL_MAP = {
        1: "First", 2: "Second", 3: "Third", 4: "Fourth", 5: "Fifth",
        6: "Sixth", 7: "Seventh", 8: "Eighth", 9: "Ninth", 10: "Tenth",
        11: "Eleventh", 12: "Twelfth", 13: "Thirteenth", 14: "Fourteenth",
        15: "Fifteenth", 16: "Sixteenth", 17: "Seventeenth", 18: "Eighteenth",
        19: "Nineteenth", 20: "Twentieth", 21: "TwentyFirst", 22: "TwentySecond",
        23: "TwentyThird", 24: "TwentyFourth", 25: "TwentyFifth", 26: "TwentySixth",
        27: "TwentySeventh", 28: "TwentyEighth", 29: "TwentyNinth", 30: "Thirtieth",
        31: "ThirtyFirst"
    }
    return ORDINAL_MAP.get(n, str(n))