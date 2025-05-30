
# ------------------------------------------------------------------------------
# Copyright (c) 2024 EncodingHouse Team. All Rights Reserved.
# ------------------------------------------------------------------------------

import xml.etree.ElementTree as ET
from xml.dom import minidom
import pandas as pd
from datetime import datetime
import re

def to_str(v):
    if pd.isna(v):
        return ""
    v_str = str(v)
    return v_str[:-2] if v_str.endswith(".0") else v_str

def to_date_string(v):
    try:
        if isinstance(v, float):
            v = str(int(v))
        v = str(v).replace(".", "-")
        dt = datetime.strptime(v, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except:
        return to_str(v)

def collect_multilingual_names(df, role_column):
    lang_map = {}
    for _, row in df.iterrows():
        lang = to_str(row.get("Language")) or to_str(row.get("language"))
        name = to_str(row.get(role_column)) or to_str(row.get(role_column.lower()))
        if name:
            lang_map[lang] = name
    return lang_map

def highlight_invalid_xml(xml_string):
    try:
        ET.fromstring(xml_string)
        return xml_string
    except ET.ParseError as e:
        error_msg = str(e)
        match = re.search(r'line (\d+), column (\d+)', error_msg)
        lines = xml_string.splitlines()
        highlighted = []
        for i, line in enumerate(lines, start=1):
            prefix = f"{i:4d}: "
            if match and i == int(match.group(1)):
                highlighted.append(f"<span style='color:red'>{prefix}{line}</span>")
            else:
                highlighted.append(f"{prefix}{line}")
        return f"<div><strong style='color:red'>Invalid XML:</strong> {error_msg}</div><pre style='white-space:pre-wrap;'>" + "\n".join(highlighted) + "</pre>"

def validate_summary_length(df: pd.DataFrame):
    errors = []
    for i, row in df.iterrows():
        summary190 = to_str(row.get("Summary190")) or to_str(row.get("summary190"))
        summary400 = to_str(row.get("Summary400")) or to_str(row.get("summary400"))
        if len(summary190) > 190:
            errors.append((i + 2, "Summary190", len(summary190)))
        if len(summary400) > 400:
            errors.append((i + 2, "Summary400", len(summary400)))
    return errors

def generate_mec_xml_from_dataframe(df: pd.DataFrame):
    nsmap = {
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xmlns:md": "http://www.movielabs.com/schema/md/v2.6/md",
        "xmlns:mdmec": "http://www.movielabs.com/schema/mdmec/v2.6",
        "xsi:schemaLocation": "http://www.movielabs.com/schema/mdmec/v2.6/mdmec-v2.6.xsd"
    }

    root = ET.Element("mdmec:CoreMetadata", nsmap)
    base = df.iloc[0]
    work_type = to_str(base.get("WorkType") or base.get("worktype")).strip().lower()

    basic = ET.SubElement(root, "mdmec:Basic", {
        "ContentID": f"md:cid:org:{to_str(base.get('ContentID') or base.get('contentid'))}"
    })

    for _, row in df.iterrows():
        lang = to_str(row.get("Language") or row.get("language"))
        if not lang:
            continue

        loc = ET.SubElement(basic, "md:LocalizedInfo", {"language": lang})
        ET.SubElement(loc, "md:TitleDisplayUnlimited").text = to_str(row.get("Title") or row.get("title"))
        ET.SubElement(loc, "md:TitleSort")

        for tag in ["boxart", "cover", "hero", "poster"]:
            path = to_str(row.get(tag))
            if path:
                if tag == "boxart":
                    res = "1920x2560" if work_type == "movie" else "2560x1920"
                elif tag == "poster":
                    res = "2000x3000"
                elif tag == "cover" and work_type == "episode":
                    res = "1920x1080"
                else:
                    res = "3840x2160"

                ET.SubElement(loc, "md:ArtReference", {
                    "resolution": res,
                    "purpose": tag
                }).text = path

        ET.SubElement(loc, "md:Summary190").text = to_str(row.get("Summary190") or row.get("summary190"))
        ET.SubElement(loc, "md:Summary400").text = to_str(row.get("Summary400") or row.get("summary400"))

        genre_cols = [col for col in df.columns if col.lower().startswith("genre")]
        for col in genre_cols:
            genre_id = to_str(row.get(col))
            if genre_id:
                ET.SubElement(loc, "md:Genre", {"id": genre_id}).text = " "

    ET.SubElement(basic, "md:ReleaseYear").text = to_str(base.get("ReleaseYear") or base.get("releaseyear"))
    ET.SubElement(basic, "md:ReleaseDate").text = to_date_string(base.get("ReleaseDate") or base.get("releasedate"))
    ET.SubElement(basic, "md:WorkType").text = to_str(base.get("WorkType") or base.get("worktype"))

    alt = ET.SubElement(basic, "md:AltIdentifier")
    ET.SubElement(alt, "md:Namespace").text = "ORG"
    ET.SubElement(alt, "md:Identifier").text = to_str(base.get("AltID_ORG") or base.get("altid_org"))

    rating_set = ET.SubElement(basic, "md:RatingSet")
    ratings = to_str(base.get("RatingInfo") or base.get("ratinginfo")).split(";")
    for r in ratings:
        parts = r.strip().split(":")
        if len(parts) == 3:
            country, system, value = parts
            rating = ET.SubElement(rating_set, "md:Rating")
            region = ET.SubElement(rating, "md:Region")
            ET.SubElement(region, "md:country").text = country
            ET.SubElement(rating, "md:System").text = system
            ET.SubElement(rating, "md:Value").text = value

    roles = ["Director", "Writer"] + [f"Actor{i}" for i in range(1, 7)]
    billing_counters = {"Director": 1, "Writer": 1, "Actor": 1}
    for role in roles:
        lang_map = collect_multilingual_names(df, role)
        if lang_map:
            person = ET.SubElement(basic, "md:People")
            job = ET.SubElement(person, "md:Job")
            func = "Actor" if "Actor" in role else role
            ET.SubElement(job, "md:JobFunction").text = func
            ET.SubElement(job, "md:BillingBlockOrder").text = str(billing_counters[func])
            billing_counters[func] += 1
            name_tag = ET.SubElement(person, "md:Name")
            for lang, name in lang_map.items():
                ET.SubElement(name_tag, "md:DisplayName", {"language": lang}).text = name

    ET.SubElement(basic, "md:OriginalLanguage").text = to_str(base.get("OriginalLanguage"))
    ET.SubElement(basic, "md:AssociatedOrg", {
        "organizationID": to_str(base.get("OrgID")),
        "role": "licensor"
    })

    if work_type in ["season", "episode"]:
        seq = to_str(base.get("SequenceNumber"))
        parent_id = to_str(base.get("ParentContentID"))
        if seq:
            seq_info = ET.SubElement(basic, "md:SequenceInfo")
            ET.SubElement(seq_info, "md:Number").text = seq
        if parent_id:
            rel = "isseasonof" if work_type == "season" else "isepisodeof"
            parent = ET.SubElement(basic, "md:Parent", {"relationshipType": rel})
            ET.SubElement(parent, "md:ParentContentID").text = f"md:cid:org:{parent_id}"

    credit = ET.SubElement(root, "mdmec:CompanyDisplayCredit")
    ET.SubElement(credit, "md:DisplayString", {"language": "en-US"}).text = to_str(base.get("DisplayString"))

    xml_str = ET.tostring(root, encoding="utf-8")
    return minidom.parseString(xml_str).toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

def is_valid_xml_structure(xml_string: str) -> bool:
    try:
        ET.fromstring(xml_string)
        return True
    except ET.ParseError:
        return False
