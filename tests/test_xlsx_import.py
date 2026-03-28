from datetime import date, datetime

from bed.services.xlsx_import import (
    apply_sign,
    extract_ticker,
    map_institution,
    normalize_type,
    parse_date,
    parse_numeric,
)


class TestExtractTicker:
    def test_stock_ticker(self):
        assert extract_ticker("CSAN3 - COSAN SA") == "CSAN3"
        assert extract_ticker("PETR4 - PETROLEO BRASILEIRO S/A PETROBRAS") == "PETR4"
        assert extract_ticker("BBAS3 - BCO BRASIL S.A.") == "BBAS3"

    def test_etf_ticker(self):
        assert extract_ticker("TAEE11 - TRANSMISSORA ALIANÇA DE ENERGIA ELÉTRICA S.A.") == "TAEE11"

    def test_treasury_bond_returns_none(self):
        assert extract_ticker("Tesouro Selic 2024") is None
        assert extract_ticker("Tesouro Prefixado 2026") is None
        assert extract_ticker("Tesouro IPCA+ 2026") is None

    def test_cdb_returns_none(self):
        assert extract_ticker("CDB - CDB321KRR3K - OMNI S/A CREDITO FINANCIAMENTO E INVESTIMENTO") is None

    def test_no_separator_returns_none(self):
        assert extract_ticker("SomeProduct") is None

    def test_strips_whitespace(self):
        assert extract_ticker("VALE3 - VALE S.A.   ") == "VALE3"


class TestMapInstitution:
    def test_inter_distribuidora(self):
        assert map_institution("INTER DISTRIBUIDORA DE TITULOS E VALORES MOBILIARIOS LTDA") == "inter"

    def test_inter_dtvm(self):
        assert map_institution("INTER DTVM LTDA") == "inter"

    def test_btg_pactual(self):
        assert map_institution("BANCO BTG PACTUAL S/A") == "btg-pactual"

    def test_unknown_institution_slugified(self):
        result = map_institution("XP INVESTIMENTOS S/A")
        assert result == "xp-investimentos-s-a"


class TestParseNumeric:
    def test_normal_number(self):
        assert parse_numeric(5.43) == 5.43
        assert parse_numeric(14118) == 14118.0

    def test_dash_returns_zero(self):
        assert parse_numeric("-") == 0.0

    def test_none_returns_zero(self):
        assert parse_numeric(None) == 0.0

    def test_empty_string_returns_zero(self):
        assert parse_numeric("") == 0.0

    def test_string_number(self):
        assert parse_numeric("42.5") == 42.5


class TestParseDate:
    def test_string_date(self):
        assert parse_date("26/03/2026") == date(2026, 3, 26)

    def test_datetime_object(self):
        assert parse_date(datetime(2026, 3, 26, 10, 30)) == date(2026, 3, 26)

    def test_date_object(self):
        assert parse_date(date(2026, 3, 26)) == date(2026, 3, 26)


class TestNormalizeType:
    def test_accent_normalization(self):
        assert normalize_type("Transferencia") == "Transferência"

    def test_already_normalized(self):
        assert normalize_type("Transferência") == "Transferência"

    def test_other_types_unchanged(self):
        assert normalize_type("Compra") == "Compra"
        assert normalize_type("Dividendo") == "Dividendo"
        assert normalize_type("Empréstimo") == "Empréstimo"


class TestApplySign:
    def test_credito_positive(self):
        assert apply_sign(100.0, "Credito") == 100.0

    def test_debito_negative(self):
        assert apply_sign(100.0, "Debito") == -100.0

    def test_zero_stays_zero(self):
        assert apply_sign(0.0, "Credito") == 0.0
        assert apply_sign(0.0, "Debito") == 0.0

    def test_already_negative_debito(self):
        assert apply_sign(-50.0, "Debito") == -50.0
