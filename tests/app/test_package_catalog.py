from nwbforge.app.packages.catalog import route_dependencies_available


def test_route_dependencies_available_checks_curated_modules(monkeypatch) -> None:
    monkeypatch.setattr(
        "nwbforge.app.packages.catalog.find_spec",
        lambda module_name: object()
        if module_name
        in {"sleap_io", "ndx_pose", "cv2", "roiextractors", "tifffile", "ndx_events", "spikeinterface"}
        else None,
    )

    assert route_dependencies_available("sleap") is True
    assert route_dependencies_available("lightningpose") is True
    assert route_dependencies_available("medpc") is True
    assert route_dependencies_available("micromanager") is True
    assert route_dependencies_available("thor") is True
    assert route_dependencies_available("intan") is True
    assert route_dependencies_available("scanimage") is True
    assert route_dependencies_available("hdf5") is False
