def test_package_import_exposes_metadata_contract():
    import smartanalyticsinvest

    assert smartanalyticsinvest.__name__ == "smartanalyticsinvest"
    assert isinstance(smartanalyticsinvest.__version__, str)
    assert smartanalyticsinvest.__version__
