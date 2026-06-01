"""
Enrutador HTTP del receptor HL7/ASTM/JSON.
La lógica vive en core.services.lims.interfaces_lims_service (InterfacesLimsService).
"""
from core.services.lims.interfaces_lims_service import InterfacesLimsService, receptor_hl7

__all__ = ['receptor_hl7', 'InterfacesLimsService']
