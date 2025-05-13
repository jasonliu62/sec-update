from pathlib import Path

# Path to the original file
file_path = "msft-20250430.htm"

# Read the HTML content
html_content = Path(file_path).read_text()

# The exact <tr> block to replicate — must match exactly
target_tr = '''<tr style="height:10pt;white-space:pre-wrap;word-break:break-word;">
     <td style="padding-top:0in;padding-left:0in;vertical-align:bottom;padding-bottom:0in;padding-right:0in;"><p style="font-size:10pt;margin-top:2pt;font-family:Times New Roman;margin-bottom:0;text-align:left;"><span style="font-family:Arial;"><ix:nonNumeric id="F_90a2aa2b-069a-431b-9289-956d06186026" contextRef="C_a17dcbb1-52c3-49bf-92c7-1f97cca1d03c" name="dei:Security12bTitle"><span style="color:#000000;white-space:pre-wrap;font-weight:bold;font-kerning:none;min-width:fit-content;">Common stock, $0.00000625 par value per share</span></ix:nonNumeric></span></p></td>
     <td style="padding-top:0in;padding-left:0in;vertical-align:top;padding-bottom:0in;padding-right:0in;text-align:left;"><p style="font-size:10pt;margin-top:2pt;font-family:Times New Roman;margin-bottom:0;text-align:center;"><span style="white-space:pre-wrap;font-family:Arial;font-kerning:none;min-width:fit-content;">&#160;</span></p></td>
     <td style="padding-top:0in;padding-left:0in;vertical-align:bottom;padding-bottom:0in;padding-right:0in;text-align:left;"><p style="font-size:10pt;margin-top:2pt;font-family:Times New Roman;margin-bottom:0;text-align:center;"><span style="font-family:Arial;"><ix:nonNumeric id="F_ff724dc0-c97a-44b6-94e7-bc16e4a380b1" contextRef="C_a17dcbb1-52c3-49bf-92c7-1f97cca1d03c" name="dei:TradingSymbol"><span style="text-transform:uppercase;color:#000000;white-space:pre-wrap;font-weight:bold;font-kerning:none;min-width:fit-content;">MSFT</span></ix:nonNumeric></span></p></td>
     <td style="padding-top:0in;padding-left:0in;vertical-align:top;padding-bottom:0in;padding-right:0in;"><p style="font-size:10pt;margin-top:2pt;font-family:Times New Roman;margin-bottom:0;text-align:left;"><span style="white-space:pre-wrap;font-family:Arial;font-kerning:none;min-width:fit-content;">&#160;</span></p></td>
     <td style="padding-top:0in;padding-left:0in;vertical-align:bottom;padding-bottom:0in;padding-right:0in;text-align:left;"><p style="font-size:10pt;margin-top:2pt;font-family:Times New Roman;margin-bottom:0;text-align:center;"><span style="font-family:Arial;"><ix:nonNumeric id="F_80771a21-114f-4a5a-a942-722817fdbbda" contextRef="C_a17dcbb1-52c3-49bf-92c7-1f97cca1d03c" name="dei:SecurityExchangeName" format="ixt-sec:exchnameen"><span style="text-transform:uppercase;color:#000000;white-space:pre-wrap;font-weight:bold;font-kerning:none;min-width:fit-content;">Nasdaq</span></ix:nonNumeric></span></p></td>
    </tr>'''

# Replace the original block with 7 copies
expanded_blocks = []
for i in range(7):
    new_block = target_tr.replace('F_90a2aa2b-069a-431b-9289-956d06186026', f'F_title_{i}')
    new_block = new_block.replace('F_ff724dc0-c97a-44b6-94e7-bc16e4a380b1', f'F_symbol_{i}')
    new_block = new_block.replace('F_80771a21-114f-4a5a-a942-722817fdbbda', f'F_exchange_{i}')
    expanded_blocks.append(new_block)

expanded_block = '\n'.join(expanded_blocks)
updated_html = html_content.replace(target_tr, expanded_block)

# Path to save the updated file
output_path = "msft-20250430_modified.htm"
Path(output_path).write_text(updated_html)

print(f"Modified HTML saved to {output_path}")
