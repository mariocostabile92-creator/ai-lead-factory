from backend.services.sales_pack import build_sales_pack, score_prospect


def test_score_prospect_is_deterministic() -> None:
    item = {
        "title": "Studio Demo",
        "source": "Google Places",
        "address": "Via Roma 1, Como",
        "phone": "031 123456",
        "website": "https://example.com",
        "maps_url": "https://maps.google.com/?cid=1",
        "rating": "4.6 (12 recensioni)",
    }

    first = score_prospect(item, "Como")
    second = score_prospect(item, "Como")

    assert first == second
    assert first["target_score"] == 10
    assert first["score_label"] == "Target forte"


def test_sales_pack_contains_messages_without_inventing_contacts() -> None:
    item = {
        "title": "Studio Demo",
        "url": "https://example.com/studio",
        "source": "Google Places",
        "address": "Via Roma 1, Como",
        "phone": "",
        "website": "",
        "maps_url": "https://maps.google.com/?cid=1",
        "rating": "",
    }

    pack = build_sales_pack(
        item=item,
        business_name="Demo SRL",
        sector="impianti elettrici",
        location="Como",
        target="studi tecnici",
    )

    assert pack["name"] == "Studio Demo"
    assert pack["phone"] == ""
    assert pack["website"] == ""
    assert pack["maps_url"] == "https://maps.google.com/?cid=1"
    assert pack["target_score"] >= 1
    assert "Oggetto:" not in pack["email_body"]
    assert "Demo SRL" in pack["email_body"]
    assert "Studio Demo" in pack["whatsapp_message"]
    assert pack["status"] == "Da contattare"
