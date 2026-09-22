import shutil
import subprocess
from pathlib import Path


def test_frontend_csv_exports_sales_pack_fields_and_escapes_values(tmp_path: Path) -> None:
    module_path = tmp_path / "csv.mjs"
    shutil.copyfile(Path("frontend/assets/js/csv.js"), module_path)
    script_path = tmp_path / "check-csv.mjs"
    script_path.write_text(
        f'''
        import {{ buildProspectsCsv }} from {module_path.resolve().as_uri()!r};
        const csv = buildProspectsCsv([{{
          name: 'Azienda, "Demo"',
          category: 'Scuola guida',
          phone: '031 123456',
          website: 'https://example.com',
          maps_url: 'https://maps.google.com/?cid=1',
          address: 'Via Roma 1\\nComo',
          rating: '4.7 (18 recensioni)',
          source: 'Google Places',
          target_score: 9,
          score_reason: 'Buon target perché telefono disponibile.',
          email_subject: 'Proposta "veloce"',
          email_body: 'Ciao,\\nemail pronta',
          whatsapp_message: 'WhatsApp pronto',
          linkedin_message: 'LinkedIn pronto',
          follow_up_message: 'Follow-up pronto',
          status: 'Contattato',
        }}]);
        if (!csv.includes('"Target score"')) throw new Error('missing score header');
        if (!csv.includes('"Oggetto email"')) throw new Error('missing subject header');
        if (!csv.includes('"Azienda, ""Demo"""')) throw new Error('bad quote escaping');
        if (!csv.includes('"Via Roma 1 Como"')) throw new Error('bad newline escaping');
        if (!csv.includes('"9/10"')) throw new Error('missing score value');
        ''',
        encoding="utf-8",
    )

    result = subprocess.run(["node", str(script_path)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
