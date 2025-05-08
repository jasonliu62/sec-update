import subprocess
from pathlib import Path
import re
from bs4 import BeautifulSoup

def convert_docx_to_html_with_pandoc(docx_path, html_out_path):
    subprocess.run(["pandoc", str(docx_path), "-t", "html", "-o", str(html_out_path)], check=True)

def extract_and_clean_html(html_path):
    html = Path(html_path).read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    body_content = soup.body or soup
    return str(body_content)

def replace_disclosure_block(insert_docx_path, html_path):
    html = Path(html_path).read_text(encoding='utf-8')

    html_regex = re.compile(
        r'(<table[^>]*?>\s*<tr[^>]*?>\s*<td[^>]*?>\s*<span[^>]*?><b>\s*Item\s+\d+\.\d+.*?</b></span>.*?</table>[\s\S]*?)(?=<p[^>]*?><b>SIGNATURE</b></p>)',
        re.IGNORECASE | re.DOTALL
    )
    match = html_regex.search(html)
    if not match:
        raise ValueError("Could not locate the first disclosure block before SIGNATURE.")

    temp_html_path = Path("temp_converted.html")
    convert_docx_to_html_with_pandoc(insert_docx_path, temp_html_path)
    inserted_html = extract_and_clean_html(temp_html_path)

    # Build consistent visual wrapper
    spacer_before = "\n".join([
        '<p style="font: 10pt Times New Roman, Times, Serif; margin: 0pt 0">&#160;</p>' for _ in range(7)
    ])
    divider = """
<div style="border-bottom: Black 1pt solid; margin-top: 6pt; margin-bottom: 6pt">
  <table cellpadding="0" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size: 10pt">
    <tr style="vertical-align: top; text-align: left">
      <td style="width: 33%">&#160;</td>
      <td style="width: 34%; text-align: center">&#160;</td>
      <td style="width: 33%; text-align: right">&#160;</td>
    </tr>
  </table>
</div>
<div style="break-before: page; margin-top: 6pt; margin-bottom: 6pt">
  <p style="margin: 0pt">&#160;</p>
</div>"""
    spacer_after = "\n".join([
        '<p style="font: 10pt Times New Roman, Times, Serif; margin: 0pt 0">&#160;</p>' for _ in range(3)
    ])

    full_insert_block = f"""
<div style="width:100%; font-family: 'Times New Roman', Times, Serif; font-size: 10pt;">
{inserted_html}
{spacer_before}
{divider}
{spacer_after}
</div>"""

    updated_html = html[:match.start()] + full_insert_block + html[match.end():]
    Path(html_path).write_text(updated_html, encoding='utf-8')

    return html_path
