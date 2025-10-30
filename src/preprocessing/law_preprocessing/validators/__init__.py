"""
Law Validators - Quality validation for law documents
"""

from .integrity_validator import DataIntegrityValidator, IntegrityReport

# TODO: Implement additional validators
# from .structure_validator import StructureValidator
# from .quality_validator import QualityValidator

__all__ = ["DataIntegrityValidator", "IntegrityReport"]
