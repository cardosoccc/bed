import re
from datetime import date, datetime

import openpyxl

INSTITUTION_MAP = {
    "INTER DISTRIBUIDORA DE TITULOS E VALORES MOBILIARIOS LTDA": "inter",
    "INTER DTVM LTDA": "inter",
    "BANCO BTG PACTUAL S/A": "btg-pactual",
}

ACCENT_NORMALIZATION = {
    "Transferencia": "Transferência",
}

NO_TICKER_PREFIXES = ("Tesouro ", "CDB ")


def parse_xlsx(file_path: str, sheet_name: str = "Movimentação") -> list[dict]:
    """Parse B3 movimentação XLSX into a list of raw transaction dicts."""
    wb = openpyxl.load_workbook(file_path, read_only=True)
    ws = wb[sheet_name]

    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            continue

        entrada_saida, data, movimentacao, produto, instituicao, quantidade, preco, valor = row

        rows.append({
            "entrada_saida": str(entrada_saida).strip(),
            "date": parse_date(data),
            "type": normalize_type(str(movimentacao).strip()),
            "product": str(produto).strip(),
            "ticker": extract_ticker(str(produto).strip()),
            "institution": map_institution(str(instituicao).strip()),
            "quantity": parse_numeric(quantidade),
            "unit_value": parse_numeric(preco),
            "total_value": parse_numeric(valor),
        })

    wb.close()
    return rows


def parse_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value).strip(), "%d/%m/%Y").date()


def parse_numeric(value) -> float:
    if value is None or str(value).strip() in ("-", ""):
        return 0.0
    return float(value)


def extract_ticker(product: str) -> str | None:
    for prefix in NO_TICKER_PREFIXES:
        if product.startswith(prefix):
            return None
    if " - " in product:
        return product.split(" - ")[0].strip()
    return None


def map_institution(name: str) -> str:
    if name in INSTITUTION_MAP:
        return INSTITUTION_MAP[name]
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug


def normalize_type(movimentacao: str) -> str:
    return ACCENT_NORMALIZATION.get(movimentacao, movimentacao)


def apply_sign(total_value: float, entrada_saida: str) -> float:
    if entrada_saida == "Debito":
        return -abs(total_value)
    return abs(total_value)
