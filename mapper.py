import pandas as pd
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable
from functools import wraps

type Data = dict[str, Any]
type SegFn = Callable[[Data], None]

parsers: dict[str, SegFn] = {}


def register_parser(format: str) -> Callable[[SegFn], SegFn]:
    def decorator(func: SegFn) -> SegFn:
        @wraps(func)
        def wrapper(data: Data) -> None:
            return func(data)

        parsers[format] = wrapper
        return wrapper

    return decorator

RELATIONSHIP: dict[str, str] = {
    "18": "employee",
    "01": "spouse",
    "19": "child",
    "15": "ward"
}
GENDER: dict[str, str] = {
    "M": "male",
    "F": "female",
    "U": "unknown"
}
MAINTENANCE: dict[str, str] = {
    "030": "addition",
    "001": "change",
    "024": "termination"
}
DTP_QUAL: dict[str, str] = {
    "356": "effective_date",
    "357": "termination_date",
    "348": "coverage_begin",
    "349": "coverage_end"
}

REF_QUALIFIER: dict[str, str] = {
    "0F": "member_id",
    "1L": "group_policy_number",
    "1W": "member_id_number",
    "23": "client_number",
    "38": "plan_number",
    "6O": "division_identifier",
    "ABB": "prior_id_number",
    "D3": "naic_code",
    "DX": "department_agency_number",
    "E8": "termination_reason",
    "GI": "group_name",
    "P2": "plan_network_id",
    "PID": "plan_id",
    "PSS": "pay_roll_number",
    "RB": "rate_code_number",
    "ZZ": "mutually_defined",
}


@register_parser("INS")
def map_ins(seg: list[str]) -> dict:
    return{
        "subscriber":        seg[1],
        "relationship":      seg[2],
        "maintenance_type":  seg[3],
        }
@register_parser("NM1")
def map_nm1(seg: list[str]) -> dict:
    return {
        "last_name":  seg[3],
        "first_name": seg[4],
        "middle":     seg[5] if len(seg) > 5 else None,
        "ssn":        seg[9] if len(seg) > 9 else None,
    }

@register_parser("DTP")
def map_dtps(segs: list[str]) -> dict:
    # Multiple DTP segments collapse into a single dict keyed by qualifier
    return {
        DTP_QUAL.get(segs[1], segs[1]): segs[3]
    }

@register_parser("HD")
def map_hd(seg: list[str]) -> dict:
    return {
        "Coverage Type": seg[3] if len(seg) > 3 else None,
        "Coverage Description": seg[4] if len(seg) > 4 else None,
    }

@register_parser("DMG")
def map_dmg(segs: list[str]) -> dict:
    return {
        "Birth Date": f'{segs[2][4:8]}{segs[2][0:4]}' if len(segs) > 3 else None,
    }

@register_parser("REF")
def map_ref(segs: list[str]) -> dict:
    return{
        REF_QUALIFIER.get(segs[1], segs[1]): segs[2]
    }
@register_parser("PER")
def map_per(segs: list[str]) -> dict:
    pass

@register_parser("AMT")
def map_amt(segs: list[str]) -> dict:
    pass

@register_parser("N3")
def map_n3(segs: list[str]) -> dict:
    pass

@register_parser("N4")
def map_n4(segs: list[str]) -> dict:
    pass


def map_member(loop: pd.DataFrame) -> dict:
    complete_dict = {}
    member_lst = loop.values.tolist()
    for row in member_lst:
        seg = row[0]
        parser = parsers.get(seg)
        if parser is None:
            raise ValueError(f"No parser for {seg}")
        parsed_dict = parser(row)
        if parsed_dict is None:
            break
        complete_dict.update(parsed_dict)
    return complete_dict



def map_ISA(seg: list) -> dict:
    return {
        'auth_info_qualifier': seg[0],
        'auth_information': seg[1],
        'security_info_qualifier': seg[2],
        'security_information': seg[3],
        'sender_id_qualifier': seg[4],
        'sender_id': seg[5],
        'receiver_id_qualifier': seg[6],
        'receiver_id': seg[7],
        'interchange_date': seg[8],
        'interchange_time': seg[9],
        'repetition_separator': seg[10],
        'control_version_number': seg[11],
        'interchange_control_number': seg[12],
        'acknowledgment_requested': seg[13],
        'usage_indicator': seg[14],
        'component_element_separator': seg[15],
    }

@dataclass(frozen=True, slots=True)
class MemberRecord:
    # --- INS, Member Level Detail ---
    is_subscriber: str  # INS01, 'Y'/'N'
    relationship_code: str  # INS02
    maintenance_type_code: str | None = None  # INS03, expected '030' full-file
    maintenance_reason_code: str | None = None  # INS04
    benefit_status_code: str | None = None  # INS05
    employment_status_code: str | None = None  # INS08
    student_status_code: str | None = None  # INS09
    handicap_indicator: str | None = None  # INS10
    death_date: date | None = field(default=None, repr=False)  # INS12

    # --- REF, Loop 2000 (repeatable -- see module docstring) ---


    # --- DTP, Member Level Dates -- resolved by parser, see module docstring ---
    maintenance_effective_date: date | None = None  # DTP*303
    employment_begin_date: date | None = None  # DTP*336
    employment_end_date: date | None = None  # DTP*337
    eligibility_begin_date: date | None = None  # DTP*356
    eligibility_end_date: date | None = None  # DTP*357, date-carried termination
    # (FR-23: used exactly as transmitted, even when later than the file
    # effective date -- never min()'d against anything)

    # --- Loop 2100A, NM1*IL / current member ---
    current_last_name: str | None = field(default=None, repr=False)  # NM103
    current_first_name: str | None = field(default=None, repr=False)  # NM104
    current_middle_name: str | None = field(default=None, repr=False)  # NM105
    current_name_prefix: str | None = field(default=None, repr=False)  # NM106
    current_name_suffix: str | None = field(default=None, repr=False)  # NM107
    current_id_qualifier: str | None = None  # NM108, '34' = SSN
    current_id_code: str | None = field(default=None, repr=False)  # NM109

    # --- Loop 2100A, DMG (current) ---
    birth_date: date | None = field(default=None, repr=False)  # DMG02
    gender_code: str | None = None  # DMG03, F/M/U
    marital_status_code: str | None = None  # DMG04

    # --- Loop 2100A, N3/N4 (residence address) ---
    address_line_1: str | None = field(default=None, repr=False)  # N301
    address_line_2: str | None = field(default=None, repr=False)  # N302
    city: str | None = field(default=None, repr=False)  # N401
    state_code: str | None = None  # N402
    postal_code: str | None = field(default=None, repr=False)  # N403
    country_code: str | None = None  # N404

    # --- Loop 2100A, PER (repeatable) ---


    # --- Loop 2100B, NM1*70 / prior member (name-change tracking) ---
    prior_last_name: str | None = field(default=None, repr=False)  # NM103
    prior_first_name: str | None = field(default=None, repr=False)  # NM104
    prior_middle_name: str | None = field(default=None, repr=False)  # NM105
    prior_id_qualifier: str | None = None  # NM108
    prior_id_code: str | None = field(default=None, repr=False)  # NM109

    # --- Loop 2100B, DMG (prior) ---
    prior_birth_date: date | None = field(default=None, repr=False)  # DMG02
    prior_gender_code: str | None = None  # DMG03

    # --- Loop 2300 / 2310 ---


    # --- Provenance ---
    ordinal: int = 0  # position of the INS segment in the interchange