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


class TestNormalizeAgfType:
    def test_jscp_normalized(self):
        from bed.services.xlsx_import import normalize_agf_type
        assert normalize_agf_type("Jscp") == "Juros Sobre Capital Próprio"

    def test_rendimento_normalized(self):
        from bed.services.xlsx_import import normalize_agf_type
        assert normalize_agf_type("RENDIMENTO") == "Rendimento"

    def test_compra_unchanged(self):
        from bed.services.xlsx_import import normalize_agf_type
        assert normalize_agf_type("Compra") == "Compra"

    def test_venda_unchanged(self):
        from bed.services.xlsx_import import normalize_agf_type
        assert normalize_agf_type("Venda") == "Venda"

    def test_dividendo_unchanged(self):
        from bed.services.xlsx_import import normalize_agf_type
        assert normalize_agf_type("Dividendo") == "Dividendo"

    def test_bonificacao_unchanged(self):
        from bed.services.xlsx_import import normalize_agf_type
        assert normalize_agf_type("Bonificação") == "Bonificação"


class TestStripFracionarioSuffix:
    def test_strips_f_suffix(self):
        from bed.services.xlsx_import import strip_fracionario_suffix
        assert strip_fracionario_suffix("VALE3F") == "VALE3"
        assert strip_fracionario_suffix("BBAS3F") == "BBAS3"
        assert strip_fracionario_suffix("TAEE11F") == "TAEE11"

    def test_no_suffix_unchanged(self):
        from bed.services.xlsx_import import strip_fracionario_suffix
        assert strip_fracionario_suffix("VALE3") == "VALE3"
        assert strip_fracionario_suffix("BBAS3") == "BBAS3"

    def test_non_matching_f_unchanged(self):
        from bed.services.xlsx_import import strip_fracionario_suffix
        # "F" not at end of ticker pattern
        assert strip_fracionario_suffix("FLRY3") == "FLRY3"
        assert strip_fracionario_suffix("FESA4") == "FESA4"

    def test_option_codes_unchanged(self):
        from bed.services.xlsx_import import strip_fracionario_suffix
        assert strip_fracionario_suffix("CSANO660") == "CSANO660"
        assert strip_fracionario_suffix("VALEJ655") == "VALEJ655"


class TestMovTypeWhitelist:
    def test_whitelist_contains_expected_types(self):
        from bed.services.xlsx_import import MOV_TYPE_WHITELIST
        assert "Dividendo" in MOV_TYPE_WHITELIST
        assert "Juros Sobre Capital Próprio" in MOV_TYPE_WHITELIST
        assert "Rendimento" in MOV_TYPE_WHITELIST
        assert "Reembolso" in MOV_TYPE_WHITELIST
        assert "Compra" in MOV_TYPE_WHITELIST
        assert "Venda" in MOV_TYPE_WHITELIST
        assert "COMPRA / VENDA" in MOV_TYPE_WHITELIST
        assert "VENCIMENTO" in MOV_TYPE_WHITELIST

    def test_whitelist_excludes_lending(self):
        from bed.services.xlsx_import import MOV_TYPE_WHITELIST
        assert "Transferência - Liquidação" not in MOV_TYPE_WHITELIST
        assert "Empréstimo" not in MOV_TYPE_WHITELIST
        assert "Transferência" not in MOV_TYPE_WHITELIST
        assert "Dividendo - Transferido" not in MOV_TYPE_WHITELIST
        assert "Juros Sobre Capital Próprio - Transferido" not in MOV_TYPE_WHITELIST
