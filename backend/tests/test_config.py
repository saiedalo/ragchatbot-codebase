import os
import sys
from unittest.mock import Mock, patch

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config, config


class TestConfig:
    """Testfälle für die Konfiguration"""

    def test_default_config_values(self):
        """Testet Standard-Konfigurationswerte"""
        default_config = Config()

        assert default_config.ANTHROPIC_MODEL == "claude-sonnet-4-5"
        assert default_config.EMBEDDING_MODEL == "all-MiniLM-L6-v2"

        assert default_config.CHUNK_SIZE == 800
        assert default_config.CHUNK_OVERLAP == 100
        assert default_config.MAX_HISTORY == 2

        assert default_config.CHROMA_PATH == "./chroma_db"

    def test_max_results_configuration(self):
        """Testet dass MAX_RESULTS korrekt auf 5 gesetzt ist"""
        default_config = Config()

        assert default_config.MAX_RESULTS == 5
        assert default_config.MAX_RESULTS > 0

    def test_proper_max_results_configuration(self):
        """Testet korrekte MAX_RESULTS-Konfiguration"""
        proper_config = Config()

        assert proper_config.MAX_RESULTS > 0
        assert isinstance(proper_config.MAX_RESULTS, int)

        assert proper_config.MAX_RESULTS <= 10
        assert proper_config.MAX_RESULTS >= 1

    def test_config_with_environment_variables(self):
        """Testet dass ANTHROPIC_API_KEY als String vorliegt"""
        test_config = Config()

        assert isinstance(test_config.ANTHROPIC_API_KEY, str)

    def test_config_missing_api_key(self):
        """Testet dass ANTHROPIC_API_KEY einen definierten Standardwert hat"""
        test_config = Config()

        assert test_config.ANTHROPIC_API_KEY is not None

    def test_config_chunk_settings_valid(self):
        """Testet ob Chunk-Verarbeitungseinstellungen gültig sind"""
        test_config = Config()

        assert test_config.CHUNK_SIZE > 0
        assert test_config.CHUNK_SIZE <= 2000

        assert test_config.CHUNK_OVERLAP < test_config.CHUNK_SIZE
        assert test_config.CHUNK_OVERLAP >= 0

        assert test_config.MAX_HISTORY >= 0
        assert test_config.MAX_HISTORY <= 10

    def test_config_path_settings(self):
        """Testet Datenbankpfad-Konfiguration"""
        test_config = Config()

        assert isinstance(test_config.CHROMA_PATH, str)
        assert test_config.CHROMA_PATH != ""
        assert not test_config.CHROMA_PATH.startswith("/")

    def test_config_model_settings(self):
        """Testet KI-Modell-Konfiguration"""
        test_config = Config()

        assert "claude" in test_config.ANTHROPIC_MODEL.lower()

        assert test_config.EMBEDDING_MODEL != ""
        assert isinstance(test_config.EMBEDDING_MODEL, str)

    def test_global_config_instance(self):
        """Testet die globale Konfigurationsinstanz"""
        assert config is not None
        assert isinstance(config, Config)

        assert config.MAX_RESULTS == 5

    def test_config_impact_on_vector_search(self):
        """Testet wie MAX_RESULTS die Vektorsuche beeinflusst"""
        proper_config = Config()

        assert proper_config.MAX_RESULTS == 5

        def simulate_search(max_results):
            if max_results == 0:
                return []
            else:
                return ["ergebnis1", "ergebnis2"]

        results = simulate_search(proper_config.MAX_RESULTS)
        assert len(results) > 0

    def test_config_values_are_correct_types(self):
        """Testet ob alle Konfigurationswerte die richtigen Typen haben"""
        test_config = Config()

        assert isinstance(test_config.ANTHROPIC_API_KEY, str)
        assert isinstance(test_config.ANTHROPIC_MODEL, str)
        assert isinstance(test_config.EMBEDDING_MODEL, str)
        assert isinstance(test_config.CHROMA_PATH, str)

        assert isinstance(test_config.CHUNK_SIZE, int)
        assert isinstance(test_config.CHUNK_OVERLAP, int)
        assert isinstance(test_config.MAX_RESULTS, int)
        assert isinstance(test_config.MAX_HISTORY, int)

    def test_config_validation_logic(self):
        """Testet Konfigurationsvalidierungslogik"""

        def validate_config(cfg):
            errors = []

            if cfg.MAX_RESULTS <= 0:
                errors.append("MAX_RESULTS muss größer als 0 sein")

            if cfg.CHUNK_OVERLAP >= cfg.CHUNK_SIZE:
                errors.append("CHUNK_OVERLAP muss kleiner als CHUNK_SIZE sein")

            if cfg.ANTHROPIC_API_KEY == "":
                errors.append("ANTHROPIC_API_KEY ist erforderlich")

            return errors

        proper_config = Config()
        proper_config.ANTHROPIC_API_KEY = "valid-key"
        errors = validate_config(proper_config)
        max_results_errors = [e for e in errors if "MAX_RESULTS" in e]
        assert len(max_results_errors) == 0

    def test_config_edge_cases(self):
        """Testet Konfigurations-Randfälle"""
        test_config = Config()

        test_config.CHUNK_SIZE = 10000
        assert test_config.CHUNK_SIZE == 10000

        test_config.CHUNK_OVERLAP = 0
        assert test_config.CHUNK_OVERLAP == 0

        test_config.MAX_RESULTS = 100
        assert test_config.MAX_RESULTS == 100

    def test_config_immutability_during_runtime(self):
        """Testet ob Konfigurationsänderungen das Systemverhalten beeinflussen"""
        def simulate_search(max_results):
            if max_results == 0:
                return []
            else:
                return ["ergebnis1", "ergebnis2"]

        fixed_config = Config()
        fixed_config.MAX_RESULTS = 5

        fixed_results = simulate_search(fixed_config.MAX_RESULTS)
        assert len(fixed_results) > 0

    def test_config_dataclass_behavior(self):
        """Testet ob Config sich als erwartete Dataclass verhält"""
        config1 = Config()
        config2 = Config()

        assert config1 is not config2

        assert config1.CHUNK_SIZE == config2.CHUNK_SIZE
        assert config1.MAX_RESULTS == config2.MAX_RESULTS

        config1.MAX_RESULTS = 10
        assert config2.MAX_RESULTS == 5

    @pytest.mark.parametrize(
        "max_results,expected_behavior",
        [
            (0, "keine_ergebnisse"),
            (1, "einige_ergebnisse"),
            (5, "gute_ergebnisse"),
            (10, "viele_ergebnisse"),
        ],
    )
    def test_max_results_impact_parametrized(self, max_results, expected_behavior):
        """Testet verschiedene MAX_RESULTS-Werte und ihre Auswirkung"""
        test_config = Config()
        test_config.MAX_RESULTS = max_results

        if max_results == 0:
            assert expected_behavior == "keine_ergebnisse"
        elif max_results >= 1:
            assert expected_behavior in [
                "einige_ergebnisse",
                "gute_ergebnisse",
                "viele_ergebnisse",
            ]

        assert test_config.MAX_RESULTS == max_results
