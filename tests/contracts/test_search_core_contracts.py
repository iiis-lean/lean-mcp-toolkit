from lean_mcp_toolkit.contracts.search_core import (
    MathlibDeclFindRequest,
    MathlibDeclFindResponse,
    MathlibDeclGetRequest,
    MathlibDeclGetResponse,
    MathlibDeclSummaryItem,
)


def test_mathlib_decl_find_request_roundtrip() -> None:
    req = MathlibDeclFindRequest.from_dict(
        {
            "query": "Nat.succ",
            "limit": 5,
            "rerank_top": 20,
            "packages": ["Mathlib"],
            "include_source_text": True,
        }
    )
    dumped = req.to_dict()
    assert dumped["query"] == "Nat.succ"
    assert dumped["limit"] == 5
    assert dumped["packages"] == ["Mathlib"]
    assert dumped["include_source_text"] is True



def test_mathlib_decl_responses_roundtrip() -> None:
    item = MathlibDeclSummaryItem(
        id=1,
        name="Nat.succ",
        module="Mathlib.Init",
        docstring="doc",
        source_text="def ...",
        source_link="https://example.com",
        dependencies="[]",
        informalization="succ",
    )
    find_resp = MathlibDeclFindResponse(
        query="Nat.succ",
        count=1,
        processing_time_ms=12,
        results=(item,),
    )
    loaded_find = MathlibDeclFindResponse.from_dict(find_resp.to_dict())
    assert loaded_find.count == 1
    assert loaded_find.results[0].name == "Nat.succ"

    get_resp = MathlibDeclGetResponse(found=True, item=item)
    loaded_get = MathlibDeclGetResponse.from_dict(get_resp.to_dict())
    assert loaded_get.found is True
    assert loaded_get.item is not None
    assert loaded_get.item.id == 1



def test_mathlib_decl_get_request_roundtrip() -> None:
    req = MathlibDeclGetRequest.from_dict({"declaration_id": 42, "include_module": False})
    dumped = req.to_dict()
    assert dumped["declaration_id"] == 42
    assert dumped["include_module"] is False
