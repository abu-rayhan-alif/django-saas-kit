import pytest
from django.conf import settings as dj_settings

@pytest.mark.django_db
def test_schema_debug_no_fixtures():
    from django.test import Client
    # Test without using the settings fixture at all  
    print("django.conf.settings.DEBUG:", dj_settings.DEBUG)
    wrapped = dj_settings._wrapped
    print("_wrapped type:", type(wrapped).__name__)
    default = getattr(wrapped, "default_settings", None)
    if default:
        print("default type:", type(default).__name__)
        dd = getattr(default, "default_settings", None)
        if dd:
            print("dd type:", type(dd).__name__)
            print("dd.DEBUG:", getattr(dd, "DEBUG", "N/A"))
    
    # Check if DEBUG is explicitly overridden somewhere
    import sys
    test_mod = sys.modules.get("config.settings.test")
    print("test_mod.DEBUG:", getattr(test_mod, "DEBUG", "N/A") if test_mod else "N/A")
    
    # Also check global_settings
    from django.conf import global_settings
    print("global_settings.DEBUG:", global_settings.DEBUG)
    
    assert False, "diagnostic"
