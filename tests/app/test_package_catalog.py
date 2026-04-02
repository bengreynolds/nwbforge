from nwbforge.app.packages.catalog import route_dependencies_available


def test_route_dependencies_available_checks_curated_modules(monkeypatch) -> None:
    monkeypatch.setattr(
        "nwbforge.app.packages.catalog.find_spec",
        lambda module_name: object()
        if module_name
        in {
            "h5py",
            "isx",
            "lxml",
            "MEArec",
            "ndx_fiber_photometry",
            "ndx_ophys_devices",
            "natsort",
            "pymatreader",
            "scipy",
            "sleap_io",
            "sonpy",
            "ndx_pose",
            "cv2",
            "roiextractors",
            "tdt",
            "tifffile",
            "ndx_events",
            "spikeinterface",
            "pyedflib",
        }
        else None,
    )

    assert route_dependencies_available("alphaomega") is True
    assert route_dependencies_available("axon") is True
    assert route_dependencies_available("axona") is True
    assert route_dependencies_available("biocam") is True
    assert route_dependencies_available("blackrock") is True
    assert route_dependencies_available("cellexplorer") is True
    assert route_dependencies_available("brukertiff") is True
    assert route_dependencies_available("caiman") is True
    assert route_dependencies_available("cnmfe") is True
    assert route_dependencies_available("sleap") is True
    assert route_dependencies_available("lightningpose") is True
    assert route_dependencies_available("medpc") is True
    assert route_dependencies_available("edf") is True
    assert route_dependencies_available("extract") is True
    assert route_dependencies_available("femtonics") is True
    assert route_dependencies_available("inscopix") is True
    assert route_dependencies_available("mcsraw") is True
    assert route_dependencies_available("maxone") is True
    assert route_dependencies_available("mearec") is True
    assert route_dependencies_available("micromanager") is True
    assert route_dependencies_available("neuralynx") is True
    assert route_dependencies_available("neuroscope") is True
    assert route_dependencies_available("thor") is True
    assert route_dependencies_available("intan") is True
    assert route_dependencies_available("kilosort") is True
    assert route_dependencies_available("openephys_binary") is True
    assert route_dependencies_available("openephys_legacy") is True
    assert route_dependencies_available("plexon") is True
    assert route_dependencies_available("plexon2") is True
    assert route_dependencies_available("phy") is True
    assert route_dependencies_available("scanbox") is True
    assert route_dependencies_available("scanimage") is True
    assert route_dependencies_available("scanimage_legacy") is True
    assert route_dependencies_available("spike2") is True
    assert route_dependencies_available("spikegadgets") is True
    assert route_dependencies_available("spikeglx") is True
    assert route_dependencies_available("tdt") is True
    assert route_dependencies_available("tdt_fiber_photometry") is True
    assert route_dependencies_available("tiff") is True
    assert route_dependencies_available("whitematter") is True
    assert route_dependencies_available("hdf5") is True
    assert route_dependencies_available("suite2p") is True
    assert route_dependencies_available("image") is False
