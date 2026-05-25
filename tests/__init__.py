import threading

# Thread-local flag; set to .active=True to prevent conftest's post_save
# signal from auto-assigning users to the test tenant.
suppress_auto_tenant = threading.local()
