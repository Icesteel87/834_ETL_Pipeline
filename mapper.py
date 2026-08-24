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



def map_ins(seg: list[str]) -> dict:
    return {
        "subscriber":        seg[1] == "Y",
        "relationship":      RELATIONSHIP.get(seg[2], seg[2]),
        "maintenance_type":  MAINTENANCE.get(seg[3], seg[3]),
    }


def map_nm1(seg: list[str]) -> dict:
    return {
        "last_name":  seg[3],
        "first_name": seg[4],
        "middle":     seg[5] if len(seg) > 5 else None,
        "ssn":        seg[9] if len(seg) > 9 else None,
    }


def map_dtps(segs: list[list[str]]) -> dict:
    # Multiple DTP segments collapse into a single dict keyed by qualifier
    return {
        DTP_QUAL.get(s[1], s[1]): s[3]
        for s in segs
    }


def map_hd(seg: list[list[str]]) -> dict:
    return {
        "Coverage Type": seg[3] if len(seg) > 3 else None,
        "Coverage Description": seg[4] if len(seg) > 4 else None,
    }


def map_dmg(segs: list[list[str]]) -> dict:
    return {
        "Birth Date": f'{segs[2][4:8]}{segs[2][0:4]}' if len(segs) > 3 else None,
    }


def map_ref(segs: list[list[str]]) -> dict:
    return{
        REF_QUALIFIER.get(s[1], s[1]): s[2]
        for s in segs
    }

def map_member(loop: dict) -> dict:
    return {
        **map_ins(loop["ins"]),
        **map_nm1(loop["nm1"]),
        "dates":    map_dtps(loop["dtps"]),
        "refs":     map_ref(loop["refs"]),  # {"0F": "MEM001", ...}
        "coverage": map_hd(loop["hd"]) if loop["hd"] else None,
        "dob":      map_dmg(loop["dmg"]) if loop["dmg"] else None,
    }



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

